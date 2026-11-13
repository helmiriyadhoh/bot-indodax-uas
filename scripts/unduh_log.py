"""Unduh log mentah forward test dari bot (lewat /api/export) ke data/forward/.
Butuh env: BOT_BASE_URL dan CRON_SECRET (dari .env lokal, JANGAN di-commit)."""
import os, sys, json, csv, urllib.request
sys.path.insert(0, ".")

def load_env():
    if os.path.exists(".env"):
        for line in open(".env", encoding="utf-8"):
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.strip().split("=", 1); os.environ.setdefault(k, v)

def fetch(base, secret, what, a, b):
    req = urllib.request.Request(f"{base}/api/export?what={what}&start={a}&stop={b}", headers={"Authorization": f"Bearer {secret}"})
    with urllib.request.urlopen(req, timeout=60) as r: return json.loads(r.read())

def main(out="data/forward"):
    load_env(); base = os.environ["BOT_BASE_URL"].rstrip("/"); secret = os.environ["CRON_SECRET"]
    os.makedirs(out, exist_ok=True)
    for what, fn in (("log", "log.jsonl"), ("snap", "snap.jsonl")):
        items, a = [], 0
        while True:
            d = fetch(base, secret, what, a, a + 499)["items"]; items += d
            if len(d) < 500: break
            a += 500
        with open(f"{out}/{fn}", "w", encoding="utf-8") as f:
            for e in items: f.write(json.dumps(e) + "\n")
        print(what, len(items), "baris ->", f"{out}/{fn}")
    json.dump(fetch(base, secret, "state", 0, 0), open(f"{out}/state.json", "w"), indent=1)
    L = [json.loads(l) for l in open(f"{out}/log.jsonl", encoding="utf-8")]
    for kind, fn in (("call", "panggilan.csv"), ("order", "order.csv"), ("daily_equity", "equity_harian.csv"), ("error", "error.csv")):
        rows = [e for e in L if e["kind"] == kind]
        keys = sorted({k for e in rows for k in e})
        with open(f"{out}/{fn}", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(rows)
        print(kind, len(rows), "->", fn)

if __name__ == "__main__": main(*sys.argv[1:2])
