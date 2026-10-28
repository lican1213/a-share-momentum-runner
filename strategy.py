"""Pure, inspectable A-share 3-session momentum research rules.

No market access or broker calls here. Daily OHLC backtest is approximate:
T+3 daily close is NOT the exact 14:50 executable price; no guarantee of fills.
"""
from __future__ import annotations

import math
import pandas as pd


CN = {"日期": "date", "开盘": "open", "收盘": "close",
      "最高": "high", "最低": "low", "成交量": "volume", "成交额": "turnover"}
COLS = ["date", "open", "high", "low", "close", "volume"]


def normalize(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.rename(columns=CN).copy()
    if any(c not in df.columns for c in COLS):
        raise ValueError(f"missing OHLC columns: {set(COLS) - set(df.columns)}")
    df["date"] = pd.to_datetime(df["date"], errors="raise").dt.normalize()
    for c in COLS[1:]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.sort_values("date").reset_index(drop=True)
    if df["date"].duplicated().any() or df[COLS].isna().any().any():
        raise ValueError("duplicate dates or invalid numeric data")
    if (df[["open", "high", "low", "close"]] <= 0).any().any():
        raise ValueError("zero/negative prices")
    if (df["volume"] < 0).any():
        raise ValueError("negative volume")
    if ((df["high"] < df[["open", "close", "low"]].max(axis=1)) |
        (df["low"] > df[["open", "close", "high"]].min(axis=1))).any():
        raise ValueError("inconsistent OHLC")
    if len(df) < 255:
        raise ValueError(f"only {len(df)} daily bars; requires at least 255")
    return df


def ceil_cent(v: float) -> float:
    return math.ceil(v * 100 - 1e-7) / 100


def floor_cent(v: float) -> float:
    return math.floor(v * 100 + 1e-7) / 100


def candidate_at(df: pd.DataFrame, i: int) -> dict | None:
    """Uses bars 0..i only; next day has no influence on signal."""
    if i < 250:
        return None
    p = df.iloc[:i + 1]
    latest = p.iloc[-1]
    prev20 = p.iloc[-21:-1]
    close = float(latest["close"])
    prev_high = float(prev20["high"].max())
    ma20 = float(p["close"].iloc[-20:].mean())
    ma60 = float(p["close"].iloc[-60:].mean())
    avg_vol = float(prev20["volume"].mean())
    change5 = close / float(p["close"].iloc[-6]) - 1
    if avg_vol <= 0 or not all([
        close > prev_high,
        close > ma20 > ma60,
        ma20 > float(p["close"].iloc[-40:-20].mean()),
        float(latest["volume"]) >= 1.2 * avg_vol,
        change5 > 0,
    ]):
        return None
    # Standard main-board 10% limit assumption. ST/ChiNext/STAR are not in universe.
    prev_close = float(p.iloc[-2]["close"])
    if close >= prev_close * 1.095:
        return None  # nearly limit-up / likely not executable
    tr = pd.concat([
        p["high"] - p["low"],
        (p["high"] - p["close"].shift()).abs(),
        (p["low"] - p["close"].shift()).abs(),
    ], axis=1).max(axis=1)
    atr = float(tr.tail(14).mean())
    trigger = ceil_cent(float(latest["high"]) * 1.001)
    max_chase = floor_cent(min(trigger * 1.012, close * 1.09))
    risk_pct = min(0.012, max(0.006, 0.8 * atr / trigger))
    target_pct = max(0.018, 1.8 * risk_pct)
    if target_pct > 0.03 or max_chase <= trigger:
        return None
    return {
        "signal_date": str(latest["date"].date()),
        "signal_close": round(close, 4), "trigger": trigger,
        "max_chase": max_chase,
        "stop": floor_cent(trigger * (1 - risk_pct)),
        "target": ceil_cent(trigger * (1 + target_pct)),
        "risk_pct": round(risk_pct, 5),
        "expected_r": round(target_pct / risk_pct, 3),
        "atr14": round(atr, 4), "volume_multiple": round(float(latest["volume"]) / avg_vol, 3),
        "ma20": round(ma20, 4), "ma60": round(ma60, 4),
        "return5": round(change5, 5),
        "assumptions": "future conditional order; main-board 10% cap; not actual fill"
    }


def historical_trades(df: pd.DataFrame, symbol: str, commission=0.00025,
                      stamp=0.0005, slippage=0.0005) -> list[dict]:
    """Conservative OHLC-only exploratory replay; entry next day, exit T+1..T+3.

    If target and stop both touched in one bar, stop executes first. If a stop
    gap occurs, sell at open less slippage. Does NOT model intraday 14:50 exactly.
    Historical constituent/stock universe selection suffers survivorship bias.
    """
    trades = []
    eligible_index = 250
    while eligible_index < len(df) - 4:
        s = candidate_at(df, eligible_index)
        if s is None:
            eligible_index += 1
            continue
        j = eligible_index + 1
        day = df.iloc[j]
        if float(day["high"]) < s["trigger"] or float(day["open"]) > s["max_chase"]:
            eligible_index += 1
            continue
        fill = max(float(day["open"]), s["trigger"])
        if fill > s["max_chase"]:
            eligible_index += 1
            continue
        risk = s["risk_pct"]
        stop = fill * (1 - risk)
        target = fill * (1 + max(0.018, 1.8 * risk))
        exit_px, exit_at, reason = None, None, None
        for k in range(j + 1, j + 4):
            x = df.iloc[k]
            op, lo, hi = float(x["open"]), float(x["low"]), float(x["high"])
            if op <= stop:
                exit_px, exit_at, reason = op, k, "stop_gap"
                break
            if lo <= stop:
                exit_px, exit_at, reason = stop, k, "stop"
                break
            if op >= target:
                exit_px, exit_at, reason = op, k, "target_gap"
                break
            if hi >= target:
                exit_px, exit_at, reason = target, k, "target"
                break
            if k == j + 3:
                exit_px, exit_at, reason = float(x["close"]), k, "T+3_close_proxy"
        # Do not extrapolate beyond available data.
        if exit_px is None:
            eligible_index += 1
            continue
        net = (exit_px * (1 - slippage) * (1 - commission - stamp)) / (
            fill * (1 + slippage) * (1 + commission)) - 1
        trades.append({
            "symbol": symbol, "signal_date": s["signal_date"],
            "entry_date": str(day["date"].date()),
            "exit_date": str(df.iloc[exit_at]["date"].date()),
            "entry": round(fill, 4), "exit": round(exit_px, 4),
            "net_return": round(net, 7),
            "r_multiple": round(net / risk, 5),
            "reason": reason,
            "hold_sessions": exit_at - j,
            "daily_proxy_not_1450": True,
        })
        eligible_index = exit_at + 1
    return trades
