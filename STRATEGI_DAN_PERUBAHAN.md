# Strategi tertulis dan catatan perubahan dari versi UTS

## Strategi UTS (acuan)
EMA Cross 21/50 long-only, saham BEI Kompas100, timeframe harian. Masuk saat EMA(21) memotong ke atas EMA(50) pada adjusted close; keluar saat memotong ke bawah; eksekusi di harga buka bar berikutnya. Maks 10 posisi, 10% modal awal per posisi, fee beli 0,15% dan jual 0,25%, spread 1 fraksi harga, batas order 5% ADTV 20 hari. Tanpa stop-loss.

## Pilihan strategi UAS (pilih SATU sebelum freeze, lalu isi bagian "Strategi yang dipakai")
Hasil backtest 3 tahun (8 Okt 2023 – 7 Nov 2026, BTC/ETH/XRP, 4 jam, fee 0,51% sementara, spread dan slippage dari snapshot awal):

| | A. DONCH4H-v1 (desain baru) | B. EMA_CROSS 21/50 (UTS diadaptasi) |
|---|---|---|
| Return total | +33,1% | +36,4% |
| CAGR | 9,7% | 10,6% |
| Max drawdown | 34,5% | 47,9% |
| Profit factor | 1,15 | 1,14 |
| Win rate | 34,0% | 27,1% |
| Jumlah trade | 206 | 181 |
| Porsi biaya | 71,5% | 67,9% |

Keduanya jauh di bawah buy and hold BTC (+214%). Selisih antar keduanya kecil, jadi pilihlah berdasarkan alasan desain (kesinambungan dengan UTS dan kemudahan dijelaskan), bukan berdasarkan angka backtest. Angka di atas masih akan berubah setelah fee diverifikasi.

Cara memilih: di `core/params.py` set `STRATEGY_TYPE = "DONCH"` atau `"EMA_CROSS"`, dan sesuaikan `STRATEGY_NAME`. Setelah itu jalankan ulang `python backtest/run_backtest.py` dan `python tests/replay_test.py`.

## Strategi yang dipakai
_(isi: A atau B, alasan pemilihan, tanggal)_

## Catatan perubahan dari versi UTS (isi sesuai pilihan; semua selesai sebelum freeze)
| Aspek | UTS | UAS | Alasan |
|---|---|---|---|
| Aset | saham BEI Kompas100 | kripto IDR Indodax: BTC, ETH, XRP | diwajibkan soal UAS; dipilih dari likuiditas 90 hari pertama data |
| Timeframe | harian | 4 jam | jumlah sinyal cukup dalam jendela forward test pendek |
| Harga sinyal | adjusted close (dividen/split) | close mentah bar tertutup | kripto tidak punya dividen/split |
| Biaya | fee 0,15%/0,25% dan spread 1 fraksi | fee taker all-in (verifikasi) dan spread + slippage dari snapshot order book | soal UAS |
| Fill | harga buka bar berikutnya | ask untuk beli, bid untuk jual dari order book live, habiskan level berikutnya | soal UAS |
| Sizing | 10% modal awal per posisi, maks 10 posisi | 25% equity saat masuk, maks 3 posisi | universe hanya 3 pasangan |
| Batas likuiditas | 5% ADTV | minimum order Rp25.000 dan kedalaman order book | data order book tersedia |
| Risk | – | daily loss limit 3% (WIB), kill switch, idempotency, retry terbatas | wajib di soal UAS |
| Aturan sinyal | EMA 21/50 | (B: sama, EMA 21/50, keluar saat EMA cepat di bawah EMA lambat) atau (A: breakout Donchian 30/15 + EMA120 + ATR trailing) | isi sesuai pilihan |
