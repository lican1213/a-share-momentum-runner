"""Opportunity-first stock scanner regression tests; all numeric rows synthetic."""
from decimal import Decimal
import copy

import pytest

from national_team.core_flow_factors import CORE_FOUR, DataGateError
from national_team.opportunity_scan import scan_opportunities


def fixture():
    metrics={
        "codes":list(CORE_FOUR),
        "basket_name":"core_csi300_four",
        "trade_date":"2026-10-27",
        "decision_cutoff":"2026-10-28T08:30:00+08:00",
        "per_etf_daily_flow_proxy_cny":{
            "510300":"10000000","510310":"5000000",
            "510330":"-1000000","159919":"1000000",
        },
        "daily_net_creation_proxy_cny":"15000000",
        "five_day":{"net_creation_pct_initial_aum":"0.032"},
    }
    baskets={e:{
        "source_url":"https://example.org/fixture-"+e,
        "published_at":"2026-10-27T08:00:00+08:00",
        "asof_date":"2026-10-27",
        "weights":{"600519":"0.4","600036":"0.4","000001":"0.2"},
    } for e in CORE_FOUR}
    stocks={
      "600519":{"adv20_cny":"50000000","freefloat_mv_cny":"40000000000",
                "rel_strength20":"0.11","listing_sessions":900},
      "600036":{"adv20_cny":"1000000000","freefloat_mv_cny":"120000000000",
                "rel_strength20":"-0.02","listing_sessions":900},
      "000001":{"adv20_cny":"150000000","freefloat_mv_cny":"10000000000",
                "rel_strength20":"0.03","listing_sessions":70},
    }
    for k,v in stocks.items():
        v.update({"source_url":"https://example.org/stock-"+k,
                  "published_at":"2026-10-28T08:20:00+08:00",
                  "asof_date":"2026-10-27",
                  "is_st":False,"suspended":False,"limit_up_locked":False})
    return metrics,baskets,stocks


def test_full_scan_returns_ranked_opportunities_not_fake_broker_orders():
    m,b,s=fixture()
    o=scan_opportunities(m,b,s,decision_cutoff="2026-10-28T08:30:00+08:00")
    assert o["status"]=="INFLOW_RESEARCH_SCAN"
    assert o["abs_flow_coverage_ratio"]=="1"
    assert o["stock_scan_count"]==3
    assert len(o["potential_inflow_watchlist"])==3
    assert o["potential_inflow_watchlist"][0]["symbol"]=="600519"
    assert "LOW_LIQUIDITY_WATCH" in o["potential_inflow_watchlist"][0]["risk_tags"]
    assert "EXTENDED_PRICE_WATCH" in o["potential_inflow_watchlist"][0]["risk_tags"]
    assert o["live_broker_orders"] is False


def test_partial_etf_basket_still_returns_partial_research_ranking():
    m,b,s=fixture()
    del b["510300"]
    result=scan_opportunities(m,b,s,decision_cutoff="2026-10-28T08:30:00+08:00")
    assert result["status"]=="INFLOW_RESEARCH_SCAN"
    assert "510300" in result["missing_or_rejected_baskets"]
    assert 0 < Decimal(result["abs_flow_coverage_ratio"]) < 1
    assert result["potential_inflow_watchlist"]
    assert result["investor_identity_inferred"] is False


def test_missing_one_stock_no_longer_blocks_remaining_candidates():
    m,b,s=fixture()
    del s["600519"]
    o=scan_opportunities(m,b,s,decision_cutoff="2026-10-28T08:30:00+08:00")
    assert o["stock_scan_count"]==2
    assert o["stock_skipped"]==1
    assert len(o["potential_inflow_watchlist"])==2


def test_negative_flow_is_still_a_useful_outflow_signal():
    m,b,s=fixture()
    m["per_etf_daily_flow_proxy_cny"]={e:"-1000000" for e in CORE_FOUR}
    m["daily_net_creation_proxy_cny"]="-4000000"
    m["five_day"]["net_creation_pct_initial_aum"]="-0.04"
    o=scan_opportunities(m,b,s,decision_cutoff="2026-10-28T08:30:00+08:00")
    assert o["status"]=="OUTFLOW_RESEARCH_SCAN"
    assert o["potential_inflow_watchlist"]==[]
    assert len(o["potential_outflow_watchlist"])==3
    assert o["relative_strength_watchlist"]


def test_future_basket_is_excluded_not_used_as_current_information():
    m,b,s=fixture()
    b["510300"]["published_at"]="2026-10-28T12:00:00+08:00"
    o=scan_opportunities(m,b,s,decision_cutoff="2026-10-28T08:30:00+08:00")
    assert "510300" in o["missing_or_rejected_baskets"]
    assert o["potential_inflow_watchlist"]
    assert Decimal(o["abs_flow_coverage_ratio"]) < 1


def test_older_basket_explicit_age_and_not_hindsight():
    m,b,s=fixture()
    b["510300"]["asof_date"]="2026-10-24"
    o=scan_opportunities(m,b,s,decision_cutoff="2026-10-28T08:30:00+08:00")
    assert o["basket_source_age_days"]["510300"]==3
    b["510300"]["asof_date"]="2026-10-01"
    o=scan_opportunities(m,b,s,decision_cutoff="2026-10-28T08:30:00+08:00")
    assert "510300" in o["missing_or_rejected_baskets"]


def test_missing_all_real_baskets_never_creates_fake_opportunities():
    m,b,s=fixture()
    o=scan_opportunities(m,{},s,decision_cutoff="2026-10-28T08:30:00+08:00")
    assert o["status"]=="NO_VERIFIABLE_BASKET_EXPOSURE"
    assert o["stock_scan_count"]==0
    assert o["potential_inflow_watchlist"]==[]


def test_wrong_core_flows_or_future_core_metrics_still_fail():
    m,b,s=fixture()
    m["per_etf_daily_flow_proxy_cny"]["159919"]="2000000"
    with pytest.raises(DataGateError,match="do not sum"):
        scan_opportunities(m,b,s,decision_cutoff="2026-10-28T08:30:00+08:00")
    m,b,s=fixture()
    with pytest.raises(DataGateError,match="not available"):
        scan_opportunities(m,b,s,decision_cutoff="2026-10-28T08:00:00+08:00")


def test_known_suspended_flag_blocks_orderable_listing_only():
    m,b,s=fixture()
    s["600519"]["suspended"]=True
    o=scan_opportunities(m,b,s,decision_cutoff="2026-10-28T08:30:00+08:00")
    assert "600519" not in [x["symbol"] for x in o["potential_inflow_watchlist"]]
    assert o["stock_scan_count"]==3


def test_unknown_trade_status_keeps_research_ranking_with_risk_label():
    m,b,s=fixture()
    s["600036"]["limit_up_locked"]=None
    o=scan_opportunities(m,b,s,decision_cutoff="2026-10-28T08:30:00+08:00")
    item=next(x for x in o["potential_inflow_watchlist"] if x["symbol"]=="600036")
    assert "TRADE_STATUS_UNKNOWN" in item["risk_tags"]
