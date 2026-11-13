"""Uji koneksi + format API Indodax dari laptop (tanpa API key). Jalankan: python scripts/cek_koneksi.py"""
import sys, time
sys.path.insert(0, ".")
from core import exchange as X, params as P

try: sts = X.server_time(lambda u: X.http_json(u)); print("server_time:", sts)
except Exception as e:
    sts = int(time.time()); print("server_time GAGAL (", str(e)[:120], ") -> pakai jam laptop:", sts)
c = X.parse_candles(X.http_json(X.candles_url("BTCIDR", sts - 560 * P.TIMEFRAME_SEC, sts)), sts)
print("candle tertutup:", len(c["t"]), "| terakhir:", time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime(c["t"][-1])), "close", c["c"][-1])
b, a = X.parse_depth(X.http_json(X.depth_url("BTCIDR"))); print("best bid/ask:", b[0], a[0])
try:
    pairs = X.http_json(X.BASE + "/api/pairs")
    for r in pairs:
        if str(r.get("id", r.get("ticker_id", ""))).replace("_", "").lower() in ("btcidr", "ethidr", "xrpidr"):
            print({k: r.get(k) for k in ("id", "ticker_id", "trade_fee_percent_taker", "trade_fee_percent_maker", "trade_min_base_currency", "price_increments") if k in r})
except Exception as e: print("/api/pairs GAGAL:", str(e)[:150])
print("CATAT hasil di atas (URL + tanggal akses) untuk bagian fee/minimum order di README.")
