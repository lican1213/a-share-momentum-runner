"""Report GitHub Actions clock drift without changing any paper intent or fill."""
from __future__ import annotations

import argparse
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

BJ = ZoneInfo("Asia/Shanghai")
WARN_AFTER_MINUTES = 60


def latest_weekday_cron_before(now: datetime, cron: str) -> datetime:
    """Expected most recent weekday cron tick, expressed in Shanghai time."""
    fields = cron.split()
    if len(fields) != 5 or fields[2:] != ["*", "*", "1-5"]:
        raise ValueError("only the project's fixed Monday-Friday cron is supported")
    minute, hour = (int(fields[0]), int(fields[1]))
    if not 0 <= minute <= 59 or not 0 <= hour <= 23:
        raise ValueError("invalid UTC cron minute/hour")
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("scheduler observation requires a timezone")
    local = now.astimezone(BJ)
    for delta in range(8):
        day = local.date() - timedelta(days=delta)
        if day.weekday() >= 5:
            continue
        expected = datetime(day.year, day.month, day.day, hour, minute, tzinfo=timezone.utc)
        # UTC cron ticks, not Shanghai clock times.
        if expected <= now.astimezone(timezone.utc):
            return expected.astimezone(BJ)
    raise ValueError("no recent scheduled weekday tick")


def diagnose(now: datetime, cron: str, upstream_completed_at: str = "") -> dict:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("timezone-aware clock required")
    if upstream_completed_at:
        expected = datetime.fromisoformat(upstream_completed_at.replace("Z", "+00:00"))
        if expected.utcoffset() is None:
            raise ValueError("upstream completed_at must carry a timezone")
        trigger = "WORKFLOW_RUN_UPSTREAM_SUCCESS"
    else:
        expected = latest_weekday_cron_before(now, cron)
        trigger = "SCHEDULE_OR_MANUAL_REFERENCE"
    lag = max(0, int((now - expected).total_seconds() // 60))
    return {
        "trigger": trigger,
        "expected_bj": expected.astimezone(BJ).isoformat(),
        "observed_bj": now.astimezone(BJ).isoformat(),
        "lag_minutes": lag,
        "status": "DELAYED" if lag > WARN_AFTER_MINUTES else "ON_TIME",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cron", required=True)
    parser.add_argument("--upstream-completed-at", default="")
    args = parser.parse_args()
    event = os.environ.get("GITHUB_EVENT_NAME", "local")
    now = datetime.now(timezone.utc)
    # Manual/push events have no scheduled deadline and should not be marked late.
    if event not in ("schedule", "workflow_run"):
        print(f"SCHEDULE_LATENCY_NOT_APPLICABLE event={event}")
        return
    if event == "workflow_run" and not args.upstream_completed_at:
        raise ValueError("workflow_run must provide its upstream completion time")
    result = diagnose(now, args.cron, args.upstream_completed_at if event == "workflow_run" else "")
    line = (f"SCHEDULE_LATENCY event={event} status={result['status']} "
            f"lag_minutes={result['lag_minutes']} expected_bj={result['expected_bj']} "
            f"observed_bj={result['observed_bj']}")
    print(line)
    if result["status"] == "DELAYED":
        print(f"::warning title=Workflow schedule delay::{line}")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a", encoding="utf-8") as target:
            target.write("| Trigger | Scheduled/upstream (Beijing) | Observed (Beijing) | Lag min | Status |\n")
            target.write("|---|---|---|---:|---|\n")
            target.write(f"| {event} | {result['expected_bj']} | {result['observed_bj']} | "
                         f"{result['lag_minutes']} | {result['status']} |\n")


if __name__ == "__main__":
    main()
