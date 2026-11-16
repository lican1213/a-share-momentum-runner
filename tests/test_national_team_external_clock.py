from datetime import datetime
from scripts.dispatch_national_team_if_late import evaluate

NOW=datetime.fromisoformat("2026-11-16T08:05:00+08:00")


def test_missing_slot_and_actual_success():
    assert evaluate(NOW,[])=="DISPATCH_MISSING_ROOT_SLOT"
    assert evaluate(NOW,[{"created_at":"2026-11-15T23:54:00Z","status":"completed",
                          "conclusion":"success"}])=="ROOT_SLOT_ALREADY_SUCCEEDED"
    assert evaluate(NOW,[{"created_at":"2026-11-15T23:54:00Z","status":"completed",
                          "conclusion":"failure"}])=="DISPATCH_MISSING_ROOT_SLOT"


def test_active_run_and_wrong_dates_do_not_forge_freshness():
    assert evaluate(NOW,[{"created_at":"2026-11-13T08:20:00Z","status":"in_progress"}])=="ROOT_ACTIVE_STALLED"
    assert evaluate(NOW,[{"created_at":"2026-11-15T23:55:00Z","status":"queued"}])=="ACTIVE_ROOT_ALREADY_EXISTS"
    assert evaluate(NOW,[{"created_at":"2026-11-13T08:20:00Z","status":"completed",
                         "conclusion":"success"}])=="DISPATCH_MISSING_ROOT_SLOT"
    assert evaluate(NOW.replace(hour=7),[])=="OUTSIDE_WATCHDOG_WINDOW"
    assert evaluate(NOW.replace(day=15),[])=="SKIP_WEEKEND"
