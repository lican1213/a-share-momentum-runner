"""Deterministic red-team unit cases; these do NOT claim market PnL."""
from national_team.short_paper_pilot import (
    MAX_RISK, RANKS, h256, one_way_fee, round_up_tick, round_down_tick,
    indicators, minute_order_outcome,
)


def test_minute_same_bar_stop_wins_not_optimistic_target():
    snapshot={"bars":[{"minute":"2026-11-04 10:00","open":10.0,"low":9.45,"high":10.65,"close":10.4},
                      {"minute":"2026-11-04 14:50","open":10.4,"low":10.3,"high":10.5,"close":10.5}]}
    assert minute_order_outcome(snapshot,9.5,10.5)==("STOP_FIRST",9.5)


def test_1450_time_exit_no_1500_price_used():
    snapshot={"bars":[{"minute":"2026-11-04 14:50","open":10.21,"low":10.2,"high":10.22,"close":10.22}]}
    assert minute_order_outcome(snapshot,9.0,11.0)==("T_PLUS_3_1450_TIME",10.21)


def test_gap_through_stop_uses_worse_open():
    snapshot={"bars":[{"minute":"2026-11-04 09:30","open":8.2,"low":8.1,"high":8.5,"close":8.4}]}
    assert minute_order_outcome(snapshot,9.0,10.5)==("GAP_STOP",8.2)


def test_bps_costs_min_ticket_and_lot_tick():
    assert one_way_fee(3000)==5.0
    assert one_way_fee(3000, sell=True)==5.0+3000*0.0005
    assert round_up_tick(9.121)==9.13
    assert round_down_tick(9.129)==9.12
    assert MAX_RISK==150 and len(RANKS["S1"])==len(RANKS["S2"])==5
    assert h256({"a": 1,"b": 2})==h256({"b":2,"a":1})


def test_breakout_uses_only_previous_10_high_and_prev_20_volume():
    bars=[]
    import datetime
    start=datetime.date(2025,1,1)
    for i in range(280):
        d=(start+datetime.timedelta(days=i)).isoformat()
        close=10+i*0.03
        bars.append({"date":d,"open":close-0.1,"high":close+0.1,
                     "low":close-0.2,"close":close,
                     "volume":200.0 if i==279 else 100.0})
    bars[-1]["date"]="2026-10-29"
    benchmark=[dict(x,open=4.0,high=4.02,low=3.98,close=4.0) for x in bars]
    d=indicators({"bars":bars},{"bars":benchmark})
    assert d["eligible"] and d["breakout_trigger"]>bars[-2]["high"]
    bars[-1]["volume"]=100.0
    assert not indicators({"bars":bars},{"bars":benchmark})["eligible"]
