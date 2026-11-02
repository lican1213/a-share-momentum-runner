"""Write a daily immutable dispatcher decision and GitHub Actions step outputs."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from national_team.event_router_v5 import route, with_digest

BJ = ZoneInfo("Asia/Shanghai")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--v3-root", default="records/national_team_v3")
    ap.add_argument("--watch-root", default="records/national_team_watch")
    ap.add_argument("--freeze-root", default="records/national_team_left_entry_v5")
    ap.add_argument("--followup-root", default="records/national_team_left_outcomes_v5")
    ap.add_argument("--out", required=True)
    ap.add_argument("--github-output", help="GITHUB_OUTPUT from Actions; optional")
    ap.add_argument("--now", help="timezone-aware fixture time; defaults to Asia/Shanghai now")
    args = ap.parse_args()
    stamp = args.now or datetime.now(BJ).isoformat()
    decision = route(args.v3_root, args.watch_root,
                     args.freeze_root, args.followup_root, now=stamp)
    decision["github_run_id"] = os.environ.get("GITHUB_RUN_ID")
    decision["github_source_commit"] = os.environ.get("GITHUB_SHA")
    decision = with_digest(decision)
    destination = Path(args.out)
    if destination.exists():
        raise FileExistsError("immutable router event exists")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(decision, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    if args.github_output:
        # Path values are returned only from repository records enumerated by the router.
        lines = {
            "dispatch": "true" if decision["status"] == "NEW_FUNDING_EVENT" else "false",
            "v3_path": decision["v3_path"],
            "watch_path": decision["watch_path"] or "",
            "selected_policy": decision["selected_policy"],
            "event_id": decision["event_id"],
        }
        with Path(args.github_output).open("a", encoding="utf-8") as fh:
            for key, value in lines.items():
                if "\n" in value or "\r" in value:
                    raise ValueError("unsafe output value")
                fh.write(key + "=" + value + "\n")
    print(json.dumps({
        "event": decision["event_id"], "status": decision["status"],
        "policy": decision["selected_policy"],
        "paired_10d_events": decision["feedback"]["paired_10d_events"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
