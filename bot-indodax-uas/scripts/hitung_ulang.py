"""hitung_ulang: menghasilkan SEMUA angka dashboard dari log mentah + candle + backtest. Tidak ada angka ditulis manual.
Pakai:  python scripts/hitung_ulang.py [--dir data/forward] [--keluar out/angka_dashboard.json]
Syarat: data/candles harus mencakup jendela forward + minimal 1 bar sesudahnya (jalankan scripts/tarik_data_indodax.py lagi
        >= 4 jam setelah forward test selesai)."""
import sys, json, argparse, collections, statistics as st, datetime as dt, glob
sys.path.insert(0, ".")
import numpy as np
from core import params as P
from backtest.run_backtest import run, metrics, load
from backtest.costs import estimate_snaps, load as load_snaps

TF = P.TIMEFRAME_SEC
iso = lambda ts: dt.datetime.fromtimestamp(ts, dt.UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
def jl(path): return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]

def fwd_metrics(L, orders):
    """Metrik forward dari log: trade dipasangkan BUY -> SELL per pasangan."""
    eq = [(e["ts"], e["equity"]) for e in L if e["kind"] == "call_end"]
    series = [P.INITIAL_CAPITAL] + [x for _, x in eq]
    peak, mdd = series[0], 0.0
    for x in series: peak = max(peak, x); mdd = max(mdd, (peak - x) / peak)
    openb, trades = {}, []
    for o in sorted(orders, key=lambda o: o["ts"]):
        mid = (o["best_bid"] + o["best_ask"]) / 2
        spread_c = o["qty"] * (o["best_ask"] - o["best_bid"]) / 2
        slip_c = o["qty"] * ((o["avg_fill"] - o["best_ask"]) if o["side"] == "BUY" else (o["best_bid"] - o["avg_fill"]))
        c = {"fee": o["fee"], "spread": spread_c, "slip": max(slip_c, 0.0)}
        if o["side"] == "BUY": openb[o["pair"]] = (o, c)
        elif o["pair"] in openb:
            b, cb = openb.pop(o["pair"])
            pnl = o["qty"] * o["avg_fill"] - o["fee"] - (b["qty"] * b["avg_fill"] + b["fee"])
            costs = sum(c.values()) + sum(cb.values())
            trades.append({"pair": o["pair"], "pnl": pnl, "costs": costs, "fee": c["fee"] + cb["fee"], "spread": c["spread"] + cb["spread"],
                           "slip": c["slip"] + cb["slip"], "entry_ts": b["ts"], "exit_ts": o["ts"]})
    wins = [t["pnl"] for t in trades if t["pnl"] > 0]; loss = [t["pnl"] for t in trades if t["pnl"] <= 0]
    costs = sum(t["costs"] for t in trades); gross = sum(t["pnl"] for t in trades) + costs
    final = series[-1]
    return {"return_total_pct": (final / P.INITIAL_CAPITAL - 1) * 100, "max_drawdown_pct": mdd * 100,
            "profit_factor": (sum(wins) / -sum(loss)) if loss and sum(loss) != 0 else None,
            "win_rate_pct": 100 * len(wins) / len(trades) if trades else None,
            "avg_win": float(np.mean(wins)) if wins else None, "avg_loss": float(np.mean(loss)) if loss else None, "n_trades": len(trades),
            "biaya_total_idr": costs, "biaya_fee": sum(t["fee"] for t in trades), "biaya_spread": sum(t["spread"] for t in trades),
            "biaya_slippage": sum(t["slip"] for t in trades), "laba_kotor_idr": gross,
            "porsi_biaya_pct_dari_laba_kotor": 100 * costs / gross if gross > 0 else None, "final_equity": final,
            "posisi_terbuka_akhir": list(openb)}, [{"ts": t, "equity": x} for t, x in eq], trades

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dir", default="data/forward"); ap.add_argument("--keluar", default="out/angka_dashboard.json")
    ap.add_argument("--interval", type=int, default=900, help="selang jadwal penjadwal (detik)")
    a = ap.parse_args()
    L = jl(f"{a.dir}/log.jsonl"); snaps_f = jl(f"{a.dir}/snap.jsonl") if glob.glob(f"{a.dir}/snap.jsonl") else []
    calls = [e for e in L if e["kind"] == "call"]; sigs = [e for e in L if e["kind"] == "signal"]; orders = [e for e in L if e["kind"] == "order"]
    if not calls or not sigs: sys.exit("Log belum berisi panggilan/sinyal.")
    t0, t1 = min(e["ts"] for e in calls), max(e["ts"] for e in L)
    summ = json.load(open("out/backtest_summary.json")); spread0, slip0 = summ["spread"], summ["slip"]
    D = {p: load(p) for p in P.UNIVERSE}; T = D[P.UNIVERSE[0]]["t"]

    # ---- forward ----
    fm, feq, ftrades = fwd_metrics(L, orders)
    # B&H BTC pada jendela yang sama dari snapshot mentah
    bt_s = sorted((s for s in snaps_f if s["pair"].lower() == "btcidr"), key=lambda s: s["waktu_server_ms"])
    mid = lambda s: (s["bid"] + s["ask"]) / 2
    bh = (mid(bt_s[-1]) / mid(bt_s[0]) - 1) * 100 if len(bt_s) >= 2 else None

    # ---- backtest dijalankan ulang pada jendela forward dgn candle yang sama ----
    bars = sorted({e["bar_t"] for e in sigs}); w_start, w_end = bars[0] + TF, bars[-1] + TF
    if w_end + TF > T[-1] + TF: print("PERINGATAN: candle belum mencakup 1 bar setelah jendela; unduh data lagi.")
    res = run(w_start, w_end, spread0, slip0); bw = metrics(res, w_start, w_end)
    bw.pop("cagr_pct", None)
    # ---- backtest penuh 3 tahun (yang dibekukan) ----
    res_full = run(summ["start"], summ["end"], spread0, slip0); bfull = metrics(res_full, summ["start"], summ["end"])
    bfull["buy_hold_btc_return_pct"] = summ["metrics"]["buy_hold_btc_return_pct"]

    # ---- kecocokan sinyal candle demi candle ----
    bot = {(e["bar_t"], e["pair"]): e["action"] for e in sigs}; bts = {(t, p): x for t, p, x, _ in res["sigs"]}
    common = sorted(set(bot) & set(bts)); diff = [k for k in common if bot[k] != bts[k]]
    miss = sorted(set(bts) - set(bot)); extra = sorted(set(bot) - set(bts))
    act_keys = [k for k in common if bts[k] in ("ENTER", "EXIT") or bot[k] in ("ENTER", "EXIT")]
    sig_match = {"bar_dibandingkan": len(common), "cocok": len(common) - len(diff), "cocok_pct": 100 * (len(common) - len(diff)) / len(common) if common else None,
                 "aksi_entry_exit": len(act_keys), "aksi_entry_exit_cocok": sum(1 for k in act_keys if bot[k] == bts[k]),
                 "tidak_diproses_bot": len(miss), "hanya_di_bot": len(extra),
                 "selisih": [{"bar": iso(k[0]), "pair": k[1], "bot": bot[k], "backtest": bts[k]} for k in diff[:50]]}

    # ---- selisih harga fill per order ----
    sigev = {(e["bar_t"], e["pair"]): e for e in sigs}
    btord = {(t - TF, p, s): (q, fill) for t, p, s, q, fill, f in res["orders"]}
    fills = []
    for o in orders:
        k = (o["bar_t"], o["pair"], o["side"]); sgn = 1 if o["side"] == "BUY" else -1
        row = {"waktu": iso(o["ts"]), "pair": o["pair"], "sisi": o["side"], "fill_bot": o["avg_fill"], "harga_sinyal": o["signal_px"],
               "best_bid": o["best_bid"], "best_ask": o["best_ask"], "terlambat_detik": sigev.get((o["bar_t"], o["pair"]), {}).get("terlambat_detik"),
               "spread_live_pct": (o["best_ask"] - o["best_bid"]) / ((o["best_ask"] + o["best_bid"]) / 2) * 100, "fill_backtest": None}
        if k in btord:
            bf = btord[k][1]; row["fill_backtest"] = bf; row["selisih_merugikan_pct"] = sgn * (o["avg_fill"] / bf - 1) * 100
            i = int(np.searchsorted(D[o["pair"]]["t"], o["bar_t"])); open_next = D[o["pair"]]["o"][i + 1] if i + 1 < len(T) else None
            if open_next:
                midl = (o["best_bid"] + o["best_ask"]) / 2
                touch = o["best_ask"] if sgn == 1 else o["best_bid"]
                row["komp_keterlambatan_pct"] = sgn * (midl / open_next - 1) * 100
                row["komp_spread_pct"] = ((o["best_ask"] - o["best_bid"]) / 2 / midl - spread0[o["pair"]] / 200) * 100
                row["komp_slippage_pct"] = (abs(o["avg_fill"] - touch) / touch - slip0[o["pair"]] / 100) * 100
                row["sisa_pct"] = row["selisih_merugikan_pct"] - row["komp_keterlambatan_pct"] - row["komp_spread_pct"] - row["komp_slippage_pct"]
        fills.append(row)
    diffs = [r["selisih_merugikan_pct"] for r in fills if "selisih_merugikan_pct" in r]

    # ---- spread: yang dipakai backtest vs seluruh snapshot ----
    allsn = load_snaps("data/snapshots.jsonl")
    for s in snaps_f: allsn.setdefault(s["pair"].upper(), []).append(s)
    est_all = estimate_snaps(allsn, P.INITIAL_CAPITAL * P.POS_FRAC)
    spread_cmp = [{"pair": p, "spread_dipakai_backtest_pct": spread0[p], "spread_semua_snapshot_pct": est_all[p]["spread_pct_median"],
                   "slippage_dipakai_pct": slip0[p], "slippage_semua_snapshot_pct": est_all[p]["slippage_pct_median"], "n_snapshot": est_all[p]["n_snapshot"]} for p in P.UNIVERSE]

    # ---- operasional ----
    cnt = collections.Counter(e["kind"] for e in L)
    err_stage = collections.Counter(e.get("stage", "?") for e in L if e["kind"] == "error")
    expected = int((t1 - t0) // a.interval) + 1
    done_bar = collections.defaultdict(lambda: None)
    for e in sigs:
        k = (e["bar_t"], e["pair"]); done_bar[k] = e["ts"] if done_bar[k] is None else min(done_bar[k], e["ts"])
    all_bars = [(int(t), p) for p in P.UNIVERSE for t in T if t + TF > t0 and t + 2 * TF <= t1]
    on_time = sum(1 for k in all_bars if done_bar.get(k) is not None and done_bar[k] <= k[0] + 2 * TF)
    late_list = [e["terlambat_detik"] for e in sigs if e.get("terlambat_detik") is not None]
    ops = {"panggilan_terjadwal_seharusnya": expected, "panggilan_terlaksana": cnt["call"], "panggilan_dilewati_lock": cnt["skip_lock"],
           "candle_pair_total": len(all_bars), "candle_pair_tepat_waktu": on_time, "uptime_pct": 100 * on_time / len(all_bars) if all_bars else None,
           "error_total": cnt["error"], "error_per_tahap": dict(err_stage), "kill_switch_event": cnt["kill_switch"], "daily_loss_limit_event": cnt["daily_loss_limit"],
           "entry_diblokir": dict(collections.Counter(e["alasan"] for e in L if e["kind"] == "entry_blocked")), "idempotent_skip": cnt["idempotent_skip"],
           "invalid_data": dict(collections.Counter(e["alasan"] for e in L if e["kind"] == "invalid_data")),
           "keterlambatan_median_detik": float(np.median(late_list)) if late_list else None, "keterlambatan_maks_detik": max(late_list) if late_list else None,
           "definisi_uptime": "candle(pair) terproses sebelum candle berikutnya ditutup / jumlah candle(pair) selama forward test"}

    out = {"dibuat_utc": dt.datetime.now(dt.UTC).strftime("%Y-%m-%d %H:%M:%S"), "strategi": P.STRATEGY_NAME, "universe": P.UNIVERSE, "fee_taker_pct": P.FEE_TAKER_PCT,
           "jendela": {"panggilan_pertama": iso(t0), "log_terakhir": iso(t1), "durasi_hari": (t1 - t0) / 86400, "bar_pertama": iso(bars[0]), "bar_terakhir": iso(bars[-1]), "jumlah_bar": len(bars)},
           "backtest_3tahun": bfull, "backtest_jendela_forward": bw,
           "forward": {**fm, "buy_hold_btc_return_pct": bh},
           "gap": {"return_forward_pct": fm["return_total_pct"], "return_backtest_jendela_pct": bw["return_total_pct"], "gap_pct_poin": fm["return_total_pct"] - bw["return_total_pct"],
                   "selisih_fill_rata2_merugikan_pct": float(np.mean(diffs)) if diffs else None, "selisih_fill_maks_pct": max(diffs) if diffs else None, "order_dibandingkan": len(diffs)},
           "kecocokan_sinyal": sig_match, "fill": fills, "spread_vs_snapshot": spread_cmp, "operasional": ops,
           "equity_harian": [{"waktu": iso(e["ts"]), "equity": e["equity"]} for e in L if e["kind"] == "daily_equity"],
           "equity_forward": feq, "equity_backtest": [{"ts": t, "equity": x} for t, x in res_full["equity"]],
           "trade_forward": ftrades, "order_mentah": [{k: o[k] for k in ("ts","pair","side","qty","avg_fill","fee")} for o in orders],
           "parameter": {k: getattr(P, k) for k in dir(P) if k.isupper() and not k.startswith("_")}, "log_jumlah_baris": len(L)}
    json.dump(out, open(a.keluar, "w"), indent=1, default=float)
    print("OK ->", a.keluar); print(json.dumps({k: out[k] for k in ("jendela", "gap", "kecocokan_sinyal")}, indent=1, default=float)[:1800])

if __name__ == "__main__": main()
