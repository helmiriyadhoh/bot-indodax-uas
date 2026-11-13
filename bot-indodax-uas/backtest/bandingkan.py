import sys, json, datetime as dt
sys.path.insert(0, ".")
from core import params as P
from backtest.run_backtest import run, metrics, load
from backtest.costs import estimate
est = estimate("data/snapshots.jsonl", P.INITIAL_CAPITAL * P.POS_FRAC)
sp = {p: est[p]["spread_pct_median"] for p in P.UNIVERSE}; sl = {p: est[p]["slippage_pct_median"] for p in P.UNIVERSE}
T = load("BTCIDR")["t"]; start = int(dt.datetime(2023, 10, 8, tzinfo=dt.UTC).timestamp()); end = int(T[-1]) + P.TIMEFRAME_SEC
for typ, fast, slow in [("DONCH", 0, 0), ("EMA_CROSS", 21, 50)]:
    P.STRATEGY_TYPE = typ
    if fast: P.EMA_FAST, P.EMA_SLOW = fast, slow
    m = metrics(run(start, end, sp, sl), start, end)
    print(typ, {k: (round(m[k], 2) if isinstance(m[k], float) else m[k]) for k in ("return_total_pct", "cagr_pct", "max_drawdown_pct", "profit_factor", "win_rate_pct", "n_trades", "porsi_biaya_pct_dari_laba_kotor")})
