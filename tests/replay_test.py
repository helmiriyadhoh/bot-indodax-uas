"""Tes offline: putar ulang data historis lewat tick() dengan exchange palsu, lalu cocokkan dengan backtest.
Tidak butuh internet. Jalankan:  python tests/replay_test.py"""
import sys, json, re, collections
sys.path.insert(0, ".")
import numpy as np
from core import params as P
from core.bot import tick, Env, LOG_KEY, KILL_KEY
from core.store import MemStore
from backtest.run_backtest import load, run

TF = P.TIMEFRAME_SEC
D = {p: load(p) for p in P.UNIVERSE}; T = D["BTCIDR"]["t"]; N = len(T)
HALF = 0.0005   # spread palsu 0,1%

def make_env(clock, store, environ=None):
    def get(url, on_err=None):
        sts = clock["ts"]
        if "server_time" in url: return {"server_time": sts}
        if "history_v2" in url:
            p = re.search(r"symbol=(\w+)", url).group(1); d = D[p]
            m = d["t"] <= sts   # termasuk bar yang masih berjalan (harus dibuang oleh bot)
            return {k: d[k][m].tolist() for k in "tohlcv"}
        p = url.rsplit("/", 1)[1].upper(); d = D[p]; k = int(np.searchsorted(d["t"], sts, side="right") - 1)
        mid = float(d["o"][k])   # open bar yang sedang berjalan = harga pasar saat bot dipanggil
        return {"buy": [[mid * (1 - HALF - j * 1e-5), 2e8 / mid] for j in range(20)], "sell": [[mid * (1 + HALF + j * 1e-5), 2e8 / mid] for j in range(20)]}
    return Env(get, store, lambda: clock["ts"], environ or {})

def replay(k0, k1, store=None, double=True, pre=None):
    store = store or MemStore(); clock = {"ts": 0}; env = make_env(clock, store)
    for k in range(k0, k1):
        if pre: pre(k, store)
        clock["ts"] = int(T[k] + TF + 420); tick(env)
        if double: tick(env); clock["ts"] += 7200; tick(env)     # panggilan ganda + panggilan di tengah bar
    return store

def logs(store): return [json.loads(x) for x in store.lists.get(LOG_KEY, [])]

if __name__ == "__main__":
    k0, k1 = N - 700, N - 1
    st = replay(k0, k1); L = logs(st)
    bot_sig = {(e["bar_t"], e["pair"]): e["action"] for e in L if e["kind"] == "signal"}
    res = run(int(T[k0] + TF), int(T[k1 - 1] + TF) + 1, {p: 0.1 for p in P.UNIVERSE}, {p: 0.0 for p in P.UNIVERSE})
    bt_sig = {(t, p): a for t, p, a, _ in res["sigs"]}
    common = set(bot_sig) & set(bt_sig); diff = [k for k in common if bot_sig[k] != bt_sig[k]]
    act = [k for k in common if bt_sig[k] in ("ENTER", "EXIT")]
    print(f"bar-sinyal dibandingkan: {len(common)} | ENTER/EXIT backtest: {len(act)} | berbeda: {len(diff)}")
    for k in sorted(diff)[:8]: print("  beda", k, "bot:", bot_sig[k], "bt:", bt_sig[k])
    orders = [e for e in L if e["kind"] == "order"]
    print("order bot:", len(orders), "| order backtest:", len(res["orders"]))
    cnt = collections.Counter(e["kind"] for e in L); print("jenis log:", dict(cnt))
    # idempotency: tiap (pair, bar) hanya satu sinyal dan tidak ada BUY ganda
    dup = [k for k, v in collections.Counter((e["bar_t"], e["pair"]) for e in L if e["kind"] == "signal").items() if v > 1]
    print("sinyal ganda untuk candle sama:", len(dup))
    # kill switch
    st2 = replay(k0, k1, pre=lambda k, s: s.set(KILL_KEY, "1")); L2 = logs(st2)
    print("kill switch -> BUY:", sum(1 for e in L2 if e["kind"] == "order" and e["side"] == "BUY"), "| entry_blocked:", sum(1 for e in L2 if e["kind"] == "entry_blocked"))
    # daily loss limit dipaksa
    old = P.DAILY_LOSS_LIMIT; P.DAILY_LOSS_LIMIT = -1.0
    st3 = replay(k0, k1, double=False); L3 = logs(st3); P.DAILY_LOSS_LIMIT = old
    print("daily loss limit dipaksa -> BUY:", sum(1 for e in L3 if e["kind"] == "order" and e["side"] == "BUY"), "| log daily_loss_limit:", sum(1 for e in L3 if e["kind"] == "daily_loss_limit"))
    err = [e for e in L if e["kind"] == "error"]; print("error:", len(err), err[:2])
