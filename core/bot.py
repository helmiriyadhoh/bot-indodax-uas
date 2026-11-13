"""Satu panggilan tick: baca state -> ambil data -> sinyal -> eksekusi simulasi -> simpan state & log."""
import json, os
import numpy as np
from . import params as P
from .strategy import signal
from . import exchange as X
from .execution import walk_notional, walk_qty, floor8

WIB = 7 * 3600
STATE_KEY, LOG_KEY, SNAP_KEY, LOCK_KEY, KILL_KEY = "bot:state", "bot:log", "bot:snap", "bot:lock", "bot:kill"
SNAP_EVERY_SEC = 3300

class Env:
    """Dependensi yang bisa diganti saat tes: get(url,on_err), store, now(), environ."""
    def __init__(self, get, store, now, environ=None): self.get, self.store, self.now, self.environ = get, store, now, environ or os.environ

def _new_state():
    return {"cash": P.INITIAL_CAPITAL, "positions": {}, "processed": {}, "day_id": None, "day_start_equity": None,
            "halted_day": None, "last_snap": {}, "started_ts": None}

def tick(env):
    S, events = env.store, []
    def log(kind, **kw):
        e = {"ts": round(env.now(), 1), "kind": kind, **kw}
        events.append(e)
        try: S.rpush(LOG_KEY, json.dumps(e, default=float))
        except Exception: pass
        return e
    log("call", strategy=P.STRATEGY_NAME)
    if not S.set_nx(LOCK_KEY, "1", 240):
        log("skip_lock", msg="panggilan lain masih berjalan"); return {"ok": True, "skipped": "lock"}
    try:
        _run(env, log)
    except Exception as e:
        log("error", stage="tick_fatal", msg=repr(e)[:300])
    finally:
        S.delete(LOCK_KEY)
    return {"ok": True, "events": len(events), "orders": [e for e in events if e["kind"] == "order"],
            "errors": [e for e in events if e["kind"] == "error"][:5]}

def _run(env, log):
    S = env.store
    on_err = lambda info: log("error", stage="api_retry", **info)
    get = lambda url: env.get(url, on_err)
    kill = S.get(KILL_KEY) == "1" or env.environ.get("KILL_SWITCH") == "1"
    try: sts = X.server_time(get)
    except Exception as e:
        sts = int(env.now())   # cadangan: jam server Vercel/GitHub (sinkron NTP); dicatat di log
        log("error", stage="server_time", msg=str(e)[:300], fallback="jam_lokal", dipakai=sts)
    raw = S.get(STATE_KEY); st = json.loads(raw) if raw else _new_state()
    if st["started_ts"] is None: st["started_ts"] = sts; log("init", capital=P.INITIAL_CAPITAL, universe=P.UNIVERSE)

    # --- order book + snapshot ---
    books = {}
    for p in P.UNIVERSE:
        try:
            bids, asks = X.parse_depth(get(X.depth_url(p)))
            books[p] = (bids, asks)
            if sts - st["last_snap"].get(p, 0) >= SNAP_EVERY_SEC and bids and asks:
                st["last_snap"][p] = sts
                S.rpush(SNAP_KEY, json.dumps({"waktu_server_ms": sts * 1000, "pair": p.lower(), "bid": bids[0][0], "ask": asks[0][0],
                        "spread_pct": (asks[0][0] - bids[0][0]) / ((asks[0][0] + bids[0][0]) / 2) * 100, "bids": bids[:20], "asks": asks[:20]}))
        except Exception as e: log("error", stage="depth", pair=p, msg=str(e)[:200])

    def best_bid(p, pos):
        b = books.get(p)
        if b and b[0]: pos["last_bid"] = b[0][0][0]
        return pos.get("last_bid", pos["entry_fill"])
    equity = st["cash"] + sum(pos["qty"] * best_bid(p, pos) for p, pos in st["positions"].items())

    # --- batas hari WIB, equity harian, daily loss limit ---
    day = int((sts + WIB) // 86400)
    if st["day_id"] != day:
        st["day_id"], st["day_start_equity"] = day, equity
        log("daily_equity", day_wib=day, equity=equity)
    if equity < st["day_start_equity"] * (1 - P.DAILY_LOSS_LIMIT) and st["halted_day"] != day:
        st["halted_day"] = day; log("daily_loss_limit", equity=equity, day_start=st["day_start_equity"])
    halted = st["halted_day"] == day
    if kill: log("kill_switch", state="AKTIF", efek="tidak ada entry baru; exit tetap diproses")

    fee = P.FEE_TAKER_PCT / 100
    for p in P.UNIVERSE:
        try: c = X.parse_candles(get(X.candles_url(p, sts - 560 * P.TIMEFRAME_SEC, sts)), sts)
        except Exception as e: log("error", stage="candles", pair=p, msg=str(e)[:200]); continue
        n = len(c["t"])
        if n < P.WARMUP_BARS: log("invalid_data", pair=p, alasan="candle_kurang", n=n); continue
        i = n - 1; bar_t = int(c["t"][i])
        if bar_t <= st["processed"].get(p, 0):
            log("idempotent_skip", pair=p, bar_t=bar_t); continue
        if sts - bar_t > 2 * P.TIMEFRAME_SEC:
            log("invalid_data", pair=p, alasan="candle_tertutup_terakhir_usang", bar_t=bar_t); continue
        pos = st["positions"].get(p)
        peak = 0.0
        if pos:
            m = (c["t"] >= pos["entry_bar_t"]) & (c["t"] < bar_t)
            peak = float(c["c"][m].max()) if m.any() else pos["entry_signal_px"]
        act, why, _ = signal(c["h"], c["l"], c["c"], c["v"], c["t"], i, bool(pos), peak)
        sig_px = float(c["c"][i])
        log("signal", pair=p, bar_t=bar_t, action=act, reason=why, close=sig_px, bar_close_ts=bar_t + P.TIMEFRAME_SEC,
            terlambat_detik=int(sts - (bar_t + P.TIMEFRAME_SEC)))
        done = True
        if act in ("ENTER", "EXIT"):
            b = books.get(p)
            if not b or not b[0] or not b[1]:
                log("error", stage="order_book_kosong", pair=p); done = False          # coba lagi di panggilan berikut
            else:
                bids, asks = b; bb, ba = bids[0][0], asks[0][0]
                if act == "EXIT":
                    avg, got, full = walk_qty(bids, pos["qty"])
                    got = floor8(got) if not full else pos["qty"]
                    proceeds = got * avg; f = proceeds * fee
                    st["cash"] += proceeds - f
                    share = got / pos["qty"]; cost_part = pos["cost_total"] * share
                    log("order", pair=p, side="SELL", qty=got, best_bid=bb, best_ask=ba, avg_fill=avg, fee=f, notional=proceeds,
                        signal_px=sig_px, selisih_vs_sinyal_pct=(avg / sig_px - 1) * 100, reason=why, bar_t=bar_t)
                    if full:
                        log("trade_closed", pair=p, pnl=proceeds - f - cost_part, entry_fill=pos["entry_fill"], exit_fill=avg, entry_bar_t=pos["entry_bar_t"], exit_bar_t=bar_t)
                        del st["positions"][p]
                    else:
                        pos["qty"] -= got; pos["cost_total"] -= cost_part; done = False; log("partial_fill", pair=p, sisa=pos["qty"])
                else:  # ENTER
                    spread = (ba - bb) / ((ba + bb) / 2) * 100
                    notional = min(P.POS_FRAC * equity, st["cash"] / (1 + fee))
                    block = None
                    if kill: block = "kill_switch"
                    elif halted: block = "daily_loss_limit"
                    elif len(st["positions"]) >= P.MAX_OPEN_POSITIONS: block = "max_posisi"
                    elif spread > P.MAX_SPREAD_PCT_ENTRY: block = f"spread_{spread:.2f}pct>2"
                    elif notional < P.MIN_ORDER_IDR: block = "di_bawah_minimum_order"
                    if block:
                        log("entry_blocked", pair=p, bar_t=bar_t, alasan=block)
                    else:
                        avg, qty, full = walk_notional(asks, notional)
                        qty = floor8(qty)
                        if not full or avg is None or qty * avg < P.MIN_ORDER_IDR:
                            log("entry_blocked", pair=p, bar_t=bar_t, alasan="book_tidak_cukup")
                        else:
                            cost = qty * avg; f = cost * fee
                            st["cash"] -= cost + f
                            st["positions"][p] = {"qty": qty, "entry_fill": avg, "entry_bar_t": bar_t, "entry_signal_px": sig_px,
                                                  "cost_total": cost + f, "last_bid": bb}
                            log("order", pair=p, side="BUY", qty=qty, best_bid=bb, best_ask=ba, avg_fill=avg, fee=f, notional=cost,
                                signal_px=sig_px, selisih_vs_sinyal_pct=(avg / sig_px - 1) * 100, reason=why, bar_t=bar_t)
        if done: st["processed"][p] = bar_t
        S.set(STATE_KEY, json.dumps(st))
    equity = st["cash"] + sum(pos["qty"] * pos.get("last_bid", pos["entry_fill"]) for pos in st["positions"].values())
    log("call_end", equity=equity, cash=st["cash"], open_positions=list(st["positions"]))
    S.set(STATE_KEY, json.dumps(st))
