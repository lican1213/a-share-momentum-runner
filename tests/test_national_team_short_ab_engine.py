"""No-network adversarial regression tests for EXP-0005-A2 / EXP-0006."""
from datetime import date,datetime,timedelta
from zoneinfo import ZoneInfo
import json
import math
import pytest
from national_team import short_ab_engine as x

BJ=ZoneInfo("Asia/Shanghai")
def now(s):return datetime.fromisoformat(s).replace(tzinfo=BJ)

def test_close_window_and_midnight_fail_closed(monkeypatch):
    monkeypatch.setattr(x,"calendar_sessions",lambda a,b:[a] if a.startswith("2026-10-30") else [])
    assert x.close_day(now("2026-10-30T17:29:59")) is None
    assert x.close_day(now("2026-10-30T18:15:00"))=="2026-10-30"
    assert x.close_day(now("2026-10-30T22:15:00"))=="2026-10-30"
    assert x.close_day(now("2026-10-31T00:55:00")) is None
    assert x.close_day(now("2026-10-29T21:00:00")) is None

def test_no_backdating_or_same_day_frozen_entry(monkeypatch):
    monkeypatch.setattr(x,"next_session",lambda d:"2026-11-02")
    f={"freeze_created_at":"2026-11-02T00:55:00+08:00",
       "asof_session":"2026-10-30","next_open_session":"2026-11-02"}
    assert x.execution_gate(f,now("2026-11-02T18:20:00"))=="FREEZE_AFTER_ENTRY_CUTOFF"
    f["freeze_created_at"]="2026-10-30T18:15:00+08:00"
    assert x.execution_gate(f,now("2026-10-30T20:00:00"))=="ENTRY_NOT_REACHED"
    assert x.execution_gate(f,now("2026-11-02T18:20:00")) is None

def test_a2_vs_b_eligibility_is_different():
    start=date(2025,1,1)
    s=[]
    b=[]
    for i in range(290):
        d=(start+timedelta(days=i)).isoformat()
        close=10+i*.02
        s.append({"date":d,"open":close,"high":close+.05,
                  "low":close-.05,"close":close,"volume":1000.,
                  "turnover":100000000.})
        b.append({"date":d,"open":4.,"high":4.05,"low":3.95,"close":4.,
                  "volume":1000.})
    last=s[-1]["date"]
    # Rolling up stock with no 1.2x volume: B passes, A fails.
    a=x.indicator({"bars":s},{"bars":b},last,"A2")
    bb=x.indicator({"bars":s},{"bars":b},last,"B")
    assert not a["eligible"] and bb["eligible"]

def test_b_50m_adv_hard_gate():
    start=date(2025,1,1)
    s=[];b=[]
    for i in range(290):
        day=(start+timedelta(days=i)).isoformat()
        close=10+i*.02
        s.append({"date":day,"close":close,"high":close+.05,"low":close-.05,
                  "volume":1000.,"turnover":49999999.})
        b.append({"date":day,"close":4.})
    assert not x.indicator({"bars":s},{"bars":b},s[-1]["date"],"B")["eligible"]

def test_b_selection_three_preserves_arms():
    checks=[]
    for g,code in x.RANK_ORDER:
        checks.append({"cohort":g,"code":code,"eligible":True})
    b=x.selects(checks,"B");a=x.selects(checks,"A2")
    assert [v["code"] for v in b]==["601825","600309","600000"]
    assert [v["code"] for v in a]==["601825","600309"]
    assert len({v["code"] for v in b})==len(b)

def test_tick_commission_and_lot_risk():
    assert x.up(9.121)==9.13 and x.down(9.129)==9.12
    assert x.fee(3000)==5.
    assert x.fee(3000,sell=True)==pytest.approx(6.5)
    position=x.entry_position(20.,{"atr14":.2},x.GROUPS["B"],20000.)
    assert position is not None and position["qty"]%100==0
    assert position["budget_risk"]<=150.
    assert position["notional"]<=8000.
    assert x.entry_position(90,{"atr14":1.},x.GROUPS["B"],20000.) is None

def test_price_gap_ceiling_for_a_and_b():
    i={"breakout":10}
    assert not x.opening_allowed(10.25,10.,i,x.GROUPS["A2"])
    assert x.opening_allowed(10.25,10.,i,x.GROUPS["B"])
    assert not x.opening_allowed(10.31,10.,i,x.GROUPS["B"])
    assert not x.opening_allowed(9.99,10.,i,x.GROUPS["B"])

def test_b2_cannot_use_1030_bar_as_after_1030_break():
    # High watermark established before/at 10:30; first trigger at 10:31.
    earlier=[{"minute":"2026-11-02 10:29","high":10.1,"open":10.,"volume":1},
             {"minute":"2026-11-02 10:30","high":10.2,"open":10.,"volume":1}]
    later=[{"minute":"2026-11-02 10:31","high":10.22,"open":10.21,"volume":50}]
    prior=[]
    for day in ("2026-10-28","2026-10-29","2026-10-30"):
        prior.append({"bars":[{"minute":f"{day} 10:{j:02d}","volume":1}
                             for j in range(31,61)]})
    # Incomplete 1-minute comparable (fewer than 50) => fail rather than invent volume.
    assert x.b2_signal({"bars":earlier+later},prior) is None

def test_b2_signals_only_with_complete_prior_same_minutes():
    earlier=[{"minute":"2026-11-02 10:30","high":10.2,"open":10.,"volume":1}]
    after=[{"minute":f"2026-11-02 10:{j:02d}","open":10.21 if j==31 else 10.22 if j==32 else 10.0,
            "high":10.22 if j in (31,32) else 10.1,"volume":20 if j==31 else 1}
           for j in range(31,60)]
    after += [{"minute":"2026-11-02 11:00","open":10.,
               "high":10.1,"volume":1}]
    past=[]
    for day in ("2026-10-28","2026-10-29","2026-10-30"):
        rows=[{"minute":f"{day} 10:{j:02d}","volume":1} for j in range(31,60)]
        rows += [{"minute":f"{day} 11:{j:02d}","volume":1} for j in range(0,31)]
        past.append({"bars":rows})
    out=x.b2_signal({"bars":earlier+after},past)
    assert out is not None
    assert out["minute"]=="2026-11-02 10:32"
    assert out["signal_bar_minute"]=="2026-11-02 10:31"

def test_frozen_sha_mismatch_is_discarded(tmp_path):
    d=tmp_path/"freezes"/"B";d.mkdir(parents=True)
    (d/"2026-10-30.json").write_text(json.dumps({"group":"B","signal_sha256":"forged"}))
    assert x.locked_freezes("B",tmp_path)==[]

def test_empty_prior_freeze_cannot_be_recreated_at_midnight(monkeypatch,tmp_path):
    monkeypatch.setattr(x,"calendar_sessions",lambda a,b:[])
    result=x.run(object(),now("2026-10-31T00:55:00"),"B",tmp_path)
    assert result["freeze_created"] is False
    assert result["freeze_status"]=="OUTSIDE_TODAY_COMPLETED_EXCHANGE_SESSION"

def test_freeze_retries_are_idempotent(monkeypatch,tmp_path):
    monkeypatch.setattr(x,"calendar_sessions",lambda a,b:["2026-10-30"])
    def stub(ak,now,group,day):
        obj={"group":group,"selected":[],"asof_session":day,
             "next_open_session":"2026-11-02",
             "four_etf_flow":{"day":"2026-10-28"}}
        return dict(obj,signal_sha256=x.sha(obj))
    monkeypatch.setattr(x,"build_freeze",stub)
    r1=x.run(object(),now("2026-10-30T18:15:00"),"B",tmp_path)
    r2=x.run(object(),now("2026-10-30T20:15:00"),"B",tmp_path)
    assert r1["freeze_created"] and not r2["freeze_created"]
    assert r2["freeze_status"]=="EXISTING_FREEZE_UNCHANGED"

def test_a2_and_b_ledgers_are_separate(monkeypatch,tmp_path):
    monkeypatch.setattr(x,"calendar_sessions",lambda a,b:["2026-10-30"])
    def stub(ak,now,group,day):
        o={"group":group,"selected":[],"asof_session":day,"next_open_session":"2026-11-02",
           "four_etf_flow":{"day":"2026-10-28"}}
        return dict(o,signal_sha256=x.sha(o))
    monkeypatch.setattr(x,"build_freeze",stub)
    assert x.run(object(),now("2026-10-30T18:15:00"),"A2",tmp_path)["freeze_created"]
    assert x.run(object(),now("2026-10-30T18:15:00"),"B",tmp_path)["freeze_created"]
    assert len(list((tmp_path/"freezes"/"A2").glob("*.json")))==1
    assert len(list((tmp_path/"freezes"/"B").glob("*.json")))==1

def test_no_real_broker_code_import():
    import inspect
    source=inspect.getsource(x)
    assert "place_order(" not in source and "submit_order(" not in source
    assert "real_broker_orders" in source

def test_source_flow_rejects_partial_etf(monkeypatch,tmp_path):
    root=tmp_path/"merged";(root/"2026-10-30").mkdir(parents=True)
    data={"first_observed_no_earlier_than":"2026-10-30T09:00:00+08:00",
          "observations_by_date":{"2026-10-27":{"510300":{"shares":"10","nav":"4"}},
                                  "2026-10-28":{"510300":{"shares":"11","nav":"4"}}}}
    (root/"2026-10-30"/"f.json").write_text(json.dumps(data))
    monkeypatch.setattr(x,"FLOW_ROOT",root)
    with pytest.raises(ValueError,match="NO_PIT_COMPLETE"):
        x.source_flow(now("2026-10-30T18:15:00"))


def test_real_four_etf_proxy_is_recomputed_no_future_obs(monkeypatch,tmp_path):
    base=tmp_path/"merged";daydir=base/"2026-10-30";daydir.mkdir(parents=True)
    first="2026-10-29T15:11:00+08:00"
    previous={code:{"shares":"100","nav":"4","shares_first_observed_at":first,
                    "nav_first_observed_at":first} for code in x.CORE}
    current={code:{"shares":"101","nav":"4","shares_first_observed_at":first,
                   "nav_first_observed_at":first} for code in x.CORE}
    data={"first_observed_no_earlier_than":first,
          "observations_by_date":{"2026-10-27":previous,"2026-10-28":current}}
    p=daydir/"actual.json";p.write_text(json.dumps(data))
    monkeypatch.setattr(x,"FLOW_ROOT",base)
    monkeypatch.setattr(x,"next_session",lambda _: "2026-10-28")
    monkeypatch.setattr(x,"calendar_sessions",lambda a,b:["2026-10-28","2026-10-29","2026-10-30"])
    good=x.source_flow(now("2026-10-30T18:15:00"))
    assert good["day"]=="2026-10-28" and float(good["net_cny"])==16.
    data["observations_by_date"]["2026-10-28"]["159919"]["shares_first_observed_at"]="2026-10-31T18:15:00+08:00"
    p.write_text(json.dumps(data))
    with pytest.raises(ValueError,match="NO_PIT_COMPLETE"):
        x.source_flow(now("2026-10-30T18:15:00"))


def test_T_plus_one_conservative_stop_wins_and_paired_ETF_is_same_minute(monkeypatch):
    trade="2026-11-02";exit_day="2026-11-03"
    def mkbar(day,price,hi,lo):
        return {"date":day,"open":price,"high":hi,"low":lo,"close":price,"volume":1000.}
    stock={"bars":[mkbar("2026-10-30",10.,10.1,9.9),
                   mkbar(trade,10.2,10.5,10.0),
                   mkbar(exit_day,10.3,11.5,9.7)],"raw_sha256":"stock"}
    ref={"bars":[mkbar("2026-10-30",4.,4.1,3.9),
                 mkbar(trade,4.0,4.1,3.9),
                 mkbar(exit_day,4.1,4.2,4.)],"raw_sha256":"ref"}
    monkeypatch.setattr(x,"next_session",lambda d:trade)
    monkeypatch.setattr(x,"calendar_sessions",
                        lambda a,b:[trade] if b==trade else [trade,exit_day])
    monkeypatch.setattr(x,"prices",lambda ak,code,through:ref if code=="510300" else stock)
    def fake_minutes(ak,code,day,*args,**kwargs):
        if code=="510300":
            bars=[{"minute":f"{day} 09:31","open":4.1,"low":4.,"high":4.2,"volume":100}]
        else:
            bars=[{"minute":f"{day} 09:31","open":10.3,"low":9.7,"high":11.5,"volume":100}]
        return {"bars":bars,"sha256":code+"-"+day}
    monkeypatch.setattr(x,"minute_rows",fake_minutes)
    f={"freeze_created_at":"2026-10-30T18:15:00+08:00",
       "asof_session":"2026-10-30","next_open_session":trade,
       "signal_sha256":"testfreeze",
       "selected":[{"code":"600000","cohort":"S1","close":10.,
                    "atr14":.10,"breakout":10.01}]}
    t=x.assess(object(),"B",f,now("2026-11-02T18:20:00"))
    assert t["entries"][0]["status"]=="EXIT_NOT_MATURED"
    result=x.assess(object(),"B",f,now("2026-11-03T18:20:00"))
    entry=result["entries"][0]
    assert entry["status"]=="PAPER_EXIT_SCENARIO_NO_BROKER_FILL"
    assert entry["exit_reason"]=="STOP_FIRST"
    assert entry["exit_time"]=="2026-11-03 09:31"
    assert entry["net_pnl"]<0 and entry["benchmark_net_pnl"] is not None
    assert entry["paired_excess_pnl"]==pytest.approx(entry["net_pnl"]-entry["benchmark_net_pnl"])
    assert not entry["broker_fill_confirmed"]


def test_existing_freeze_hash_tamper_fails_business_gate(monkeypatch,tmp_path):
    monkeypatch.setattr(x,"calendar_sessions",lambda a,b:["2026-10-30"])
    p=tmp_path/"freezes"/"B"/"2026-10-30.json"
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps({"group":"B","asof_session":"2026-10-30",
                             "signal_sha256":"tampered","selected":[]}))
    r=x.run(object(),now("2026-10-30T20:15:00"),"B",tmp_path)
    assert r["freeze_status"]=="FREEZE_FAILED_NO_BACKFILL"
    assert any("INTEGRITY" in e for e in r["errors"])


def test_actual_git_commit_proof_is_required_for_entry(monkeypatch):
    import subprocess
    class Reply:
        returncode=0
        stdout="2026-10-30T18:16:22+08:00\n"
    monkeypatch.setattr(subprocess,"run",lambda *a,**k:Reply())
    stamp=x.freeze_archive_commit_at("records/national_team_short_ab/freezes/B/2026-10-30.json")
    assert stamp==now("2026-10-30T18:16:22")
    class NoCommit:
        returncode=0
        stdout=""
    monkeypatch.setattr(subprocess,"run",lambda *a,**k:NoCommit())
    assert x.freeze_archive_commit_at("no-file.json") is None


def test_arbitrary_after_midnight_freeze_not_eligible_even_if_calendar_next_day(monkeypatch):
    monkeypatch.setattr(x,"calendar_sessions",lambda a,b:["2026-10-30","2026-11-02"])
    assert x.close_day(now("2026-11-02T00:55:00")) is None


def test_b_hard_position_limits_hold_after_tiny_price_change():
    for price in (2.01,9.99,20.01,49.99,80.01):
        pos=x.entry_position(price,{"atr14":.25},x.GROUPS["B"],20000.)
        if pos:
            assert pos["qty"]%100==0
            assert pos["notional"]<=8000
            assert pos["budget_risk"]<=150


def test_end_to_end_synthetic_source_freeze_persist_idempotent_and_next_open(monkeypatch,tmp_path):
    """Hermetic full pipeline, NOT evidence of genuine market fills or alpha."""
    class FakeNames:
        columns=("code","name")
        def iterrows(self):
            return iter((i,{"code":code,"name":"SYN"+code})
                        for i,(_,code) in enumerate(x.RANK_ORDER))
    class FakeAK:
        def stock_info_a_code_name(self):return FakeNames()
    ak=FakeAK()
    # 300 completed *synthetic* historical observations, with one explicitly dated
    # new as-of session. Daily order is deterministic and aligned to benchmark.
    sessions=[(date(2025,1,1)+timedelta(days=i)).isoformat() for i in range(300)]
    sessions.append("2026-10-30")
    stock=[]
    etf=[]
    for i,d in enumerate(sessions):
        c=10+i*.01
        stock.append({"date":d,"open":c,"high":c+.02,"low":c-.02,
                      "close":c,"volume":200 if i==300 else 100,
                      "turnover":100000000})
        etf.append({"date":d,"open":4.,"high":4.02,"low":3.98,
                    "close":4.,"volume":10000})
    stock[-1]["close"]=stock[-2]["close"]+.25
    stock[-1]["open"]=stock[-1]["close"]
    stock[-1]["high"]=stock[-1]["close"]+.02
    stock[-1]["low"]=stock[-1]["close"]-.02
    cache={"510300":{"bars":etf,"raw_sha256":x.sha(etf)}}
    for group,code in x.RANK_ORDER:
        cache[code]={"bars":stock,"raw_sha256":x.sha(stock),"kind":"SYNTHETIC"}
    monkeypatch.setattr(x,"prices",lambda ak,code,through:cache[code])
    monkeypatch.setattr(x,"source_flow",lambda now:{"net_cny":"1000",
                           "day":"2026-10-28","first_observed_at":"2026-10-29T17:00:00+08:00",
                           "scope":"SYNTHETIC_TEST"})
    monkeypatch.setattr(x,"strategy_snapshot",lambda now:{"first_public_at":"2026-10-28T23:46:43+08:00",
                                                          "path":"SYNTHETIC","sha256":"fixture"})
    monkeypatch.setattr(x,"calendar_sessions",lambda a,b:["2026-10-30"] if b=="2026-10-30" else ["2026-11-02"])
    monkeypatch.setattr(x,"next_session",lambda day:"2026-11-02")
    for group in ("A2","B"):
        result=x.run(ak,now("2026-10-30T18:15:00"),group,tmp_path)
        assert result["freeze_status"]=="FROZEN_BEFORE_NEXT_SESSION"
        freeze_file=tmp_path/"freezes"/group/"2026-10-30.json"
        frozen=json.loads(freeze_file.read_text())
        assert frozen["signal_sha256"]==x.sha({k:v for k,v in frozen.items() if k!="signal_sha256"})
        assert frozen["next_open_session"]=="2026-11-02"
        assert str(frozen["source_run_id"])
        assert len(frozen["checked"])==10
        assert 1<=len(frozen["selected"])<=x.GROUPS[group]["max_positions"]
        assert frozen["real_orders"]==0
        again=x.run(ak,now("2026-10-30T20:15:00"),group,tmp_path)
        assert again["freeze_status"]=="EXISTING_FREEZE_UNCHANGED"
        assert json.loads(freeze_file.read_text())==frozen
    # Even if the program is manually invoked after midnight, no additional
    # 10/30 signal can be forged or rewritten.
    missed=x.run(ak,now("2026-10-31T00:55:00"),"B",tmp_path)
    assert not missed["freeze_created"]


def test_same_funding_date_cannot_generate_second_session_paper_signal(monkeypatch,tmp_path):
    monkeypatch.setattr(x,"calendar_sessions",lambda a,b:[a] if a==b else [a,b])
    monkeypatch.setattr(x,"next_session",lambda day:"2026-11-02" if day=="2026-10-30" else "2026-11-03")
    def fake_freeze(ak,now,group,day):
        freeze={"group":group,"asof_session":day,"selected":[],
                "next_open_session":x.next_session(day),
                "four_etf_flow":{"day":"2026-10-28","net_cny":"3246374430"}}
        return dict(freeze,signal_sha256=x.sha(freeze))
    monkeypatch.setattr(x,"build_freeze",fake_freeze)
    assert x.run(object(),now("2026-10-30T18:15:00"),"B",tmp_path)["freeze_created"]
    next_day=x.run(object(),now("2026-11-02T18:15:00"),"B",tmp_path)
    assert next_day["freeze_status"]=="NO_NEW_FOUR_ETF_EVENT"
    assert next_day["duplicate_funding_day"]=="2026-10-28"
    assert not next_day["freeze_created"]
    assert not (tmp_path/"freezes"/"B"/"2026-11-02.json").exists()


def test_negative_funding_is_valid_cash_decision_not_ci_failure(monkeypatch,tmp_path):
    monkeypatch.setattr(x,"calendar_sessions",lambda a,b:[a])
    def no_positive(ak,now,group,day):
        raise ValueError("FOUR_ETF_FLOW_NOT_POSITIVE:2026-10-29:-100")
    monkeypatch.setattr(x,"build_freeze",no_positive)
    result=x.run(object(),now("2026-10-30T18:15:00"),"B",tmp_path)
    assert result["freeze_status"]=="NO_POSITIVE_CORE_FOUR_FLOW"
    assert result["errors"]==[]
    assert not result["freeze_created"]

def test_unknown_higher_rank_never_promotes_lower():
    checked=[{"cohort":g,"code":c,"eligible":True,"data_status":"VERIFIED"}
             for g,c in x.RANK_ORDER]
    checked[0]["data_status"]="UNVERIFIED"
    checked[0]["eligible"]=False
    assert [v["code"] for v in x.selects(checked,"A2")]==["600309"]
    assert [v["code"] for v in x.selects(checked,"B")]==["600309"]

def test_gate_reasons_strict_vs_aggressive():
    stk=[];bench=[]
    for i in range(300):
        d=(date(2025,1,1)+timedelta(days=i)).isoformat()
        c=10+i*.01
        stk.append({"date":d,"open":c,"high":c+.05,"low":c-.05,
                    "close":c,"volume":100,"turnover":60000000})
        bench.append({"date":d,"close":4.})
    a=x.indicator({"bars":stk},{"bars":bench},stk[-1]["date"],"A2")
    b=x.indicator({"bars":stk},{"bars":bench},stk[-1]["date"],"B")
    assert "VOLUME_1P2X" in a["rejection_reasons"]
    assert b["eligible"] and not b["rejection_reasons"]

def test_partial_vendor_outage_keeps_verified_arm_and_audit(monkeypatch):
    monkeypatch.setattr(x,"next_session",lambda d:"2026-11-02")
    class Names:
        columns=("code","name")
        def iterrows(self):
            return iter((i,{"code":c,"name":"SAFE"}) for i,(_,c) in enumerate(x.RANK_ORDER))
    class AK:
        def stock_info_a_code_name(self):return Names()
    def price(ak,code,day):
        if code=="600000":raise ConnectionError("vendor timeout")
        return {"bars":[{"date":day,"close":10}],"raw_sha256":"test","kind":"TEST"}
    def ind(stock,bench,day,group):
        return {"eligible":True,"close":10.,"atr14":.2,"breakout":9.,
                "rejection_reasons":[],"gate_checks":{}}
    monkeypatch.setattr(x,"prices",price)
    monkeypatch.setattr(x,"indicator",ind)
    f=x.build_freeze(AK(),now("2026-10-30T18:15:00"),"B","2026-10-30",
                     flow={"day":"2026-10-29","net_cny":"500"},v2={"path":"V2"})
    assert len(f["checked"])==10 and f["candidate_diagnostics"]["unverified"]==1
    assert [v["code"] for v in f["selected"]]==["601825","600309"]

def test_entry_exit_create_only_replay_drift(tmp_path):
    frozen={"signal_sha256":"freeze"}
    row={"signal_id":"freeze-0-600000","code":"600000","cohort":"S1","group":"B",
         "entry_session":"2026-11-02","entry_price":10.01,
         "entry_time":"2026-11-02 09:30","method":"B1_0930_OPEN",
         "qty":100,"notional":1001.,"stop":9.7,"target":10.63,
         "budget_risk":45.,"entry_fee":5.,"benchmark_entry_price":4.0,
         "benchmark_quantity":200,"entry_daily_bar_sha256":"stock",
         "benchmark_entry_daily_bar_sha256":"etf",
         "status":"PAPER_EXIT_SCENARIO_NO_BROKER_FILL",
         "exit_day":"2026-11-03","exit_time":"2026-11-03 10:01",
         "exit_reason":"TARGET","exit_price":10.6,
         "net_pnl":50.,"benchmark_minute_sha256":"bm",
         "exit_minute_sha256":"minute","benchmark_exit_price":4.05,
         "benchmark_net_pnl":1.,"paired_excess_pnl":49.}
    when=now("2026-10-30T18:16:00")
    a=x.lock_paper_replay("B",frozen,{"entries":[dict(row)]},tmp_path,when)
    assert len(a["locked_entries"])==len(a["locked_exits"])==1
    assert not x.lock_paper_replay("B",frozen,{"entries":[dict(row)]},tmp_path,when)["drifts"]
    wrong=dict(row,stop=9.9)
    assert x.lock_paper_replay("B",frozen,{"entries":[wrong]},tmp_path,when)["drifts"]
    assert wrong["status"]=="ENTRY_LEDGER_DRIFT_BLOCKED" and "net_pnl" not in wrong
    wrong=dict(row,net_pnl=999.)
    assert x.lock_paper_replay("B",frozen,{"entries":[wrong]},tmp_path,when)["drifts"]
    assert wrong["status"]=="EXIT_LEDGER_DRIFT_BLOCKED" and "net_pnl" not in wrong

def test_preopen_possible_three_percent_gap_is_not_a_false_rejection(monkeypatch):
    """Buying one lot at a legal low-gap quote may fit even if +3% doesn't."""
    monkeypatch.setattr(x,"next_session",lambda day:"2026-11-02")
    class Names:
        columns=("code","name")
        def iterrows(self):
            return iter((i,{"code":c,"name":"SAFE"}) for i,(_,c) in enumerate(x.RANK_ORDER))
    class AK:
        def stock_info_a_code_name(self):return Names()
    def price(ak,code,day):
        return {"bars":[{"date":day,"close":49.5}],"raw_sha256":"test","kind":"TEST"}
    def ind(hist,ref,day,group):
        return {"eligible":True,"close":49.5,"breakout":49.5,
                "atr14":.2,"rejection_reasons":[],"gate_checks":{}}
    monkeypatch.setattr(x,"prices",price)
    monkeypatch.setattr(x,"indicator",ind)
    f=x.build_freeze(AK(),now("2026-10-30T18:15:00"),"A2","2026-10-30",
                     flow={"day":"2026-10-29","net_cny":"500"},v2={"path":"V2"})
    assert f["checked"][0]["eligible"] is True
    assert 100*49.5*1.03>5000
    assert [i["code"] for i in f["selected"]]==["601825","600309"]

def test_four_etf_prior_observation_future_stamp_rejected(monkeypatch,tmp_path):
    folder=tmp_path/"merged"/"2026-10-30"
    folder.mkdir(parents=True)
    stamp="2026-10-29T15:10:00+08:00"
    older={code:{"shares":"100","nav":"4",
                 "shares_first_observed_at":stamp,"nav_first_observed_at":stamp}
           for code in x.CORE}
    current={code:{"shares":"101","nav":"4",
                   "shares_first_observed_at":stamp,"nav_first_observed_at":stamp}
             for code in x.CORE}
    older["510300"]["shares_first_observed_at"]="2026-10-31T00:00:00+08:00"
    (folder/"evidence.json").write_text(json.dumps({
        "first_observed_no_earlier_than":stamp,
        "observations_by_date":{"2026-10-27":older,"2026-10-28":current}}))
    monkeypatch.setattr(x,"FLOW_ROOT",tmp_path/"merged")
    monkeypatch.setattr(x,"next_session",lambda d:"2026-10-28")
    monkeypatch.setattr(x,"calendar_sessions",lambda a,b:["2026-10-28","2026-10-29","2026-10-30"])
    with pytest.raises(ValueError,match="NO_PIT_COMPLETE"):
        x.source_flow(now("2026-10-30T18:15:00"))

def test_sina_stock_history_unadjusted_schema_and_turnover(monkeypatch):
    import pandas as pd
    frame=pd.DataFrame([
        {"date":"2026-10-29","open":10.,"high":11.,"low":9.,"close":10.5,
         "volume":10000,"amount":102000000},
        {"date":"2026-10-30","open":10.5,"high":11.,"low":10.,"close":10.8,
         "volume":11000,"amount":119000000}])
    class AK:
        def stock_zh_a_daily(self,**kwargs):
            assert kwargs["symbol"]=="sh601825" and kwargs["adjust"]==""
            return frame
        def stock_zh_a_hist(self,**kwargs):
            raise AssertionError("EM must not be called when Sina works")
    out=x.prices(AK(),"601825","2026-10-30")
    assert out["kind"]=="SINA_STOCK_DAILY_NO_ADJUST"
    assert out["bars"][-1]["turnover"]==119000000
    assert out["bars"][-1]["date"]=="2026-10-30"
    assert out["raw_sha256"]==x.sha(out["bars"])

def test_official_sse_roster_over_broken_generic_name_api():
    import pandas as pd
    class AK:
        def stock_info_sh_name_code(self,**kwargs):
            assert kwargs["symbol"]=="主板A股"
            return pd.DataFrame([{"证券代码":"601825","证券简称":"沪市样例"}])
        def stock_info_a_code_name(self):
            raise AssertionError("no generic call if SSE success")
    names,provider=x.stock_names(AK())
    assert names["601825"]=="沪市样例"
    assert provider=="SSE_OFFICIAL_MAIN_BOARD"

def test_sina_minute_history_accepted_only_if_complete(monkeypatch):
    import pandas as pd
    from datetime import datetime,timedelta
    date_string="2026-10-30"
    morning=[datetime.fromisoformat(date_string+" 09:30")+timedelta(minutes=i)
             for i in range(121)]
    afternoon=[datetime.fromisoformat(date_string+" 13:00")+timedelta(minutes=i)
               for i in range(111)]
    minutes=morning+afternoon
    frame=pd.DataFrame([{"day":t.strftime("%Y-%m-%d %H:%M:%S"),
                         "open":10.,"high":10.1,"low":9.9,
                         "close":10.,"volume":100}
                        for t in minutes])
    class AK:
        def stock_zh_a_minute(self,**kwargs):
            assert kwargs["symbol"]=="sh601825"
            return frame
        def stock_zh_a_hist_min_em(self,**kwargs):
            raise AssertionError("should not query EM when Sina is complete")
    got=x.minute_rows(AK(),"601825",date_string)
    assert got["provider"]=="SINA_1MIN"
    assert got["bars"][-1]["minute"]==date_string+" 14:50"
    assert got["sha256"]==x.sha(got["bars"])
    with pytest.raises(ValueError,match="INCOMPLETE_MINUTE_SOURCE"):
        x._normalize_minutes(frame.iloc[:-1],"601825",date_string,"09:30","14:50","SINA_1MIN")


def test_daily_etf_can_use_real_complete_current_1m_not_prior_nav(monkeypatch):
    import pandas as pd
    from datetime import datetime,timedelta
    day="2026-10-30"
    historical=pd.DataFrame([
        {"date":(date(2026,7,1)+timedelta(days=i)).isoformat(),
         "open":4.,"high":4.1,"low":3.9,"close":4.,"volume":10000}
        for i in range(121)])
    # Complete 1-minute actual-day timeline, ending at 15:00.
    times=([datetime.fromisoformat(day+" 09:30")+timedelta(minutes=i) for i in range(121)] +
           [datetime.fromisoformat(day+" 13:00")+timedelta(minutes=i) for i in range(121)])
    ticks=pd.DataFrame([{"day":v.strftime("%Y-%m-%d %H:%M:%S"),
                        "open":4.02,"high":4.05,"low":4.0,
                        "close":4.03,"volume":100.} for v in times])
    class AK:
        def fund_etf_hist_em(self,**kwargs):
            raise RuntimeError("Push2RateLimitError: too many requests")
        def fund_etf_hist_sina(self,**kwargs):
            return historical
        def stock_zh_a_minute(self,**kwargs):
            assert kwargs["symbol"]=="sh510300" and kwargs["adjust"]==""
            return ticks
    monkeypatch.setattr(x,"_EM_RATE_LIMITED",False)
    result=x.prices(AK(),"510300",day)
    assert result["kind"]=="SINA_ETF_PRIOR_DAILY_PLUS_VERIFIED_1M_SESSION"
    assert x.bar(result,day)["close"]==4.03
    assert x.bar(result,day)["volume"]==len(times)*100
    assert result["current_session_minute_sha256"]
    class Truncated(AK):
        def stock_zh_a_minute(self,**kwargs):
            return ticks.iloc[:-1]
    with pytest.raises(ValueError,match="ETF_1M_SESSION_NOT_COMPLETE"):
        x._completed_etf_daily_from_sina_minutes(Truncated(),day)


def test_etf_minute_incomplete_cannot_substitute_1450_for_1500():
    import pandas as pd
    class AK:
        def stock_zh_a_minute(self,**kwargs):
            return pd.DataFrame([{"day":"2026-10-30 14:50:00",
                                  "open":4.,"high":4.,"low":4.,"close":4.,
                                  "volume":1000}])
    with pytest.raises(ValueError,match="ETF_1M_SESSION_NOT_COMPLETE"):
        x._completed_etf_daily_from_sina_minutes(AK(),"2026-10-30")

def test_frozen_benchmark_close_cannot_be_revised_on_paper_replay(monkeypatch):
    frozen={"group":"B","next_open_session":"2026-11-02",
            "asof_session":"2026-10-30","benchmark_asof_close":4.065,
            "selected":[],"signal_sha256":"fixture"}
    monkeypatch.setattr(x,"execution_gate",lambda freeze,now:None)
    monkeypatch.setattr(x,"calendar_sessions",lambda first,last:["2026-11-02"])
    monkeypatch.setattr(x,"prices",lambda ak,code,day:{
        "bars":[{"date":"2026-10-30","close":4.075}],
        "raw_sha256":"later_revision"})
    result=x.assess(object(),"B",frozen,now("2026-11-02T18:15:00"))
    assert result["status"]=="BENCHMARK_FREEZE_CLOSE_REVISED"
    assert result["entries"]==[]


# 2026-10-30 Sol P0 red-team regressions: unknown != validated cash;
# exact minute trading grid; T+1/T+2 final 10m; shared account.
def _grid_minutes(day, last="15:00", ending=False):
    from datetime import datetime,timedelta
    def series(st,fin):
        t=datetime.fromisoformat(day+" "+st)
        u=datetime.fromisoformat(day+" "+fin)
        out=[]
        while t<=u:
            out.append(t.strftime("%Y-%m-%d %H:%M:%S"))
            t+=timedelta(minutes=1)
        return out
    first="09:31" if ending else "09:30"
    second="13:01" if ending else "13:00"
    stamps=series(first,"11:30")
    if last!="11:30":
        stamps+=series(second,last)
    return stamps

def _minute_df(stamps):
    import pandas as pd
    return pd.DataFrame([{"day":stamp,"open":10.,"high":10.1,
                          "low":9.9,"close":10.,"volume":100.}
                         for stamp in stamps])


@pytest.mark.parametrize("ending", [False,True])
def test_exact_minute_grid_accepts_only_complete_legal_sessions(ending):
    day="2026-10-30"
    got=x._normalize_minutes(_minute_df(_grid_minutes(day,ending=ending)),
                              "601825",day,"09:30","15:00","FIXTURE")
    assert len(got["bars"]) in (240,242)
    assert got["bars"][-1]["minute"]==day+" 15:00"


@pytest.mark.parametrize("damage",["delete_1000","delete_open","lunch",
                                   "duplicate","delete_1500","delete_1455"])
def test_missing_or_illegal_single_minute_must_not_hide_stop(damage):
    day="2026-10-30";stamps=_grid_minutes(day)
    if damage=="delete_1000":
        stamps.remove(day+" 10:00:00")
    elif damage=="delete_open":
        stamps.remove(day+" 09:30:00")
    elif damage=="lunch":
        stamps.append(day+" 12:01:00")
    elif damage=="duplicate":
        stamps.append(day+" 10:00:00")
    elif damage=="delete_1500":
        stamps.remove(day+" 15:00:00")
    else:
        stamps.remove(day+" 14:55:00")
    stamps.sort()
    with pytest.raises(ValueError,match="MINUTE"):
        x._normalize_minutes(_minute_df(stamps),"601825",day,"09:30","15:00","FIXTURE")


def test_incomplete_510300_daily_reconstruction_does_not_make_a_false_close():
    import pandas as pd
    day="2026-10-30"
    valid=_minute_df(_grid_minutes(day,ending=True))
    missing=valid[valid["day"]!=day+" 14:55:00"]
    class AK:
        def stock_zh_a_minute(self,**kw):return missing
    with pytest.raises(ValueError,match="ETF_1M_SESSION_NOT_COMPLETE"):
        x._completed_etf_daily_from_sina_minutes(AK(),day)


def test_source_unknown_remains_retryable_then_can_freeze_without_backdating(monkeypatch,tmp_path):
    day="2026-10-30"
    monkeypatch.setattr(x,"calendar_sessions",lambda a,b:[a])
    signal={"group":"B","asof_session":day,"next_open_session":"2026-11-02",
            "selected":[],"four_etf_flow":{"day":"2026-10-29","net_cny":"100"},
            "checked":[{"code":c,"cohort":g,"data_status":"UNVERIFIED"}
                       for g,c in x.RANK_ORDER]}
    def create(verified):
        obj=dict(signal)
        obj["checked"]=[dict(v,data_status="VERIFIED" if verified else "UNVERIFIED")
                        for v in signal["checked"]]
        obj["candidate_diagnostics"]={"total":10,
                                      "verified":10 if verified else 0,
                                      "unverified":0 if verified else 10}
        obj["signal_sha256"]=x.sha(obj)
        return obj
    monkeypatch.setattr(x,"build_freeze",lambda ak,now,group,day:create(False))
    bad=x.run(object(),now("2026-10-30T18:15:00"),"B",tmp_path)
    assert bad["freeze_status"]=="SOURCE_INCOMPLETE_RETRYABLE"
    assert bad["unconsumed_funding_day"]=="2026-10-29"
    assert not bad["freeze_created"]
    assert not list((tmp_path/"freezes").glob("**/*.json"))
    monkeypatch.setattr(x,"build_freeze",lambda ak,now,group,day:create(True))
    recovered=x.run(object(),now("2026-10-30T20:15:00"),"B",tmp_path)
    assert recovered["freeze_created"]
    assert recovered["freeze_status"]=="VALIDATED_CASH_FREEZE"
    frozen=json.loads((tmp_path/"freezes"/"B"/(day+".json")).read_text())
    assert frozen["status"]=="VALIDATED_CASH_NO_SIGNAL"
    assert frozen["selected"]==[]
    assert frozen["signal_sha256"]==x.sha({k:v for k,v in frozen.items() if k!="signal_sha256"})
    repeat=x.run(object(),now("2026-10-30T22:15:00"),"B",tmp_path)
    assert repeat["freeze_status"]=="EXISTING_FREEZE_UNCHANGED"


def test_one_arm_unknown_keeps_other_arm_verification_without_consuming_event(monkeypatch,tmp_path):
    day="2026-10-30"
    monkeypatch.setattr(x,"calendar_sessions",lambda a,b:[a])
    checked=[]
    for arm,code in x.RANK_ORDER:
        status="VERIFIED" if arm=="S1" else "UNVERIFIED"
        checked.append({"cohort":arm,"code":code,"data_status":status,
                        "eligible":arm=="S1"})
    def build(ak,now,group,day):
        obj={"group":group,"asof_session":day,"next_open_session":"2026-11-02",
             "selected":[checked[0]],"checked":checked,
             "candidate_diagnostics":{"total":10,"verified":5,"unverified":5},
             "four_etf_flow":{"day":"2026-10-29","net_cny":"1"}}
        return dict(obj,signal_sha256=x.sha(obj))
    monkeypatch.setattr(x,"build_freeze",build)
    run=x.run(object(),now("2026-10-30T18:15:00"),"A2",tmp_path)
    assert run["independent_verified_arms"]["S1"]["complete"]
    assert not run["independent_verified_arms"]["S2"]["complete"]
    assert run["independent_verified_arms"]["S1"]["candidates"]==["601825"]
    assert run["freeze_status"]=="SOURCE_INCOMPLETE_RETRYABLE"
    assert not run["freeze_created"]


@pytest.mark.parametrize("outcome,expected_minute,expected_last",[
    ("t1_late_stop","2026-11-03 14:55","15:00"),
    ("t2_late_target","2026-11-04 14:58","15:00"),
    ("t3_forced","2026-11-05 14:50","14:50"),
])
def test_exit_uses_full_T1_T2_market_and_only_T3_1450(monkeypatch,outcome,expected_minute,expected_last):
    days=["2026-11-02","2026-11-03","2026-11-04","2026-11-05"]
    def daily(day,close,high,low):
        return {"date":day,"open":close,"high":high,"low":low,
                "close":close,"volume":1000.}
    stock={"bars":[daily("2026-10-30",10,10.2,9.9),
                   daily(days[0],10.1,10.4,10.0),
                   daily(days[1],10.1,11.0,9.5),
                   daily(days[2],10.1,11.0,9.5),
                   daily(days[3],10.1,10.4,10.0)],"raw_sha256":"stock"}
    bench={"bars":[daily("2026-10-30",4.,4.05,3.95)]+
            [daily(day,4.,4.05,3.95) for day in days],"raw_sha256":"benchmark"}
    monkeypatch.setattr(x,"prices",lambda ak,code,through:bench if code=="510300" else stock)
    monkeypatch.setattr(x,"next_session",lambda d:days[0])
    monkeypatch.setattr(x,"calendar_sessions",lambda a,b:days[:days.index(b)+1])
    calls=[]
    def minutes(ak,code,day,first="09:30",last="14:50"):
        calls.append((code,day,last))
        if day==days[3]:assert last=="14:50"
        else:assert last=="15:00"
        bars=[{"minute":day+" 09:31","open":4. if code=="510300" else 10.1,
               "high":4.04 if code=="510300" else 10.2,
               "low":3.96 if code=="510300" else 10.0}]
        if day==days[1] and outcome=="t1_late_stop" and code!="510300":
            hi,lo=10.2,9.5
        elif day==days[2] and outcome=="t2_late_target" and code!="510300":
            hi,lo=11.0,10.0
        else:
            hi,lo=(4.04,3.96) if code=="510300" else (10.2,10.0)
        terminal="14:50" if last=="14:50" else "15:00"
        if terminal=="15:00":
            bars.append({"minute":day+(" 14:55" if day==days[1] else " 14:58"),
                         "open":4. if code=="510300" else 10.1,
                         "high":hi,"low":lo})
        bars.append({"minute":day+" "+terminal,
                     "open":4. if code=="510300" else 10.1,
                     "high":4.04 if code=="510300" else 10.2,
                     "low":3.96 if code=="510300" else 10.0})
        return {"bars":bars,"sha256":day+code+last}
    monkeypatch.setattr(x,"minute_rows",minutes)
    frozen={"freeze_created_at":"2026-10-30T18:15:00+08:00",
            "asof_session":"2026-10-30","next_open_session":days[0],
            "signal_sha256":"forward-test",
            "selected":[{"code":"600000","cohort":"S1","close":10.,"atr14":.10,
                         "breakout":10.01}]}
    result=x.assess(object(),"B",frozen,now("2026-11-05T18:10:00"))
    event=result["entries"][0]
    assert event["status"]=="PAPER_EXIT_SCENARIO_NO_BROKER_FILL"
    assert event["exit_time"]==expected_minute
    assert (event["exit_reason"]=="STOP_FIRST" if outcome=="t1_late_stop"
            else event["exit_reason"]=="TARGET" if outcome=="t2_late_target"
            else event["exit_reason"]=="T_PLUS_3_1450")
    assert ("510300",event["exit_day"],expected_last) in calls


def test_shared_account_cash_open_positions_and_release_timing():
    first={"group":"B","code":"601825","signal_id":"a",
           "entry_session":"2026-11-02","notional":7000.,"entry_fee":5.,
           "entry_price":70.,"status":"EXIT_NOT_MATURED"}
    second=dict(first,code="600309",signal_id="b",
                entry_session="2026-11-03",notional=7000.)
    current=x.account_snapshot_before([first,second],"2026-11-04","B")
    assert current["cash_available"]==16000-10
    assert current["gross_active"]==14000
    assert current["active_positions"]==2
    closed=dict(first,status="PAPER_EXIT_SCENARIO_NO_BROKER_FILL",
                exit_day="2026-11-04",net_pnl=60.)
    too_early=x.account_snapshot_before([closed,second],"2026-11-04","B")
    assert too_early["active_positions"]==2  # 14:xx sale cannot fund 09:30 buy
    released=x.account_snapshot_before([closed,second],"2026-11-05","B")
    assert released["active_positions"]==1
    assert released["gross_active"]==7000
    assert released["cash_available"]==30000+60-7005
    assert x.account_snapshot_before([first],"2026-11-03","A2")["cash_available"]==30000


def test_run_three_overlapping_events_reuses_one_account_not_three(monkeypatch,tmp_path):
    sessions=["2026-11-02","2026-11-03","2026-11-04"]
    archives=[]
    for i,trade in enumerate(sessions):
        f={"group":"B","asof_session":"2026-10-30",
           "next_open_session":trade,"freeze_created_at":"2026-10-30T18:15:00+08:00",
           "selected":[],"signal_sha256":f"fund-{i}"}
        archives.append((tmp_path/f"f{i}.json",f))
    monkeypatch.setattr(x,"locked_freezes",lambda group,root:archives)
    monkeypatch.setattr(x,"freeze_archive_commit_at",
                        lambda p:now("2026-10-30T18:18:00"))
    monkeypatch.setattr(x,"calendar_sessions",lambda a,b:sessions[:sessions.index(b)+1])
    monkeypatch.setattr(x,"next_session",lambda d:"2026-11-02")
    monkeypatch.setattr(x,"close_day",lambda now:None)
    monkeypatch.setattr(x,"lock_paper_replay",
                        lambda *args,**kw:{"drifts":[],"locked_entries":[],"locked_exits":[]})
    snapshots=[]
    def fake_assess(ak,group,frozen,now,portfolio=None):
        snapshots.append(portfolio)
        amount=(7000.,7000.,5000.)[len(snapshots)-1]
        e={"group":"B","code":("601825","600309","601919")[len(snapshots)-1],
           "signal_id":"x"+str(len(snapshots)),
           "entry_session":frozen["next_open_session"],
           "entry_price":10.,"notional":amount,"entry_fee":5.,
           "status":"EXIT_NOT_MATURED"}
        return {"status":"REPLAYED_PAPER_SCENARIOS_NOT_LIVE","entries":[e]}
    monkeypatch.setattr(x,"assess",fake_assess)
    result=x.run(object(),now("2026-11-04T18:15:00"),"B",tmp_path)
    assert len(snapshots)==3
    assert snapshots[0]["gross_active"]==0.
    assert snapshots[1]["gross_active"]==7000.
    assert snapshots[2]["gross_active"]==14000.
    assert result["portfolio_latest_verified"]["gross_active"]==19000.
    assert result["portfolio_latest_verified"]["active_positions"]==3
    assert result["portfolio_latest_verified"]["cash_available"]==30000-19000-15
