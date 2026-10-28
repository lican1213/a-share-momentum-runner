"""Freeze prospective S1/S2 stock paper events from authentic watchlist artifacts.

An event can only be frozen after the stock ranking is fully computed.
Never back-date it to the ETF underlying settlement day.
"""
from __future__ import annotations
import argparse,hashlib,json,os
from datetime import datetime,date,timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from decimal import Decimal
from national_team.core_flow_factors import utc_aware

BEIJING=ZoneInfo("Asia/Shanghai")
def freeze_watch(watch:dict,*,source_path:str,model_sha:str)->dict:
    asof=watch.get("funding_date")
    captured=watch.get("event_first_public_no_earlier_than")
    if watch.get("status")!="INDEX_PROXY_RESEARCH_WATCHLIST" or not captured:
        return {"status":"NO_FREEZABLE_RANKING","reason":watch.get("status"),
                "source_watch":source_path,"no_broker_orders":True}
    stamp=utc_aware(captured,"ranking first public").astimezone(BEIJING)
    if date.fromisoformat(asof)>stamp.date():
        raise ValueError("future ETF event funding date")
    if (stamp.date()-date.fromisoformat(asof)).days>4:
        return {"status":"STALE_FUNDING_NOT_FROZEN","source_watch":source_path,
                "age_calendar_days":(stamp.date()-date.fromisoformat(asof)).days,
                "no_broker_orders":True}
    ranking=watch.get("research_ranking") or {}
    if ranking.get("source_kind")!="CSI300_LATEST_INDEX_WEIGHT_PROXY_NOT_ETF_PCF":
        raise ValueError("cannot freeze unclassified PCF or weights")
    positive=ranking.get("candidates") or []
    if not positive:
        return {"status":"NO_POSITIVE_RESEARCH_EVENT","source_watch":source_path,
                "outflow_risk":ranking.get("outflow_risk",[]),
                "no_broker_orders":True}
    s1=[r["symbol"] for r in positive[:5]]
    with_strength=[r for r in positive if r.get("relative_strength20") is not None]
    # This S2 remains a predefined exploratory ranking, not a tuned threshold.
    with_strength.sort(key=lambda r:(-Decimal(r["relative_strength20"]),
                                      -Decimal(r["signed_exposure_over_adv20"]),r["symbol"]))
    s2=[r["symbol"] for r in with_strength[:5]]
    # Stable economic event identity: multiple reruns or source refreshes
    # of the SAME fund settlement day must never count as independent trials.
    # The FIRST frozen prospective ranking is the immutable cohort.
    base=hashlib.sha256(f"CSI300_CORE4|{asof}|INDEX_PROXY_V1".encode()).hexdigest()[:20]
    events=[]
    for strat,portfolio in (("S1_FLOW_OVER_ADV20",s1),("S2_FLOW_PLUS_PRICE_STRENGTH",s2)):
        if not portfolio:continue
        events.append({
            "id":f"NT-{base}-{strat}",
            "strategy_id":strat,
            "candidate_symbols":portfolio,
            "first_public_at":stamp.isoformat(),
            "frozen_by_commit":model_sha,
            "benchmark_etf":"510300",
            "funding_underlying_day":asof,
            "source_watch":source_path,
            "source_kind":ranking["source_kind"],
            "ETF_PCF_verified":False,
            "central_huijin_order_verified":False,
            "broker_trades_authorized":False,
            "data_quality":{"source_ETF_scope":ranking.get("data_scope"),
                            "observed_fund_count":len(ranking.get("observed_funds",[])),
                            "pool_is_partial":ranking.get("topn_pool_is_partial",True)}
        })
    return {"status":"FROZEN_PROSPECTIVE_RESEARCH_EVENTS","source_watch":source_path,
            "frozen_at":stamp.isoformat(),"events":events,"no_broker_orders":True}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--source",required=True)
    parser.add_argument("--out",default="records/national_team_events")
    args=parser.parse_args()
    path=Path(args.source)
    watch=json.loads(path.read_text(encoding="utf-8"))
    stamp=datetime.now(BEIJING)
    run=os.environ.get("GITHUB_RUN_ID","local")
    attempt=os.environ.get("GITHUB_RUN_ATTEMPT","1")
    target=Path(args.out)/stamp.date().isoformat()/f"{run}-a{attempt}.json"
    if target.exists():raise FileExistsError("refuse rewrite original frozen event")
    target.parent.mkdir(parents=True,exist_ok=True)
    existing_ids=set()
    for old in Path(args.out).glob("*/*.json"):
        try:
            prior=json.loads(old.read_text(encoding="utf-8"))
            existing_ids.update(e.get("id") for e in prior.get("events",[]))
        except (OSError,ValueError):
            continue
    try:
        out=freeze_watch(watch,source_path=str(path),model_sha=os.environ.get("GITHUB_SHA","unknown"))
        if out.get("events"):
            original=len(out["events"])
            out["events"]=[e for e in out["events"] if e["id"] not in existing_ids]
            out["duplicate_already_frozen"]=original-len(out["events"])
            if not out["events"]:
                out["status"]="ALL_EVENTS_DUPLICATE_PREVIOUSLY_FROZEN"
    except Exception as exc:
        out={"status":"FREEZE_FAILED","reason":f"{type(exc).__name__}:{str(exc)[:230]}",
             "source_watch":str(path),"no_broker_orders":True}
    target.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"paper_freeze":out["status"],"event_count":len(out.get("events",[])),
                      "record":str(target)},ensure_ascii=False))
if __name__=="__main__":main()
