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
