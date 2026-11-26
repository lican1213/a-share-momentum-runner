"""Clock edge adversarial tests: historical revisions and execution-time bounds."""
from datetime import datetime
from decimal import Decimal
import copy
import json

from national_team.core_flow_factors import CORE_FOUR
from national_team.shadow_basket import MEMBERS
from scripts.research_funding_clock_edge import evaluate, public_signal, run

D=Decimal
DAYS=["2026-11-16","2026-11-17","2026-11-18","2026-11-19","2026-11-20","2026-11-23"]


def vintage(at,positive=True,sha="a"):
    ch=1 if positive else -1
    return {"session":DAYS[0],"available_at":at,"commit":sha*40,"blob_sha":"f"*40,
            "run_id":1,"evidence":"MATCHED_SUCCESSFUL_PAGES_RUN_UPDATED_AT",
            "reported_total":ch*8,"etfs":[{"c":c,"cat":MEMBERS[c],"share":100,
                                        "dsh":ch,"nav":2,"today":ch*2} for c in CORE_FOUR]}


def prices(values):
    return {day:(D(p),D(p),D(p),D(p)) for day,p in zip(DAYS,values)}


def original(positive=True):
    return {DAYS[0]:{"observed":datetime.fromisoformat(DAYS[1]+"T13:00:00+08:00"),
                     "flow":D(8 if positive else -8),"positive":4 if positive else 0,
                     "negative":0 if positive else 4}}


def test_actual():
    r=run()
    for row in (r["base_cost"],r["double_cost"]):
        assert row["economic_gate"]=="EXPLORATORY_NO_INDEPENDENT_OOS"
        assert row["trade_authorized"] is False
        assert row["matched_dates"]==row["public_earlier_open"]+row["public_later_open"]+row["public_same_open"]
        assert all(x["known_at"]<x["execution_session"]+"T09:30:00+08:00" for x in row["events"])
    print("FUND_CLOCK_RESULT",json.dumps(r,ensure_ascii=False))


def test_late_or_invalid_revision_no_backdating():
    v=vintage(DAYS[1]+"T09:30:00+08:00")
    assert public_signal([v],DAYS[0],DAYS)["open_index"]==2
    earlier=vintage(DAYS[0]+"T23:00:00+08:00")
    bad=copy.deepcopy(earlier);bad["commit"]="b"*40
    bad["available_at"]=DAYS[1]+"T08:00:00+08:00"
    bad["etfs"][0]["dsh"]=None
    assert public_signal([earlier,bad],DAYS[0],DAYS) is None
    correction=vintage(DAYS[1]+"T10:00:00+08:00",False,"c")
    got=public_signal([earlier,bad,correction],DAYS[0],DAYS)
    assert got["open_index"]==2 and got["state"]=="BROAD_REDEMPTION"


def test_earlier_buy_can_help_or_hurt():
    v=vintage(DAYS[0]+"T23:00:00+08:00")
    up=evaluate(DAYS,prices(["4","4","5","5","5","5"]),original(),[v])
    down=evaluate(DAYS,prices(["4","5","4","4","4","4"]),original(),[v])
    assert up["public_earlier_open"]==1 and up["source_agreement"]==1
    assert D(up["paired_sources"][0]["buy_timing_delta_cny"])>0
    assert D(down["paired_sources"][0]["buy_timing_delta_cny"])<0
    disagree=evaluate(DAYS,prices(["4"]*6),original(False),[v])
    assert disagree["source_agreement"]==0
    assert disagree["paired_sources"][0]["buy_timing_delta_cny"] is None


def test_earlier_sell_can_help_or_hurt():
    v=vintage(DAYS[0]+"T23:00:00+08:00",False)
    down=evaluate(DAYS,prices(["4","5","4","4","4","4"]),original(False),[v])
    up=evaluate(DAYS,prices(["4","4","5","5","5","5"]),original(False),[v])
    assert D(down["paired_sources"][0]["exit_timing_delta_per_100_shares_cny"])>0
    assert D(up["paired_sources"][0]["exit_timing_delta_per_100_shares_cny"])<0


def test_prefix_invariant_and_future_revision():
    v=vintage(DAYS[0]+"T23:00:00+08:00")
    later=vintage(DAYS[3]+"T23:00:00+08:00",False,"b")
    assert public_signal([v],DAYS[0],DAYS[:2])==public_signal([v,later],DAYS[0],DAYS)
    p=prices(["4"]*6)
    r=evaluate(DAYS[:2],{x:p[x] for x in DAYS[:2]},original(),[v])
    assert r["events"][0]["net_t1_cny"] is None
    assert r["summary"]["PUBLIC_PROXY"]["BROAD_SUBSCRIPTION"]["T1"]["mean_net_cny"] is None
