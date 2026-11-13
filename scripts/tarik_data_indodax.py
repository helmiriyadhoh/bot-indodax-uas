"""
tarik_data_indodax.py -- tarik candle historis Indodax (API publik, tanpa API key) MUNDUR dari sekarang sampai >= 3 tahun.

Pemakaian (di terminal, di laptop):
    python tarik_data_indodax.py                          # 8 pasangan bawaan, timeframe 4 jam
    python tarik_data_indodax.py --pairs btcidr ethidr --tf 240 --tahun 3.25
    python tarik_data_indodax.py --selftest               # tampilkan contoh respons mentah (untuk cek format)
Hasil: folder data_indodax/<PAIR>_<tf>.json  + ringkasan validasi di layar.
Aturan: satu request history_v2 hanya memberi ~650 bar terakhir sebelum 'to', jadi 'to' digeser mundur ke bar paling awal
yang sudah didapat. Maksimal ~2,5 request/detik, tidak paralel. Bar yang belum tertutup dibuang (Time + durasi > server_time).
Hanya library bawaan Python.
"""
import json, os, time, argparse, datetime, urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
PAIRS = ["btcidr", "ethidr", "solidr", "xrpidr", "dogeidr", "bnbidr", "adaidr", "usdtidr"]
TF_DETIK = {"1": 60, "15": 900, "30": 1800, "60": 3600, "240": 14400, "1D": 86400}
JEDA = 0.4


def get(url, tries=4):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30) as r:
                return json.load(r)
        except Exception as e:
            err = e; time.sleep(2 * (k + 1))
    raise err


def server_detik():
    j = get("https://indodax.com/api/server_time")
    return int(j["server_time"] // 1000) if j["server_time"] > 1e11 else int(j["server_time"])


def parse(j):
    """Terima daftar objek {Time,Open,High,Low,Close,Volume} (huruf besar/kecil bebas) atau dict-larik gaya TradingView."""
    rows = []
    if isinstance(j, dict) and "t" in j:
        for i, t in enumerate(j["t"]):
            rows.append((t, j["o"][i], j["h"][i], j["l"][i], j["c"][i], j.get("v", [0] * len(j["t"]))[i]))
    else:
        for b in j:
            g = {str(k).lower(): v for k, v in b.items()}
            rows.append((g.get("time", g.get("t")), g.get("open", g.get("o")), g.get("high", g.get("h")),
                         g.get("low", g.get("l")), g.get("close", g.get("c")), g.get("volume", g.get("v", 0))))
    out = []
    for t, o, h, l, c, v in rows:
        t = int(t); t = t // 1000 if t > 1e11 else t
        out.append((t, float(o), float(h), float(l), float(c), float(v)))
    return out


def tarik(pair, tf, tahun, now):
    dur = TF_DETIK[tf]; awal = now - int(tahun * 365.25 * 86400); cur_to = now; semua = {}; terawal = None; n_req = 0
    while True:
        url = "https://indodax.com/tradingview/history_v2?symbol=%s&tf=%s&from=%d&to=%d" % (pair.upper(), tf, awal, cur_to)
        bars = parse(get(url)); n_req += 1
        if not bars: break
        for b in bars: semua[b[0]] = b
        t0 = min(b[0] for b in bars)
        print("  %s request %d: %d bar, terawal %s" % (pair, n_req, len(bars), datetime.datetime.utcfromtimestamp(t0).strftime("%Y-%m-%d %H:%M")))
        if t0 <= awal or (terawal is not None and t0 >= terawal): break   # sudah cukup jauh, atau riwayat habis
        terawal = t0; cur_to = t0; time.sleep(JEDA)
    data = sorted(semua.values())
    return [b for b in data if b[0] + dur <= now]       # buang bar yang belum tertutup


def validasi(data, dur):
    gap = sum(1 for a, b in zip(data, data[1:]) if b[0] - a[0] > dur)
    nol = sum(1 for b in data if min(b[1:5]) <= 0 or b[5] <= 0)
    return dict(bar=len(data), pertama=datetime.datetime.utcfromtimestamp(data[0][0]).strftime("%Y-%m-%d"),
                terakhir=datetime.datetime.utcfromtimestamp(data[-1][0]).strftime("%Y-%m-%d %H:%M"),
                tahun=(data[-1][0] - data[0][0]) / 31557600, gap=gap, bar_nol=nol)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", nargs="+", default=PAIRS); ap.add_argument("--tf", default="240", choices=list(TF_DETIK))
    ap.add_argument("--tahun", type=float, default=3.25); ap.add_argument("--out", default="data_indodax"); ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(); now = server_detik()
    if a.selftest:
        j = get("https://indodax.com/tradingview/history_v2?symbol=BTCIDR&tf=%s&from=%d&to=%d" % (a.tf, now - 86400 * 3, now))
        print("tipe:", type(j).__name__, "| contoh:", json.dumps(j[:2] if isinstance(j, list) else {k: v[:2] for k, v in j.items()})[:400]); return
    os.makedirs(a.out, exist_ok=True)
    for p in a.pairs:
        try:
            d = tarik(p, a.tf, a.tahun, now)
            v = validasi(d, TF_DETIK[a.tf])
            json.dump(dict(pair=p.upper(), tf=a.tf, diunduh_utc=datetime.datetime.utcfromtimestamp(now).isoformat() + "Z", sumber="Indodax history_v2",
                           t=[b[0] for b in d], o=[b[1] for b in d], h=[b[2] for b in d], l=[b[3] for b in d], c=[b[4] for b in d], v=[b[5] for b in d]),
                      open(os.path.join(a.out, "%s_%s.json" % (p.upper(), a.tf)), "w"), separators=(",", ":"))
            print("OK %s: %d bar, %s s/d %s (%.2f tahun), gap %d, bar bernilai nol %d\n" % (p.upper(), v["bar"], v["pertama"], v["terakhir"], v["tahun"], v["gap"], v["bar_nol"]))
        except Exception as e:
            print("GAGAL %s: %s\n" % (p.upper(), e))
        time.sleep(JEDA)


if __name__ == "__main__":
    main()
