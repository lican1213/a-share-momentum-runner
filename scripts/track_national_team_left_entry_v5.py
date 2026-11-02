"""Track all recent EXP-0012 event freezes; compare two shadow paper rankings."""
from __future__ import annotations

import argparse
import copy
import json
import os
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from national_team.left_entry_outcomes import track
from national_team.left_entry_v4 import digest
from national_team.left_entry_v5 import POLICIES, RIGHT_POLICY
from national_team.ohlc_fallback_v5 import backfill_future_bars
from scripts.track_national_team_left_entry_v4 import collect

BJ = ZoneInfo("Asia/Shanghai")


def recent_freezes(root, *, today, max_events=24):
    latest = {}
    for path in sorted(Path(root).glob("*/*.json")):
        obj = json.loads(path.read_text(encoding="utf-8"))
        if obj.get("experiment_id") != "EXP-0012":
            continue
        signal = obj["signal_session"]
        if signal >= today:
            continue
        if signal not in latest:
            latest[signal] = (path, obj)
    return [latest[key] for key in sorted(latest)[-max_events:]]


def follow_one(ak, frozen, source_path, asof):
    # A common OHLC snapshot for both models: no one gets more recent prices.
    group_orders = []
    stock_codes = set()
    active_policies = [p for p in (*POLICIES, RIGHT_POLICY)
                       if p in frozen["paper_policies"]]
    for policy in active_policies:
        for order in frozen["paper_policies"][policy]["orders"]:
            if order["stock"] not in stock_codes:
                group_orders.append(order)
                stock_codes.add(order["stock"])
    shared = copy.deepcopy(frozen)
    shared["accounts"]["F1_LEFT"]["orders"] = group_orders
    seen = collect(ak, shared, asof)
    seen = backfill_future_bars(seen, ["510300", *sorted(stock_codes)],
                                frozen["signal_session"], asof)
    # All market-source retrieval must predate the actual evaluation clock.
    seen["capture_time"] = datetime.now(BJ).isoformat()
    seen["first_observed_at"] = seen["capture_time"]
    observed_at = datetime.now(BJ).isoformat()
    policy_results = {}
    for policy in active_policies:
        model = copy.deepcopy(frozen)
        model["accounts"]["F1_LEFT"]["orders"] = frozen["paper_policies"][policy]["orders"]
        outcome = track(model, seen, observed_at=observed_at)
        policy_results[policy] = {
            "F1_LEFT": outcome["F1_LEFT"],
            "F2_WEAK": outcome["F2_WEAK"],
            "errors": outcome["errors"],
            "source_new_ohlc_sha256": outcome["source_new_ohlc_sha256"],
        }
    return {
        "experiment_id": "EXP-0012",
        "source_freeze_sha256": frozen["freeze_payload_sha256"],
        "freeze_path": str(source_path),
        "signal_session": frozen["signal_session"],
        "cluster_anchor": frozen["cluster_anchor"],
        "extension_experiment_id": frozen.get("extension_experiment_id"),
        "asof": asof,
        "first_observed_at": observed_at,
        "policy_results": policy_results,
        "source_new_ohlc": seen,
        "source_new_ohlc_sha256": digest(seen),
        "trade_authorized": False,
        "broker_orders": [],
        "execution": "OHLC_OPEN_SCENARIO_NOT_BROKER_FILL",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--freeze-root", default="records/national_team_left_entry_v5")
    ap.add_argument("--max-events", type=int, default=24)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    now = datetime.now(BJ)
    asof = now.date().isoformat()
    import akshare as ak
    freezes = recent_freezes(args.freeze_root, today=asof, max_events=args.max_events)
    results = []
    for path, frozen in freezes:
        results.append(follow_one(ak, frozen, path, asof))
    batch = {
        "schema": 1, "version": "NT_EVENT_FOLLOWUP_V5",
        "experiment_id": "EXP-0012", "asof": asof,
        "capture_time": datetime.now(BJ).isoformat(),
        "akshare_version": getattr(ak, "__version__", "UNKNOWN"),
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "results": results,
        "tracked_freeze_count": len(results),
        "trade_authorized": False, "broker_orders": [],
    }
    batch["snapshot_sha256"] = digest(batch)
    out = Path(args.out)
    if out.exists():
        raise FileExistsError("refuse to overwrite outcome evidence")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(batch, indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    print(json.dumps({
        "asof": asof, "tracked_events": len(results),
        "policies": list((*POLICIES, RIGHT_POLICY)),
        "paired_10d": sum(any(
            h.get("status") == "PAIRED"
            for p in r["policy_results"].values()
            for item in p["F1_LEFT"]
            for h in [item.get("horizons", {}).get("10", {})]
        ) for r in results),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
