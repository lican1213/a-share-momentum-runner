"""Independent audit of REAL persisted 2026-10-28 market records, not fixtures.

These are historical research inputs with first-observed timestamp 2026-10-28,
NOT executed historical trades. Fixed run ID is an immutable acceptance sample.
"""
import copy,json
from pathlib import Path
import pytest
from national_team.audit_gate import check_funding,check_stock_watch,AuditViolation

ROOT=Path(__file__).resolve().parents[1]
ETF=ROOT/"records/national_team_merged/2026-10-28/40702572594-a1.json"
WATCH=ROOT/"records/national_team_watch/2026-10-28/40702572594-a1.json"

def record(p):
    return json.loads(p.read_text(encoding="utf-8"))

def test_real_four_etf_snapshot_can_be_recomputed_without_factor_helper():
    funding=record(ETF)
    audit=check_funding(funding)
    assert audit["verified"]
    assert audit["day_net_creation_proxy_cny"]=="5612203530.000000"
    assert audit["unusually_large_abs_five_day_intensity"] is True
    assert funding["conflicted_date_code_pairs"]==0
    assert len(funding["funding_event"]["complete_four_days"])>=6

def test_real_30_stock_watchlist_is_consistent_with_official_index_weights_and_true_flow():
    funding=record(ETF)
    watch=record(WATCH)
    result=check_stock_watch(watch,funding)
    assert result["verified"]
    assert result["sampled_constituents"]==30
    assert result["candidate_rows_checked"]>=5
    assert not result["all_300_constituents_covered"]

def test_real_market_record_mutation_trips_audit_instead_of_hiding_it():
    funding=record(ETF)
    watch=record(WATCH)
    watch["research_ranking"]["candidates"][0]["implied_index_exposure_cny"]="9999999999999"
    with pytest.raises(AuditViolation,match="weight arithmetic"):
        check_stock_watch(watch,funding)
