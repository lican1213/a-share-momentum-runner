"""Synthetic test for continuous paper-tracking status, never re-report fills."""
import json
from pathlib import Path
from datetime import date
from national_team.live_paper_tracker import assess

def test_no_event_is_not_an_implicit_zero_percent_success(tmp_path):
    class NeverUsed:pass
    o=assess(NeverUsed(),tmp_path,date(2026,10,28))
    assert o["status"]=="NO_FROZEN_PAPER_EVENTS"
    assert o["result_records"]==[]

def test_new_event_is_kept_pending_not_returned_as_profitable(tmp_path,monkeypatch):
    from national_team import live_paper_tracker as tracker
    event={"id":"NT-unique-1","strategy_id":"S1_FLOW_OVER_ADV20",
           "first_public_at":"2026-10-28T22:00:00+08:00",
           "candidate_symbols":["600519"],"benchmark_etf":"510300"}
    d=tmp_path/"2026-10-28";d.mkdir()
    (d/"one.json").write_text(json.dumps({"events":[event]}))
    (d/"two.json").write_text(json.dumps({"events":[event]}))  # duplicate run
    monkeypatch.setattr(tracker,"exchange_sessions",lambda *args,**kwargs:["2026-10-27","2026-10-28"])
    o=tracker.assess(object(),tmp_path,date(2026,10,28))
    assert o["source_events"]==1
    assert o["result_records"][0]["status"]=="NOT_MATURED_YET"
    assert "paired_excess_net_return" not in str(o)
