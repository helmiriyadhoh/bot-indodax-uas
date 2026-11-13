"""Parameter dibekukan. Dipakai bersama oleh backtest dan bot (satu sumber kebenaran)."""
STRATEGY_TYPE = "DONCH"   # "DONCH" (breakout) atau "EMA_CROSS" (adaptasi strategi UTS)
STRATEGY_NAME = "DONCH4H-v1"
EMA_FAST = 21       # dipakai bila STRATEGY_TYPE == "EMA_CROSS"
EMA_SLOW = 50
TIMEFRAME_SEC = 4 * 3600
UNIVERSE = ["BTCIDR", "ETHIDR", "XRPIDR"]

# --- aturan sinyal ---
ENTRY_N = 30        # breakout: close > highest high N bar sebelumnya
EXIT_M = 15         # keluar: close < lowest low M bar sebelumnya
EMA_N = 120         # filter tren: close > EMA(120)
ATR_N = 14
ATR_MULT = 3.0      # chandelier: close < peak_close - 3*ATR
LOOKBACK = 500       # indikator dihitung dari max 500 bar tertutup terakhir (identik di bot & backtest)
WARMUP_BARS = max(ENTRY_N, EMA_N, ATR_N, EXIT_M) + 1

# --- sizing & risk ---
INITIAL_CAPITAL = 100_000_000.0
POS_FRAC = 0.25               # ukuran per posisi = 25% equity saat masuk
MAX_OPEN_POSITIONS = 3
DAILY_LOSS_LIMIT = 0.03       # 3% dari equity awal hari (batas hari 00.00 WIB)
MIN_ORDER_IDR = 25_000.0      # lebih ketat dari /api/pairs (Rp10.000); verifikasi sebelum freeze
MAX_SPREAD_PCT_ENTRY = 2.0    # bot tidak membuka posisi bila spread > 2%

# --- biaya ---
# TODO(WAJIB VERIFIKASI sebelum freeze): ambil trade_fee_percent_taker dari /api/pairs dan
# angka dari halaman rincian biaya resmi help.indodax.com, catat URL + tanggal akses, pakai yang lebih mahal.
# Nilai di bawah adalah PLACEHOLDER KONSERVATIF (angka tertinggi yang ditemukan: 0,51% all-in taker).
FEE_TAKER_PCT = 0.51
