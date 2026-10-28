"""Ongoing evidence-based paper tracking of FIRST-frozen national-team watchlists.

Only actual share/price sources are queried. Ineligible or unexpired signals
remain unscored. Execution remains a market OHLC scenario, never a broker fill.
"""
from __future__ import annotations
import argparse,hashlib,json,os
from datetime import date,datetime,timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from national_team.forward_evaluation import evaluate_frozen_event
from national_team.event_pipeline import exchange_sessions

BEIJING=ZoneInfo("Asia/Shanghai")
def load_history(ak,code,start,end):
    """Read genuine unadjusted daily OHLC for a stock or ETF; preserve source."""
    if code=="510300":
        df=ak.fund_etf_hist_em(symbol=code,period="daily",
                               start_date=start,end_date=end,adjust="")
        source="EASTMONEY_ETF_DAILY_OHLC"
    else:
        try:
            df=ak.stock_zh_a_hist(symbol=code,period="daily",
                                   start_date=start,end_date=end,adjust="")
            source="EASTMONEY_STOCK_DAILY_OHLC"
        except Exception:
            prefix="sh" if code.startswith(("6","9")) else "sz"
            df=ak.stock_zh_a_daily(symbol=prefix+code,
                                   start_date=start,end_date=end,adjust="")
            source="SINA_STOCK_DAILY_OHLC"
    if "日期" in df.columns:
        day,opening,closing,volume="日期","开盘","收盘","成交量"
    else:
        day,opening,closing,volume="date","open","close","volume"
    if not all(c in df.columns for c in (day,opening,closing,volume)):
        raise ValueError("unknown market OHLC schema")
    out={}
    for _,r in df.iterrows():
        d=str(r[day])[:10]
        if d>date.fromisoformat(end).isoformat() or d<date.fromisoformat(start).isoformat():
            continue
        if d in out:raise ValueError(f"{code}: duplicate OHLC day")
        o=float(r[opening]);c=float(r[closing]);v=float(r[volume])
        if not (o>0 and c>0 and v>=0):
            raise ValueError(f"{code} invalid OHLC/volume {d}")
        out[d]={"open":str(o),"close":str(c),
                # A nonzero day volume alone does NOT establish an exact fill.
                "entry_blocked":False if v>0 else True,
                "exit_blocked":False if v>0 else True}
    return out,source,hashlib.sha256(df.to_csv(index=False).encode()).hexdigest()

def assess(ak,events_root:Path,asof:date,max_events:int=64)->dict:
    asof_s=asof.isoformat()
    paths=list(events_root.glob("*/*.json"))
    candidates=[]
    for path in paths:
        try:
            obj=json.loads(path.read_text(encoding="utf-8"))
        except Exception:continue
        for event in obj.get("events",[]):
            candidates.append((event,path))
    # Earliest archived copy is canonical; no double-counting reruns.
    candidates.sort(key=lambda pair:pair[0].get("first_public_at",""))
    unique={}
    for e,p in candidates:
        unique.setdefault(e["id"],(e,str(p)))
    # Two frozen portfolios per trading day over >=20 sessions: last eight
    # silently censored mature 20-session outcomes. Keep a rolling 60 calendar
    # day PIT window (including holidays), capped for source-call control.
    window=[]
    for e,p in unique.values():
        try:
            pub=datetime.fromisoformat(e["first_public_at"]).astimezone(BEIJING)
            age=(asof-pub.date()).days
            if 0<=age<=60:
                window.append((e,p))
        except (ValueError,KeyError,TypeError):
            continue
    events=window[-max_events:]
    first_start=min((datetime.fromisoformat(e["first_public_at"]).astimezone(BEIJING).date()
                     -timedelta(days=4) for e,_ in events),default=asof).strftime("%Y%m%d")
    price_cache={}
    out={"status":"NO_FROZEN_PAPER_EVENTS" if not events else "PAPER_EVALUATION_ATTEMPTED",
         "asof":asof_s,"source_events":len(unique),
         "assessed_events":len(events),"eligible_60d_window_count":len(window),
         "max_events":max_events,
         "model":"NEXT_EXECUTABLE_OPEN_OHLC_SCENARIO_NOT_LIVE_ORDER",
         "result_records":[],"errors":[],
         "calculation_never_backdates_data_discovery":True}
    for event,origin in events:
        e_id=event["id"]
        try:
            pub=datetime.fromisoformat(event["first_public_at"])
            if pub.tzinfo is None:raise ValueError("missing timezone")
            if pub.astimezone(BEIJING).date()>asof:
                out["result_records"].append({"id":e_id,"status":"FUTURE_EVENT"});continue
            sessions=exchange_sessions(asof_s,lookback_days=110)
            start_day=(pub.astimezone(BEIJING).date()-timedelta(days=4)).isoformat()
            ses=[x for x in sessions if x>=start_day and x<=asof_s]
            # If no 5-session holding can have ended, preserve PENDING without
            # querying or fabricating any market prices.
            if len(ses)<7:
                out["result_records"].append({"id":e_id,"status":"NOT_MATURED_YET",
                                               "source_event":origin});continue
            names=set(event["candidate_symbols"]+["510300"])
            prices={};sources={}
            for symbol in names:
                try:
                    # Once per instrument per run; individual event evaluation
                    # still uses its own prospective entry date and horizon.
                    if symbol not in price_cache:
                        price_cache[symbol]=load_history(
                            ak,symbol,first_start,asof_s.replace("-",""))
                    prices[symbol],src,sha=price_cache[symbol]
                    sources[symbol]={"source":src,"raw_sha256":sha,
                                     "historical_query_start":first_start,
                                     "first_observed_at":datetime.now(BEIJING).isoformat()}
                except Exception as exc:
                    out["errors"].append(f"{e_id}:{symbol}:{type(exc).__name__}:{str(exc)[:160]}")
            res=evaluate_frozen_event(event,ses,prices)
            out["result_records"].append({"id":e_id,"strategy_id":event.get("strategy_id"),
                "source_event":origin,"provider_sources":sources,"evaluation":res,
                "actual_broker_fill_confirmed":False})
        except Exception as exc:
            out["errors"].append(f"{e_id}:{type(exc).__name__}:{str(exc)[:180]}")
            out["result_records"].append({"id":e_id,"status":"PAPER_EVALUATION_FAILED"})
    return out

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--events",default="records/national_team_events")
    p.add_argument("--out",default="records/national_team_paper")
    p.add_argument("--max-events",type=int,default=64)
    a=p.parse_args()
    now=datetime.now(BEIJING)
    run=os.environ.get("GITHUB_RUN_ID","local")
    attempt=os.environ.get("GITHUB_RUN_ATTEMPT","1")
    target=Path(a.out)/now.date().isoformat()/f"{run}-a{attempt}.json"
    if target.exists():raise FileExistsError("do not overwrite paper evidence")
    target.parent.mkdir(parents=True,exist_ok=True)
    try:
        import akshare as ak
        result=assess(ak,Path(a.events),now.date(),max_events=a.max_events)
    except Exception as exc:
        result={"status":"PAPER_EVALUATION_UNAVAILABLE",
                "errors":[f"{type(exc).__name__}:{str(exc)[:240]}"]}
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"paper_status":result["status"],
                      "examined":result.get("assessed_events",0),
                      "errors":len(result.get("errors",[])),
                      "path":str(target)},ensure_ascii=False))
if __name__=="__main__":main()
