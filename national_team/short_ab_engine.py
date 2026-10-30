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


_EM_RATE_LIMITED=False

def normalize(df,code,kind):
    """Normalize *genuine* Eastmoney Chinese or Sina English OHLCV frames."""
    cn={"日期":"date","开盘":"open","最高":"high","最低":"low",
        "收盘":"close","成交量":"volume","成交额":"turnover"}
    en={"date":"date","open":"open","high":"high","low":"low",
        "close":"close","volume":"volume","amount":"turnover"}
    mapping=cn if "日期" in df.columns else en
    fields={key:out for key,out in mapping.items()
            if out!="turnover" or code!="510300"}
    if not all(key in df.columns for key in fields):
        raise ValueError(f"{code}: OHLCV/turnover schema is missing in {kind}")
    out=[]
    for _,row in df.sort_values(next(k for k,v in fields.items() if v=="date")).iterrows():
        item={outkey:(str(row[key])[:10] if outkey=="date" else float(row[key]))
              for key,outkey in fields.items()}
        o,h,l,c,v=(item[k] for k in ("open","high","low","close","volume"))
        if not all(math.isfinite(z) for z in item.values() if isinstance(z,float)):
            raise ValueError(f"{code}: nonfinite quote")
        if min(o,h,l,c)<=0 or v<0 or not l<=min(o,c)<=max(o,c)<=h:
            raise ValueError(f"{code}: invalid OHLC")
        if "turnover" in item and item["turnover"]<0:
            raise ValueError(f"{code}: negative turnover")
        if out and item["date"]<=out[-1]["date"]:
            raise ValueError(f"{code}: duplicate/nonascending history")
        out.append(item)
    return {"kind":kind,"code":code,"bars":out,"raw_sha256":sha(out)}


def _pause_eastmoney(error):
    global _EM_RATE_LIMITED
    if ("Push2RateLimitError" in type(error).__name__ or
        "Connection reset" in str(error) or "temporarily rate" in str(error).lower()):
        _EM_RATE_LIMITED=True


def stock_names(ak):
    """Prefer Shanghai exchange main-board roster; never guess ST status."""
    failures=[]
    try:
        frame=ak.stock_info_sh_name_code(symbol="主板A股")
        if "证券代码" not in frame.columns or "证券简称" not in frame.columns:
            raise ValueError("SSE_NAME_SCHEMA_MISSING")
        names={str(row["证券代码"]).zfill(6):str(row["证券简称"])
               for _,row in frame.iterrows() if str(row["证券代码"]).strip()}
        if names:return names,"SSE_OFFICIAL_MAIN_BOARD"
        raise ValueError("EMPTY_SSE_SECURITY_ROSTER")
    except Exception as exc:
        failures.append("SSE:"+type(exc).__name__+":"+str(exc)[:100])
    try:
        frame=ak.stock_info_a_code_name()
        if "code" not in frame.columns or "name" not in frame.columns:
            raise ValueError("GENERIC_NAME_SCHEMA_MISSING")
        names={str(row["code"]).zfill(6):str(row["name"])
               for _,row in frame.iterrows() if str(row["code"]).strip()}
        if names:return names,"AKSHARE_ALL_BOARD"
        raise ValueError("EMPTY_ALL_BOARD_ROSTER")
    except Exception as exc:
        failures.append("GENERIC:"+type(exc).__name__+":"+str(exc)[:100])
    raise ValueError("NO_VERIFIED_SECURITY_NAMES:"+";".join(failures))


def _completed_etf_daily_from_sina_minutes(ak,day):
    """Construct same-security ETF close ONLY from genuinely complete 1m session."""
    frame=ak.stock_zh_a_minute(symbol="sh510300",period="1",adjust="")
    keys=("day","open","high","low","close","volume")
    if not all(k in frame.columns for k in keys):
        raise ValueError("ETF_1M_ENGLISH_SCHEMA_REQUIRED")
    rows=[]
    for _,r in frame.iterrows():
        stamp=str(r["day"])[:16]
        if not f"{day} 09:30"<=stamp<=f"{day} 15:00":continue
        v={k:float(r[k]) for k in keys[1:]}
        if not all(math.isfinite(z) for z in v.values()):
            raise ValueError("ETF_MINUTE_NONFINITE")
        if (min(v["open"],v["high"],v["low"],v["close"])<=0 or v["volume"]<0
            or not v["low"]<=min(v["open"],v["close"])<=max(v["open"],v["close"])<=v["high"]):
            raise ValueError("ETF_MINUTE_INVALID_OHLC")
        if rows and stamp<=rows[-1]["minute"]:
            raise ValueError("ETF_MINUTE_DUPLICATED_OR_UNSORTED")
        rows.append({"minute":stamp,**v})
    if len(rows)<238 or rows[0]["minute"]>f"{day} 09:35" or rows[-1]["minute"]!=f"{day} 15:00":
        raise ValueError(f"ETF_1M_SESSION_NOT_COMPLETE:{len(rows)}")
    daily={"date":day,"open":rows[0]["open"],
           "high":max(v["high"] for v in rows),
           "low":min(v["low"] for v in rows),
           "close":rows[-1]["close"],
           "volume":sum(v["volume"] for v in rows)}
    if not daily["low"]<=min(daily["open"],daily["close"])<=max(daily["open"],daily["close"])<=daily["high"]:
        raise ValueError("ETF_COMPUTED_DAILY_OHLC_INVALID")
    return daily,sha(rows)


def prices(ak,code,through):
    """Actual unadjusted daily prices; Sina is preferred for stocks to avoid EM push2 bans."""
    end=through.replace("-","")
    prefix=("sh" if code.startswith(("5","6","9")) else "sz")+code
    failures=[]
    if code!="510300":
        try:
            frame=ak.stock_zh_a_daily(symbol=prefix,start_date="20250101",
                                      end_date=end,adjust="")
            if frame is None or frame.empty:raise ValueError("EMPTY_SINA_DAILY")
            result=normalize(frame,code,"SINA_STOCK_DAILY_NO_ADJUST")
            if bar(result,through) is None:raise ValueError("SINA_DAILY_ASOF_BAR_MISSING")
            return result
        except Exception as exc:
            failures.append("SINA:"+type(exc).__name__+":"+str(exc)[:120])
    if not _EM_RATE_LIMITED:
        try:
            if code=="510300":
                frame=ak.fund_etf_hist_em(symbol=code,period="daily",
                                          start_date="20250101",end_date=end,adjust="")
                kind="EASTMONEY_ETF_DAILY_NO_ADJUST"
            else:
                frame=ak.stock_zh_a_hist(symbol=code,period="daily",
                                         start_date="20250101",end_date=end,adjust="")
                kind="EASTMONEY_STOCK_DAILY_NO_ADJUST"
            if frame is None or frame.empty:raise ValueError("EMPTY_EASTMONEY_DAILY")
            result=normalize(frame,code,kind)
            if bar(result,through) is None:raise ValueError("EASTMONEY_DAILY_ASOF_BAR_MISSING")
            return result
        except Exception as exc:
            _pause_eastmoney(exc)
            failures.append("EASTMONEY:"+type(exc).__name__+":"+str(exc)[:120])
    else:
        failures.append("EASTMONEY:CIRCUIT_BREAKER_PAUSED")
    if code=="510300":
        try:
            frame=ak.fund_etf_hist_sina(symbol="sh510300")
            if frame is None or frame.empty:raise ValueError("EMPTY_SINA_ETF_DAILY")
            date_field="date" if "date" in frame.columns else "日期"
            frame=frame[(frame[date_field].astype(str).str[:10]>="2025-01-01") &
                        (frame[date_field].astype(str).str[:10]<=through)]
            if frame.empty:raise ValueError("SINA_ETF_NO_ASOF_BARS")
            result=normalize(frame,code,"SINA_ETF_DAILY_NO_ADJUST")
            if bar(result,through) is not None:return result
            # The fund daily vendor can be one session late even after 15:00.
            # Complete Shanghai/Sina 1m for the EXACT ETF ticker is an
            # independently dated, observable last-day OHLC replacement.
            # A 14:50 or 14:59 quote MUST NOT be treated as a 15:00 close.
            latest=result["bars"][-1]["date"]
            if latest>=through:raise ValueError("ETF_DAILY_ASOF_UNEXPECTED")
            today_daily,today_minutes_sha=_completed_etf_daily_from_sina_minutes(ak,through)
            bars=result["bars"]+[today_daily]
            return {"kind":"SINA_ETF_PRIOR_DAILY_PLUS_VERIFIED_1M_SESSION",
                    "code":code,"bars":bars,"raw_sha256":sha(bars),
                    "current_session_minute_sha256":today_minutes_sha,
                    "prior_daily_last_session":latest}
        except Exception as exc:
            failures.append("SINA_ETF:"+type(exc).__name__+":"+str(exc)[:120])
    if code=="510300":
        # Same ETF identifier on the independent Sina securities K-line endpoint.
        # This must *never* be replaced by CSI300 index prices or latest NAV.
        try:
            frame=ak.stock_zh_a_daily(symbol="sh510300",start_date="20250101",
                                      end_date=end,adjust="")
            if frame is None or frame.empty:raise ValueError("EMPTY_SINA_SECURITY_ETF")
            result=normalize(frame,code,"SINA_SECURITY_510300_DAILY_NO_ADJUST")
            if bar(result,through) is None:raise ValueError("SINA_SECURITY_ETF_ASOF_MISSING")
            return result
        except Exception as exc:
            failures.append("SINA_SECURITY_ETF:"+type(exc).__name__+":"+str(exc)[:240])
    raise ValueError(f"{code}:DAILY_PROVIDERS_UNVERIFIED:"+";".join(failures))


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
    gates={"ABOVE_MA20":c>ma20,"POSITIVE_RS20":relative>0,
           "ADV20_THRESHOLD":turnover>=GROUPS[group]["min_adv"]}
    if group=="A2":
        gates.update({"ABOVE_MA60":c>ma60,"TEN_DAY_BREAKOUT":c>=up(past10+.01),
                      "VOLUME_1P2X":volume_prev20>0 and arr[i]["volume"]>=1.2*volume_prev20})
    return {"asof":day,"eligible":all(gates.values()),"close":c,"ma20":ma20,"ma60":ma60,
            "breakout":up(past10+.01),"rel20":relative,"adv20":turnover,
            "relvol":arr[i]["volume"]/volume_prev20 if volume_prev20 else None,
            "atr14":atr,"gate_checks":gates,
            "rejection_reasons":[k for k,v in gates.items() if not v]}


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
                for snapshot in (older,latest):
                    for name in ("shares_first_observed_at","nav_first_observed_at"):
                        if name not in snapshot:
                            raise ValueError(f"{code}: missing PIT timestamp")
                        first=datetime.fromisoformat(snapshot[name])
                        if first.tzinfo is None or first.astimezone(BJ)>now:
                            raise ValueError(f"{code}: missing timezone or future observation")
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
    """Original V2 ranked precedence cannot be silently bypassed on vendor errors."""
    lookup={v["code"]:v for v in checked}
    def first_eligible(arm):
        for code in RANKS[arm]:
            item=lookup.get(code)
            if item is None or item.get("data_status")=="UNVERIFIED":
                return None
            if item.get("eligible") is True:return item
        return None
    selected=[v for g in ("S1","S2") if (v:=first_eligible(g)) is not None]
    if group=="B":
        already={x["code"] for x in selected}
        for arm,code in RANK_ORDER:
            if code in already:continue
            item=lookup.get(code)
            if item is None or item.get("data_status")=="UNVERIFIED":break
            if item.get("eligible") is True:
                selected.append(item);break
    return selected[:GROUPS[group]["max_positions"]]

def build_freeze(ak, now, group, market_session, flow=None, v2=None):
    if close_day(now,[market_session])!=market_session:
        raise ValueError("freeze prohibited before today's session close")
    flow=flow if flow is not None else source_flow(now)
    v2=v2 if v2 is not None else strategy_snapshot(now)
    benchmark=prices(ak,"510300",market_session)
    if bar(benchmark,market_session) is None:raise ValueError("benchmark close not available")
    try:
        names,name_provider=stock_names(ak)
        name_error=None
    except Exception as error:
        names={};name_provider="UNVERIFIED";name_error=f"{type(error).__name__}:{str(error)[:160]}"
    checked=[]
    for cohort,code in RANK_ORDER:
        name=names.get(code)
        item={"cohort":cohort,"code":code,"name":name,"eligible":False}
        if name is None:
            item.update({"data_status":"UNVERIFIED","reason":"SECURITY_NAME_UNVERIFIED",
                         "source_error":name_error or "MISSING_SECURITY_NAME"})
        elif "ST" in name.upper() or "退" in name:
            item.update({"data_status":"VERIFIED",
                         "reason":"SPECIAL_TREATMENT_OR_DELISTING",
                         "rejection_reasons":["SPECIAL_TREATMENT_OR_DELISTING"]})
        else:
            try:
                hist=prices(ak,code,market_session)
                ind=indicator(hist,benchmark,market_session,group)
                item.update(ind)
                item.update({"data_status":"VERIFIED","price_sha256":hist["raw_sha256"],
                             "price_provider":hist["kind"]})
                # Do not pre-reject an affordable one-lot buy on a hypothetical
                # maximum gap. The exact budget and risk are checked at entry.
                # A2 cannot open below both prior close and breakout. B2 can
                # open below prior close; 80% is only a conservative price floor.
                cheapest=max(ind["close"],ind["breakout"]) if group=="A2" else .8*ind["close"]
                minimum_lot=100*up(cheapest*(1+SLIP))
                item["minimum_possible_lot_cny"]=minimum_lot
                if ind["eligible"] and minimum_lot>GROUPS[group]["max_each"]:
                    item["eligible"]=False
                    item["reason"]="MINIMUM_OPEN_LOT_UNAFFORDABLE"
                    item["rejection_reasons"].append(item["reason"])
            except Exception as error:
                item.update({"eligible":False,"data_status":"UNVERIFIED",
                             "reason":"STOCK_HISTORY_OR_INDICATOR_UNVERIFIED",
                             "source_error":f"{type(error).__name__}:{str(error)[:180]}"})
        checked.append(item)
    selected=selects(checked,group)
    freeze={"status":"FROZEN_NO_BROKER_ORDER","experiment":GROUPS[group]["experiment"],
            "version":GROUPS[group]["version"],"group":group,"asof_session":market_session,
            "next_open_session":next_session(market_session),
            "freeze_created_at":now.astimezone(BJ).isoformat(),
            "source_code_sha":os.getenv("GITHUB_SHA","UNKNOWN"),
            "source_run_id":os.getenv("GITHUB_RUN_ID","local"),
            "frozen_v2":v2,"four_etf_flow":flow,"security_name_provider":name_provider,
            "benchmark_sha256":benchmark["raw_sha256"],
            "checked":checked,"selected":selected,
             "candidate_diagnostics":{"total":len(checked),
                 "verified":sum(v.get("data_status")=="VERIFIED" for v in checked),
                 "unverified":sum(v.get("data_status")=="UNVERIFIED" for v in checked),
                 "eligible":sum(v.get("eligible") is True for v in checked),
                 "selected":len(selected),
                 "blocked_unverified":[v["code"] for v in checked if v.get("data_status")=="UNVERIFIED"]},
             "paper_account":ACCOUNT,
            "max_gross":GROUPS[group]["max_gross"],"max_each":GROUPS[group]["max_each"],
            "max_initial_risk":RISK,"real_orders":0,"expected_entry_model":"PAPER_SCENARIO"}
    freeze["signal_sha256"]=sha(freeze)
    return freeze


def _normalize_minutes(frame,code,day,first,last,provider):
    """Timestamped 1min bars must be complete; never infer missing 14:50 quotes."""
    keys_cn=("时间","开盘","最高","最低","收盘","成交量")
    keys_en=("day","open","high","low","close","volume")
    if all(k in frame.columns for k in keys_cn):
        keys=keys_cn
    elif all(k in frame.columns for k in keys_en):
        keys=keys_en
    else:raise ValueError("MINUTE_SCHEMA_MISSING")
    rows=[]
    for _,r in frame.iterrows():
        stamp=str(r[keys[0]])[:16]
        if not (f"{day} {first}"<=stamp<=f"{day} {last}"):continue
        item={"minute":stamp,"open":float(r[keys[1]]),
              "high":float(r[keys[2]]),"low":float(r[keys[3]]),
              "close":float(r[keys[4]]),"volume":float(r[keys[5]])}
        values=(item["open"],item["high"],item["low"],item["close"],item["volume"])
        if not all(math.isfinite(v) for v in values) or item["volume"]<0:
            raise ValueError("INVALID_MINUTE_QUOTE")
        if item["low"]<=0 or not item["low"]<=min(item["open"],item["close"])<=max(item["open"],item["close"])<=item["high"]:
            raise ValueError("INCONSISTENT_MINUTE_QUOTE")
        if rows and stamp<=rows[-1]["minute"]:raise ValueError("MINUTE_ORDER_OR_DUPLICATE")
        rows.append(item)
    min_rows=110 if last=="11:30" else 215
    if (len(rows)<min_rows or not rows or
        rows[0]["minute"]>f"{day} 09:35" or rows[-1]["minute"]!=f"{day} {last}"):
        raise ValueError(f"INCOMPLETE_MINUTE_SOURCE:{provider}:{len(rows)}")
    return {"bars":rows,"sha256":sha(rows),"provider":provider,"code":code}


def minute_rows(ak,code,day,first="09:30",last="14:50"):
    """Sina 1m primary, EM last resort; exact dated 1m evidence required."""
    prefix=("sh" if code.startswith(("5","6","9")) else "sz")+code
    errors=[]
    try:
        frame=ak.stock_zh_a_minute(symbol=prefix,period="1",adjust="")
        return _normalize_minutes(frame,code,day,first,last,"SINA_1MIN")
    except Exception as exc:
        errors.append("SINA:"+type(exc).__name__+":"+str(exc)[:130])
    if not _EM_RATE_LIMITED:
        try:
            start=f"{day} {first}:00";end=f"{day} {last}:59"
            if code=="510300":
                frame=ak.fund_etf_hist_min_em(symbol=code,period="1",
                                             start_date=start,end_date=end,adjust="")
            else:
                frame=ak.stock_zh_a_hist_min_em(symbol=code,period="1",
                                                start_date=start,end_date=end,adjust="")
            return _normalize_minutes(frame,code,day,first,last,"EASTMONEY_1MIN")
        except Exception as exc:
            _pause_eastmoney(exc)
            errors.append("EASTMONEY:"+type(exc).__name__+":"+str(exc)[:130])
    else:errors.append("EASTMONEY:CIRCUIT_BREAKER_PAUSED")
    raise ValueError(f"{code}:MINUTE_PROVIDERS_UNVERIFIED:"+";".join(errors))


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
                           "entry_daily_bar_sha256":sha(opening),
                           "benchmark_entry_daily_bar_sha256":sha(etf_entry),
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


PAPER_ENTRY_FIELDS=("signal_id","code","cohort","group","entry_session","entry_price",
                    "entry_time","method","qty","notional","stop","target",
                    "budget_risk","entry_fee","benchmark_entry_price",
                    "benchmark_quantity","entry_daily_bar_sha256",
                    "benchmark_entry_daily_bar_sha256","b2_evidence")

def write_paper_event_once(path,obj):
    """No overwrite: first simulated evidence survives subsequent replays."""
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))==obj
    with path.open("x",encoding="utf-8") as out:
        out.write(json.dumps(obj,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    return True

def lock_paper_replay(group,frozen,result,root,archive_time):
    audit={"locked_entries":[],"locked_exits":[],"drifts":[]}
    for entry in result.get("entries",[]):
        if "entry_price" not in entry:continue
        signal_id=entry["signal_id"]
        original={"frozen_signal_sha256":frozen["signal_sha256"],
                  "freeze_git_archive_at":archive_time.isoformat(),
                  "original_entry":{k:entry.get(k) for k in PAPER_ENTRY_FIELDS},
                  "broker_fill_confirmed":False}
        entry_path=root/"ledger"/"entries"/group/f"{signal_id}.json"
        if not write_paper_event_once(entry_path,original):
            entry["status"]="ENTRY_LEDGER_DRIFT_BLOCKED"
            entry["reason"]="entry terms disagree with first immutable paper event"
            for key in ("net_pnl","benchmark_net_pnl","paired_excess_pnl",
                        "r_multiple","paired_excess_pct_of_account"):
                entry.pop(key,None)
            audit["drifts"].append(str(entry_path))
            continue
        audit["locked_entries"].append(str(entry_path))
        if entry["status"]!="PAPER_EXIT_SCENARIO_NO_BROKER_FILL":continue
        exit_obj={"frozen_signal_sha256":frozen["signal_sha256"],"signal_id":signal_id,
                  "entry_lock_sha256":sha(original),
                  "exit_day":entry["exit_day"],"exit_time":entry["exit_time"],
                  "exit_reason":entry["exit_reason"],"exit_price":entry["exit_price"],
                  "net_pnl":entry["net_pnl"],"exit_minute_sha256":entry["exit_minute_sha256"],
                  "benchmark_minute_sha256":entry["benchmark_minute_sha256"],
                  "benchmark_exit_price":entry["benchmark_exit_price"],
                  "benchmark_net_pnl":entry["benchmark_net_pnl"],
                  "paired_excess_pnl":entry["paired_excess_pnl"],
                  "broker_fill_confirmed":False}
        exit_path=root/"ledger"/"exits"/group/f"{signal_id}.json"
        if not write_paper_event_once(exit_path,exit_obj):
            entry["status"]="EXIT_LEDGER_DRIFT_BLOCKED"
            entry["reason"]="exit differs from first immutable paper event"
            for key in ("net_pnl","benchmark_net_pnl","paired_excess_pnl",
                        "r_multiple","paired_excess_pct_of_account"):
                entry.pop(key,None)
            audit["drifts"].append(str(exit_path))
        else:audit["locked_exits"].append(str(exit_path))
    return audit

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
        # Old frozen events remain immutable on disk even after the replay window.
        from datetime import timedelta
        if date.fromisoformat(f["next_open_session"])<now.date()-timedelta(days=9):
            continue
        try:
            assessment=assess(ak,group,f,now)
            locks=lock_paper_replay(group,f,assessment,root,archive_time)
            if locks["drifts"]:
                records["errors"].append("IMMUTABLE_PAPER_LEDGER_DRIFT:"+",".join(locks["drifts"]))
            records["prior_freezes"].append({"path":str(p),"signal_sha256":f["signal_sha256"],
                                             "archive_commit_at":archive_time.isoformat(),
                                             "paper_ledger":locks,"result":assessment})
        except Exception as exc:
            records["errors"].append(f"ASSESS:{p.name}:{type(exc).__name__}:{str(exc)[:150]}")
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
                funding_day=freeze["four_etf_flow"]["day"]
                previously_frozen_days={
                    previous.get("four_etf_flow",{}).get("day")
                    for _,previous in locked_freezes(group,root)
                }
                if funding_day in previously_frozen_days:
                    records["freeze_status"]="NO_NEW_FOUR_ETF_EVENT"
                    records["duplicate_funding_day"]=funding_day
                    records["selected_codes"]=[]
                else:
                    path.parent.mkdir(parents=True,exist_ok=True)
                    with path.open("x",encoding="utf-8") as w:
                        w.write(json.dumps(freeze,ensure_ascii=False,indent=2)+"\n")
                    records["freeze_created"]=True
                    records["freeze_status"]="FROZEN_BEFORE_NEXT_SESSION"
                    records["freeze_signal_sha256"]=freeze["signal_sha256"]
                    records["freeze_path"]=str(path)
                    records["selected_codes"]=[x["code"] for x in freeze["selected"]]
                    records["candidate_diagnostics"]=freeze["candidate_diagnostics"]
                    records["candidate_rejections"]=[
                        {"cohort":v["cohort"],"code":v["code"],
                         "status":v.get("data_status"),"reason":v.get("reason"),
                         "failed_gates":v.get("rejection_reasons",[]),
                         "source_error":v.get("source_error")}
                        for v in freeze["checked"] if not v.get("eligible")]
            except ValueError as e:
                if str(e).startswith("FOUR_ETF_FLOW_NOT_POSITIVE:"):
                    records["freeze_status"]="NO_POSITIVE_CORE_FOUR_FLOW"
                    records["selected_codes"]=[]
                else:
                    records["freeze_status"]="FREEZE_FAILED_NO_BACKFILL"
                    records["errors"].append(f"FREEZE:{type(e).__name__}:{str(e)[:220]}")
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
