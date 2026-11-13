"""Akses API publik Indodax (tanpa API key) dengan retry terbatas + parser."""
import json, time, urllib.request
import numpy as np
from . import params as P

BASE = "https://indodax.com"
class ApiError(Exception): pass

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
           "Accept": "application/json, text/plain, */*", "Referer": "https://indodax.com/"}

def http_json(url, retries=3, timeout=10, on_error=None, sleep=time.sleep):
    last = None
    for k in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read().decode("utf-8", "replace")
            if not body.strip(): raise ApiError("respons_kosong")
            return json.loads(body)
        except Exception as e:
            last = e
            if on_error: on_error({"url": url, "attempt": k + 1, "of": retries, "err": repr(e)[:200]})
            if k < retries - 1: sleep(min(2 ** k, 4))
    raise ApiError(f"gagal setelah {retries}x: {url}: {last!r}"[:300])

def server_time(get):
    d = get(BASE + "/api/server_time")
    v = float(d["server_time"])
    return int(v / 1000) if v > 1e12 else int(v)

def candles_url(pair, frm, to):
    return f"{BASE}/tradingview/history_v2?symbol={pair}&tf=240&from={int(frm)}&to={int(to)}"

def depth_url(pair): return f"{BASE}/api/depth/{pair.lower()}"

def parse_candles(raw, server_ts):
    """Return dict array t,o,h,l,c,v HANYA bar tertutup (Time + TF <= server_time)."""
    rows = []
    if isinstance(raw, dict) and "t" in raw:
        for k in range(len(raw["t"])): rows.append((raw["t"][k], raw["o"][k], raw["h"][k], raw["l"][k], raw["c"][k], raw["v"][k]))
    elif isinstance(raw, list):
        for r in raw:
            if isinstance(r, dict):
                g = lambda *ks: next(r[k] for k in ks if k in r)
                rows.append((g("Time", "time", "t"), g("Open", "open", "o"), g("High", "high", "h"), g("Low", "low", "l"), g("Close", "close", "c"), g("Volume", "volume", "v")))
            else: rows.append(tuple(r[:6]))
    else: raise ApiError("format_candle_tidak_dikenal")
    d = {}
    for r in rows:
        t = int(float(r[0])); t = t // 1000 if t > 1e12 else t
        d[t] = tuple(float(x) for x in r[1:6])
    ts = sorted(t for t in d if t + P.TIMEFRAME_SEC <= server_ts)       # buang candle yang masih berjalan
    out = {"t": np.array(ts, dtype=float)}
    for j, k in enumerate("ohlcv"): out[k] = np.array([d[t][j] for t in ts], dtype=float)
    return out

def parse_depth(raw):
    bids = sorted(([float(p), float(q)] for p, q in raw.get("buy", [])), key=lambda x: -x[0])
    asks = sorted(([float(p), float(q)] for p, q in raw.get("sell", [])), key=lambda x: x[0])
    return bids, asks
