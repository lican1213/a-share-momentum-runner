"""Prospective A2/B short-term *paper* cohorts; no brokerage APIs.

EXP-0005 A original stays immutable/missed. A2 is recovery, B is EXP-0006.
Only freezes created after an actual session close can be traded next session.
Entry and exit are labeled OHLC/minute scenarios, NOT broker executions.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

BJ=ZoneInfo("Asia/Shanghai")
CORE=("510300","510310","510330","159919")
GROUPS={
 "A2":{"experiment":"EXP-0005-A2","version":"EXP0005_A2_20261030","max_gross":10000,
       "max_each":5000,"max_positions":2,"gap_limit":.02,"min_adv":0},
 "B":{"experiment":"EXP-0006","version":"EXP0006_B_20261030","max_gross":20000,
      "max_each":8000,"max_positions":3,"gap_limit":.03,"min_adv":50000000},
}
RANKS={"S1":["601825","600000","601229","601166","600519"],
       "S2":["600309","601919","600660","601012","601838"]}
RANK_ORDER=[(c,s) for pair in zip(RANKS["S1"],RANKS["S2"]) for c,s in
            (("S1",pair[0]),("S2",pair[1]))]
ACCOUNT=30000.0
RISK=150.0
FEE=.0003; SLIP=.0005; STAMP=.0005
CUT=time(17,30); LAST_FREEZE=time(23,59,59)
STRATEGY_PATH=Path("records/national_team_strategy/2026-10-28/40719359363-a1-v2.json")
FLOW_ROOT=Path("records/national_team_merged")
RECORD_ROOT=Path("records/national_team_short_ab")
EARLIEST=date(2026,10,30)


def sha(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,ensure_ascii=False,
                    separators=(",",":"),default=str).encode("utf-8")).hexdigest()


def up(v):
    return math.ceil(float(v)*100-1e-9)/100


def down(v):
    return math.floor(float(v)*100+1e-9)/100


def fee(value,sell=False,etf=False):
    return max(5.0,value*FEE)+(value*STAMP if sell and not etf else 0.0)


def calendar_sessions(start,end):
    import exchange_calendars as xc
    return [x.strftime("%Y-%m-%d") for x in
            xc.get_calendar("XSHG").sessions_in_range(start,end)]


def close_day(now, sessions=None):
    """Freeze ONLY the current completed exchange session in Beijing.
    Delayed midnight schedules cannot capture yesterday as if on time.
    """
    if now.tzinfo is None:
        raise ValueError("timezone required")
    local=now.astimezone(BJ)
    today=local.date().isoformat()
    if local.date()<EARLIEST or not (CUT<=local.timetz().replace(tzinfo=None)<=LAST_FREEZE):
        return None
    if sessions is None:
        sessions=calendar_sessions(today,today)
    return today if today in sessions else None


def next_session(day):
    from datetime import timedelta
    all_days=calendar_sessions(day,(date.fromisoformat(day)+timedelta(days=12)).isoformat())
    next_days=[x for x in all_days if x>day]
    if not next_days:raise ValueError("exchange calendar has no next session")
    return next_days[0]


def normalize(df, code, kind):
    fields={"日期":"date","开盘":"open","最高":"high","最低":"low",
            "收盘":"close","成交量":"volume"}
    if code!="510300":fields["成交额"]="turnover"
    if not all(k in df.columns for k in fields):
        raise ValueError(f"{code}: OHLCV/turnover schema is missing")
    out=[]
    for _,row in df.sort_values("日期").iterrows():
        b={dest:(str(row[src])[:10] if dest=="date" else float(row[src]))
           for src,dest in fields.items()}
        o,h,l,c,v=(b[k] for k in ("open","high","low","close","volume"))
        if not all(math.isfinite(x) for x in b.values() if isinstance(x,float)):
            raise ValueError(f"{code}: nonfinite quote")
        if min(o,h,l,c)<=0 or v<0 or not l<=min(o,c)<=max(o,c)<=h:
            raise ValueError(f"{code}: invalid OHLC")
        if out and b["date"]<=out[-1]["date"]:
            raise ValueError(f"{code}: duplicate/nonascending history")
        out.append(b)
    return {"kind":kind,"code":code,"bars":out,"raw_sha256":sha(out)}


def prices(ak,code,through):
    end=through.replace("-","")
    if code=="510300":
        df=ak.fund_etf_hist_em(symbol=code,period="daily",start_date="20250101",end_date=end,adjust="")
        return normalize(df,code,"EASTMONEY_ETF_DAILY_NO_ADJUST")
    df=ak.stock_zh_a_hist(symbol=code,period="daily",start_date="20250101",end_date=end,adjust="")
    return normalize(df,code,"EASTMONEY_STOCK_DAILY_NO_ADJUST")


def bar(rows,day):
    return next((x for x in rows["bars"] if x["date"]==day),None)


def indicator(stock, benchmark, day, group):
    arr=stock["bars"];ref=benchmark["bars"]
    i=next((j for j,x in enumerate(arr) if x["date"]==day),None)
    k=next((j for j,x in enumerate(ref) if x["date"]==day),None)
    if i is None or k is None or i<250 or k<60:
        raise ValueError("250 prior stock and 60 benchmark sessions required")
    if arr[i-20]["date"]!=ref[k-20]["date"]:
        raise ValueError("20-session price calendar mismatch")
    c=arr[i]["close"]
    ma20=sum(x["close"] for x in arr[i-19:i+1])/20
    ma60=sum(x["close"] for x in arr[i-59:i+1])/60
    relative=c/arr[i-20]["close"]-ref[k]["close"]/ref[k-20]["close"]
    turnover=sum(x["turnover"] for x in arr[i-19:i+1])/20
    volume_prev20=sum(x["volume"] for x in arr[i-20:i])/20
    past10=max(x["high"] for x in arr[i-10:i])
    true_range=[]
    for j in range(i-13,i+1):
        prev=arr[j-1]["close"];cur=arr[j]
        true_range.append(max(cur["high"]-cur["low"],abs(cur["high"]-prev),abs(cur["low"]-prev)))
    atr=sum(true_range)/14
    if atr<=0:raise ValueError("ATR invalid")
    common=c>ma20 and relative>0 and turnover>=GROUPS[group]["min_adv"]
    if group=="A2":
        eligible=common and c>ma60 and c>=up(past10+.01) and volume_prev20>0 and arr[i]["volume"]>=1.2*volume_prev20
    else:
        eligible=common
    return {"asof":day,"eligible":eligible,"close":c,"ma20":ma20,"ma60":ma60,
            "breakout":up(past10+.01),"rel20":relative,"adv20":turnover,
            "relvol":arr[i]["volume"]/volume_prev20 if volume_prev20 else None,
            "atr14":atr}


def source_flow(now):
    """Recalculate 4-ETF day delta from a provenance-bearing persisted snapshot."""
    files=sorted(FLOW_ROOT.glob("*/*.json"),reverse=True)
    valid=[]
    for path in files[:100]:
        try:
            blob=path.read_bytes()
            obj=json.loads(blob)
            created=datetime.fromisoformat(obj["first_observed_no_earlier_than"]).astimezone(BJ)
            if created>now or created.tzinfo is None:continue
            by=obj["observations_by_date"]
            days=sorted(d for d,v in by.items() if all(code in v and
                "shares" in v[code] and "nav" in v[code] for code in CORE))
            if len(days)<2:continue
            last,prior=days[-1],days[-2]
            if next_session(prior)!=last:continue
            if date.fromisoformat(last)>now.date():continue
            # Reject data older than four actual exchange sessions.
            from datetime import timedelta
            elapsed=calendar_sessions(last,now.date().isoformat())
            if len(elapsed)>5:continue
            amount=Decimal("0")
            for code in CORE:
                latest=by[last][code];older=by[prior][code]
                for name in ("shares_first_observed_at","nav_first_observed_at"):
                    if name not in latest:
                        raise ValueError(f"{code}: missing PIT timestamp")
                    if datetime.fromisoformat(latest[name]).astimezone(BJ)>now:
                        raise ValueError(f"{code}: observation from the future")
                amount+=(Decimal(str(latest["shares"]))-Decimal(str(older["shares"])))*Decimal(str(latest["nav"]))
            valid.append((last,created,str(path),hashlib.sha256(blob).hexdigest(),amount))
        except (OSError,KeyError,ValueError,TypeError,ArithmeticError):
            continue
    if not valid:raise ValueError("NO_PIT_COMPLETE_FOUR_ETF_SOURCE")
    day,observed,path,digest,amount=max(valid,key=lambda x:(x[0],x[1]))
    if amount<=0:raise ValueError(f"FOUR_ETF_FLOW_NOT_POSITIVE:{day}:{amount}")
    return {"day":day,"first_observed_at":observed.isoformat(),"net_cny":str(amount),
            "path":path,"sha256":digest,"scope":"FOUR_ETF_ALL_INVESTORS_NOT_HUIJIN"}


def strategy_snapshot(now):
    raw=STRATEGY_PATH.read_bytes()
    obj=json.loads(raw)
    if datetime.fromisoformat(obj["strategy_first_public_at"]).astimezone(BJ)>now:
        raise ValueError("frozen V2 source is not yet public")
    if obj["flow_scope"]!="FULL_CORE_FOUR":
        raise ValueError("V2 lacks four ETF scope")
    if [x["symbol"] for x in obj["s1_ranked"]]!=RANKS["S1"] or [x["symbol"] for x in obj["s2_ranked"]]!=RANKS["S2"]:
        raise ValueError("frozen original V2 ranks mismatch")
    return {"path":str(STRATEGY_PATH),"sha256":hashlib.sha256(raw).hexdigest(),
            "first_public_at":obj["strategy_first_public_at"]}


def selects(checked,group):
    eligible={x["code"]:x for x in checked if x.get("eligible") is True}
    c=GROUPS[group]
    if group=="A2":
        desired=[]
        for g in ("S1","S2"):
            item=next((eligible[x] for x in RANKS[g] if x in eligible),None)
            if item:desired.append(item)
    else:
        # Reserve S1/S2 diversification first; choose third by original frozen interleaving order.
        desired=[]
        for g in ("S1","S2"):
            x=next((eligible[code] for code in RANKS[g] if code in eligible),None)
            if x:desired.append(x)
        if len(desired)==2:
            used={x["code"] for x in desired}
            third=next((eligible[code] for g,code in RANK_ORDER if code in eligible and code not in used),None)
            if third:desired.append(third)
        elif len(desired)<2:
            used={x["code"] for x in desired}
            for g,code in RANK_ORDER:
                if code in eligible and code not in used:
                    desired.append(eligible[code]);used.add(code)
                if len(desired)==c["max_positions"]:break
    return desired[:c["max_positions"]]


def build_freeze(ak, now, group, market_session, flow=None, v2=None):
    if close_day(now,[market_session])!=market_session:
        raise ValueError("freeze prohibited before today's session close")
    flow=flow if flow is not None else source_flow(now)
    v2=v2 if v2 is not None else strategy_snapshot(now)
    benchmark=prices(ak,"510300",market_session)
    if bar(benchmark,market_session) is None:raise ValueError("benchmark close not available")
    names_df=ak.stock_info_a_code_name()
    names={str(r["code"]).zfill(6):str(r["name"]) for _,r in names_df.iterrows()}
    checked=[]
    for cohort,code in RANK_ORDER:
        if code not in names:raise ValueError(f"{code}: name missing; cannot skip")
        name=names[code];entry={"cohort":cohort,"code":code,"name":name}
        if "ST" in name.upper() or "退" in name:
            entry["eligible"]=False;entry["reason"]="SPECIAL_TREATMENT_OR_DELISTING"
        else:
            hist=prices(ak,code,market_session)
            ind=indicator(hist,benchmark,market_session,group)
            entry.update(ind)
            entry["price_sha256"]=hist["raw_sha256"]
            entry["price_provider"]=hist["kind"]
            if ind["eligible"] and 100*ind["close"]*1.03>GROUPS[group]["max_each"]:
                entry["eligible"]=False
                entry["reason"]="ONE_LOT_EXCEEDS_PER_STOCK_BUDGET"
        checked.append(entry)
    selected=selects(checked,group)
    freeze={"status":"FROZEN_NO_BROKER_ORDER","experiment":GROUPS[group]["experiment"],
            "version":GROUPS[group]["version"],"group":group,"asof_session":market_session,
            "next_open_session":next_session(market_session),
            "freeze_created_at":now.astimezone(BJ).isoformat(),
            "source_code_sha":os.getenv("GITHUB_SHA","UNKNOWN"),
            "source_run_id":os.getenv("GITHUB_RUN_ID","local"),
            "frozen_v2":v2,"four_etf_flow":flow,
            "benchmark_sha256":benchmark["raw_sha256"],
            "checked":checked,"selected":selected,"paper_account":ACCOUNT,
            "max_gross":GROUPS[group]["max_gross"],"max_each":GROUPS[group]["max_each"],
            "max_initial_risk":RISK,"real_orders":0,"expected_entry_model":"PAPER_SCENARIO"}
    freeze["signal_sha256"]=sha(freeze)
    return freeze


def minute_rows(ak, code, day, first="09:30", last="14:50"):
    """Reject if provider cannot supply genuine 1-minute dated history."""
    start=f"{day} {first}:00";end=f"{day} {last}:59"
    if code=="510300":
        df=ak.fund_etf_hist_min_em(symbol=code,period="1",start_date=start,end_date=end,adjust="")
    else:
        df=ak.stock_zh_a_hist_min_em(symbol=code,period="1",start_date=start,end_date=end,adjust="")
    keys=("时间","开盘","最高","最低","收盘","成交量")
    if not all(k in df.columns for k in keys):raise ValueError("MINUTE_SCHEMA_MISSING")
    out=[]
    for _,r in df.iterrows():
        stamp=str(r["时间"])[:16]
        if not (f"{day} {first}"<=stamp<=f"{day} {last}"):continue
        b={"minute":stamp,"open":float(r["开盘"]),"high":float(r["最高"]),
           "low":float(r["最低"]),"close":float(r["收盘"]),"volume":float(r["成交量"])}
        if not all(math.isfinite(x) for x in (b["open"],b["high"],b["low"],b["close"],b["volume"])):
            raise ValueError("INVALID_MINUTE_QUOTE")
        if b["volume"]<0 or b["low"]<=0 or not b["low"]<=min(b["open"],b["close"])<=max(b["open"],b["close"])<=b["high"]:
            raise ValueError("INCONSISTENT_MINUTE_QUOTE")
        if out and stamp<=out[-1]["minute"]:raise ValueError("MINUTE_ORDER_OR_DUPLICATE")
        out.append(b)
    min_rows=110 if last=="11:30" else 215
    if len(out)<min_rows or out[0]["minute"]>f"{day} 09:35" or out[-1]["minute"]!=f"{day} {last}":
        raise ValueError("INCOMPLETE_MINUTE_SOURCE")
    return {"bars":out,"sha256":sha(out),"provider":"EASTMONEY_1MIN"}


def b2_signal(today_minutes, prior_minutes):
    """First 10:31..11:30 break above HIGH observed by 10:30;
    10:30-11:30 cumulative volume must exceed 1.2x comparable prior days.
    """
    b=today_minutes["bars"]
    before=[x for x in b if x["minute"][11:]<="10:30"]
    if not before or before[-1]["minute"][11:]!="10:30":return None
    threshold=max(x["high"] for x in before)
    prior=[]
    for x in prior_minutes:
        window=[v for v in x["bars"] if "10:31"<=v["minute"][11:]<="11:30"]
        if len(window)<50:return None
        prior.append(sum(t["volume"] for t in window))
    if len(prior)<3 or min(prior)<=0:return None
    running=0
    for index,x in enumerate(b):
        clock=x["minute"][11:]
        if not ("10:31"<=clock<="11:29"):continue
        running+=x["volume"]
        # Relative to same elapsed interval in each of previous 3 sessions.
        minute_count=sum("10:31"<=v["minute"][11:]<=clock for v in b)
        baseline=[]
        for p in prior_minutes:
            window=[v for v in p["bars"] if "10:31"<=v["minute"][11:]<=clock]
            if len(window)!=minute_count:break
            baseline.append(sum(v["volume"] for v in window))
        if len(baseline)!=len(prior):continue
        average=sum(baseline)/len(baseline)
        if average>0 and running>=1.2*average and x["high"]>=up(threshold+.01):
            # The crossing/volume bar is only *known at the end* of this minute.
            # The first eligible paper quote is the NEXT observed minute OPEN.
            if index+1>=len(b):return None
            following=b[index+1]
            stamp=datetime.strptime(x["minute"],"%Y-%m-%d %H:%M")
            next_stamp=datetime.strptime(following["minute"],"%Y-%m-%d %H:%M")
            if (next_stamp-stamp).total_seconds()!=60 or following["open"]<up(threshold+.01):
                return None
            return {"minute":following["minute"],"trigger":up(threshold+.01),
                    "signal_bar_minute":x["minute"],
                    "price":following["open"],
                    "volume_ratio":running/average}
    return None


def entry_position(price,ind,cfg,remaining):
    if not math.isfinite(price) or price<=0:return None
    entry=up(price*(1+SLIP))
    risk_dist=max(1.5*ind["atr14"],.02*entry)
    stop=down(entry-risk_dist)
    target=up(entry+2*(entry-stop))
    if stop<=0:return None
    feasible=[]
    for qty in range(100,1+math.floor(min(cfg["max_each"],remaining)/entry),100):
        gross=qty*entry
        if gross>cfg["max_each"] or gross>remaining:continue
        # Sell side adverse slippage budget + both minimum ticket fees and stamp.
        budget=qty*(entry-stop+stop*SLIP)+fee(gross)+fee(qty*stop,True)
        if budget<=RISK:feasible.append((qty,budget))
    if not feasible:return None
    qty,budget=feasible[-1]
    return {"qty":qty,"entry_price":entry,"stop":stop,"target":target,
            "budget_risk":budget,"notional":qty*entry,
            "entry_fee":fee(qty*entry)}


def locked_freezes(group,root=RECORD_ROOT):
    frozen=[]
    for p in sorted((root/"freezes"/group).glob("*.json")):
        try:
            obj=json.loads(p.read_text(encoding="utf-8"))
            if obj.get("group")==group and obj.get("signal_sha256")==sha({k:v for k,v in obj.items() if k!="signal_sha256"}):
                frozen.append((p,obj))
        except (OSError,ValueError,TypeError):continue
    return frozen


def freeze_archive_commit_at(path):
    """Checkout must prove the freeze had a Git commit before market entry."""
    import subprocess
    command=["git","log","-1","--format=%cI","--",str(path)]
    result=subprocess.run(command,text=True,capture_output=True,check=False,timeout=8)
    stamp=result.stdout.strip()
    if result.returncode!=0 or not stamp:
        return None
    try:
        parsed=datetime.fromisoformat(stamp)
        if parsed.tzinfo is None:return None
        return parsed.astimezone(BJ)
    except ValueError:
        return None


def opening_allowed(stock_open,prior,ind,cfg):
    gap=stock_open/prior-1
    return 0<=gap<=cfg["gap_limit"] and (cfg is GROUPS["B"] or stock_open>=ind["breakout"])


def execution_gate(frozen,now):
    first=datetime.fromisoformat(frozen["freeze_created_at"]).astimezone(BJ)
    trade=frozen["next_open_session"]
    cutoff=datetime.combine(date.fromisoformat(trade),time(9,25),BJ)
    # Must have been frozen *on the actual as-of trading date*, after close.
    # E.g. a 00:55 Monday retry can never masquerade as Friday's close.
    if (first.date().isoformat()!=frozen["asof_session"]
            or first.time()<CUT or first>=cutoff
            or frozen["asof_session"]>=trade):
        return "FREEZE_AFTER_ENTRY_CUTOFF"
    if now<cutoff:return "ENTRY_NOT_REACHED"
    # Trading session must match the true next exchange session after freeze.
    if next_session(frozen["asof_session"])!=trade:
        return "CALENDAR_MISMATCH"
    return None


def assess(ak,group,frozen,now):
    """Replay after close, with a prior archived freeze. No retrospective signal creation."""
    cfg=GROUPS[group];today=now.astimezone(BJ).date().isoformat()
    failed=execution_gate(frozen,now)
    if failed:return {"status":failed,"entries":[]}
    trade=frozen["next_open_session"]
    if today<trade or (today==trade and now.astimezone(BJ).time()<CUT):
        return {"status":"WAIT_FOR_COMPLETED_ENTRY_SESSION","entries":[]}
    series=calendar_sessions(trade,today)
    if not series or series[0]!=trade:return {"status":"NO_EXCHANGE_SESSIONS","entries":[]}
    bench=prices(ak,"510300",today)
    used=0.0;entries=[]
    for index,item in enumerate(frozen["selected"]):
        code=item["code"]
        record={"signal_id":f"{frozen['signal_sha256'][:16]}-{index}-{code}",
                "code":code,"cohort":item["cohort"],"group":group,
                "entry_session":trade,"status":"ENTRY_UNVERIFIED"}
        try:
            history=prices(ak,code,today)
            original=bar(history,frozen["asof_session"])
            opening=bar(history,trade)
            if original is None or abs(original["close"]-item["close"])>1e-8:
                raise ValueError("FREEZE_HISTORY_REVISED")
            if opening is None or opening["volume"]<=0:
                raise ValueError("OPEN_MISSING_OR_SUSPENDED")
            if abs(opening["high"]-opening["low"])<1e-8:
                raise ValueError("ONE_PRICE_FILL_UNVERIFIABLE")
            entry_method=None;trigger=None;quote=None
            if opening_allowed(opening["open"],original["close"],item,cfg):
                entry_method="B1_0930_OPEN" if group=="B" else "A2_0930_OPEN"
                quote=opening["open"]
                trigger=f"{trade} 09:30"
            elif group=="B":
                # B2 requires historical intraday comparison; failed fetch => NO FILL.
                from datetime import timedelta
                prior_sessions=calendar_sessions((date.fromisoformat(trade)-timedelta(days=15)).isoformat(),frozen["asof_session"])
                prior_days=prior_sessions[-3:]
                if len(prior_days)<3:raise ValueError("B2_COMPARABLE_SESSIONS_MISSING")
                tmin=minute_rows(ak,code,trade,last="11:30")
                comparables=[minute_rows(ak,code,x,last="11:30") for x in prior_days]
                signal=b2_signal(tmin,comparables)
                if not signal:raise ValueError("B2_MINUTE_BREAKOUT_NOT_CONFIRMED")
                if signal["price"]/original["close"]>1+cfg["gap_limit"]:
                    raise ValueError("B2_CHASE_LIMIT")
                entry_method="B2_INTRADAY_AFTER_1030"
                trigger=signal["minute"];quote=signal["price"]
                record["b2_evidence"]={"trigger":signal,"minute_hash":tmin["sha256"],
                                       "comparables_sha":[x["sha256"] for x in comparables]}
            else:raise ValueError("A2_OPEN_PRICE_GATE_REJECTED")
            position=entry_position(quote,item,cfg,cfg["max_gross"]-used)
            if not position:raise ValueError("LOT_OR_RISK_OR_PORTFOLIO_BUDGET")
            # S0 ETF is matched to the exact same entry time, including intraday B2.
            etf_entry=bar(bench,trade)
            if etf_entry is None or etf_entry["volume"]<=0:
                raise ValueError("BENCHMARK_ENTRY_OPEN_UNVERIFIED")
            if entry_method=="B2_INTRADAY_AFTER_1030":
                etf_min=minute_rows(ak,"510300",trade,last="11:30")
                matched_entry=next((m for m in etf_min["bars"] if m["minute"]==trigger),None)
                if matched_entry is None:raise ValueError("BENCHMARK_B2_SAME_MINUTE_UNVERIFIED")
                bm_quote=matched_entry["open"]
                record["benchmark_entry_sha256"]=etf_min["sha256"]
            else:
                bm_quote=etf_entry["open"]
                record["benchmark_entry_sha256"]=bench["raw_sha256"]
            bm_buy=up(bm_quote*(1+SLIP))
            bm_qty=math.floor(position["notional"]/(100*bm_buy))*100
            if bm_qty<100:raise ValueError("BENCHMARK_LOT_UNAFFORDABLE")
            record["benchmark_entry_price"]=bm_buy
            record["benchmark_quantity"]=bm_qty
            used+=position["notional"]
            record.update(position)
            record.update({"method":entry_method,"entry_time":trigger,
                           "entry_stock_data_sha256":history["raw_sha256"],
                           "status":"PAPER_ENTRY_SCENARIO_NO_BROKER_FILL"})
            if len(series)<2:
                record["status"]="EXIT_NOT_MATURED"
                entries.append(record);continue
            # Exit: use 1-minute chronological data for each T+1..T+3.
            for si in range(1,min(len(series),4)):
                day=series[si]
                try:
                    m=minute_rows(ak,code,day)
                    mbench=minute_rows(ak,"510300",day)
                    daybar=bar(history,day)
                    if daybar is None or daybar["volume"]<=0 or abs(daybar["high"]-daybar["low"])<1e-8:
                        raise ValueError("EXIT_SUSPENDED_OR_ONE_PRICE_UNVERIFIABLE")
                    if m["bars"][0]["minute"]>f"{day} 09:35":
                        raise ValueError("MINUTE_OPEN_NOT_OBSERVED")
                    reason=None;closebar=None
                    for b in m["bars"]:
                        if b["open"]<=position["stop"]:
                            reason="STOP_GAP";closebar=b;exit_quote=b["open"];break
                        if b["low"]<=position["stop"]:
                            reason="STOP_FIRST";closebar=b;exit_quote=position["stop"];break
                        if b["open"]>=position["target"]:
                            reason="TARGET_GAP";closebar=b;exit_quote=b["open"];break
                        if b["high"]>=position["target"]:
                            reason="TARGET";closebar=b;exit_quote=position["target"];break
                    if reason is None and si==3:
                        reason="T_PLUS_3_1450"
                        closebar=m["bars"][-1];exit_quote=closebar["open"]
                    if reason is None:
                        record["status"]="EXIT_PENDING";continue
                    previous_session=series[si-1]
                    previous_bar=bar(history,previous_session)
                    if previous_bar and abs(closebar["high"]-closebar["low"])<1e-8 and closebar["open"]<=previous_bar["close"]*.953:
                        raise ValueError("POSSIBLE_LIMIT_DOWN_ONE_MINUTE_EXIT_QUEUE_UNVERIFIED")
                    matching=next((x for x in mbench["bars"] if x["minute"]==closebar["minute"]),None)
                    if matching is None:raise ValueError("BENCHMARK_SAME_MINUTE_UNAVAILABLE")
                    sell=down(exit_quote*(1-SLIP))
                    net=position["qty"]*(sell-position["entry_price"])-position["entry_fee"]-fee(position["qty"]*sell,True)
                    bm_sell=down(matching["open"]*(1-SLIP))
                    bmn=record["benchmark_quantity"]
                    bmnet=bmn*(bm_sell-record["benchmark_entry_price"])-fee(bmn*record["benchmark_entry_price"],etf=True)-fee(bmn*bm_sell,sell=True,etf=True)
                    record.update({"status":"PAPER_EXIT_SCENARIO_NO_BROKER_FILL",
                                   "exit_day":day,"exit_time":closebar["minute"],"exit_reason":reason,
                                   "exit_price":sell,"net_pnl":net,"r_multiple":net/position["budget_risk"],
                                   "exit_minute_sha256":m["sha256"],"benchmark_minute_sha256":mbench["sha256"],
                                   "benchmark_exit_quote":matching["open"],
                                   "benchmark_exit_price":bm_sell,"benchmark_net_pnl":bmnet,
                                   "paired_excess_pnl":net-bmnet,
                                   "paired_excess_pct_of_account":(net-bmnet)/ACCOUNT,
                                   "broker_fill_confirmed":False})
                    break
                except (ValueError,KeyError,TypeError,IndexError) as e:
                    record["status"]="EXIT_MINUTE_OR_MATCHED_BENCHMARK_UNVERIFIED"
                    record["exit_error"]=f"{type(e).__name__}:{str(e)[:160]}"
                    break
            entries.append(record)
        except Exception as e:
            record["status"]="NO_VALID_PAPER_ENTRY"
            record["reason"]=f"{type(e).__name__}:{str(e)[:160]}"
            entries.append(record)
    return {"status":"REPLAYED_PAPER_SCENARIOS_NOT_LIVE","account":ACCOUNT,
            "initial_gross":used,"initial_unallocated_cash":ACCOUNT-used,
            "entries":entries,"benchmark":"510300","real_broker_orders":0}


def run(ak,now,group,root=RECORD_ROOT):
    now=now.astimezone(BJ);today=now.date().isoformat()
    records={"captured_at":now.isoformat(),"group":group,"experiment":GROUPS[group]["experiment"],
             "version":GROUPS[group]["version"],"github_run_id":os.getenv("GITHUB_RUN_ID","local"),
             "github_sha":os.getenv("GITHUB_SHA","UNKNOWN"),"real_broker_orders":0,
             "freeze_created":False,"prior_freezes":[],"errors":[]}
    # Evaluate only ALREADY PERSISTED historical freeze files; never the fresh one.
    for p,f in locked_freezes(group,root):
        if f["next_open_session"]>today:continue
        # No settled bot commit before 09:25, no retrospectively filled entry.
        archive_time=freeze_archive_commit_at(p)
        cutoff=datetime.combine(date.fromisoformat(f["next_open_session"]),time(9,25),BJ)
        if archive_time is None or archive_time>=cutoff:
            records["prior_freezes"].append({"path":str(p),"signal_sha256":f["signal_sha256"],
                "result":{"status":"ARCHIVED_FREEZE_COMMIT_BEFORE_OPEN_NOT_VERIFIED",
                          "archive_commit_time":archive_time.isoformat() if archive_time else None}})
            continue
        # Only recently frozen events can still be T+3 open; older ones stay immutable in archives.
        from datetime import timedelta
        if date.fromisoformat(f["next_open_session"])<now.date()-timedelta(days=9):
            continue
        try:
            records["prior_freezes"].append({"path":str(p),"signal_sha256":f["signal_sha256"],
                                             "archive_commit_at":archive_time.isoformat(),
                                             "result":assess(ak,group,f,now)})
        except Exception as e:
            records["errors"].append(f"ASSESS:{p.name}:{type(e).__name__}:{str(e)[:150]}")
    day=close_day(now)
    if day:
        path=root/"freezes"/group/f"{day}.json"
        if path.exists():
            try:
                stored=json.loads(path.read_text(encoding="utf-8"))
                expected=sha({k:v for k,v in stored.items() if k!="signal_sha256"})
                if stored.get("signal_sha256")!=expected or stored.get("group")!=group or stored.get("asof_session")!=day:
                    raise ValueError("IMMUTABLE_FREEZE_HASH_OR_IDENTITY_CHANGED")
                records["freeze_status"]="EXISTING_FREEZE_UNCHANGED"
            except (OSError,ValueError,TypeError) as e:
                records["freeze_status"]="FREEZE_FAILED_NO_BACKFILL"
                records["errors"].append(f"FREEZE_INTEGRITY:{type(e).__name__}:{str(e)[:120]}")
        else:
            try:
                freeze=build_freeze(ak,now,group,day)
                path.parent.mkdir(parents=True,exist_ok=True)
                with path.open("x",encoding="utf-8") as w:
                    w.write(json.dumps(freeze,ensure_ascii=False,indent=2)+"\n")
                records["freeze_created"]=True
                records["freeze_status"]="FROZEN_BEFORE_NEXT_SESSION"
                records["freeze_signal_sha256"]=freeze["signal_sha256"]
                records["freeze_path"]=str(path)
                records["selected_codes"]=[x["code"] for x in freeze["selected"]]
            except Exception as e:
                records["freeze_status"]="FREEZE_FAILED_NO_BACKFILL"
                records["errors"].append(f"FREEZE:{type(e).__name__}:{str(e)[:220]}")
    else:
        records["freeze_status"]="OUTSIDE_TODAY_COMPLETED_EXCHANGE_SESSION"
    records["status"]="RESEARCH_ONLY_NO_BROKER_ORDERS"
    return records


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--group",choices=("A2","B"),required=True)
    parser.add_argument("--root",default=str(RECORD_ROOT))
    args=parser.parse_args()
    now=datetime.now(BJ)
    rid=os.getenv("GITHUB_RUN_ID","local")
    att=os.getenv("GITHUB_RUN_ATTEMPT","1")
    target=Path(args.root)/"runs"/args.group/now.date().isoformat()/f"{rid}-a{att}.json"
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():raise FileExistsError(f"immutable run already exists: {target}")
    try:
        import akshare as ak
        result=run(ak,now,args.group,Path(args.root))
        result["runtime_akshare"]=getattr(ak,"__version__","unknown")
    except Exception as e:
        result={"status":"PAPER_RUNNER_ERROR","group":args.group,
                "captured_at":now.isoformat(),"errors":[f"{type(e).__name__}:{str(e)[:300]}"],
                "real_broker_orders":0}
    with target.open("x",encoding="utf-8") as w:
        w.write(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"status":result["status"],"group":args.group,
                      "freeze_status":result.get("freeze_status"),"errors":result.get("errors",[]),
                      "run_record":str(target)},ensure_ascii=False))


    # A green job must not conceal an expired/failed business gate.
    if result.get("freeze_status")=="FREEZE_FAILED_NO_BACKFILL" or result["status"]=="PAPER_RUNNER_ERROR" or result.get("errors"):
        raise SystemExit(2)

if __name__=="__main__":
    main()
