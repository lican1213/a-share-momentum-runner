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
    assert replay(DAYS,p,{0:{}},{0:{}})["accounts"]["S2"]["trades"]==[]


def test_false_exit_and_zero_exit_not_success():
    p={d:(D(v),D(v),D(v),D(v)) for d,v in zip(DAYS,["4","4","5","5"])}
    assert D(replay(DAYS,p,{0:{}},{1:{}})["exit_incremental_pnl_cny"])<0
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
