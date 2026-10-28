"""2026 aggregate ETF units must invalidate stale 2025 national-team identity claims."""
import json
from pathlib import Path
import pytest
from national_team.holder_evidence import (
    reconcile_latest_total_historical_holders,HolderEvidenceError,
)

def fixture():
    h=json.loads(Path("data/national_team_holders/159919-2024H1-2025H1.json").read_text())
    total=json.loads(Path("data/national_team_holders/159919-2026H1-fund-total.json").read_text())
    return h,total

def test_2025_huijin_holdings_impossible_to_carry_unchanged_into_2026_whole_fund():
    old,latest=fixture()
    out=reconcile_latest_total_historical_holders(old,latest,"2026-10-28")
    assert out["status"]=="HISTORICAL_NATIONAL_TEAM_HOLDINGS_EXCEED_NEW_TOTAL"
    assert out["historical_two_Huijin_entities_shares"]=="35498494985"
    assert out["new_whole_fund_total_shares"]=="6939216676"
    assert out["prior_combined_holdings_exceed_new_total_by_shares"]=="28559278309"
    assert out["can_assert_prior_named_holdings_unchanged_in_new_period"] is False
    assert out["proved_exact_sale_dates_or_counterparties"] is False

def test_fund_total_not_known_before_publication():
    old,latest=fixture()
    out=reconcile_latest_total_historical_holders(old,latest,"2026-08-30")
    assert out["status"]=="LATER_FUND_TOTAL_NOT_YET_PUBLIC"

def test_reject_misreported_new_fund_total():
    old,latest=fixture()
    latest["total_fund_shares"]="7000000000"
    with pytest.raises(HolderEvidenceError,match="does not reconcile"):
        reconcile_latest_total_historical_holders(old,latest,"2026-10-28")

def test_wrong_fund_cannot_be_used_to_declare_old_holders_exited():
    old,latest=fixture()
    latest["asset"]="510300"
    with pytest.raises(HolderEvidenceError,match="fund mismatch"):
        reconcile_latest_total_historical_holders(old,latest,"2026-10-28")
