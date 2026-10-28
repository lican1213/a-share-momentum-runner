"""Adversarial 20-session maturity: more than eight daily frozen cohorts remain measurable."""
import json
from datetime import date, timedelta

from national_team import live_paper_tracker as tracker


def test_all_twelve_cohorts_survive_eight_event_old_cap_and_reuse_market_data(tmp_path, monkeypatch):
    day = tmp_path / "2026-10-28"
    day.mkdir()
    events = [{
        "id": f"NT2-unique-{i}",
        "first_public_at": "2026-10-28T23:46:43+08:00",
        "candidate_symbols": ["600519"],
        "strategy_id": f"V2_{i}"
    } for i in range(12)]
    (day / "test.json").write_text(json.dumps({"events": events}), encoding="utf-8")
    sessions = [(date(2026,10,29)+timedelta(days=i)).isoformat() for i in range(28)]
    monkeypatch.setattr(tracker, "exchange_sessions", lambda *args, **kwargs: sessions)
    calls = []
    def fake_prices(_ak, symbol, start, end):
        calls.append(symbol)
        dates = [(date(2026,10,24)+timedelta(days=i)).isoformat() for i in range(38)]
        return {d: {"open": "10", "close": "11",
                    "entry_blocked": False, "exit_blocked": False} for d in dates}, "FIXTURE", "hash"
    monkeypatch.setattr(tracker, "load_history", fake_prices)
    result = tracker.assess(object(), tmp_path, date(2026,11,25))
    assert result["source_events"] == 12
    assert result["eligible_60d_window_count"] == 12
    assert result["assessed_events"] == 12
    assert len(result["result_records"]) == 12
    assert all(r["evaluation"]["results"]["20"]["status"] == "COMPUTED_OHLC_PROXY"
               for r in result["result_records"])
    assert sorted(calls) == ["510300", "600519"], "no duplicate provider pulls per frozen event"
    assert result["errors"] == []


def test_cold_expired_events_not_reloaded_forever(tmp_path):
    d = tmp_path / "2026-01-01"
    d.mkdir()
    (d / "old.json").write_text(json.dumps({"events": [{
        "id":"very-old", "first_public_at":"2026-01-01T22:00:00+08:00",
        "candidate_symbols":["600519"]}]}), encoding="utf-8")
    res = tracker.assess(object(),tmp_path,date(2026,11,25))
    assert res["source_events"]==1
    assert res["eligible_60d_window_count"]==0
    assert res["result_records"]==[]
