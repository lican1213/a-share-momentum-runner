"""EXP-0016 verifies completion chaining and honest scheduler lateness."""
from datetime import datetime, timezone
from pathlib import Path

from scripts.check_national_team_schedule_latency import diagnose, latest_weekday_cron_before

ROOT = Path(__file__).resolve().parents[1]


def test_real_nov_2_scheduled_runs_report_ten_hour_delay():
    cases = (
        ("25 9 * * 1-5", "2026-11-02T19:35:57+00:00", 610),
        ("5 10 * * 1-5", "2026-11-02T20:02:08+00:00", 597),
        ("45 10 * * 1-5", "2026-11-02T20:29:49+00:00", 584),
    )
    for cron, actual, expected_lag in cases:
        result = diagnose(datetime.fromisoformat(actual), cron)
        assert result["lag_minutes"] == expected_lag
        assert result["status"] == "DELAYED"


def test_upstream_completion_chaining_uses_actual_timestamp_not_cron():
    now = datetime.fromisoformat("2026-11-02T19:40:00+00:00")
    status = diagnose(now, "5 10 * * 1-5", "2026-11-02T19:37:04Z")
    assert status["trigger"] == "WORKFLOW_RUN_UPSTREAM_SUCCESS"
    assert status["lag_minutes"] == 2
    assert status["status"] == "ON_TIME"


def test_weekend_and_beijing_utc_day_boundary():
    monday = datetime.fromisoformat("2026-11-02T10:27:00+00:00")
    assert latest_weekday_cron_before(monday, "25 9 * * 1-5").isoformat() == (
        "2026-11-02T17:25:00+08:00")
    before_monday = datetime.fromisoformat("2026-11-02T00:00:00+00:00")
    assert latest_weekday_cron_before(before_monday, "25 9 * * 1-5").date().isoformat() == (
        "2026-10-30")


def test_completion_dependency_with_scheduled_fallbacks_is_explicit():
    v3 = (ROOT / ".github/workflows/national-team-v3-replay.yml").read_text()
    router = (ROOT / ".github/workflows/national-team-event-router-v5.yml").read_text()
    outcome = (ROOT / ".github/workflows/national-team-left-outcomes-v5.yml").read_text()
    assert "name: National-team V3 four-ETF coverage and historical event replay" in v3
    assert "workflows: ['National-team V3 four-ETF coverage and historical event replay']" in router
    assert "workflows: ['National-team EXP-0012 event router and self-iterating left-side paper']" in outcome
    for workflow in (router, outcome):
        assert "types: [completed]" in workflow
        assert "github.event.workflow_run.conclusion == 'success'" in workflow
        assert "cron:" in workflow and "schedule:" in workflow
        assert "scripts/check_national_team_schedule_latency.py" in workflow


def test_old_nov3_intent_remains_nov4_and_is_not_rewritten():
    # The scheduler patch must not touch this trading-date rule or earlier records.
    from datetime import date

    from scripts.run_national_team_left_entry_v4 import next_weekday

    assert next_weekday(date(2026, 11, 3)) == "2026-11-04"
    old_file = ROOT / "records/national_team_left_entry_v5/2026-11-03/41515451702-a1.json"
    if old_file.exists():
        import json
        snapshot = json.loads(old_file.read_text(encoding="utf-8"))
        assert snapshot["paper_policies"]["SHALLOW_DIP"]["orders"][0]["intended_session"] == "2026-11-04"
