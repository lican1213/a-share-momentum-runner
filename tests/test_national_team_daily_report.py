"""Real archived source regression: digest cannot relabel partial ETF flow as full."""
from pathlib import Path
import json,copy
from national_team.daily_report import compile_digest,human_readable,compile_latest,supplement_prior_full_four,attach_v2_freezes
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


def test_latest_complete_four_can_be_from_same_run_or_independently_audited_archive():
    day, filename, d=compile_latest(ROOT)
    # A newly archived *real* 2026-10-28 full-four observation supersedes the
    # earlier 2026-10-27 factor. Old test asserted stale dates forever.
    expected_date="2026-10-28" if day>="2026-10-29" else "2026-10-27"
    expected_amt=("3246374430.000000" if expected_date=="2026-10-28"
                  else "5612203530.000000")
    assert d["latest_full_four_funding_date"]==expected_date
    assert d["full_four_daily_flow_cny"]==expected_amt
    if d["full_four_factor_carried_forward"]:
        assert "national_team_merged" in d["full_four_prior_source_path"]
    else:
        assert d["source_paths"]["merged"].startswith("records/national_team_merged/")
        current=json.loads((ROOT/d["source_paths"]["merged"]).read_text(encoding="utf-8"))
        assert current["funding_event"]["four_etf_factor"]["trade_date"]==expected_date
        assert current["funding_event"]["four_etf_factor"]["daily_net_creation_proxy_cny"]==expected_amt
        assert current["funding_event"]["four_etf_factor"]["investor_identity_attributable"] is False
    assert d["latest_partial_funding_dates"]==["2026-10-27","2026-10-28"]
    assert d["latest_partial_flow_cny"]=="1670914440.000000"
    assert "不得" not in human_readable(d) or "不可相加" in human_readable(d)


def test_future_discovered_complete_four_cannot_backdate_into_old_signal():
    d=compile_digest(*inputs())
    v=supplement_prior_full_four(d,ROOT,signal_public_at="2026-10-28T00:00:00+08:00")
    assert v["full_four_factor_carried_forward"] is False
    assert v["latest_full_four_funding_date"] is None


def test_duplicate_current_run_retains_first_immutable_s2_cohort():
    day,filename,d=compile_latest(ROOT)
    assert d["latest_ranked_stock_date"]=="2026-10-28"
    assert d["S2_frozen_observation"]==["600000","601816","601166","600519","000333"]
    assert d.get("S2_immutable_event_id","").endswith("S2_FLOW_PLUS_PRICE_STRENGTH") or not d["S2_restored_from_earlier_immutable_event"]


def test_primary_report_restores_only_v2_freeze_public_at_its_actual_cutoff():
    day, filename, d=compile_latest(ROOT)
    assert d["latest_full_four_funding_date"] in ("2026-10-27","2026-10-28")
    # The 2026-10-29 stock-watch was first public 15:15; the independent
    # V2 10/28-flow freeze occurred at 16:26. Do not leak the latter backward.
    if d["latest_full_four_funding_date"]=="2026-10-28":
        assert d["v2_cohort_status"]=="NO_MATCHING_V2_FREEZE"
        assert d["v2_s1_frozen_symbols"]==[]
        restored=attach_v2_freezes(dict(d),ROOT,"2026-10-29T17:30:00+08:00")
        assert restored["v2_cohort_status"]=="ORIGINAL_FREEZE_VERIFIED"
        assert restored["v2_funding_date"]=="2026-10-28"
        assert restored["v2_frozen_at"].startswith("2026-10-29T16:26:45")
    else:
        restored=d
        assert d["v2_cohort_status"]=="ORIGINAL_FREEZE_VERIFIED"
        assert d["v2_frozen_at"].startswith("2026-10-28T23:46:43")
    assert restored["v2_s1_frozen_symbols"]==["601825","600000","601229","601166","600519"]
    assert restored["v2_s2_frozen_symbols"]==["600309","601919","600660","601012","601838"]
    assert restored["v2_s2_frozen_symbols"]!=restored["S2_frozen_observation"]
    prose=human_readable(restored)
    assert "V2 独立选股" in prose and "V1 旧版" in prose
