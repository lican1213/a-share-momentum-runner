"""Reconcile actual shares and NAV with consecutive XSHG exchange sessions.

Values downloaded today cannot be used in historical paper signals before
their archived first-observed timestamp. Three-fund observations remain useful
partial research rather than invented four-fund events.
"""
from __future__ import annotations
from decimal import Decimal
from typing import Mapping,Sequence
from national_team.core_flow_factors import CORE_FOUR,calculate,utc_aware

def reconcile_funding_snapshot(raw:Mapping,sessions:Sequence[str])->dict:
    if not sessions or list(sessions)!=sorted(set(sessions)):
        raise ValueError("exchange sessions must be nonempty chronological unique")
    asof=str(raw["asof_requested"])
    capture=str(raw["first_observed_no_earlier_than"])
    utc_aware(capture,"capture time")
    if sessions[-1]>asof:
        raise ValueError("calendar extends beyond source asof")
    panel=raw.get("observations_by_date",{})
    out={"status":"NO_COMPLETE_FOUR_ETF_EVENT","funds":list(CORE_FOUR),
         "asof":asof,"first_available_at":capture,
         "provider_run_id":str(raw.get("run_id","unknown")),
         "publication_time_policy":"historical observations first available after this capture",
         "verified_consecutive_session_flow":False,
         "series_kind":"ETF_NET_CREATION_PROXY_NOT_HUIJIN_ACCOUNT_ORDERS",
         "history_sessions":list(sessions),
         "complete_four_days":[],"missing_by_day":{},
         "partial_funding":None,"four_etf_factor":None}
    effective_dates=[d for d in sessions if d in panel and d<=asof]
    if not effective_dates:
        return out
    effective_date=effective_dates[-1]
    out["latest_available_trading_day"]=effective_date
    effective_sessions=[d for d in sessions if d<=effective_date]
    for d in effective_sessions:
        obs=panel.get(d,{})
        missing=[c for c in CORE_FOUR if c not in obs or "shares" not in obs[c] or "nav" not in obs[c]]
        if missing:out["missing_by_day"][d]=missing
        else:out["complete_four_days"].append(d)
    if len(effective_sessions)>=2:
        prev,current=effective_sessions[-2:]
        sse=CORE_FOUR[:3]
        if all(c in panel.get(prev,{}) and c in panel.get(current,{})
               and "nav" in panel[current][c] for c in sse):
            flows={c:(Decimal(str(panel[current][c]["shares"]))-
                      Decimal(str(panel[prev][c]["shares"])))*
                      Decimal(str(panel[current][c]["nav"])) for c in sse}
            out["partial_funding"]={
                "period":[prev,current],"funds":list(sse),
                "net_creation_proxy_cny":format(sum(flows.values(),Decimal(0)),"f"),
                "per_fund_proxy_cny":{c:format(v,"f") for c,v in flows.items()},
                "fund_count_coverage":"3/4",
                "market_session_adjacency_verified":True}
    # A newest-day three-ETF observation must not erase yesterday's valid
    # complete FOUR-ETF five-day factor. Each stream retains its own date.
    full_dates=set(out["complete_four_days"])
    last_full=next((d for d in reversed(effective_sessions) if d in full_dates),None)
    if last_full is None:
        if out["partial_funding"] is not None:out["status"]="PARTIAL_FUNDING_ONLY"
        return out
    last_full_idx=effective_sessions.index(last_full)
    if last_full_idx<5:
        if out["partial_funding"] is not None:out["status"]="PARTIAL_FUNDING_ONLY"
        return out
    last6=list(effective_sessions[last_full_idx-5:last_full_idx+1])
    if any(d not in full_dates for d in last6):
        if out["partial_funding"] is not None:out["status"]="PARTIAL_FUNDING_ONLY"
        return out
    factor_panel={}
    for d in last6:
        factor_panel[d]={}
        for c in CORE_FOUR:
            src=panel[d][c]
            source_url=("https://www.sse.com.cn/assortment/fund/etf/list/scale/"
                        if c!="159919" else "https://www.szse.cn/market/fund/volume/etf/index.html")
            factor_panel[d][c]={
                "shares":src["shares"],"share_unit":"shares","nav":src["nav"],
                "nav_unit":"CNY/share","source_url":source_url,
                "nav_source_url":f"https://fundf10.eastmoney.com/jjjz_{c}.html",
                "published_at":capture,"nav_published_at":capture,
                "corporate_action":None}
    f=calculate(factor_panel,last6,last6[-1],decision_cutoff=capture)
    if not f.get("five_day"):
        raise ValueError("six-session factor did not compute")
    out["four_etf_factor"]=f
    out["latest_complete_four_etf_factor_date"]=f["trade_date"]
    out["status"]=("PARTIAL_LATEST_WITH_PRIOR_FULL_FOUR_FACTOR"
                   if f["trade_date"]!=effective_date
                   else "FULL_FOUR_ETF_SHARES_NAV_OBSERVED_RESEARCH")
    out["verified_consecutive_session_flow"]=True
    out["factor_quality"]={
        "exchange_shares_via_official_providers":True,
        "NAV_from_Eastmoney_not_original_fund_report":True,
        "corporate_actions_explicitly_verified":f["corporate_actions_explicitly_verified"],
        "market_float_denominators_available":False,
        "first_available_at":capture,"national_team_investor_identified":False}
    return out

def exchange_sessions(last:str,lookback_days:int=24)->list[str]:
    import pandas as pd
    import exchange_calendars as xcals
    cal=xcals.get_calendar("XSHG")
    d=pd.Timestamp(last)
    first=d-pd.Timedelta(days=lookback_days)
    return [x.date().isoformat() for x in cal.sessions_in_range(first,d)]
