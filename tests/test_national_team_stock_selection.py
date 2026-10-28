"""Synthetic-only regression for national team ETF -> equity candidate research.

These are NOT authentic ETF subscriptions, holdings, prices or alpha results.
"""
from decimal import Decimal
import copy
import pytest

from national_team.core_flow_factors import DataGateError, CORE_FOUR
from national_team.stock_selection import research_stock_watchlists

ASOF="2026-10-27"
CUTOFF="2026-10-28T08:30:00+08:00"


def fixture():
    core={
        "codes":list(CORE_FOUR),"basket_name":"core_csi300_four","trade_date":ASOF,
        "decision_cutoff":CUTOFF,
        "per_etf_daily_flow_proxy_cny":{
            "510300":"10000000","510310":"5000000","510330":"-1000000","159919":"1000000",
        },
        "daily_net_creation_proxy_cny":"15000000",
        "five_day":{"net_creation_pct_initial_aum":"0.032"}
    }
    weights={"600036":"0.50","600519":"0.30","000001":"0.20"}
    baskets={e:{
      "asof_date":ASOF,"published_at":"2026-10-27T08:20:00+08:00",
      "source_url":"https://example.org/test-only-PCF-"+e,
      "representation":"ETF_PORTFOLIO_WEIGHT","weights":weights.copy(),
      "cash_substitution_unresolved":False
    } for e in CORE_FOUR}
    stock={
      "600036":{"adv20_cny":"1000000000","freefloat_mv_cny":"100000000000",
                "rel_strength20":"0.03"},
      "600519":{"adv20_cny":"300000000","freefloat_mv_cny":"50000000000",
                "rel_strength20":"0.08"},
      "000001":{"adv20_cny":"50000000","freefloat_mv_cny":"10000000000",
                "rel_strength20":"0.04"},
    }
    for key in stock:
        stock[key].update({
          "asof_date":ASOF,"published_at":"2026-10-27T16:00:00+08:00",
          "source_url":"https://example.org/synthetic-stock-"+key,
          "is_st":False,"suspended":False,"limit_up_locked":False,
          "listing_sessions":1000,
        })
    return core,baskets,stock


def test_only_research_watchlist_and_no_inferred_huijin_account_orders():
    core,baskets,stock=fixture()
    x=research_stock_watchlists(core,baskets,stock,decision_cutoff=CUTOFF)
    assert x["status"]=="PIT_RESEARCH_WATCHLIST_ONLY"
    assert x["eligible_stock_count"]==2 and x["rejected_stock_count"]==1
    assert x["stock_coverage"]==3
    assert x["top_by_implied_flow_over_turnover"][0]["symbol"]=="600519"
    assert x["top_by_relative_price_confirmation"][0]["symbol"]=="600519"
    assert x["broker_trade_authorized"] is False
    assert x["identifies_investor"] is False
    assert x["is_ap_execution_evidence"] is False
    assert Decimal(x["core_total_daily_flow_proxy_cny"])==Decimal("15000000")
    assert all(z["symbol"]!="000001" for z in x["top_by_implied_flow_over_turnover"])


def test_reject_missing_fund_weight_or_non_current_pcf():
    core,baskets,stock=fixture()
    del baskets["159919"]
    with pytest.raises(DataGateError,match="four current"):
        research_stock_watchlists(core,baskets,stock,decision_cutoff=CUTOFF)
    core,baskets,stock=fixture()
    baskets["510300"]["asof_date"]="2026-10-24"
    with pytest.raises(DataGateError,match="applicable"):
        research_stock_watchlists(core,baskets,stock,decision_cutoff=CUTOFF)


def test_publication_delays_cannot_be_backfilled():
    core,baskets,stock=fixture()
    baskets["510300"]["published_at"]="2026-10-28T12:00:00+08:00"
    with pytest.raises(DataGateError,match="not public"):
        research_stock_watchlists(core,baskets,stock,decision_cutoff=CUTOFF)
    core,baskets,stock=fixture()
    stock["600036"]["published_at"]="2026-10-28T12:00:00+08:00"
    with pytest.raises(DataGateError,match="not public"):
        research_stock_watchlists(core,baskets,stock,decision_cutoff=CUTOFF)


def test_negative_net_etf_flow_never_converts_to_positive_stock_buy_list():
    core,baskets,stock=fixture()
    core["per_etf_daily_flow_proxy_cny"]={e:"-1000000" for e in CORE_FOUR}
    core["daily_net_creation_proxy_cny"]="-4000000"
    core["five_day"]["net_creation_pct_initial_aum"]="-0.04"
    x=research_stock_watchlists(core,baskets,stock,decision_cutoff=CUTOFF)
    assert x["status"]=="NO_POSITIVE_CORE_FUNDING_EVENT"
    assert x["top_by_implied_flow_over_turnover"]==[]
    assert x["top_by_relative_price_confirmation"]==[]


def test_no_silent_nine_fund_basket_substitution_or_unaudited_flow():
    core,baskets,stock=fixture()
    core["codes"].append("510050")
    with pytest.raises(DataGateError,match="original fixed four"):
        research_stock_watchlists(core,baskets,stock,decision_cutoff=CUTOFF)
    core,baskets,stock=fixture()
    core["daily_net_creation_proxy_cny"]="15500000"
    with pytest.raises(DataGateError,match="!= declared"):
        research_stock_watchlists(core,baskets,stock,decision_cutoff=CUTOFF)


def test_cash_substitution_is_not_presented_as_stock_trade():
    core,baskets,stock=fixture()
    baskets["510300"]["cash_substitution_unresolved"]=True
    x=research_stock_watchlists(core,baskets,stock,decision_cutoff=CUTOFF)
    assert x["cash_substitution_unresolved_etfs"]==["510300"]
    assert x["is_actual_stock_purchase"] is False
    assert x["broker_trade_authorized"] is False


def test_reject_incomplete_basket_and_stale_stock_data():
    core,baskets,stock=fixture()
    baskets["510300"]["weights"]={"600036":"0.1"}
    with pytest.raises(DataGateError,match="weight coverage"):
        research_stock_watchlists(core,baskets,stock,decision_cutoff=CUTOFF)
    core,baskets,stock=fixture()
    stock["600519"]["asof_date"]="2026-10-24"
    with pytest.raises(DataGateError,match="stale stock"):
        research_stock_watchlists(core,baskets,stock,decision_cutoff=CUTOFF)
