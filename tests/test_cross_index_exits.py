"""Matched ablation and adversarial tests: no economic gate from fixture wins."""
from datetime import datetime
from decimal import Decimal
import copy
import json

from scripts import research_cross_index_exits as exp
from scripts import research_national_team_timing as timing
from scripts.research_shadow_pit_history import BASKETS, load
from national_team.shadow_basket import MEMBERS
from national_team.core_flow_factors import CORE_FOUR

D=Decimal
DAYS=["2026-11-16","2026-11-17","2026-11-18","2026-11-19","2026-11-20","2026-11-23","2026-11-24"]
CODES=BASKETS["COMMON23"]
EXIT={1:{"signal_session":DAYS[0],"known_at":DAYS[0]+"T23:00:00+08:00"}}


def vintage(day,at,positive,sha="a"):
    rows=[]
    for c in CODES:
        change=-1 if c in CORE_FOUR or not positive else 1
        rows.append({"c":c,"cat":MEMBERS[c],"share":100,"dsh":change,"nav":2,"today":change*2})
    return {"session":day,"available_at":at,"commit":sha*40,"blob_sha":"f"*40,
            "run_id":1,"evidence":"MATCHED_SUCCESSFUL_PAGES_RUN_UPDATED_AT",
            "reported_total":sum(x["today"] for x in rows),"etfs":rows}


def prices(values):
    return {day:(D(v),D(v),D(v),D(v)) for day,v in zip(DAYS,values)}


def test_actual_history(capsys):
    r=exp.run()
    assert r["oos_independent_clusters"]==0 and r["trade_authorized"] is False
    for name,row in r["baskets"].items():
        assert row["base_cost"]["S2"]["net_pnl_cny"]=="-921.15"
        assert row["base_cost"]["economic_gate"]=="INSUFFICIENT_INDEPENDENT_OUT_OF_SAMPLE_EVIDENCE"
    main=r["baskets"]["COMMON23"]["base_cost"]
    assert main["S3_minus_S2_cny"]=="0.00"
    assert len(main["effective_exit_veto_pairs"])==0
    veto=[x for x in main["cross_decisions"] if x["decision"]=="VETO_ROTATION"]
    assert len(veto)==1 and veto[0]["execution_session"]=="2026-11-13"
    assert D(veto[0]["forward_open_to_close_return"]["3"])<0
    assert main["S4_mature_pairs"]==0 and main["S4_mean_net_vs_cash_cny"] is None
    with capsys.disabled():
        print("CROSS_ABLATION_RESULT",json.dumps(r,ensure_ascii=False))


def test_paired_veto_can_help_or_hurt():
    # Exit signal for prior session is visible before the second opening.
    # The same entry on day 0 is only for synthetic testing.
    v=vintage(DAYS[0],DAYS[0]+"T23:10:00+08:00",True)
    up=exp.compare(DAYS,prices(["4","4","5","5","5","5","5"]),{0:{}},EXIT,{},[v],CODES)
    down=exp.compare(DAYS,prices(["4","4","3","3","3","3","3"]),{0:{}},EXIT,{},[v],CODES)
    assert D(up["S3_minus_S2_cny"])>0 and up["effective_exit_veto_pairs"][0]["avoided_false_exit"]
    assert D(down["S3_minus_S2_cny"])<0 and down["effective_exit_veto_pairs"][0]["harmful_veto"]
    assert up["S1"]["trades"]==down["S1"]["trades"] or up["S1"]["trades"][0]==down["S1"]["trades"][0]


def test_late_and_missing_revision_cannot_veto():
    v=vintage(DAYS[0],DAYS[1]+"T09:30:00+08:00",True)
    keep,dec=exp.cross_exits(DAYS,EXIT,[v],CODES)
    assert keep==EXIT and dec[0]["decision"]=="CORE_EXIT_FALLBACK"
    v["available_at"]=DAYS[0]+"T23:00:00+08:00"
    assert exp.cross_exits(DAYS,EXIT,[v],CODES)[0]=={}
    invalid=copy.deepcopy(v);invalid["commit"]="b"*40
    invalid["available_at"]=DAYS[1]+"T08:00:00+08:00"
    invalid["etfs"].pop();invalid["reported_total"]=sum(x["today"] for x in invalid["etfs"])
    assert exp.cross_exits(DAYS,EXIT,[v,invalid],CODES)[0]==EXIT


def test_prefix_and_future_spike():
    v=vintage(DAYS[0],DAYS[0]+"T23:10:00+08:00",False)
    future=vintage(DAYS[0],DAYS[3]+"T20:00:00+08:00",True,"b")
    p=prices(["4","4","3","3","3","3","3"])
    old=exp.compare(DAYS,p,{0:{}},EXIT,{},[v],CODES)
    changed=prices(["4","4","3","30","30","30","30"])
    new=exp.compare(DAYS,changed,{0:{}},EXIT,{},[v,future],CODES)
    prefix=exp.compare(DAYS[:3],{d:p[d] for d in DAYS[:3]},{0:{}},EXIT,{},[v],CODES)
    def decision_only(result):
        return [{k:v for k,v in row.items() if k!="forward_open_to_close_return"}
                for row in result["cross_decisions"]]
    assert decision_only(old)==decision_only(new)==decision_only(prefix)
    assert old["cross_decisions"][0]["forward_open_to_close_return"]["3"]!=new["cross_decisions"][0]["forward_open_to_close_return"]["3"]
    assert prefix["cross_decisions"][0]["forward_open_to_close_return"]["3"] is None
    assert old["S3"]["trades"]==new["S3"]["trades"]==prefix["S3"]["trades"]
    assert old["S3"]["net_pnl_cny"]==prefix["S3"]["net_pnl_cny"]


def test_reentry_is_new_signal_and_costed_pair():
    negative=vintage(DAYS[0],DAYS[0]+"T23:10:00+08:00",False)
    positive=vintage(DAYS[1],DAYS[1]+"T23:10:00+08:00",True,"b")
    core={DAYS[1]:{"observed":datetime.fromisoformat(DAYS[1]+"T23:00:00+08:00"),"flow":D(1)}}
    p=prices(["4","4","4","4","5","5","5"])
    a=exp.compare(DAYS,p,{0:{}},EXIT,core,[negative,positive],CODES)
    b=exp.compare(DAYS,p,{0:{}},EXIT,core,[negative,positive],CODES,cost=D(2))
    pair=a["S4_reentry_event_pairs"][0]
    assert pair["reentry_session"]==DAYS[2] and pair["exit_after_reentry"]==DAYS[4]
    assert a["S4_mature_pairs"]==1 and D(a["S4_mean_net_vs_cash_cny"])>D(b["S4_mean_net_vs_cash_cny"])>0
    assert D(b["S2"]["net_pnl_cny"])<D(a["S2"]["net_pnl_cny"])
    missing=exp.compare(DAYS,p,{0:{}},EXIT,core,[negative],CODES)
    assert missing["S4_mature_pairs"]==0 and missing["S4_mean_net_vs_cash_cny"] is None
    loss=exp.compare(DAYS,prices(["4","4","4","4","3","3","3"]),{0:{}},EXIT,core,[negative,positive],CODES)
    assert loss["S4_reentry_event_pairs"][0]["harmful_reentry"]
    truncated=exp.compare(DAYS[:3],{d:p[d] for d in DAYS[:3]},{0:{}},EXIT,core,[negative,positive],CODES)
    assert truncated["S4_reentry_event_pairs"][0]["status"]=="PENDING_OUTCOME"
    assert truncated["S4_mean_net_vs_cash_cny"] is None
