"""Download-free V3 replay CLI; inputs are exact, hashed external source snapshots.

Usage: python scripts/replay_national_team_v3.py --shares upstream.json --index csi300.csv
Optional: --fetch-nav-akshare (retrospective Eastmoney NAV, first publication unverified)
          --nav nav.json --denominators data/national_team/csi300_float_mv.csv
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode

# Running this file by path from the repository root must work without pip install -e.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from national_team.core_flow_factors import CORE_FOUR
from national_team.coverage_v3 import (
    DENOM_KINDS, INDEX_SOURCE, SHARES_SOURCE, read_denominators, read_nav,
    read_prices, read_shares, replay, sha256_file,
)


def fetch_nav_akshare():
    """Akshare/Eastmoney retrospective NAV is *not* an as-published PIT archive."""
    import akshare as ak  # optional; don't require finance libraries for pure replay
    nav = {}
    failures = {}
    for code in CORE_FOUR:
        try:
            frame = ak.fund_open_fund_info_em(symbol=code, indicator="单位净值走势")
            if frame is None or frame.empty:
                raise ValueError("empty NAV dataframe")
            for _, row in frame.iterrows():
                day = str(row["净值日期"])[:10]
                value = row.get("单位净值")
                if value is None:
                    continue
                numeric = float(value)
                if not math.isfinite(numeric) or numeric <= 0:
                    continue
                nav.setdefault(day, {})[code] = {
                    "nav": numeric,
                    "corporate_action": "unknown",
                    "source_url": f"https://fundf10.eastmoney.com/jjjz_{code}.html",
                    "published_at": None,
                }
        except Exception as exc:
            failures[code] = f"{type(exc).__name__}: {str(exc)[:120]}"
    return nav, failures


def fetch_live_csi300(prices):
    """Augment the frozen Tencent CSV with Eastmoney CSI300 K-line observations.

    Cross-check the overlapping last historic close. Retain source provenance
    and never overwrite earlier frozen prices from the CSV.
    """
    import requests
    last = max(prices)
    start = (datetime.strptime(last, "%Y-%m-%d") - timedelta(days=12)).strftime("%Y%m%d")
    end = datetime.now(timezone(timedelta(hours=8))).strftime("%Y%m%d")
    url = "https://push2his.eastmoney.com/api/qt/stock/kline/get?" + urlencode({
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56",
        "ut": "7eea3edcaed734bea9cbfc24409ed989",
        "klt": 101, "fqt": 0, "secid": "1.000300",
        "beg": start, "end": end, "lmt": 1000,
    })
    metadata = {"source_url": url, "provider": "Eastmoney CSI300 index Kline",
                "source_first_public_times": "UNVERIFIED", "baseline_last_day": last}
    try:
        resp = requests.get(url, timeout=30, headers={
            "User-Agent": "Mozilla/5.0", "Referer": "https://quote.eastmoney.com/",
        })
        resp.raise_for_status()
        payload = resp.json()
        lines = (payload.get("data") or {}).get("klines") or []
        updated = {}
        overlap = 0
        for line in lines:
            parts = line.split(",")
            if len(parts) < 3:
                continue
            day, close = parts[0], float(parts[2])
            if not math.isfinite(close) or close <= 0 or day > datetime.now(timezone.utc).date().isoformat():
                continue
            if day in prices:
                overlap += 1
                if abs(close / prices[day] - 1) > 0.01:
                    raise ValueError(f"overlapping CSI300 close source conflict on {day}")
            if day > last:
                updated[day] = close
        if overlap == 0:
            raise ValueError("no index-source overlapping close for independent cross-check")
        metadata.update({"status": "SUCCESS", "overlap_days": overlap, "added_days": len(updated),
                         "last_added": max(updated) if updated else None})
        return {**prices, **updated}, metadata
    except Exception as exc:
        metadata.update({"status": "FETCH_FAILED", "error": f"{type(exc).__name__}: {str(exc)[:180]}",
                         "added_days": 0})
        return prices, metadata


def main(argv=None):
    parser = argparse.ArgumentParser(description="EXP-0010 four-ETF daily coverage/event replay")
    parser.add_argument("--shares", required=True, help="Upstream original cache JSON")
    parser.add_argument("--index", required=True, help="CSI300 close CSV")
    parser.add_argument("--nav", help="Retrospective per-day four-ETF NAV JSON")
    parser.add_argument("--fetch-live-index", action="store_true", help="Add dated Eastmoney CSI300 K-lines after cached CSV")
    parser.add_argument("--fetch-nav-akshare", action="store_true")
    parser.add_argument("--denominators", help="CSV index market cap; exact-date source-stamped")
    parser.add_argument("--out", help="JSON output path; defaults to stdout")
    args = parser.parse_args(argv)
    if args.nav and args.fetch_nav_akshare:
        parser.error("supply --nav OR --fetch-nav-akshare, not both")
    if args.fetch_nav_akshare:
        nav, failures = fetch_nav_akshare()
        nav_provenance = {"provider": "AKShare fund_open_fund_info_em / Eastmoney",
                          "first_public_times": "UNVERIFIED",
                          "fund_errors": failures,
                          "funds_with_history": {c: sum(c in d for d in nav.values()) for c in CORE_FOUR}}
    else:
        nav = read_nav(args.nav)
        nav_provenance = {"source": args.nav, "sha256": sha256_file(args.nav)} if args.nav else {}
    prov = {
        "as_of_utc": datetime.now(timezone.utc).isoformat(),
        "share_cache": {"url": SHARES_SOURCE, "sha256": sha256_file(args.shares),
                        "historical_first_public_times": "UNKNOWN"},
        "index": {"url": INDEX_SOURCE, "sha256": sha256_file(args.index)},
        "nav": nav_provenance,
        "denominators": {"path": args.denominators,
                         "sha256": sha256_file(args.denominators)} if args.denominators else None,
        "repo_source_commit": os.environ.get("GITHUB_SHA", "LOCAL_UNVERIFIED"),
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
    }
    index_prices = read_prices(args.index)
    if args.fetch_live_index:
        index_prices, live_meta = fetch_live_csi300(index_prices)
        prov["index_live"] = live_meta
    result = replay(index_prices, read_shares(args.shares), nav=nav,
                    denominators=read_denominators(args.denominators), source_provenance=prov)
    output = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if args.out:
        dst = Path(args.out)
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(output, encoding="utf-8")
    else:
        print(output)
    q = result["data_quality"]
    share = result["summary"]["share_proxy"]["horizons"]
    print(f"V3_OK ratio_days={q['ratio_days']} ratio_pit_verified={q['ratio_pit_verified_days']} "
          f"share_clusters={result['summary']['share_proxy']['event_clusters']} "
          f"share_5d={share['5']['wins']}/{share['5']['matured_events']} "
          f"share_10d={share['10']['wins']}/{share['10']['matured_events']} "
          f"share_20d={share['20']['wins']}/{share['20']['matured_events']}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
