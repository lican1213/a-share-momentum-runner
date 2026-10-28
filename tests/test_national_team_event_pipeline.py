"""Synthetic source-reconciliation tests: zero claims of historical availability."""
from datetime import date,timedelta
from national_team.event_pipeline import reconcile_funding_snapshot
from national_team.core_flow_factors import CORE_FOUR

def fixture():
    dates=["2026-10-19","2026-10-20","2026-10-21","2026-10-22",
           "2026-10-23","2026-10-26","2026-10-27","2026-10-28"]
    panel={}
    for n,d in enumerate(dates[:-1]):
        panel[d]={e:{"shares":str(100000000+n*100000),
                     "nav":"4.25","shares_source":"SSE" if e!="159919" else "SZSE_DATED_JSON"}
                  for e in CORE_FOUR}
    return dates,{"asof_requested":"2026-10-28","run_id":"fixture",
                  "first_observed_no_earlier_than":"2026-10-28T22:00:00+08:00",
                  "observations_by_date":panel}

def test_latest_complete_four_session_not_fake_asof_trade():
    sess,raw=fixture()
    result=reconcile_funding_snapshot(raw,sess)
    assert result["status"]=="FULL_FOUR_ETF_SHARES_NAV_OBSERVED_RESEARCH"
    assert result["latest_available_trading_day"]=="2026-10-27"
    assert result["four_etf_factor"]["trade_date"]=="2026-10-27"
    assert result["four_etf_factor"]["five_day"]["end"]=="2026-10-27"
    assert result["first_available_at"].startswith("2026-10-28")
    assert result["verified_consecutive_session_flow"] is True
    assert result["factor_quality"]["NAV_from_Eastmoney_not_original_fund_report"] is True

def test_one_missing_shenzhen_session_does_not_forge_five_day_factor():
    sess,raw=fixture()
    del raw["observations_by_date"]["2026-10-23"]["159919"]
    r=reconcile_funding_snapshot(raw,sess)
    assert r["status"]=="PARTIAL_FUNDING_ONLY"
    assert r["four_etf_factor"] is None
    assert r["partial_funding"]["fund_count_coverage"]=="3/4"

def test_missing_latest_exchange_clearings_rolls_back_only_to_observed_date():
    sess,raw=fixture()
    del raw["observations_by_date"]["2026-10-27"]
    r=reconcile_funding_snapshot(raw,sess)
    assert r["latest_available_trading_day"]=="2026-10-26"
    assert r["partial_funding"]["period"]==["2026-10-23","2026-10-26"]

def test_true_calendar_gap_cannot_be_misread_as_consecutive():
    sess,raw=fixture()
    del raw["observations_by_date"]["2026-10-26"]
    r=reconcile_funding_snapshot(raw,sess)
    assert r["four_etf_factor"] is None
    assert r["partial_funding"] is None
