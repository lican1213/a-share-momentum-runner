"""Fund-flow identification and availability edge, not a new stock policy.

The two sources can share exchange inputs. Publication is a proxy for availability,
not identity of the beneficial investor. All historical paths are exploratory.
"""
from __future__ import annotations

import json
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import exchange_calendars as xc
from national_team.core_flow_factors import CORE_FOUR, utc_aware
from national_team.left_entry_v4 import CAPITAL, d
from national_team.paper_account_v5 import _buy, _sell
from scripts import research_national_team_timing as timing
from scripts.research_shadow_pit_history import load, measure

ROOT=timing.ROOT


def state(flow,positive,negative):
    if flow>0 and positive>=3:
        return "BROAD_SUBSCRIPTION"
    if flow<0 and negative>=3:
        return "BROAD_REDEMPTION"
    return "MIXED"


def public_signal(vintages,session,days,*,max_age=2):
    """First actionable opening, latest published revision at that opening."""
    start=days.index(session)
    for i in range(start+1,min(len(days),start+max_age+1)):
        cutoff=timing.opening(days[i])
        eligible=[v for v in vintages if v["session"]==session and
                  utc_aware(v["available_at"],"publication")<cutoff]
        if not eligible:
            continue
        last=max(utc_aware(v["available_at"],"publication") for v in eligible)
        latest=[v for v in eligible if utc_aware(v["available_at"],"publication")==last]
        if len(latest)!=1:
            continue
        v=latest[0]
        row=measure(v,CORE_FOUR)
        if not row or not row["eligible_for_exploratory_replay"]:
            continue
        changes=[d(x["dsh"],"change") for x in v["etfs"] if x["c"] in CORE_FOUR]
        flow=Decimal(row["net_100m_cny_rounded"])*Decimal(100000000)
        return {"session":session,"known_at":row["available_at"],"open_index":i,
                "state":state(flow,sum(x>0 for x in changes),sum(x<0 for x in changes)),
                "flow_cny":str(flow),"commit":row["commit"],"source":"PUBLIC_PROXY"}
    return None


def original_signal(row,session,days):
    if not row:
        return None
    i=timing.next_open(days,row["observed"])
    if i is None or i-days.index(session)>2 or i<=days.index(session):
        return None
    return {"session":session,"known_at":row["observed"].isoformat(),"open_index":i,
            "state":state(row["flow"],row["positive"],row["negative"]),
            "flow_cny":str(row["flow"]),"source":"ARCHIVED_CORE"}


def net_path(prices,days,i,j,cost=Decimal(1)):
    if j>=len(days) or j<=i:
        return None
    op,cl=prices[days[i]][0],prices[days[j]][3]
    def buy(q):
        gross=op*q
        return gross+(_buy(op,q,etf=True)-gross)*cost
    qty=int(CAPITAL/(op*100))*100
    while qty and buy(qty)>CAPITAL:
        qty-=100
    if not qty:
        return None
    gross=cl*qty
    return (gross-(gross-_sell(cl,qty,etf=True))*cost-buy(qty)).quantize(Decimal(".01"))


def evaluate(days,prices,core,vintages,*,cost=Decimal(1)):
    """Same funding dates and T+1/T+2 horizons; separate latency and direction."""
    events=[];pairs=[];seen={"PUBLIC_PROXY":set(),"ARCHIVED_CORE":set()}
    for session in days[:-1]:
        early=public_signal(vintages,session,days)
        official=original_signal(core.get(session),session,days)
        for signal in (early,official):
            if signal is None:
                continue
            i=signal["open_index"]
            if utc_aware(signal["known_at"],"signal clock")>=timing.opening(days[i]):
                raise ValueError("signal after opening")
            # Distinct funding dates can land on the same execution day: no portfolio
            # stacking or claim of independent events.
            signal["execution_session"]=days[i]
            signal["execution_collision"]=i in seen[signal["source"]]
            seen[signal["source"]].add(i)
            signal["net_t1_cny"]=None
            signal["net_t2_cny"]=None
            for h in (1,2):
                result=net_path(prices,days,i,i+h,cost)
                signal[f"net_t{h}_cny"]=str(result) if result is not None else None
            events.append(signal)
        if not early or not official:
            continue
        e,o=early["open_index"],official["open_index"]
        same=early["state"]==official["state"]
        pair={"session":session,"public_state":early["state"],"core_state":official["state"],
              "agreement":same,"public_open":days[e],"core_open":days[o],
              "lead_sessions":o-e,"public_commit":early["commit"],
              "public_known_at":early["known_at"],"core_known_at":official["known_at"],
              "buy_timing_delta_cny":None,"exit_timing_delta_per_100_shares_cny":None}
        # Direct clock comparison with same terminal, T+1 minimum and <=3 sessions.
        # Agreement is a retrospective diagnostic, not a live admission condition.
        if same and abs(o-e)<=1 and early["state"]=="BROAD_SUBSCRIPTION":
            j=min(o,e)+2
            a=net_path(prices,days,e,j,cost);b=net_path(prices,days,o,j,cost)
            if a is not None and b is not None:
                pair["buy_timing_delta_cny"]=str(a-b)
        if same and early["state"]=="BROAD_REDEMPTION":
            def proceeds(i):
                p=prices[days[i]][0];gross=p*100
                return gross-(gross-_sell(p,100,etf=True))*cost
            pair["exit_timing_delta_per_100_shares_cny"]=str((proceeds(e)-proceeds(o)).quantize(Decimal(".01")))
        pairs.append(pair)
    summary={}
    for source in seen:
        summary[source]={}
        for label in ("BROAD_SUBSCRIPTION","BROAD_REDEMPTION","MIXED"):
            subset=[x for x in events if x["source"]==source and x["state"]==label]
            result={"candidate_dates":len(subset),"distinct_execution_days":len({x["execution_session"] for x in subset})}
            for h in (1,2):
                values=[Decimal(x[f"net_t{h}_cny"]) for x in subset if x[f"net_t{h}_cny"] is not None]
                result[f"T{h}"]={"mature":len(values),"wins":sum(v>0 for v in values),
                                 "mean_net_cny":str((sum(values)/len(values)).quantize(Decimal(".01"))) if values else None}
            summary[source][label]=result
    return {"cost_multiplier":str(cost),"events":events,"paired_sources":pairs,"summary":summary,
            "source_agreement":sum(x["agreement"] for x in pairs),"matched_dates":len(pairs),
            "public_earlier_open":sum(x["lead_sessions"]>0 for x in pairs),
            "public_later_open":sum(x["lead_sessions"]<0 for x in pairs),
            "public_same_open":sum(x["lead_sessions"]==0 for x in pairs),
            "economic_gate":"EXPLORATORY_NO_INDEPENDENT_OOS",
            "trade_authorized":False,"broker_orders":[]}


def run(root=ROOT):
    days=[x.date().isoformat() for x in xc.get_calendar("XSHG").sessions_in_range(timing.START,timing.END)]
    ext=[x.date().isoformat() for x in xc.get_calendar("XSHG").sessions_in_range("2026-11-02",timing.END)]
    prices=timing.recover_prices(timing.read(root/timing.OUTCOMES),days)
    core,missing=timing.core_events(timing.read(root/timing.MERGED),ext,root)
    vintages=load(root)
    return {"scope":"FUND_FLOW_CLOCK_EDGE_EXPLORATORY","start":days[0],"end":days[-1],
            "source_missing_or_anomalous":missing,"beneficial_owner_identified":False,
            "official_exchange_publication_independently_verified":False,
            "base_cost":evaluate(days,prices,core,vintages),
            "double_cost":evaluate(days,prices,core,vintages,cost=Decimal(2))}


if __name__=="__main__":
    print(json.dumps(run(),ensure_ascii=False,indent=2))
