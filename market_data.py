"""Independent, genuinely queried BaoStock daily OHLC fallback.

BaoStock is not AKShare; report the provider explicitly. No mock rows or cached
prices are used. The API has no guaranteed real-time quotes.
"""
from __future__ import annotations

import socket
import pandas as pd


def baostock_daily(symbol: str, start_yyyymmdd: str, end_yyyymmdd: str) -> pd.DataFrame:
    import baostock as bs
    if len(symbol) != 6 or not symbol.isdigit():
        raise ValueError("invalid ticker")
    # Fail quickly on CI environments that block BaoStock's non-HTTP socket.
    try:
        with socket.create_connection(("www.baostock.com", 10030), timeout=3):
            pass
    except Exception as exc:
        raise ConnectionError(f"BaoStock socket inaccessible: {type(exc).__name__}: {exc}") from exc
    result = bs.login()
    if result.error_code != "0":
        raise ConnectionError(f"BaoStock login error {result.error_code}: {result.error_msg}")
    try:
        ticker = ("sh." if symbol.startswith("6") else "sz.") + symbol
        response = bs.query_history_k_data_plus(
            ticker,
            "date,open,high,low,close,volume,tradestatus,isST",
            start_date=f"{start_yyyymmdd[:4]}-{start_yyyymmdd[4:6]}-{start_yyyymmdd[6:]}",
            end_date=f"{end_yyyymmdd[:4]}-{end_yyyymmdd[4:6]}-{end_yyyymmdd[6:]}",
            frequency="d",
            adjustflag="3",
        )
        if response.error_code != "0":
            raise RuntimeError(f"BaoStock query: {response.error_code}: {response.error_msg}")
        rows = []
        while response.next():
            rows.append(response.get_row_data())
        if not rows:
            raise ValueError("BaoStock returned empty rows")
        df = pd.DataFrame(rows, columns=response.fields)
        df = df[df["tradestatus"] == "1"].copy()
        if df.empty:
            raise ValueError("BaoStock returned no traded rows")
        if df.iloc[-1]["isST"] == "1":
            raise ValueError("BaoStock security marked as ST")
        return df
    finally:
        bs.logout()
