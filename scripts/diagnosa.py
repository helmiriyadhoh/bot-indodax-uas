"""Diagnosa 403: coba tiap endpoint Indodax dengan dua identitas. Jalankan: python scripts/diagnosa.py"""
import time, urllib.request, urllib.error
t = int(time.time()); B = "https://indodax.com"
URLS = [("server_time", B + "/api/server_time"), ("depth", B + "/api/depth/btcidr"), ("ticker_all", B + "/api/ticker_all"),
        ("pairs", B + "/api/pairs"), ("history_v2", f"{B}/tradingview/history_v2?symbol=BTCIDR&tf=240&from={t-86400}&to={t}")]
UA = {"python-bawaan": None, "browser": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
for ua, val in UA.items():
    print("=== identitas:", ua)
    for nama, url in URLS:
        req = urllib.request.Request(url, headers={"User-Agent": val} if val else {})
        try:
            with urllib.request.urlopen(req, timeout=15) as r: print(f"{nama:12s} {r.status} server={r.headers.get('Server')} | {r.read(90)!r}")
        except urllib.error.HTTPError as e: print(f"{nama:12s} {e.code} server={e.headers.get('Server')} | {e.read(90)!r}")
        except Exception as e: print(f"{nama:12s} ERROR {e!r}"[:200])
        time.sleep(1)
