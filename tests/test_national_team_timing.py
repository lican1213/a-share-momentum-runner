"""Red-team checks: source clocks, source anomalies and matched early exits."""
from datetime import datetime
from decimal import Decimal
import json
from pathlib import Path

import pytest

from national_team.shadow_basket import GROUPS, MEMBERS, observe
from scripts.research_national_team_timing import next_open, replay, run, BJ, verified

D=Decimal
DAYS=["2026-11-23","2026-11-24","2026-11-25","2026-11-26"]
CLOCK="2026-11-26T08:00:00+08:00"


def sample():
    rows=[{"c":c,"cat":g,"share":100,"nav":2,"dsh":-1,"today":-2} for c,g in MEMBERS.items()]
    return {"asof":"2026-11-25","generated":"2026-11-26 07:00","etfs":rows,"today":{"net":-70}}


def shadow(payload):
    return observe(payload,observed_at=CLOCK,source_commit="a"*40,source_sha256="b"*64)


def test_fixed_membership_and_no_authorization():
    report=shadow(sample())
    assert len(MEMBERS)==35 and len(GROUPS)==13
    assert report["core_four"]["negative_funds"]==4
    assert report["expanded_ex_core"]["funds"]==31
    assert report["trade_authorized"] is False and verified(report)


@pytest.mark.parametrize("case",["missing","duplicate","wrong_group","future","wrong_units","wrong_total"])
def test_shadow_rejects_corruption(case):
    p=sample()
    if case=="missing":p["etfs"].pop()
    elif case=="duplicate":p["etfs"][-1]=p["etfs"][0]
    elif case=="wrong_group":p["etfs"][0]["cat"]="other"
    elif case=="future":p["generated"]="2026-11-26 09:00"
    elif case=="wrong_units":p["etfs"][0]["dsh"]=-100
    elif case=="wrong_total":p["today"]["net"]=100
    with pytest.raises(ValueError):
        shadow(p)


def test_no_same_open_after_disclosure():
    assert next_open(DAYS,datetime.fromisoformat("2026-11-25T13:43:58+08:00"))==3
    assert next_open(DAYS,datetime.fromisoformat("2026-11-25T09:30:00+08:00"))==3
    assert next_open(DAYS,datetime.fromisoformat("2026-11-26T09:31:00+08:00")) is None


def test_paired_exit_avoids_loss_and_respects_t1():
    p={d:(D(v),D(v),D(v),D(v)) for d,v in zip(DAYS,["4","4","3","3"])}
    report=replay(DAYS,p,{0:{}},{1:{}})
    assert report["early_exit_count"]==1
    assert D(report["exit_incremental_pnl_cny"])>0
    assert report["accounts"]["S2"]["trades"][1]["session"]==DAYS[1]
    blocked=replay(DAYS,p,{0:{}},{0:{}})
    assert blocked["accounts"]["S2"]["trades"]==[]
    assert len(blocked["accounts"]["S1"]["trades"])==2
    assert blocked["blocked_entries"]==1
    assert report["mature_early_exit_pairs"][0]["false_exit"] is False


def test_false_exit_and_zero_exit_not_success():
    p={d:(D(v),D(v),D(v),D(v)) for d,v in zip(DAYS,["4","4","5","5"])}
    bad=replay(DAYS,p,{0:{}},{1:{}})
    assert D(bad["exit_incremental_pnl_cny"])<0
    assert bad["false_exits"]==1
    assert replay(DAYS,p,{0:{}},{})["withdrawal_effect_status"]=="NO_MATURE_EXECUTABLE_EARLY_EXIT"


def test_real_pit_replay(capsys):
    result=run()
    assert result["trade_authorized"] is False
    assert result["third_party_shadow_used_for_history"] is False
    assert "2026-11-20" in result["missing_or_anomalous"]
    assert any(x["signal_session"]=="2026-11-24" for x in result["pending_exits"])
    assert all(datetime.fromisoformat(x["known_at"])<datetime.fromisoformat(day+"T09:30:00+08:00")
               for day,x in result["entries"].items())
    with capsys.disabled():
        print("PIT_TIMING_REAL_RESULT",json.dumps(result,ensure_ascii=False))


def test_pinned_public_source_schema():
    payload=json.loads("{\"asof\":\"2026-11-25\",\"generated\":\"2026-11-25 23:39\",\"etfs\":[{\"c\":\"510330\",\"cat\":\"沪深300\",\"share\":234.4,\"nav\":4.1426,\"dsh\":28.611,\"today\":118.5},{\"c\":\"510310\",\"cat\":\"沪深300\",\"share\":308.2,\"nav\":3.8601,\"dsh\":22.761,\"today\":87.9},{\"c\":\"510500\",\"cat\":\"中证500\",\"share\":136.7,\"nav\":5.9234,\"dsh\":11.616,\"today\":68.8},{\"c\":\"588080\",\"cat\":\"科创板50\",\"share\":504.6,\"nav\":1.2154,\"dsh\":37.65,\"today\":45.8},{\"c\":\"510300\",\"cat\":\"沪深300\",\"share\":559.2,\"nav\":3.9718,\"dsh\":11.142,\"today\":44.3},{\"c\":\"510050\",\"cat\":\"上证50\",\"share\":254.2,\"nav\":2.8691,\"dsh\":12.744,\"today\":36.6},{\"c\":\"159915\",\"cat\":\"创业板\",\"share\":548.9,\"nav\":2.1986,\"dsh\":14.23,\"today\":31.3},{\"c\":\"512100\",\"cat\":\"中证1000\",\"share\":261.9,\"nav\":2.2547,\"dsh\":6.2,\"today\":14},{\"c\":\"588000\",\"cat\":\"科创板50\",\"share\":1053.3,\"nav\":1.2548,\"dsh\":10.14,\"today\":12.7},{\"c\":\"159952\",\"cat\":\"创业板\",\"share\":149.2,\"nav\":1.3354,\"dsh\":5.355,\"today\":7.2},{\"c\":\"159338\",\"cat\":\"中证A500\",\"share\":271.7,\"nav\":0.9906,\"dsh\":-5.49,\"today\":-5.4},{\"c\":\"159949\",\"cat\":\"创业板50\",\"share\":252.1,\"nav\":0.9769,\"dsh\":3.68,\"today\":3.6},{\"c\":\"159361\",\"cat\":\"中证A500\",\"share\":266.5,\"nav\":1.0111,\"dsh\":-3.45,\"today\":-3.5},{\"c\":\"159352\",\"cat\":\"中证A500\",\"share\":308.9,\"nav\":1.0327,\"dsh\":-2.25,\"today\":-2.3},{\"c\":\"563360\",\"cat\":\"中证A500\",\"share\":381.5,\"nav\":1.0468,\"dsh\":-1.62,\"today\":-1.7},{\"c\":\"512050\",\"cat\":\"中证A500\",\"share\":174.2,\"nav\":0.9875,\"dsh\":-1.32,\"today\":-1.3},{\"c\":\"159845\",\"cat\":\"中证1000\",\"share\":23.8,\"nav\":2.3135,\"dsh\":-0.51,\"today\":-1.2},{\"c\":\"588050\",\"cat\":\"科创板50\",\"share\":68.8,\"nav\":1.2173,\"dsh\":-0.99,\"today\":-1.2},{\"c\":\"560010\",\"cat\":\"中证1000\",\"share\":25.5,\"nav\":2.3113,\"dsh\":-0.48,\"today\":-1.1},{\"c\":\"515330\",\"cat\":\"沪深300\",\"share\":99.1,\"nav\":1.1411,\"dsh\":-0.78,\"today\":-0.9},{\"c\":\"159977\",\"cat\":\"创业板\",\"share\":66,\"nav\":1.1409,\"dsh\":0.68,\"today\":0.8},{\"c\":\"159901\",\"cat\":\"深证100\",\"share\":13.1,\"nav\":2.6332,\"dsh\":0.308,\"today\":0.8},{\"c\":\"159629\",\"cat\":\"中证1000\",\"share\":8.1,\"nav\":2.3215,\"dsh\":0.3,\"today\":0.7},{\"c\":\"159351\",\"cat\":\"中证A500\",\"share\":85.7,\"nav\":0.9834,\"dsh\":0.57,\"today\":0.6},{\"c\":\"512500\",\"cat\":\"中证500\",\"share\":20.1,\"nav\":3.352,\"dsh\":0.136,\"today\":0.5},{\"c\":\"510100\",\"cat\":\"上证50\",\"share\":9.5,\"nav\":2.8256,\"dsh\":0.144,\"today\":0.4},{\"c\":\"563220\",\"cat\":\"中证A500\",\"share\":78.4,\"nav\":1.0328,\"dsh\":-0.36,\"today\":-0.4},{\"c\":\"159922\",\"cat\":\"中证500\",\"share\":31.3,\"nav\":2.4024,\"dsh\":-0.13,\"today\":-0.3},{\"c\":\"159633\",\"cat\":\"中证1000\",\"share\":12,\"nav\":2.3783,\"dsh\":-0.14,\"today\":-0.3},{\"c\":\"515800\",\"cat\":\"中证800\",\"share\":40.7,\"nav\":1.0607,\"dsh\":0.225,\"today\":0.2},{\"c\":\"563800\",\"cat\":\"中证A500\",\"share\":112.3,\"nav\":0.9905,\"dsh\":-0.12,\"today\":-0.1},{\"c\":\"510180\",\"cat\":\"上证180\",\"share\":44.6,\"nav\":3.5808,\"dsh\":-0.015,\"today\":-0.1},{\"c\":\"510230\",\"cat\":\"上证180金融\",\"share\":5.4,\"nav\":1.393,\"dsh\":0.1,\"today\":0.1},{\"c\":\"560050\",\"cat\":\"MSCI中国A50\",\"share\":21.1,\"nav\":0.9048,\"dsh\":-0.125,\"today\":-0.1},{\"c\":\"159919\",\"cat\":\"沪深300\",\"share\":213.3,\"nav\":4.146,\"dsh\":-0.009,\"today\":0}],\"today\":{\"net\":454.6}}")
    report=observe(payload,observed_at=CLOCK,source_commit="2f242054e55da87f04817524dcdfcb286d3c79e7",source_sha256="a"*64)
    assert report["session"]=="2026-11-25"
    assert D(report["upstream_reported_total_100m_cny"])==D("454.6")
    assert report["per_fund_official_dates_verified"] is False
