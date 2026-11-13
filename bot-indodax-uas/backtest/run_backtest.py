import json, sys, csv, math, datetime as dt
import numpy as np
sys.path.insert(0, ".")
from core import params as P
from core.strategy import signal
from backtest.costs import estimate

WIB = 7 * 3600
def load(pair):
    d = json.load(open(f"data/candles/{pair}_240.json"))
    return {k: np.array(d[k], dtype=float) for k in "tohlcv"}

def run(start_ts, end_ts, spread, slip, fee_pct=P.FEE_TAKER_PCT, verbose=True):
    D = {p: load(p) for p in P.UNIVERSE}
    # semua pair berbagi timeline yang sama (sudah dicek: 7122 bar, tanpa celah)
    T = D[P.UNIVERSE[0]]["t"]
    cash = P.INITIAL_CAPITAL; pos = {}; trades = []; orders = []; eq = []; sigs = []
    day_start_eq = None; cur_day = None; halted_days = 0; day_halted = False
    fee = fee_pct / 100
    for i in range(len(T) - 1):
        t_close = T[i] + P.TIMEFRAME_SEC            # bar i tertutup pada t_close; eksekusi di open bar i+1
        if t_close < start_ts or t_close > end_ts: continue
        # equity marking: posisi dinilai di bid (close bar i * (1 - half spread))
        mark = cash + sum(q["qty"] * D[p]["c"][i] * (1 - spread[p] / 200) for p, q in pos.items())
        day = int((t_close + WIB) // 86400)
        if day != cur_day:
            cur_day, day_start_eq, day_halted = day, mark, False
            eq.append((int(t_close), mark))
        if not day_halted and mark < day_start_eq * (1 - P.DAILY_LOSS_LIMIT):
            day_halted = True; halted_days += 1
        for p in P.UNIVERSE:
            d = D[p]; in_pos = p in pos
            act, why, peak = signal(d["h"], d["l"], d["c"], d["v"], d["t"], i, in_pos, pos[p]["peak"] if in_pos else 0.0)
            sigs.append((int(T[i]), p, act, why))
            if in_pos: pos[p]["peak"] = peak
            px_open = d["o"][i + 1]
            if act == "EXIT":
                half = spread[p] / 200; sl = slip[p] / 100
                fill = px_open * (1 - half - sl); q = pos[p]["qty"]
                proceeds = q * fill; f = proceeds * fee
                cash += proceeds - f
                pnl = proceeds - f - pos[p]["cost_total"]
                tr = {**pos[p], "exit_t": int(t_close), "exit_fill": fill, "exit_fee": f, "pair": p, "reason": why,
                      "exit_spread_cost": q * px_open * half, "exit_slip_cost": q * px_open * sl, "pnl": pnl}
                trades.append(tr); orders.append((int(t_close), p, "SELL", q, fill, f)); del pos[p]
            elif act == "ENTER" and not day_halted and len(pos) < P.MAX_OPEN_POSITIONS:
                half = spread[p] / 200; sl = slip[p] / 100
                notional = min(P.POS_FRAC * mark, cash / (1 + fee))
                if notional < P.MIN_ORDER_IDR: continue
                fill = px_open * (1 + half + sl); q = notional / fill; f = notional * fee
                cash -= notional + f
                pos[p] = {"entry_t": int(t_close), "entry_fill": fill, "qty": q, "peak": peak,
                          "entry_fee": f, "cost_total": notional + f,
                          "entry_spread_cost": q * px_open * half, "entry_slip_cost": q * px_open * sl}
                orders.append((int(t_close), p, "BUY", q, fill, f))
    # tutup mark akhir (tidak dipaksa jual; nilai di bid)
    i = len(T) - 1
    final = cash + sum(q["qty"] * D[p]["c"][i] * (1 - spread[p] / 200) for p, q in pos.items())
    return {"trades": trades, "orders": orders, "equity": eq, "final_equity": final, "open_positions": list(pos), "sigs": sigs, "halted_days": halted_days}

def metrics(res, start_ts, end_ts):
    tr = res["trades"]; E = [e for _, e in res["equity"]] + [res["final_equity"]]
    peak, mdd = -1, 0
    for e in E:
        peak = max(peak, e); mdd = max(mdd, (peak - e) / peak)
    yrs = (end_ts - start_ts) / (365.25 * 86400)
    ret = res["final_equity"] / P.INITIAL_CAPITAL - 1
    wins = [t["pnl"] for t in tr if t["pnl"] > 0]; losses = [t["pnl"] for t in tr if t["pnl"] <= 0]
    gross_profit = sum(wins); gross_loss = -sum(losses)
    costs = sum(t["entry_fee"] + t["exit_fee"] + t["entry_spread_cost"] + t["exit_spread_cost"] + t["entry_slip_cost"] + t["exit_slip_cost"] for t in tr)
    gross_pnl = sum(t["pnl"] for t in tr) + costs
    return {"return_total_pct": ret * 100, "cagr_pct": ((1 + ret) ** (1 / yrs) - 1) * 100, "max_drawdown_pct": mdd * 100,
            "profit_factor": gross_profit / gross_loss if gross_loss else None, "win_rate_pct": 100 * len(wins) / len(tr) if tr else None,
            "avg_win": np.mean(wins) if wins else None, "avg_loss": np.mean(losses) if losses else None, "n_trades": len(tr),
            "biaya_total_idr": costs, "laba_kotor_idr": gross_pnl, "porsi_biaya_pct_dari_laba_kotor": 100 * costs / gross_pnl if gross_pnl > 0 else None,
            "final_equity": res["final_equity"], "open_at_end": res["open_positions"], "hari_kena_daily_loss_limit": res["halted_days"]}

if __name__ == "__main__":
    est = estimate("data/snapshots.jsonl", P.INITIAL_CAPITAL * P.POS_FRAC)
    spread = {p: est[p]["spread_pct_median"] for p in P.UNIVERSE}
    slip = {p: est[p]["slippage_pct_median"] for p in P.UNIVERSE}
    print("spread/slip dari snapshot:", json.dumps({p: est[p] for p in P.UNIVERSE}, indent=1))
    T = load(P.UNIVERSE[0])["t"]
    start = int(dt.datetime(2023, 10, 8, tzinfo=dt.UTC).timestamp()); end = int(T[-1]) + P.TIMEFRAME_SEC
    res = run(start, end, spread, slip); m = metrics(res, start, end)
    btc = load("BTCIDR"); i0 = int(np.searchsorted(btc["t"], start)); bh = btc["c"][-1] / btc["o"][i0] - 1
    m["buy_hold_btc_return_pct"] = bh * 100
    print(json.dumps(m, indent=1, default=float))
    json.dump({"metrics": m, "spread": spread, "slip": slip, "start": start, "end": end}, open("out/backtest_summary.json", "w"), indent=1, default=float)
    with open("out/backtest_trades.csv", "w", newline="") as f:
        w = csv.writer(f); keys = list(res["trades"][0].keys()) if res["trades"] else []
        w.writerow(keys); [w.writerow([t[k] for k in keys]) for t in res["trades"]]
