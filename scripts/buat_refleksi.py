"""Buat DRAF refleksi dengan angka terisi otomatis dari out/angka_dashboard.json.
Bagian penjelasan (kenapa) harus kamu tulis/koreksi sendiri berdasarkan angka-angka ini."""
import json, argparse
ap = argparse.ArgumentParser(); ap.add_argument("--angka", default="out/angka_dashboard.json"); ap.add_argument("--keluar", default="refleksi_draft.md")
a = ap.parse_args(); D = json.load(open(a.angka))
F, W, B, G, S, O, J = D["forward"], D["backtest_jendela_forward"], D["backtest_3tahun"], D["gap"], D["kecocokan_sinyal"], D["operasional"], D["jendela"]
p = lambda x: "n/a" if x is None else f"{x:,.2f}%"
rp = lambda x: "n/a" if x is None else f"Rp{x:,.0f}"
kom = [r for r in D["fill"] if "komp_keterlambatan_pct" in r]
avg = lambda k: sum(r[k] for r in kom) / len(kom) if kom else None
sp = "\n".join(f"- {r['pair']}: spread dipakai backtest {r['spread_dipakai_backtest_pct']:.3f}% vs seluruh snapshot {r['spread_semua_snapshot_pct']:.3f}% (n={r['n_snapshot']})" for r in D["spread_vs_snapshot"])
md = f"""# Refleksi: backtest vs forward test (DRAF — lengkapi bagian "Penjelasan")

## 0. Catatan jujur tentang jendela
Forward test berjalan {J['panggilan_pertama']} sampai {J['log_terakhir']} ({J['durasi_hari']:.1f} hari, {J['jumlah_bar']} bar 4 jam), {'**lebih pendek dari 10 hari** yang diminta soal. Alasan: _(tulis alasanmu)_. ' if J['durasi_hari'] < 10 else ''}Dengan {F['n_trades']} trade, angka return tidak signifikan secara statistik.

## 1. Hasil
- Forward: return {p(F['return_total_pct'])}, max drawdown {p(F['max_drawdown_pct'])}, {F['n_trades']} trade. Buy and hold BTC pada jendela sama: {p(F['buy_hold_btc_return_pct'])}.
- Backtest dijalankan ulang pada jendela yang sama: return {p(W['return_total_pct'])}, {W['n_trades']} trade.
- **Gap: {G['gap_pct_poin']:.2f} poin persen.**
- Backtest 3 tahun (acuan): return {p(B['return_total_pct'])}, CAGR {p(B['cagr_pct'])}, max drawdown {p(B['max_drawdown_pct'])}.

## 2. Kecocokan sinyal
{S['cocok']} dari {S['bar_dibandingkan']} sinyal cocok ({p(S['cocok_pct'])}); ENTER/EXIT cocok {S['aksi_entry_exit_cocok']}/{S['aksi_entry_exit']}. Bar tidak diproses bot: {S['tidak_diproses_bot']}.
Penjelasan jika < 100%: _(tulis; lihat tabel selisih di dashboard)_.

## 3. Sumber selisih harga fill (dalam angka)
Dari {G['order_dibandingkan']} order yang bisa dipasangkan, selisih fill rata-rata yang merugikan bot {p(G['selisih_fill_rata2_merugikan_pct'])} (maks {p(G['selisih_fill_maks_pct'])}). Rata-rata komponen:
- keterlambatan jadwal: {p(avg('komp_keterlambatan_pct'))} (median telat {O['keterlambatan_median_detik']} detik, maks {O['keterlambatan_maks_detik']} detik)
- spread live vs asumsi: {p(avg('komp_spread_pct'))}
- slippage vs asumsi: {p(avg('komp_slippage_pct'))}
- sisa tidak terjelaskan: {p(avg('sisa_pct'))}

Penjelasan: _(tulis kenapa angka-angka ini bisa terjadi: bot jalan beberapa menit setelah candle tertutup, bukan tepat di open bar berikutnya; spread live berbeda dari median snapshot; dst.)_

## 4. Spread backtest vs seluruh snapshot
{sp}

Penjelasan: _(snapshot awal hanya ~2 jam pada satu hari; bandingkan dengan seluruh snapshot dan bahas dampaknya)_

## 5. Biaya
Porsi biaya (fee + spread + slippage) terhadap laba kotor: forward {p(F['porsi_biaya_pct_dari_laba_kotor'])}, backtest 3 tahun {p(B['porsi_biaya_pct_dari_laba_kotor'])}. Fee taker yang dipakai {D['fee_taker_pct']}% _(cantumkan sumber, URL, tanggal akses)_.

## 6. Stabilitas bot
Panggilan terlaksana {O['panggilan_terlaksana']} dari {O['panggilan_terjadwal_seharusnya']} terjadwal; uptime {p(O['uptime_pct'])} ({O['candle_pair_tepat_waktu']}/{O['candle_pair_total']} candle-pair tepat waktu). Error: {O['error_total']} {O['error_per_tahap']}. Kill switch dipakai {O['kill_switch_event']} kali; daily loss limit terpicu {O['daily_loss_limit_event']} kali; panggilan ganda ditolak idempotency {O['idempotent_skip']} kali.
Dampak keterlambatan penjadwal (GitHub Actions): _(tulis)_.

## 7. Kesimpulan dan keterbatasan
_(tulis: apa yang bisa dan tidak bisa disimpulkan dari jendela sependek ini; perubahan bug-fix selama forward test jika ada.)_
"""
open(a.keluar, "w", encoding="utf-8").write(md); print("OK ->", a.keluar)
