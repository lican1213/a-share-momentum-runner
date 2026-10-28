"""Independent red-team gate for persisted national-team run artifacts.

This gate recomputes cash flows directly from RAW source observations, not via
the original factor helper. Tests audit integrity and true evidence classification,
not trading profitability. Unexpected mismatches raise and fail CI.
"""
from __future__ import annotations
import argparse,json,os
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo
from national_team.core_flow_factors import CORE_FOUR

class AuditViolation(AssertionError):pass

def check_funding(raw:dict)->dict:
    event=raw.get("funding_event") or {}
    factor=event.get("four_etf_factor")
    if factor is None:
        return {"result":"NO_COMPLETE_FOUR_FACTOR","verified":False}
    dates=event.get("history_sessions")
    if not dates or factor.get("trade_date") not in dates:
        raise AuditViolation("factor date absent from original exchange calendar")
    end=dates.index(factor["trade_date"])
    if end<5:
        raise AuditViolation("less than 5 actual preceding exchange sessions")
    actual=dates[end-5:end+1]
    obs=raw.get("observations_by_date") or {}
    for day in actual:
        if any(not all(k in obs.get(day,{}).get(c,{}) for k in ("shares","nav"))
               for c in CORE_FOUR):
            raise AuditViolation(f"missing raw four ETF shares or NAV on {day}")
    rows=[obs[d] for d in actual]
    totals=[]
    for before,after in zip(rows[:-1],rows[1:]):
        amount=sum((Decimal(str(after[c]["shares"]))-Decimal(str(before[c]["shares"])))*
                   Decimal(str(after[c]["nav"])) for c in CORE_FOUR)
        totals.append(amount)
    claimed_daily=Decimal(str(factor["daily_net_creation_proxy_cny"]))
    claimed_five=Decimal(str(factor["five_day"]["net_creation_cny_daily_sum"]))
    if totals[-1]!=claimed_daily:
        raise AuditViolation(f"daily ETF flow mismatch {totals[-1]} != {claimed_daily}")
    if sum(totals)!=claimed_five:
        raise AuditViolation(f"5d ETF flow mismatch {sum(totals)} != {claimed_five}")
    first_aum=sum(Decimal(str(rows[0][c]["shares"]))*
                  Decimal(str(rows[0][c]["nav"])) for c in CORE_FOUR)
    ratio=claimed_five/first_aum
    if abs(ratio-Decimal(str(factor["five_day"]["net_creation_pct_initial_aum"])))>Decimal("1e-20"):
        raise AuditViolation("5d ETF intensity ratio mismatch")
    if raw.get("conflicts"):
        # source conflicts require explicit censorship (no contradictory funds
        # could have contributed to this factor's exact 6-session window).
        for conflict in raw["conflicts"]:
            if conflict["date"] in actual and conflict["code"] in CORE_FOUR:
                raise AuditViolation("computed full factor includes conflicting source record date")
    return {"result":"FOUR_ETF_FUNDING_RECALCULATED","verified":True,
            "day_net_creation_proxy_cny":str(claimed_daily),
            "five_day_net_creation_proxy_cny":str(claimed_five),
            "five_day_intensity":str(ratio),
            "unusually_large_abs_five_day_intensity":abs(ratio)>Decimal("0.10"),
            "unusually_large_is_review_flag_not_auto_rejection":True,
            "not_actual_huijin_buy":True}

def check_stock_watch(watch:dict,funding:dict)->dict:
    ranking=watch.get("research_ranking") or {}
    if watch.get("status")!="INDEX_PROXY_RESEARCH_WATCHLIST":
        return {"result":"NO_RANKING_TO_AUDIT","verified":False}
    if ranking.get("not_actual_ETF_PCF") is not True:
        raise AuditViolation("index proxy mislabeled as actual ETF PCF")
    if watch.get("index_weight",{}).get("kind")!="CSI300_LATEST_INDEX_WEIGHT_PROXY_NOT_ETF_PCF":
        raise AuditViolation("unknown weights provenance")
    if ranking.get("not_executable_orders") is not True:
        raise AuditViolation("unexpected executable order claim")
    if watch.get("funding_date")!=funding.get("funding_event",{}).get("latest_available_trading_day"):
        raise AuditViolation("stock ranking uses mismatched ETF trade date")
    if ranking.get("data_scope")=="FOUR_ETF_DATED_SHARE_FLOW":
        factor=(funding.get("funding_event") or {}).get("four_etf_factor")
        if factor is None:
            raise AuditViolation("stock watch claims four-fund flow with no four-fund factor")
        if Decimal(ranking["known_ETF_net_flow_proxy_cny"])!=Decimal(factor["daily_net_creation_proxy_cny"]):
            raise AuditViolation("stock watch net flow disagrees with original factor")
    if ranking.get("data_scope")=="PARTIAL_SSE_THREE_EXCLUDES_159919":
        latest=(funding.get("funding_event") or {}).get("partial_funding") or {}
        if not latest:
            raise AuditViolation("partial three-ETF stock watch has no source funding record")
        if Decimal(str(latest.get("net_creation_proxy_cny")))!=Decimal(
                str(ranking["known_ETF_net_flow_proxy_cny"])):
            raise AuditViolation("stock watch partial source flow disagrees with ETF fund shares")
        if watch.get("funding_date")!=latest.get("period",[])[-1]:
            raise AuditViolation("stock watch partial event date disagrees with latest source")
    wts=watch.get("index_weight",{}).get("weights",{})
    checked=0
    for section in ("candidates","outflow_risk"):
        for row in ranking.get(section,[]):
            symbol=row["symbol"]
            if symbol not in wts:raise AuditViolation("stock not in source CSI300 file")
            wt=Decimal(str(wts[symbol]))
            flow=Decimal(ranking["known_ETF_net_flow_proxy_cny"])
            claimed=Decimal(str(row["implied_index_exposure_cny"]))
            adv=Decimal(str(row["adv20_cny"]))
            ratio=Decimal(str(row["signed_exposure_over_adv20"]))
            if claimed!=wt*flow:
                raise AuditViolation(f"stock {symbol} flow weight arithmetic mismatch")
            if adv<=0 or abs(claimed/adv-ratio)>Decimal("1e-20"):
                raise AuditViolation(f"stock {symbol} relative turnover ratio mismatch")
            if section=="candidates" and claimed<=0:
                raise AuditViolation("long-research candidate has negative flow pressure")
            checked+=1
    if ranking.get("ranked_from_n_stocks",0)>watch.get("index_weight",{}).get("weight_count",0):
        raise AuditViolation("ranked more stocks than source constituent universe")
    return {"result":"INDEX_PROXY_RANKING_RECALCULATED","verified":True,
            "candidate_rows_checked":checked,
            "sampled_constituents":ranking.get("ranked_from_n_stocks"),
            "all_300_constituents_covered":ranking.get("ranked_from_n_stocks")==300}

def check_paper(frozen:dict,watch:dict)->dict:
    events=frozen.get("events") or []
    ids=[e["id"] for e in events]
    if len(ids)!=len(set(ids)):raise AuditViolation("duplicate frozen event id")
    watch_capture=watch.get("event_first_public_no_earlier_than")
    for e in events:
        if e.get("broker_trades_authorized") is not False:
            raise AuditViolation("unexpected stock order authorization")
        if e.get("ETF_PCF_verified") is not False:
            raise AuditViolation("index proxy event falsely claims actual PCF")
        if watch_capture and datetime.fromisoformat(e["first_public_at"])<datetime.fromisoformat(watch_capture):
            raise AuditViolation("event timestamp predates stock data capture")
    return {"result":"IMMUTABLE_FROZEN_EVENTS_CHECKED","count":len(events)}

def audit(bundle:dict)->dict:
    original=bundle["source"];merged=bundle["merged"]
    watch=bundle["watch"];frozen=bundle["frozen"]
    # The merged observation must preserve original source evidence rather
    # than overwriting official exchange data in place.
    if not isinstance(merged.get("sources_used"),list) or not merged["sources_used"]:
        raise AuditViolation("composite without source run IDs")
    if not any(str(original.get("run_id"))==str(r.get("run_id"))
               for r in merged["sources_used"]):
        raise AuditViolation("merged data omits current raw-source provenance")
    if merged.get("trade_orders_authorized") is not False:
        raise AuditViolation("source snapshot authorizes trading unexpectedly")
    funds=check_funding(merged)
    stocks=check_stock_watch(watch,merged)
    paper=check_paper(frozen,watch)
    both_verified=funds["verified"] and stocks["verified"]
    full_factor_date=((merged.get("funding_event") or {}).get("four_etf_factor") or {}).get("trade_date")
    stock_signal_date=watch.get("funding_date")
    mixed_date=bool(full_factor_date and stock_signal_date and full_factor_date!=stock_signal_date)
    status=("RESEARCH_PRIOR_FOUR_CURRENT_PARTIAL_AUDITED" if both_verified and mixed_date
            else "RESEARCH_DATA_AUDIT_PASS" if both_verified
            else "RESEARCH_PARTIAL_SOURCES_AUDITED")
    return {"status":status,"latest_complete_four_factor_date":full_factor_date,
            "stock_signal_trading_day":stock_signal_date,
            "funding_and_stock_signals_use_distinct_dates":mixed_date,
            "funds":funds,"stock_proxy":stocks,"paper":paper,
            "audit_does_not_prove_alpha":True,
            "audit_does_not_verify_actual_broker_execution":True,
            "investor_identity_verified":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",required=True)
    p.add_argument("--merged",required=True)
    p.add_argument("--watch",required=True)
    p.add_argument("--frozen",required=True)
    p.add_argument("--out",default="records/national_team_audits")
    args=p.parse_args()
    raw={k:json.loads(Path(getattr(args,k)).read_text(encoding="utf-8"))
         for k in ("source","merged","watch","frozen")}
    now=datetime.now(ZoneInfo("Asia/Shanghai"))
    run=os.environ.get("GITHUB_RUN_ID","local")
    attempt=os.environ.get("GITHUB_RUN_ATTEMPT","1")
    path=Path(args.out)/now.date().isoformat()/f"{run}-a{attempt}.json"
    if path.exists():raise FileExistsError("red-team audit record cannot be overwritten")
    path.parent.mkdir(parents=True,exist_ok=True)
    try:
        out=audit(raw)
        out["failures"]=[]
        failed=False
    except Exception as exc:
        failed=True
        out={"status":"RED_TEAM_AUDIT_FAILED",
             "failures":[f"{type(exc).__name__}:{str(exc)[:300]}"],
             "audit_does_not_prove_alpha":True}
    out["source_paths"]={k:getattr(args,k) for k in raw}
    out["evaluated_at"]=now.isoformat()
    path.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"redteam_status":out["status"],"record":str(path),
                      "failures":out["failures"]},ensure_ascii=False))
    if failed:raise SystemExit(2)
if __name__=="__main__":main()
