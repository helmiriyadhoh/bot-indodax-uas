"""
snapshot_orderbook.py -- simpan snapshot order book Indodax (API publik, tanpa API key) untuk estimasi spread dan slippage.

Pemakaian (di terminal):
    python snapshot_orderbook.py                 # jalan terus, tiap 1 jam (Ctrl+C untuk berhenti)
    python snapshot_orderbook.py --sekali        # satu kali saja (untuk uji)
    python snapshot_orderbook.py --menit 30 --pairs btcidr ethidr solidr
Hasil: snapshots.jsonl (satu baris JSON per pasangan per snapshot). Laptop harus menyala dan tidak tidur;
setelah bot Vercel aktif, bot menyimpan snapshot yang sama tiap kali berjalan.
Hanya library bawaan Python. Batas Indodax 180 request/menit; skrip ini jauh di bawahnya.
"""
import json, time, argparse, datetime, urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
PAIRS = ["btcidr", "ethidr", "usdtidr", "xrpidr", "solidr", "dogeidr", "bnbidr", "adaidr"]
NIVEL = 20  # jumlah level order book yang disimpan per sisi


def get(url, tries=3):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=20) as r:
                return json.load(r)
        except Exception as e:
            err = e; time.sleep(1.5 * (k + 1))
    raise err


def snapshot(pair):
    st = get("https://indodax.com/api/server_time")["server_time"]          # milidetik
    d = get("https://indodax.com/api/depth/%s" % pair)
    bids = [[float(p), float(q)] for p, q in d.get("buy", [])][:NIVEL]
    asks = [[float(p), float(q)] for p, q in d.get("sell", [])][:NIVEL]
    if not bids or not asks:
        raise ValueError("order book kosong")
    bid, ask = bids[0][0], asks[0][0]
    return dict(waktu_server_ms=st, waktu_utc=datetime.datetime.fromtimestamp(st / 1000, datetime.timezone.utc).isoformat(),
                pair=pair, bid=bid, ask=ask, spread_pct=(ask - bid) / ((ask + bid) / 2) * 100, bids=bids, asks=asks)


def satu_putaran(pairs, out):
    ok = 0
    for p in pairs:
        try:
            s = snapshot(p)
            with open(out, "a", encoding="utf-8") as f: f.write(json.dumps(s, separators=(",", ":")) + "\n")
            ok += 1
            print("%s %-8s bid %s ask %s spread %.3f%%" % (s["waktu_utc"][11:19], p, s["bid"], s["ask"], s["spread_pct"]))
        except Exception as e:
            print("GAGAL %-8s %s" % (p, e))
        time.sleep(0.5)
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", nargs="+", default=PAIRS); ap.add_argument("--menit", type=float, default=60)
    ap.add_argument("--sekali", action="store_true"); ap.add_argument("--out", default="snapshots.jsonl")
    a = ap.parse_args()
    while True:
        n = satu_putaran(a.pairs, a.out)
        print("-- %d/%d pasangan tersimpan di %s" % (n, len(a.pairs), a.out))
        if a.sekali: break
        time.sleep(a.menit * 60)


if __name__ == "__main__":
    main()
