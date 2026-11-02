"""Freeze a new-day EXP-0012 left-side paper event from *matched* real sources."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from national_team.left_entry_v5 import freeze
from national_team.left_entry_v4 import digest
from national_team.ohlc_fallback_v5 import backfill_asof_prices
from scripts.run_national_team_left_entry_v4 import collect, next_weekday

BJ = ZoneInfo("Asia/Shanghai")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--v3", required=True)
    parser.add_argument("--watch", required=True)
    parser.add_argument("--policy", choices=("SHALLOW_DIP", "DEEP_DIP"), required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--prices", help="test-only previously captured OHLC")
    parser.add_argument("--max-stocks", type=int, default=150)
    args = parser.parse_args()
    v3 = json.loads(Path(args.v3).read_text(encoding="utf-8"))
    watch = json.loads(Path(args.watch).read_text(encoding="utf-8"))
    asof = v3["daily"][-1]["date"]
    if args.prices:
        prices = json.loads(Path(args.prices).read_text(encoding="utf-8"))
    else:
        import akshare as ak
        prices = collect(ak, watch, asof, max_stocks=args.max_stocks)
        prices = backfill_asof_prices(prices, asof)
    now = datetime.now(BJ)
    result = freeze(v3, watch, prices, now=now.isoformat(),
                    next_session=next_weekday(now.date()),
                    selected_policy=args.policy)
    result["collection_errors"] = prices.get("collection_errors", {})
    result["collection_scope"] = {
        "completed_stock_source_count": len(prices.get("stocks", {})),
        "requested_source_count": len(prices.get("universe", [])),
        "baostock_recovered": len(prices.get("fallback_recovered_codes", [])),
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "run_commit": os.environ.get("GITHUB_SHA"),
    }
    result.pop("freeze_payload_sha256", None)
    result["freeze_payload_sha256"] = digest(result)
    out = Path(args.out)
    if out.exists():
        raise FileExistsError("refuse to rewrite paper intent")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    print(json.dumps({
        "experiment": result["experiment_id"],
        "session": asof,
        "policy": args.policy,
        "ohlc_verified": result["universe"]["ohlc_verified"],
        "unrisen_eligible": sum(float(x["r5"]) <= 0
                               for x in result["candidates_ranked"]),
        "primary": [o["stock"] for o in result["accounts"]["F1_LEFT"]["orders"]],
        "shadow": {
            k: [o["stock"] for o in p["orders"]]
            for k, p in result["paper_policies"].items()
        },
        "broker_orders": len(result["broker_orders"]),
        "out": str(out),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
