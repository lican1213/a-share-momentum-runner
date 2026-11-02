"""Capture official-policy evidence before the existing 18:05 V5 ETF router."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from national_team.policy_overlay import collect_snapshot, load_prior_first_seen


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--history-root", default="records/national_team_policy")
    parser.add_argument("--out", required=True)
    parser.add_argument("--now", help="timezone-aware Beijing capture time for replay")
    args = parser.parse_args()
    stamp = args.now or datetime.now(ZoneInfo("Asia/Shanghai")).isoformat()
    result = collect_snapshot(now=stamp, prior_first_seen=load_prior_first_seen(args.history_root))
    path = Path(args.out)
    if path.exists():
        raise FileExistsError("policy snapshot already exists")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "policy_source_health": result["source_health"],
        "source_results": [{k: s[k] for k in ("source", "status", "fetched", "relevant")}
                           for s in result["sources"]],
        "policy_events": len(result["events"]),
        "out": str(path),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
