"""Timestamped, optional real-data market environment audit.

Unavailable sources are recorded as errors, never filled with inferred values.
Missing context must block future authorization of actionable trading signals.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any
import re

import pandas as pd

INDEX_CODES = {"CSI300": "000300", "CSI1000": "000852"}


def compute_index(raw: pd.DataFrame, asof: date) -> dict[str, Any]:
    columns = {"日期": "date", "收盘": "close", "成交额": "turnover"}
    df = raw.rename(columns=columns).copy()
    if not {"date", "close"}.issubset(df.columns):
        raise ValueError("missing index date / close")
    df["date"] = pd.to_datetime(df["date"], errors="raise")
    df["close"] = pd.to_numeric(df["close"], errors="raise")
    df = df.sort_values("date")
    if len(df) < 61 or df["date"].dt.date.iloc[-1] != asof:
        raise ValueError(f"index OHLC stale/short: bars={len(df)} last={df['date'].iloc[-1] if len(df) else None}")
    c = df["close"]
    if (c <= 0).any() or c.isna().any():
        raise ValueError("invalid index closes")
    return {
        "asof": str(asof), "source": "AKShare index_zh_a_hist (Eastmoney)",
        "last_close": round(float(c.iloc[-1]), 4),
        "ma20": round(float(c.tail(20).mean()), 4),
        "ma60": round(float(c.tail(60).mean()), 4),
        "returns": {f"{n}d": round(float(c.iloc[-1] / c.iloc[-1-n] - 1), 6) for n in (5, 10, 20)},
        "above_ma20": bool(c.iloc[-1] > c.tail(20).mean()),
        "above_ma60": bool(c.iloc[-1] > c.tail(60).mean()),
        "historical_rows": len(df),
    }


def compute_breadth(raw: pd.DataFrame, asof: date) -> dict[str, Any]:
    if not {"代码", "名称", "涨跌幅"}.issubset(raw.columns):
        raise ValueError("missing breadth schema")
    df = raw.copy()
    df["代码"] = df["代码"].astype(str).str.zfill(6)
    df = df[df["代码"].str.match(r"^(000|001|002|003|300|301|600|601|603|605|688|689)[0-9]{3}$")]
    change = pd.to_numeric(df["涨跌幅"], errors="coerce").dropna()
    if len(change) < 2500:
        raise ValueError(f"breadth snapshot only {len(change)} rows; not full A-share breadth")
    return {
        "source": "AKShare stock_zh_a_spot_em (Eastmoney), price-change snapshot",
        "capture_time_local": datetime.now().astimezone().isoformat(),
        "session_alignment": "not verified against asof daily K-line date",
        "quote_exchange_timestamp": None,
        "advancers": int((change > 0).sum()),
        "decliners": int((change < 0).sum()),
        "unchanged": int((change == 0).sum()),
        "covered_symbols": len(change),
        "warning": "capture time is not exchange time; breadth cannot be verified intraday without tick timestamps",
    }


def live_context(ak, asof: date, snapshot: pd.DataFrame | None = None) -> dict:
    """Each component is independent and has an explicit execution status."""
    out: dict[str, Any] = {
        "asof": str(asof),
        "funding_margin_balance": {"status": "NOT_FETCHED", "reason": "reliable same-date interface not yet validated"},
        "four_etf_shares_nav": {"status": "NOT_FETCHED", "reason": "same-day share/NAV consistency not yet validated"},
        "indices": {}, "breadth": {},
    }
    for name, sym in INDEX_CODES.items():
        problems = []
        for provider in ("AKShare Eastmoney", "AKShare Sina"):
            try:
                if provider == "AKShare Eastmoney":
                    df = ak.index_zh_a_hist(
                        symbol=sym, period="daily",
                        start_date=(asof - pd.Timedelta(days=150)).strftime("%Y%m%d"),
                        end_date=(asof + pd.Timedelta(days=1)).strftime("%Y%m%d"))
                else:
                    # Sina accepts exchange-prefixed symbols: sh000300, sh000852.
                    df = ak.stock_zh_index_daily(symbol="sh" + sym)
                out["indices"][name] = {"status": "OK", **compute_index(df, asof),
                                        "provider_used": provider}
                break
            except Exception as exc:
                problems.append(f"{provider}: {type(exc).__name__}: {exc}"[:250])
        else:
            out["indices"][name] = {"status": "FAILED", "errors": problems}
    try:
        frame = snapshot if snapshot is not None else ak.stock_zh_a_spot_em()
        out["breadth"] = {"status": "OK", **compute_breadth(frame, asof)}
    except Exception as exc:
        out["breadth"] = {"status": "FAILED", "error": f"{type(exc).__name__}: {exc}"[:420]}
    out["passes_market_data_gate"] = all(
        out["indices"][x]["status"] == "OK" for x in INDEX_CODES
    ) and out["breadth"].get("status") == "OK"
    return out
