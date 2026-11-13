# Bot Dry Run Indodax — UAS Algoritma Trading

Bot trading **dry run** (order simulasi, tanpa uang dan tanpa API key) untuk pasar IDR Indodax. Berjalan di Vercel,
dipanggil penjadwal GitHub Actions, menyimpan state dan log di Upstash Redis.

- Strategi: dipilih lewat `STRATEGY_TYPE` di `core/params.py` (lihat `STRATEGI_DAN_PERUBAHAN.md`), long-only, timeframe 4 jam, universe BTCIDR, ETHIDR, XRPIDR.
- Sinyal: `core/strategy.py` dipakai **sama persis** oleh `backtest/` dan bot (`core/bot.py`).
- Eksekusi: beli di ask, jual di bid dari order book live, habiskan level berikutnya (`core/execution.py`).

## Struktur
`core/` logika bersama · `api/tick.py` endpoint bot · `api/export.py` ekspor log · `backtest/` backtest ·
`tests/replay_test.py` tes offline bot vs backtest · `scripts/` uji koneksi · `.github/workflows/tick.yml` penjadwal.

## Jalankan lokal
    pip install numpy
    python scripts/cek_koneksi.py        # uji API Indodax + catat fee/minimum order
    python backtest/run_backtest.py      # backtest 3 tahun
    python tests/replay_test.py          # bot vs backtest (offline)

## Deploy
1. Vercel: Add New > Project > import repo ini. Storage > Upstash Redis (free) > hubungkan ke project.
2. Environment Variables: `CRON_SECRET` (teks acak panjang). Redeploy.
3. GitHub > Settings > Secrets and variables > Actions: `CRON_SECRET` (nilai sama) dan `TICK_URL` (`https://NAMA.vercel.app/api/tick`).
4. Actions > tick > Run workflow untuk uji manual. Respons 200 berisi ringkasan.
5. Kill switch tanpa deploy: Redis `SET bot:kill 1` (cabut: `DEL bot:kill`) atau env `KILL_SWITCH=1`. Efek: tidak ada entry baru, exit tetap jalan, dicatat di log.

## Biaya & minimum order (ISI sebelum freeze)
| Item | Nilai dipakai | Sumber / URL | Tanggal akses |
|---|---|---|---|
| Fee taker all-in | _(isi; sementara 0,51% di `core/params.py`)_ | /api/pairs dan help.indodax.com | _ |
| Minimum order | Rp25.000 | /api/pairs (Rp10.000) vs mode Pro (Rp25.000) | _ |

## Freeze
_(isi: hash commit, waktu commit, waktu mulai forward test, dan alasan bila kurang dari 10 hari)_

## Setelah forward test selesai (urutan)
1. Hentikan penjadwal: GitHub > Actions > tick > menu "..." > Disable workflow. Catat waktu berhenti.
2. Buat file `.env` lokal (tidak di-commit) berisi `BOT_BASE_URL` dan `CRON_SECRET`, lalu: `python scripts/unduh_log.py` (hasil di `data/forward/`).
3. Tarik candle terbaru, tunggu >= 4 jam setelah forward test selesai agar ada 1 bar sesudah jendela: `python scripts/tarik_data_indodax.py`, lalu salin hasilnya ke `data/candles/`.
4. `python scripts/hitung_ulang.py` -> `out/angka_dashboard.json` (semua angka dihitung dari log mentah).
5. `python scripts/buat_dashboard.py --nama "Helmi Riyadhoh" --nim 25110200005 --kelas Trad1` -> `out/UAS_<NIM>_<Nama>.html` (offline, mandiri, gaya dashboard UTS). Salin ke `public/index.html` lalu commit dan push untuk halaman Vercel.
6. `python scripts/buat_refleksi.py` -> `refleksi_draft.md`; lengkapi bagian "Penjelasan" dengan kata-katamu sendiri.
7. Kumpulkan ZIP (termasuk folder `.git`), link Vercel, link repositori. Pastikan tidak ada `.env`.
