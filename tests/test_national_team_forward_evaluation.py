"""Synthetic scenarios; no claim about observed prices or profitability."""
import pytest
from national_team.forward_evaluation import evaluate_frozen_event

DAYS=[f"2026-10-{i:02d}" for i in range(1,29)]
EVENT={"id":"frozen-event-1","first_public_at":"2026-10-02T22:00:00+08:00",
       "candidate_symbols":["600036","600519"]}
# Entry is 2026-10-03 in synthetic exchange session list (not actual calendar).
def fixture():
    sessions=DAYS[:25]
    px={}
    for sym,opening in (("600036",10),("600519",20),("510300",5)):
        px[sym]={d:{"open":opening,"close":opening*(1+0.001*i),
                    "entry_blocked":False,"exit_blocked":False}
                 for i,d in enumerate(sessions)}
    return sessions,px

def test_forward_horizons_paired_with_same_entry_and_costs():
    days,p=fixture()
    r=evaluate_frozen_event(EVENT,days,p)
    assert r["entry_session"]=="2026-10-03"
    assert all(r["results"][str(h)]["status"]=="COMPUTED_OHLC_PROXY" for h in (5,10,20))
    assert r["results"]["5"]["exit_session"]=="2026-10-08"
    assert r["results"]["5"]["filled_stock_count"]==2
    # identical gross path, stock sell stamp produces lower stock return.
    assert float(r["results"]["5"]["paired_excess_net_return"])<0

def test_no_future_horizon_maturity_faked():
    days,px=fixture()
    r=evaluate_frozen_event(EVENT,days[:9],px)
    assert r["results"]["5"]["status"]=="COMPUTED_OHLC_PROXY"
    assert r["results"]["10"]["status"]=="NOT_MATURED"
    assert r["results"]["20"]["status"]=="NOT_MATURED"

def test_unfillable_stock_is_counted_as_cash_not_good_trade():
    days,px=fixture()
    px["600519"]["2026-10-03"]["entry_blocked"]=True
    r=evaluate_frozen_event(EVENT,days,px)
    assert r["results"]["5"]["filled_stock_count"]==1
    assert r["results"]["5"]["unfilled_cash_allocations"]==1

def test_blocked_exit_is_unknown_not_profits():
    days,px=fixture()
    px["600519"]["2026-10-08"]["exit_blocked"]=True
    r=evaluate_frozen_event(EVENT,days,px)
    assert r["results"]["5"]["status"]=="STOCK_EXIT_UNVERIFIED"
    assert "paired_excess_net_return" not in r["results"]["5"]

def test_future_signal_or_same_day_trade_not_leaked():
    days,px=fixture()
    e=dict(EVENT,first_public_at="2026-10-24T22:00:00+08:00")
    r=evaluate_frozen_event(e,days,px)
    assert r["entry_session"]=="2026-10-25"
    assert r["results"]["5"]["status"]=="NOT_MATURED"
    e["first_public_at"]="2026-11-01T09:00:00+08:00"
    r=evaluate_frozen_event(e,days,px)
    assert r["status"]=="ENTRY_NOT_YET_AVAILABLE"

def test_required_event_dedupe_and_tz():
    days,px=fixture()
    with pytest.raises(ValueError,match="unique"):
        evaluate_frozen_event(dict(EVENT,candidate_symbols=["600036","600036"]),days,px)
    with pytest.raises(ValueError,match="timezone"):
        evaluate_frozen_event(dict(EVENT,first_public_at="2026-10-02T22:00:00"),days,px)
