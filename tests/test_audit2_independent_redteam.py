"""Second independent audit reproduction, fixed against first-seen 2026-10-30 HEAD.

No network, no broker, synthetic market fixtures. Keep these red-team cases
even after the original branch fails and is repaired.
"""
from datetime import datetime
import json
from national_team import short_ab_engine as x

def now(s):
    return datetime.fromisoformat(s).replace(tzinfo=x.BJ)

def synthetic_freeze(day,complete=False,changed=False):
    checked=[]
    for arm,code in x.RANK_ORDER:
        verified=complete or arm=="S1"
        eligible=verified and not (changed and code=="601825")
        checked.append(dict(cohort=arm,code=code,
                            data_status="VERIFIED" if verified else "UNVERIFIED",
                            eligible=eligible))
    event=dict(group="A2",asof_session=day,
               next_open_session={"2026-10-30":"2026-11-02",
                                  "2026-11-02":"2026-11-03"}[day],
               freeze_created_at=day+"T18:15:00+08:00",
               four_etf_flow={"day":"2026-10-29"},
               checked=checked,selected=x.selects(checked,"A2"),
               candidate_diagnostics={"total":10,"verified":10 if complete else 5,
                                      "unverified":0 if complete else 5})
    return dict(event,signal_sha256=x.sha(event))

def test_R2_partial_cannot_reconsume_same_funding_on_future_day(monkeypatch,tmp_path):
    monkeypatch.setattr(x,"close_day",lambda t:t.date().isoformat())
    monkeypatch.setattr(x,"freeze_archive_commit_at",lambda p:now("2026-10-30T18:20:00"))
    monkeypatch.setattr(x,"assess",lambda *a,**kw:dict(entries=[],status="VERIFIED_NO_ENTRY_PRICE_GATE"))
    monkeypatch.setattr(x,"build_freeze",lambda ak,t,g,d:synthetic_freeze(d))
    x.run(None,now("2026-10-30T18:15:00"),"A2",tmp_path)
    r=x.run(None,now("2026-11-02T18:15:00"),"A2",tmp_path)
    names=[p.name for p in (tmp_path/"freezes"/"A2").glob("*.json")]
    assert names==["2026-10-30-S1.json"],(r["freeze_status"],names)

def test_R3_recovery_locks_entire_S1_not_old_ticker_only(monkeypatch,tmp_path):
    monkeypatch.setattr(x,"close_day",lambda t:t.date().isoformat())
    monkeypatch.setattr(x,"build_freeze",lambda ak,t,g,d:synthetic_freeze(d))
    x.run(None,now("2026-10-30T18:15:00"),"A2",tmp_path)
    monkeypatch.setattr(x,"build_freeze",lambda ak,t,g,d:synthetic_freeze(d,True,True))
    x.run(None,now("2026-10-30T20:15:00"),"A2",tmp_path)
    picks=[p for _,f in x.locked_freezes("A2",tmp_path) for p in f["selected"]]
    assert sum(p["cohort"]=="S1" for p in picks)==1,[(p["cohort"],p["code"]) for p in picks]
    assert any(p["cohort"]=="S2" for p in picks)

def fixture(monkeypatch,terminal_hit=False):
    days=["2026-11-02","2026-11-03","2026-11-04","2026-11-05"]
    def price(ak,code,through):
        p=4. if code=="510300" else 10.1
        bars=[dict(date="2026-10-30",open=10.,close=10.,high=10.2,
                   low=9.9,volume=1000.)]
        bars += [dict(date=d,open=p,close=p,high=p+.05,low=p-.05,volume=1000.)
                 for d in days]
        return dict(bars=bars,raw_sha256=code)
    monkeypatch.setattr(x,"prices",price)
    monkeypatch.setattr(x,"next_session",lambda d:days[0])
    monkeypatch.setattr(x,"calendar_sessions",lambda a,b:days[:days.index(b)+1])
    def minute(ak,code,day,first="09:30",last="14:50"):
        p=4. if code=="510300" else 10.1
        rows=[dict(minute=day+" 09:31",open=p,high=p+.05,low=p-.05)]
        rows.append(dict(minute=day+" "+last,open=p,high=p+.05,
                         low=9.5 if terminal_hit and day==days[-1] and code!="510300" else p-.05))
        return dict(bars=rows,sha256=code+day,minute_convention="BAR_START")
    monkeypatch.setattr(x,"minute_rows",minute)
    return dict(group="B",freeze_created_at="2026-10-30T18:15:00+08:00",
                asof_session="2026-10-30",next_open_session=days[0],
                signal_sha256="fixture",selected=[
                    dict(code="601825",cohort="S1",close=10.,atr14=.1,breakout=10.01)])

def test_R1_earlier_data_unknown_blocks_later_account_funding(monkeypatch,tmp_path):
    fixture(monkeypatch)
    prior=[]
    for i,(day,trade,code,close) in enumerate([
        ("2026-10-30","2026-11-02","601825",10.),
        ("2026-11-02","2026-11-03","600309",10.1)]):
        f=dict(group="B",asof_session=day,next_open_session=trade,
               freeze_created_at=day+"T18:15:00+08:00",signal_sha256=str(i),
               selected=[dict(code=code,cohort="S1",close=close,atr14=.1,breakout=10.01)])
        prior.append((tmp_path/f"{i}.json",f))
    monkeypatch.setattr(x,"locked_freezes",lambda g,r:prior)
    monkeypatch.setattr(x,"freeze_archive_commit_at",
                        lambda p:now(("2026-10-30" if p.stem=="0" else "2026-11-02")+"T18:20:00"))
    monkeypatch.setattr(x,"close_day",lambda t:None)
    monkeypatch.setattr(x,"next_session",
                        lambda d:{"2026-10-30":"2026-11-02",
                                  "2026-11-02":"2026-11-03"}[d])
    monkeypatch.setattr(x,"calendar_sessions",
                        lambda a,b:[d for d in ("2026-11-02","2026-11-03") if a<=d<=b])
    real=x.prices
    def outage(ak,code,through):
        if code=="601825":raise ValueError("DAILY_PROVIDERS_UNVERIFIED")
        return real(ak,code,through)
    monkeypatch.setattr(x,"prices",outage)
    first=x.run(None,now("2026-11-03T18:15:00"),"B",tmp_path)
    assert first["freeze_status"]=="ENTRY_DATA_UNKNOWN_BLOCKS_ACCOUNT"
    assert not list((tmp_path/"ledger"/"entries"/"B").glob("*.json"))
    decision=list((tmp_path/"ledger"/"decisions"/"B").glob("*.json"))
    assert len(decision)==1
    assert json.loads(decision[0].read_text())["decision_status"]=="ENTRY_DATA_UNKNOWN"
    # The later vendor recover cannot retro-authorize the original entry.
    monkeypatch.setattr(x,"prices",real)
    second=x.run(None,now("2026-11-03T19:15:00"),"B",tmp_path)
    assert second["freeze_status"]=="ENTRY_DATA_UNKNOWN_BLOCKS_ACCOUNT"
    assert not list((tmp_path/"ledger"/"entries"/"B").glob("*.json"))

def test_R4_1450_forced_sell_precedes_1450_start_bar_low(monkeypatch):
    frozen=fixture(monkeypatch,True)
    e=x.assess(None,"B",frozen,now("2026-11-05T18:15:00"))["entries"][0]
    assert e["exit_reason"]=="T_PLUS_3_1450"
    assert e["exit_time"]=="2026-11-05 14:50"

def test_R5_missing_V2_stock_cannot_turn_ETF_loss_into_excess_profit():
    from national_team.forward_evaluation import evaluate_frozen_event
    sessions=["2026-11-02","2026-11-03","2026-11-04",
              "2026-11-05","2026-11-06","2026-11-09"]
    event=dict(id="audit",first_public_at="2026-10-30T18:15:00+08:00",
               candidate_symbols=["600000"])
    prices={"510300":{d:dict(open=4.,close=3.,entry_blocked=False,exit_blocked=False)
                       for d in sessions}}
    h=evaluate_frozen_event(event,sessions,prices)["results"]["5"]
    assert h["status"]=="STOCK_ENTRY_DATA_UNKNOWN"
    assert h["paired_excess_net_return"] is None


def test_R2_partial_to_complete_next_day_still_same_fund_event(monkeypatch,tmp_path):
    monkeypatch.setattr(x,"close_day",lambda t:t.date().isoformat())
    monkeypatch.setattr(x,"freeze_archive_commit_at",lambda p:now("2026-10-30T18:20:00"))
    monkeypatch.setattr(x,"assess",lambda *a,**kw:dict(entries=[],status="VERIFIED_NO_ENTRY_PRICE_GATE"))
    monkeypatch.setattr(x,"build_freeze",lambda ak,t,g,d:synthetic_freeze(d))
    first=x.run(None,now("2026-10-30T18:15:00"),"A2",tmp_path)
    assert first["freeze_created"]
    monkeypatch.setattr(x,"build_freeze",lambda ak,t,g,d:synthetic_freeze(d,complete=True))
    second=x.run(None,now("2026-11-02T18:15:00"),"A2",tmp_path)
    assert second["freeze_status"]=="NO_NEW_FOUR_ETF_EVENT"
    assert len(x.locked_freezes("A2",tmp_path))==1


def test_R4_end_labelled_terminal_bar_uses_close_1450_not_open(monkeypatch):
    frozen=fixture(monkeypatch)
    def minute(ak,code,day,first="09:30",last="14:50"):
        p=4. if code=="510300" else 10.1
        bars=[dict(minute=day+" 09:31",open=p,high=p+.01,low=p-.01,close=p)]
        bars.append(dict(minute=day+" "+last,open=p,high=p+.01,low=p-.01,
                         close=p+.02))
        return {"bars":bars,"sha256":code+day,"minute_convention":"BAR_END"}
    monkeypatch.setattr(x,"minute_rows",minute)
    e=x.assess(None,"B",frozen,now("2026-11-05T18:15:00"))["entries"][0]
    assert e["exit_reason"]=="T_PLUS_3_1450"
    assert e["minute_convention"]=="BAR_END"
    assert e["benchmark_minute_convention"]=="BAR_END"
    assert e["benchmark_exit_quote"]==4.02


def test_R4_end_labelled_prior_minute_stop_still_wins(monkeypatch):
    frozen=fixture(monkeypatch)
    def minute(ak,code,day,first="09:30",last="14:50"):
        p=4. if code=="510300" else 10.1
        bars=[dict(minute=day+" 09:31",open=p,high=p+.01,low=p-.01,close=p)]
        stop=day=="2026-11-05" and code!="510300"
        bars.append(dict(minute=day+" "+last,open=p,high=p+.01,
                         low=9.5 if stop else p-.01,close=p))
        return {"bars":bars,"sha256":code+day,"minute_convention":"BAR_END"}
    monkeypatch.setattr(x,"minute_rows",minute)
    e=x.assess(None,"B",frozen,now("2026-11-05T18:15:00"))["entries"][0]
    assert e["exit_reason"]=="STOP_FIRST"


def test_R5_partial_missing_V2_stock_blocks_full_portfolio_pnl():
    from national_team.forward_evaluation import evaluate_frozen_event
    sessions=["2026-11-02","2026-11-03","2026-11-04",
              "2026-11-05","2026-11-06","2026-11-09"]
    event={"id":"partial","first_public_at":"2026-10-30T18:15:00+08:00",
           "candidate_symbols":["600000","600309"]}
    prices={
      "510300":{d:{"open":4.,"close":3.,"entry_blocked":False,"exit_blocked":False}
                for d in sessions},
      "600000":{d:{"open":10.,"close":12.,"entry_blocked":False,"exit_blocked":False}
                for d in sessions}}
    result=evaluate_frozen_event(event,sessions,prices)["results"]["5"]
    assert result["status"]=="STOCK_ENTRY_DATA_UNKNOWN"
    assert result["unknown_entry_symbols"]==["600309"]
    assert result["paired_excess_net_return"] is None


def test_R1_manual_expiry_is_immutable_and_never_backfills(monkeypatch,tmp_path):
    frozen={"group":"B","signal_sha256":"source-frozen","asof_session":"2026-10-30",
            "next_open_session":"2026-11-02","selected":[]}
    monkeypatch.setattr(x,"locked_freezes",lambda group,root:[(tmp_path/"source.json",frozen)])
    entry={"signal_id":"source-frozen-0-601825","code":"601825","cohort":"S1",
           "group":"B","entry_session":"2026-11-02",
           "status":"ENTRY_DATA_UNKNOWN","reason":"vendor source unavailable"}
    assert x.persist_entry_decision("B",frozen,entry,tmp_path,now("2026-11-02T18:15:00"))
    assert x.load_entry_decisions("B",tmp_path)[entry["signal_id"]]["decision_status"]=="ENTRY_DATA_UNKNOWN"
    expiry=x.expire_unknown_entry("B",tmp_path,entry["signal_id"],
                                  now("2026-11-03T18:30:00"),
                                  "human-reviewed: no verified paper fill, permanently abandon entry")
    assert expiry.is_file()
    before=x.load_entry_decisions("B",tmp_path,now=now("2026-11-03T18:00:00"))
    assert before[entry["signal_id"]]["decision_status"]=="ENTRY_DATA_UNKNOWN"
    after=x.load_entry_decisions("B",tmp_path,now=now("2026-11-03T19:00:00"))
    assert after[entry["signal_id"]]["decision_status"]=="ENTRY_EXPIRED"
    assert x.expire_unknown_entry("B",tmp_path,entry["signal_id"],
                                  now("2026-11-03T18:30:00"),
                                  "human-reviewed: no verified paper fill, permanently abandon entry")==expiry
    import pytest
    with pytest.raises(ValueError,match="IMMUTABLE_ENTRY_EXPIRY_DRIFT"):
        x.expire_unknown_entry("B",tmp_path,entry["signal_id"],
                               now("2026-11-03T20:00:00"),"trying to backdate a changed decision")
