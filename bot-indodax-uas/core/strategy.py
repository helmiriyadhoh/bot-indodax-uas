"""Fungsi sinyal murni. Backtest dan bot memanggil fungsi yang SAMA."""
import numpy as np
from . import params as P

def ema(x, n):
    a = 2.0 / (n + 1); out = np.empty(len(x)); out[0] = x[0]
    for i in range(1, len(x)): out[i] = a * x[i] + (1 - a) * out[i - 1]
    return out

def atr(h, l, c, n):
    tr = np.empty(len(c)); tr[0] = h[0] - l[0]
    for i in range(1, len(c)):
        tr[i] = max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
    out = np.empty(len(c)); out[0] = tr[0]
    for i in range(1, len(c)): out[i] = (out[i - 1] * (n - 1) + tr[i]) / n  # Wilder
    return out

def data_valid(h, l, c, v, t, i):
    """Jendela indikator tanpa celah, harga/volume > 0 pada bar sinyal."""
    s = i - P.WARMUP_BARS + 1
    if s < 0: return False, "warmup"
    if c[i] <= 0 or v[i] <= 0 or h[i] <= 0 or l[i] <= 0: return False, "harga_atau_volume_nol"
    w = t[s:i + 1]
    if len(w) > 1 and np.any(np.diff(w) != P.TIMEFRAME_SEC): return False, "candle_hilang"
    return True, "ok"

def signal_donch(h, l, c, v, t, i, in_pos, peak_close):
    """Hitung sinyal pada bar tertutup index i. Return (aksi, alasan, peak_baru)."""
    s0 = max(0, i + 1 - P.LOOKBACK)
    h, l, c, v, t = h[s0:i + 1], l[s0:i + 1], c[s0:i + 1], v[s0:i + 1], t[s0:i + 1]
    i = i - s0
    ok, why = data_valid(h, l, c, v, t, i)
    e = ema(c[:i + 1], P.EMA_N)[i]
    a = atr(h[:i + 1], l[:i + 1], c[:i + 1], P.ATR_N)[i]
    if in_pos:
        peak = max(peak_close, c[i])
        ll = np.min(l[i - P.EXIT_M:i])
        if c[i] < ll: return "EXIT", "donchian_low", peak
        if c[i] < peak - P.ATR_MULT * a: return "EXIT", "atr_trail", peak
        return "HOLD", "in_pos", peak
    if not ok: return "SKIP", why, 0.0
    hh = np.max(h[i - P.ENTRY_N:i])
    if c[i] > hh and c[i] > e: return "ENTER", "breakout_trend", c[i]
    return "FLAT", "no_signal", 0.0


def signal_ema(h, l, c, v, t, i, in_pos, peak_close):
    """EMA cross (strategi UTS diadaptasi ke 4 jam). Masuk saat EMA cepat memotong ke atas EMA lambat; keluar saat EMA cepat di bawah EMA lambat."""
    s0 = max(0, i + 1 - P.LOOKBACK)
    h, l, c, v, t = h[s0:i + 1], l[s0:i + 1], c[s0:i + 1], v[s0:i + 1], t[s0:i + 1]
    i = i - s0
    ok, why = data_valid(h, l, c, v, t, i)
    ef, es = ema(c, P.EMA_FAST), ema(c, P.EMA_SLOW)
    if in_pos:
        return ("EXIT", "ema_cross_down", c[i]) if ef[i] < es[i] else ("HOLD", "in_pos", c[i])
    if not ok: return "SKIP", why, 0.0
    if ef[i] > es[i] and ef[i - 1] <= es[i - 1]: return "ENTER", "ema_cross_up", c[i]
    return "FLAT", "no_signal", 0.0

def signal(h, l, c, v, t, i, in_pos, peak_close):
    f = signal_ema if P.STRATEGY_TYPE == "EMA_CROSS" else signal_donch
    return f(h, l, c, v, t, i, in_pos, peak_close)
