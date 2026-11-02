"""Single optional Baostock fallback for EXP-0012 source and future OHLC.

Both callers reuse one login per batch. Returned bars are raw, dated, unadjusted
daily OHLC; no missing session is invented or filled forward.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

BJ = ZoneInfo("Asia/Shanghai")
FIELDS = "date,open,high,low,close"


def fetch_baostock(codes, start, end, *, backend=None):
    if not codes:
        return {}, {}
    if backend is None:
        import baostock as backend
    source, errors = {}, {}
    login = backend.login()
    if str(login.error_code) != "0":
        return {}, {code: "BAOSTOCK_LOGIN:" + str(login.error_msg)[:130]
                    for code in codes}
    try:
        for code in dict.fromkeys(codes):
            if len(code) != 6 or not code.isdigit():
                errors[code] = "INVALID_SYMBOL"
                continue
            symbol = ("sh." if code.startswith(("5", "6", "9")) else "sz.") + code
            try:
                result = backend.query_history_k_data_plus(
                    symbol, FIELDS, start_date=start, end_date=end,
                    frequency="d", adjustflag="3")
                if str(result.error_code) != "0":
                    raise ValueError(str(result.error_msg)[:120])
                bars = []
                while result.next():
                    row = result.get_row_data()
                    if len(row) != 5:
                        continue
                    day, op, hi, lo, cl = row
                    if not start <= day <= end:
                        continue
                    try:
                        if any(Decimal(x) <= 0 for x in (op, hi, lo, cl)):
                            continue
                    except (InvalidOperation, TypeError):
                        continue
                    bars.append({"date": day, "open": op, "high": hi,
                                 "low": lo, "close": cl})
                if not bars:
                    raise ValueError("no dated OHLC bars")
                bars.sort(key=lambda x: x["date"])
                if len(set(x["date"] for x in bars)) != len(bars):
                    raise ValueError("duplicate source sessions")
                source[code] = {
                    "bars": bars, "vendor": "BAOSTOCK",
                    "source_url": "http://baostock.com",
                    "source_sha256": hashlib.sha256(
                        json.dumps(bars, sort_keys=True,
                                   separators=(",", ":")).encode("utf-8")).hexdigest(),
                    "first_observed_at": datetime.now(BJ).isoformat(),
                }
            except Exception as exc:
                errors[code] = type(exc).__name__ + ":" + str(exc)[:160]
    finally:
        backend.logout()
    return source, errors



def backfill_asof_prices(prices, asof, *, fetcher=fetch_baostock):
    """Only complete same-session, >=21-bar replacements enter paper freeze."""
    missing = [code for code in prices.get("universe", [])
               if code not in prices.get("stocks", {})]
    if not missing:
        return prices
    start = (date.fromisoformat(asof) - timedelta(days=100)).isoformat()
    sources, errors = fetcher(missing, start, asof)
    prices.setdefault("collection_errors", {}).update(
        {"BAOSTOCK:" + code: err for code, err in errors.items()})
    recovered = []
    for code, item in sources.items():
        bars = item["bars"]
        if len(bars) < 21 or bars[-1]["date"] != asof:
            prices["collection_errors"]["BAOSTOCK:" + code] = "STALE_OR_SHORT_OHLC"
            continue
        prices["stocks"][code] = {
            **item, "asof": asof, "bars": bars[-45:]}
        recovered.append(code)
    prices["fallback_recovered_codes"] = recovered
    return prices


def backfill_future_bars(observations, codes, signal_date, asof, *,
                         fetcher=fetch_baostock):
    """Replace absent later OHLC only, retaining the failed primary-source errors."""
    missing = [code for code in dict.fromkeys(codes)
               if not observations.get("bars_by_symbol", {}).get(code)]
    if not missing:
        return observations
    start = (date.fromisoformat(signal_date) + timedelta(days=1)).isoformat()
    sources, errors = fetcher(missing, start, asof)
    observations.setdefault("errors", {}).update(
        {"BAOSTOCK:" + code: err for code, err in errors.items()})
    recovered = []
    for code, item in sources.items():
        bars = [row for row in item["bars"] if signal_date < row["date"] <= asof]
        if not bars:
            continue
        observations["bars_by_symbol"][code] = bars
        observations.setdefault("source_url", {})[code] = item["source_url"]
        observations.setdefault("source_sha256", {})[code] = item["source_sha256"]
        recovered.append(code)
    observations["fallback_recovered_codes"] = recovered
    return observations
