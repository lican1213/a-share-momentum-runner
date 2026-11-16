"""Exact-session ordinary circulating market cap, never index-adjusted market cap.

Vendor quotes are observations, not exchange publication timestamps. Source
captures are archived inside existing V3 records; prior raw evidence is read
without modifying it. The same dated official CSV remains the primary archive.
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

BJ = ZoneInfo("Asia/Shanghai")
URL = "https://push2.eastmoney.com/api/qt/stock/get"
PARAMS = {"secid": "1.000300", "fltt": "2", "invt": "2",
          "fields": "f57,f58,f43,f116,f117,f124"}
KIND = "CSI300_ordinary_float_mv"


def final_index_sessions(prices, observed_at):
    local = observed_at.astimezone(BJ)
    today = local.date().isoformat()
    return {day: value for day, value in prices.items()
            if day < today or (day == today and local.time() >= time(15, 5))}


def parse_quote(payload, prices, observed_at):
    """Require index identity, an explicitly timestamped final close and yuan."""
    d = payload["data"]
    if str(d["f57"]) != "000300" or "沪深300" not in str(d["f58"]).replace(" ", ""):
        raise ValueError("not CSI300")
    stamp = int(d["f124"])
    if stamp > 10**12:
        stamp //= 1000
    qt = datetime.fromtimestamp(stamp, BJ)
    day = qt.date().isoformat()
    if qt > observed_at.astimezone(BJ) or qt.time() < time(15):
        raise ValueError("not completed close")
    if not prices or day != max(prices):
        raise ValueError("quote session differs from latest finalized index session")
    close = float(d["f43"])
    ordinary, total = float(d["f117"]), float(d["f116"])
    if not all(math.isfinite(x) for x in (close,ordinary,total)):
        raise ValueError("invalid cap quote")
    if abs(close - float(prices[day])) > .03:
        raise ValueError("independent index close mismatch")
    if not 10**12 <= ordinary <= total <= 10**15:
        raise ValueError("unexpected CNY market cap or missing ordinary float")
    return {"date": day, "kind": KIND, "value_cny": ordinary,
            "index_code": "000300.SH", "unit": "CNY",
            "source_url": URL + "?secid=1.000300&fltt=2&fields=f57,f58,f43,f116,f117,f124",
            "published_at": observed_at.astimezone(BJ).isoformat(),
            "method": "VENDOR_REPORTED_F117_OBSERVED_TIME_NOT_ORIGINAL_PUBLICATION",
            "quote_time": qt.isoformat(), "close": close, "total_mv_cny": total}


def collect(prices, *, getter=None, observed_at=None):
    if getter is None:
        import requests
        getter = requests.get
    captured = observed_at or datetime.now(BJ)
    payload = None
    try:
        response = getter(URL, params=PARAMS, headers={"User-Agent":"Mozilla/5.0",
                           "Referer":"https://quote.eastmoney.com/"}, timeout=12)
        response.raise_for_status()
        payload = response.json()
        captured = observed_at or datetime.now(BJ)
        result = parse_quote(payload, prices, captured)
        return {"status": "VENDOR_DATED_ORDINARY_FLOAT", "record": result,
                "raw_quote": payload, "sha256": hashlib.sha256(json.dumps(
                    payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()}
    except Exception as exc:
        result = {"status":"SOURCE_UNAVAILABLE", "observed_at":captured.isoformat(),
                  "error":f"{type(exc).__name__}:{str(exc)[:160]}"}
        if isinstance(payload,dict):
            result["rejected_raw_quote"] = payload
            result["sha256"] = hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        return result


def add_captures(official, history_root, current):
    """Recover earlier successful captures without rewriting their archive.

    A disagreement between provider observations for one exact session is
    reported and removed from the vendor-only series. Official dated rows
    always retain their original provenance.
    """
    result = dict(official)
    vendor = {}
    conflicts = set()
    captures = []
    for p in sorted(Path(history_root).glob("*/*.json")):
        try:
            item = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        stored = item.get("source_provenance", {}).get("denominator_capture")
        if stored:
            captures.append(stored)
    captures.append(current)
    for item in captures:
        if item.get("status") != "VENDOR_DATED_ORDINARY_FLOAT":
            continue
        row = item["record"]
        if row.get("kind") != KIND or row.get("index_code") != "000300.SH" or row.get("unit") != "CNY":
            continue
        key = (row["date"], KIND)
        if key in official:
            continue
        if key in vendor and abs(vendor[key]["value_cny"] - row["value_cny"]) > 1:
            conflicts.add(key)
        elif key not in vendor or row["published_at"] < vendor[key]["published_at"]:
            vendor[key] = row
    for key, row in vendor.items():
        if key not in conflicts:
            result[key] = row
    return result, {"vendor_rows":len(vendor)-len(conflicts),
                    "conflicted_dates":sorted(key[0] for key in conflicts),
                    "official_rows":len(official)}
