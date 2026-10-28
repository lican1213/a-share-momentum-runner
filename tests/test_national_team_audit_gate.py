"""Adversarial mutations must cause a RED audit, not quietly pass."""
import copy
import pytest
from national_team.record_merge import merge_snapshot_records
from national_team.event_pipeline import reconcile_funding_snapshot
from national_team.audit_gate import check_funding, audit, AuditViolation
from national_team.core_flow_factors import CORE_FOUR

DAYS=["2026-10-19","2026-10-20","2026-10-21","2026-10-22","2026-10-23","2026-10-26"]
STAMP="2026-10-28T23:00:00+08:00"

def source():
    rows={d:{code:{"shares":str(100000000+i*100000),"nav":"4"}
              for code in CORE_FOUR} for i,d in enumerate(DAYS)}
    return {"asof_requested":"2026-10-28","run_id":"rawrun",
            "capture_completed_beijing":"2026-10-28T22:00:00+08:00",
            "observations_by_date":rows}

def inputs():
    raw=source()
    merged=merge_snapshot_records([("records/source.json",raw)],"2026-10-28",at=STAMP)
    merged["funding_event"]=reconcile_funding_snapshot(merged,DAYS)
    watch={"status":"WATCHLIST_BUILD_UNAVAILABLE"}
    frozen={"status":"NO_FREEZABLE_RANKING","events":[]}
    return {"source":raw,"merged":merged,"watch":watch,"frozen":frozen}

def test_true_original_observations_recompute_independently():
    data=inputs()
    r=check_funding(data["merged"])
    assert r["result"]=="FOUR_ETF_FUNDING_RECALCULATED"
    assert r["verified"] is True
    assert r["day_net_creation_proxy_cny"]=="1600000"
    combined=audit(data)
    assert combined["status"]=="RESEARCH_PARTIAL_SOURCES_AUDITED"
    assert combined["funds"]["verified"]

def test_tampered_daily_cashflow_is_rejected():
    data=inputs()
    data["merged"]["funding_event"]["four_etf_factor"]["daily_net_creation_proxy_cny"]="999"
    with pytest.raises(AuditViolation,match="daily ETF flow mismatch"):
        audit(data)

def test_tampered_five_day_flow_is_rejected():
    data=inputs()
    data["merged"]["funding_event"]["four_etf_factor"]["five_day"]["net_creation_cny_daily_sum"]="1000"
    with pytest.raises(AuditViolation,match="5d ETF flow mismatch"):
        audit(data)

def test_original_evidence_run_required_in_merge():
    data=inputs()
    data["merged"]["sources_used"][0]["run_id"]="fabricated"
    with pytest.raises(AuditViolation,match="provenance"):
        audit(data)
