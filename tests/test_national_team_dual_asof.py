"""Red-team regression: latest 3-ETF observations must not erase prior 4-ETF factor.

Uses true archived 2026-10-28 source and stock watch snapshots, not fake prices.
"""
import json
from pathlib import Path
import copy
import pytest
from national_team.event_pipeline import reconcile_funding_snapshot
from national_team.index_proxy import partial_flow_to_stocks
from national_team.audit_gate import audit,AuditViolation

ROOT=Path(__file__).resolve().parents[1]
RUN="40706300084"
def record(kind):
    return json.loads((ROOT/"records"/kind/"2026-10-28"/f"{RUN}-a1.json").read_text(encoding="utf-8"))

def test_true_later_partial_is_reconciled_alongside_prior_full_four_factor():
    merged=record("national_team_merged")
    old=merged["funding_event"]
    assert old["status"]=="PARTIAL_FUNDING_ONLY"
    result=reconcile_funding_snapshot(merged,old["history_sessions"])
    assert result["status"]=="PARTIAL_LATEST_WITH_PRIOR_FULL_FOUR_FACTOR"
    assert result["latest_available_trading_day"]=="2026-10-28"
    assert result["partial_funding"]["period"]==["2026-10-27","2026-10-28"]
    assert result["partial_funding"]["net_creation_proxy_cny"]=="1670914440.000000"
    assert result["latest_complete_four_etf_factor_date"]=="2026-10-27"
    assert result["four_etf_factor"]["daily_net_creation_proxy_cny"]=="5612203530.000000"
    assert result["four_etf_factor"]["five_day"]

def test_stock_ranker_uses_more_recent_partial_and_preserves_fund_coverage():
    merged=record("national_team_merged")
    merged["funding_event"]=reconcile_funding_snapshot(
        merged,merged["funding_event"]["history_sessions"])
    watch=record("national_team_watch")
    r=partial_flow_to_stocks(merged,watch["index_weight"],watch["stock_snapshots"],top_n=10)
    assert r["data_scope"]=="PARTIAL_SSE_THREE_EXCLUDES_159919"
    assert r["known_ETF_net_flow_proxy_cny"]=="1670914440.000000"
    assert r["missing_funds"]==["159919"]
    assert r["ranked_from_n_stocks"]==150

def test_independent_redteam_distinguishes_prior_four_from_latest_partial():
    merged=record("national_team_merged")
    merged["funding_event"]=reconcile_funding_snapshot(
        merged,merged["funding_event"]["history_sessions"])
    raw=record("national_team_etf")
    watch=record("national_team_watch")
    paper=record("national_team_events")
    result=audit({"source":raw,"merged":merged,"watch":watch,"frozen":paper})
    assert result["status"]=="RESEARCH_PRIOR_FOUR_CURRENT_PARTIAL_AUDITED"
    assert result["funds"]["verified"] and result["stock_proxy"]["verified"]
    assert result["latest_complete_four_factor_date"]=="2026-10-27"
    assert result["stock_signal_trading_day"]=="2026-10-28"
    assert result["funding_and_stock_signals_use_distinct_dates"] is True
    tampered=copy.deepcopy(watch)
    tampered["research_ranking"]["known_ETF_net_flow_proxy_cny"]="999999999"
    with pytest.raises(AuditViolation,match="partial source flow"):
        audit({"source":raw,"merged":merged,"watch":tampered,"frozen":paper})
