"""Real archived source regression: digest cannot relabel partial ETF flow as full."""
from pathlib import Path
import json,copy
from national_team.daily_report import compile_digest,human_readable,compile_latest,supplement_prior_full_four
from national_team.holder_evidence import evidence_as_known_at

ROOT=Path(__file__).resolve().parents[1]
RUN="40706300084-a1.json"
DAY="2026-10-28"

def inputs():
    def read(f):return json.loads((ROOT/f).read_text(encoding="utf-8"))
    return (
        read(f"records/national_team_merged/{DAY}/{RUN}"),
        read(f"records/national_team_watch/{DAY}/{RUN}"),
        read(f"records/national_team_events/{DAY}/{RUN}"),
        read(f"records/national_team_paper/{DAY}/{RUN}"),
        read(f"records/national_team_audits/{DAY}/{RUN}"),
        read("data/national_team_holders/159919-2024H1-2025H1.json"),
    )

def test_genuine_archived_150_stock_snapshot_does_not_invent_national_team_buy():
    result=compile_digest(*inputs())
    assert result["status"]=="EVIDENCE_BACKED_RESEARCH_DIGEST"
    assert result["ranked_stocks_count"]==150
    assert result["latest_partial_flow_cny"]=="1670914440.000000"
    assert result["latest_partial_fund_scope"]==["510300","510310","510330"]
    assert result["latest_ranked_stock_date"]=="2026-10-28"
    assert result["S1_observation"][0]["symbol"]=="601825"
    assert result["S2_frozen_observation"][0]=="600000"
    assert result["independent_after_cost_alpha_validated"] is False
    assert result["last_known_legal_holder"]["latest_period_end"]=="2025-06-30"
    assert result["fund_flow_identifies_a_specific_national_team_investor"] is False

def test_mismatched_stock_signal_date_can_never_produce_ranked_claim():
    merged,watch,events,paper,audit,holders=inputs()
    watch["funding_date"]="2026-10-20"
    out=compile_digest(merged,watch,events,paper,audit,holders)
    assert out["S1_observation"]==[]
    assert out["audit_approved_candidate_display"] is False

def test_failed_red_team_censors_all_stock_research_candidates():
    merged,watch,events,paper,audit,holders=inputs()
    audit["failures"]=["deliberate data tampering"]
    out=compile_digest(merged,watch,events,paper,audit,holders)
    assert out["status"]=="PARTIAL_RESEARCH_DIGEST"
    assert out["S1_observation"]==[]

def test_report_says_not_verified_and_prior_2025_holder():
    result=compile_digest(*inputs())
    prose=human_readable(result)
    assert "159919" in prose
    assert "2025-06-30" in prose
    assert "尚未证实" in prose
    assert "601825" in prose
    assert "10月28日" not in prose # machine date remains ISO

def test_latest_saved_complete_evidence_can_be_discovered_without_network():
    day,filename,digest=compile_latest(ROOT)
    assert day>="2026-10-28"
    assert filename.endswith(".json")
    assert digest["audit_status"].startswith("RESEARCH_")


def test_prior_complete_four_is_recovered_from_independently_audited_archived_run():
    day,filename,d=compile_latest(ROOT)
    assert d["latest_full_four_funding_date"]=="2026-10-27"
    assert d["full_four_daily_flow_cny"]=="5612203530.000000"
    assert d["full_four_factor_carried_forward"] is True
    assert "national_team_merged" in d["full_four_prior_source_path"]
    assert d["latest_partial_funding_dates"]==["2026-10-27","2026-10-28"]
    assert d["latest_partial_flow_cny"]=="1670914440.000000"
    assert "不得" not in human_readable(d) or "不可相加" in human_readable(d)


def test_future_discovered_complete_four_cannot_backdate_into_old_signal():
    d=compile_digest(*inputs())
    v=supplement_prior_full_four(d,ROOT,signal_public_at="2026-10-28T00:00:00+08:00")
    assert v["full_four_factor_carried_forward"] is False
    assert v["latest_full_four_funding_date"] is None
