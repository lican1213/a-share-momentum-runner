"""Deterministic one-price daily-bar execution guard.

Daily positive traded volume does not establish that a strategy could join
the opening or closing auction. A price-limit one-price bar is censored,
not simulated as a filled order.
"""
from __future__ import annotations

def conservative_ohlc_bar(opening, high, low, closing, volume, previous_close=None):
    values=(opening,high,low,closing)
    if any(x is None or float(x)<=0 for x in values) or float(volume)<0:
        raise ValueError("nonpositive or missing OHLC/negative volume")
    opening,high,low,closing=(float(v) for v in values)
    if not (low<=min(opening,closing)<=max(opening,closing)<=high):
        raise ValueError("inconsistent OHLC high/low")
    suspended=float(volume)==0
    one_price=abs(high-low)<=max(1e-9,1e-7*close)
    pct=(opening/float(previous_close)-1) if previous_close is not None and float(previous_close)>0 else None
    possible_up=bool(one_price and pct is not None and pct>=.045)
    possible_down=bool(one_price and pct is not None and pct<=-.045)
    return {
        "entry_blocked":suspended or possible_up,
        "exit_blocked":suspended or possible_down,
        "entry_reason":"NO_VOLUME" if suspended else "ONE_PRICE_POSSIBLE_LIMIT_UP" if possible_up else "DAILY_BAR_FILL_UNCONFIRMED",
        "exit_reason":"NO_VOLUME" if suspended else "ONE_PRICE_POSSIBLE_LIMIT_DOWN" if possible_down else "DAILY_BAR_FILL_UNCONFIRMED",
        "exact_order_fill_known":False,
        "daily_bar_only":True,
        "one_price_session":one_price,
        "previous_close":str(previous_close) if previous_close is not None else None
    }
