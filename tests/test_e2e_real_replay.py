"""Real immutable market-evidence end-to-end replay: source -> 4ETF -> stock -> paper -> audit.

No synthetic financial figures. Historical data was first captured 2026-10-28
so this test is SOURCE/ENGINEERING acceptance, NOT a profitable OOS backtest.
"""
import json
from pathlib import Path
from national_team.paper_events import freeze_watch
from national_team.audit_gate import audit,AuditViolation
from national_team.forward_evaluation import evaluate_frozen_event

ROOT=Path(__file__).resolve().parents[1]
RUN="40702572594"
BASE=ROOT/"records"

def load(folder):
    p=BASE/folder/"2026-10-28"/f"{RUN}-a1.json"
    return json.loads(p.read_text(encoding="utf-8"))

def test_real_archived_four_etf_to_stock_watch_to_frozen_paper_to_independent_red_team():
    source=load("national_team_etf")
    merged=load("national_team_merged")
    watch=load("national_team_watch")
    frozen=freeze_watch(watch,
        source_path=f"records/national_team_watch/2026-10-28/{RUN}-a1.json",
        model_sha="actual-source-evidence-replay")
    assert frozen["status"]=="FROZEN_PROSPECTIVE_RESEARCH_EVENTS"
    assert {x["strategy_id"] for x in frozen["events"]}=={
        "S1_FLOW_OVER_ADV20","S2_FLOW_PLUS_PRICE_STRENGTH"
    }
    assert len(frozen["events"][0]["candidate_symbols"])==5
    assert frozen["events"][0]["ETF_PCF_verified"] is False
    for event in frozen["events"]:
        assert event["first_public_at"].startswith("2026-10-28T22:08")
        assert event["benchmark_etf"]=="510300"
        assert event["broker_trades_authorized"] is False
    result=audit({"source":source,"merged":merged,"watch":watch,"frozen":frozen})
    assert result["status"]=="RESEARCH_DATA_AUDIT_PASS"
    assert result["funds"]["verified"] is True
    assert result["stock_proxy"]["verified"] is True
    assert result["paper"]["count"]==2
    assert result["audit_does_not_prove_alpha"] is True
    assert result["audit_does_not_verify_actual_broker_execution"] is True

def test_frozen_first_discovery_cannot_become_2026_10_27_historical_trade():
    watch=load("national_team_watch")
    frozen=freeze_watch(watch,source_path="real-origin",model_sha="test")
    event=frozen["events"][0]
    assert event["funding_underlying_day"]=="2026-10-27"
    assert event["first_public_at"][:10]=="2026-10-28"
    # Historical event date occurs before public capture; no simulated
    # trading session in the prior date can be called a strategy fill.
    r=evaluate_frozen_event(event,["2026-10-26","2026-10-27"],{})
    assert r["status"]=="ENTRY_NOT_YET_AVAILABLE"
