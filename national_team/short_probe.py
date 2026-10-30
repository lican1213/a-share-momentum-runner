"""Read-only post-close vendor probe. NEVER freezes signals or simulates orders."""
from __future__ import annotations
import hashlib
import json
import os
from datetime import datetime, timedelta, time
from pathlib import Path
from national_team import short_ab_engine as x

ROOT=Path("records/national_team_short_ab")

def read_only_probe(ak, now):
    now=now.astimezone(x.BJ)
    today=now.date()
    # Today's daily OHLC is allowed only after exchange has completed the session.
    until=today if now.time()>=time(15,35) else today-timedelta(days=1)
    days=x.calendar_sessions((until-timedelta(days=20)).isoformat(),until.isoformat())
    result={"status":"DIAGNOSTIC_ONLY_NO_FREEZE_NO_ORDER","captured_at":now.isoformat(),
            "run_id":os.getenv("GITHUB_RUN_ID","local"),
            "source_commit_sha":os.getenv("GITHUB_SHA","UNKNOWN"),
            "asof_session":days[-1] if days else None,
            "candidate_pool":[code for _,code in x.RANK_ORDER],
            "real_broker_orders":0,"paper_positions_created":0,
            "warnings":[],"candidates":[],"groups":{}}
    if not days:
        result["warnings"].append("NO_COMPLETED_EXCHANGE_SESSION")
        return result
    asof=days[-1]
    try:result["four_etf_flow"]=x.source_flow(now)
    except Exception as exc:
        result["warnings"].append("FOUR_ETF:"+type(exc).__name__+":"+str(exc)[:180])
    try:result["original_v2"]=x.strategy_snapshot(now)
    except Exception as exc:
        result["warnings"].append("V2:"+type(exc).__name__+":"+str(exc)[:180])
    try:
        benchmark=x.prices(ak,"510300",asof)
        if x.bar(benchmark,asof) is None:raise ValueError("CURRENT_ETF_CLOSE_MISSING")
        result["benchmark"]={"price_sha256":benchmark["raw_sha256"],
                              "asof_close":x.bar(benchmark,asof)["close"],
                              "history_count":len(benchmark["bars"])}
    except Exception as exc:
        result["warnings"].append("BENCHMARK:"+type(exc).__name__+":"+str(exc)[:180])
        return result
    try:
        names,name_provider=x.stock_names(ak)
        result["security_name_provider"]=name_provider
    except Exception as exc:
        names={}
        result["warnings"].append("SECURITY_NAMES:"+type(exc).__name__+":"+str(exc)[:180])
    for cohort,code in x.RANK_ORDER:
        item={"code":code,"cohort":cohort,"name":names.get(code),
              "status":"UNVERIFIED","group_gates":{}}
        try:
            hist=x.prices(ak,code,asof)
            item["price_sha256"]=hist["raw_sha256"]
            item["history_count"]=len(hist["bars"])
            last=x.bar(hist,asof)
            if last is None:raise ValueError("TODAY_CLOSE_UNAVAILABLE")
            item["close"]=last["close"]
            if not item["name"]:raise ValueError("NAME_UNVERIFIED_ST_STATUS_UNKNOWN")
            if "ST" in item["name"].upper() or "退" in item["name"]:
                item["status"]="VERIFIED_EXCLUDED_ST"
            else:
                for group in ("A2","B"):
                    try:
                        ind=x.indicator(hist,benchmark,asof,group)
                        item["group_gates"][group]={
                            "eligible_indicative_only":ind["eligible"],
                            "gate_checks":ind["gate_checks"],
                            "rejection_reasons":ind["rejection_reasons"],
                            "atr14":ind["atr14"],"close":ind["close"],
                            "adv20":ind["adv20"],"rel20":ind["rel20"]}
                    except Exception as exc:
                        item["group_gates"][group]={"error":type(exc).__name__+":"+str(exc)[:160]}
                item["status"]="MARKET_DATA_VERIFIED_NO_FREEZE"
        except Exception as exc:
            item["error"]=type(exc).__name__+":"+str(exc)[:180]
        result["candidates"].append(item)
    result["groups"]={
       group:{"data_verified":sum(v["status"]=="MARKET_DATA_VERIFIED_NO_FREEZE" for v in result["candidates"]),
              "indicative_eligible":sum(v["group_gates"].get(group,{}).get("eligible_indicative_only",False)
                                         for v in result["candidates"]),
              "not_a_frozen_signal":True}
       for group in ("A2","B")}
    # Minute market-data readiness is diagnostic, not an exit-time execution.
    result["minute_source_checks"]={}
    for code in ("510300","601825","600309"):
        try:
            m=x.minute_rows(ak,code,asof)
            result["minute_source_checks"][code]={"ok":True,"sha256":m["sha256"],"bars":len(m["bars"])}
        except Exception as exc:
            result["minute_source_checks"][code]={"ok":False,
                "error":type(exc).__name__+":"+str(exc)[:160]}
    return result

def main():
    import akshare as ak
    now=datetime.now(x.BJ)
    rid=os.getenv("GITHUB_RUN_ID","local")
    att=os.getenv("GITHUB_RUN_ATTEMPT","1")
    path=ROOT/"probes"/now.date().isoformat()/f"{rid}-a{att}.json"
    path.parent.mkdir(parents=True,exist_ok=True)
    result=read_only_probe(ak,now)
    result["akshare_version"]=getattr(ak,"__version__","unknown")
    with path.open("x",encoding="utf-8") as out:
        out.write(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"probe_file":str(path),"status":result["status"],
                      "asof":result["asof_session"],"groups":result["groups"],
                      "warnings":result["warnings"],"minute_checks":result.get("minute_source_checks",{})},
                     ensure_ascii=False))
if __name__=="__main__":
    main()
