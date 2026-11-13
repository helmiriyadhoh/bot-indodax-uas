"""Estimasi spread & slippage dari snapshot order book mentah (median per pasangan)."""
import json, statistics as st, collections
from core import params as P
from core.execution import walk_notional

def walk(levels, notional):
    avg, qty, full = walk_notional(levels, notional)
    return avg, full

def load(path):
    S = [json.loads(l) for l in open(path) if l.strip()]
    by = collections.defaultdict(list)
    for s in S: by[s["pair"].upper()].append(s)
    return by

def estimate(path, order_notional):
    return estimate_snaps(load(path), order_notional)

def estimate_snaps(by, order_notional):
    out = {}
    for pair, snaps in by.items():
        sp, sl, partial = [], [], 0
        for s in snaps:
            bid, ask = s["bids"][0][0], s["asks"][0][0]
            mid = (bid + ask) / 2
            sp.append((ask - bid) / mid * 100)
            pb, okb = walk(s["bids"], order_notional); pa, oka = walk(s["asks"], order_notional)
            if not (okb and oka): partial += 1
            if pb and pa:
                sl.append(((pa - ask) / ask * 100 + (bid - pb) / bid * 100) / 2)  # rata2 sisi beli & jual
        out[pair] = {"n_snapshot": len(snaps), "spread_pct_median": st.median(sp),
                     "slippage_pct_median": st.median(sl) if sl else None, "snapshot_book_tidak_cukup": partial}
    return out
