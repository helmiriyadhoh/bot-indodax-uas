"""Simulasi fill di order book: habiskan level berikutnya, pakai harga rata-rata."""
import math

def walk_notional(levels, notional):
    """Beli senilai `notional` IDR. Return (harga_rata2, qty, terpenuhi_penuh)."""
    rem, qty, cost = notional, 0.0, 0.0
    for px, q in levels:
        take = min(rem, px * q)
        cost += take; qty += take / px; rem -= take
        if rem <= 1e-9: break
    return (cost / qty if qty else None), qty, rem <= 1e-6

def walk_qty(levels, qty):
    """Jual `qty` koin. Return (harga_rata2, qty_terjual, terpenuhi_penuh)."""
    rem, got, proceeds = qty, 0.0, 0.0
    for px, q in levels:
        take = min(rem, q)
        got += take; proceeds += take * px; rem -= take
        if rem <= 1e-12: break
    return (proceeds / got if got else None), got, rem <= 1e-10

def floor8(x): return math.floor(x * 1e8) / 1e8
