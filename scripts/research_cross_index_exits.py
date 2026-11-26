"""EXP-0018 stage 2: frozen, matched ETF exit/re-entry ablations.

Historical public vintages are exploratory, not official per-fund PIT or live fills.
No strategy selection from these already inspected sessions.
"""
from __future__ import annotations

import json
import sys
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import exchange_calendars as xc
from national_team.core_flow_factors import utc_aware
from national_team.left_entry_v4 import CAPITAL
from national_team.paper_account_v5 import _buy, _sell
from scripts import research_national_team_timing as timing
from scripts.research_shadow_pit_history import BASKETS, load, measure

ROOT=timing.ROOT
FREEZE="2026-11-26"
# Two-session recovery search, then original T+2 exit. Never T+0.
RECOVERY_SESSIONS=2


def shadow_at(vintages,codes,session,cutoff):
    candidates=[v for v in vintages if v["session"]==session and
                utc_aware(v["available_at"],"publication")<cutoff]
    if not candidates:
        return None
    latest=max(utc_aware(v["available_at"],"publication") for v in candidates)
    selected=[v for v in candidates if utc_aware(v["available_at"],"publication")==latest]
    if len(selected)!=1:
        return None
    # A later incomplete revision must not be silently replaced by an earlier good one.
    row=measure(selected[0],codes)
    return row if row and row["eligible_for_exploratory_replay"] else None


def cross_exits(days, exits, vintages, codes):
    keep={};decisions=[]
    for i,event in sorted(exits.items()):
        clock=timing.opening(days[i])
        known=utc_aware(event["known_at"],"core observed")
        if known>=clock or event["signal_session"]>=days[i]:
            raise ValueError("future core exit signal")
        row=shadow_at(vintages,codes,event["signal_session"],clock)
        veto=row is not None and Decimal(row["expanded_ex_core_100m_cny_rounded"])>0
        if not veto:
            keep[i]=event
        decisions.append({"execution_session":days[i],"signal_session":event["signal_session"],
                          "core_known_at":known.isoformat(),"cross_known_at":row["available_at"] if row else None,
                          "cross_commit":row["commit"] if row else None,
                          "expanded_ex_core":row["expanded_ex_core_100m_cny_rounded"] if row else None,
                          "decision":"VETO_ROTATION" if veto else ("CONFIRM_CORE_EXIT" if row else "CORE_EXIT_FALLBACK")})
    return keep,decisions


def exit_effects(days,prices,baseline,overlay,decisions,cost):
    """Equal original shares isolate the direct effect of each actual exit veto."""
    candidates={x["execution_session"]:x for x in decisions if x["decision"]=="VETO_ROTATION"}
    effects=[]
    trades=baseline["accounts"]["S2"]["trades"]
    other=overlay["accounts"]["S2"]["trades"]
    def proceeds(price,qty):
        gross=price*qty
        return gross-(gross-_sell(price,qty,etf=True))*cost
    entry=None
    for trade in trades:
        if trade["side"]=="BUY":
            entry=trade
        elif trade.get("reason")=="EARLY_REDEMPTION_RESEARCH" and trade["session"] in candidates:
            end=days.index(entry["session"])+2
            if end>=len(days):
                continue
            # Only a real early sale suppressed by the veto is counted.
            if any(x["side"]=="SELL" and x["session"]==trade["session"] and
                   x.get("reason")=="EARLY_REDEMPTION_RESEARCH" for x in other):
                continue
            # Another later core exit can still end S3's position before T+2.
            overlay_sale=next((x for x in other if x["side"]=="SELL" and
                               trade["session"]<=x["session"]<=days[end]),None)
            if overlay_sale is None:
                continue
            qty=trade["shares"]
            delta=proceeds(Decimal(overlay_sale["price"]),qty)-proceeds(Decimal(trade["price"]),qty)
            effects.append({"entry_session":entry["session"],"core_exit_session":trade["session"],
                            "overlay_exit_session":overlay_sale["session"],"shares":qty,
                            "same_shares_incremental_net_cny":str(delta.quantize(Decimal(".01"))),
                            "harmful_veto":delta<0,"avoided_false_exit":delta>0})
    return effects


def recovery_pairs(days,prices,core,exits,overlay,vintages,codes,cost):
    """Separate conditional event study: re-entry vs cash, not a continuous S4 account.

    Search at most two future session opens after an actual S3 early exit.
    Keep event windows non-overlapping without using future prices to decide.
    """
    pairs=[];reserved_until=-1
    for sale in overlay["accounts"]["S2"]["trades"]:
        if sale.get("reason")!="EARLY_REDEMPTION_RESEARCH":
            continue
        i=days.index(sale["session"])
        if i<=reserved_until:
            continue
        withdrawal=exits[i]["signal_session"]
        item={"exit_session":days[i],"withdrawal_session":withdrawal,"status":"NO_RECOVERY",
              "reentry_session":None,"net_vs_cash_cny":None}
        # The research budget is fixed, independent of S3's actual capital path.
        for j in range(i+1,min(i+RECOVERY_SESSIONS+1,len(days))):
            if j in exits:
                continue
            clock=timing.opening(days[j])
            visible=[(day,row) for day,row in core.items()
                     if withdrawal<day<days[j] and day in days[max(0,j-2):j] and row["observed"]<clock]
            if not visible:
                continue
            day,row=max(visible,key=lambda x:x[0])
            cross=shadow_at(vintages,codes,day,clock)
            if row["flow"]<=0 or not cross or Decimal(cross["expanded_ex_core_100m_cny_rounded"])<=0:
                continue
            available=max(row["observed"],utc_aware(cross["available_at"],"cross publication"))
            if available<=timing.opening(days[i]):
                continue
            item.update(status="PENDING_OUTCOME",reentry_session=days[j],recovery_session=day,
                        known_at=available.isoformat(),cross_commit=cross["commit"])
            reserved_until=j+2
            if j+2>=len(days):
                break
            buy=prices[days[j]][0];sell=prices[days[j+2]][3]
            def entry_cost(qty):
                gross=buy*qty
                return gross+(_buy(buy,qty,etf=True)-gross)*cost
            qty=int(CAPITAL/(buy*100))*100
            while qty and entry_cost(qty)>CAPITAL:
                qty-=100
            if not qty:
                item["status"]="NO_AFFORDABLE_LOT"
                break
            gross=sell*qty
            proceeds=gross-(gross-_sell(sell,qty,etf=True))*cost
            delta=proceeds-entry_cost(qty)
            item.update(status="MATURED",exit_after_reentry=days[j+2],shares=qty,
                        net_vs_cash_cny=str(delta.quantize(Decimal(".01"))),
                        harmful_reentry=delta<0)
            break
        if item["status"]=="NO_RECOVERY" and i+RECOVERY_SESSIONS>=len(days):
            item["status"]="PENDING_RECOVERY_WINDOW"
        pairs.append(item)
    return pairs


def compare(days,prices,entries,exits,core,vintages,codes,*,cost=Decimal(1)):
    base=timing.replay(days,prices,entries,exits,cost_multiplier=cost)
    retained,decisions=cross_exits(days,exits,vintages,codes)
    overlay=timing.replay(days,prices,entries,retained,cost_multiplier=cost)
    # These calls use identical source, entry opportunities and cash/fee assumptions.
    if base["accounts"]["S1"]!=overlay["accounts"]["S1"] or base["accounts"]["S0"]!=overlay["accounts"]["S0"]:
        raise ValueError("baseline contamination")
    # Alphalens-style event paths include signals while flat, not simulated fills.
    for row in decisions:
        i=days.index(row["execution_session"])
        op=prices[days[i]][0]
        row["forward_open_to_close_return"]={
            str(h):str(prices[days[i+h-1]][3]/op-1) if i+h-1<len(days) else None
            for h in (1,3)}
        row["event_path_is_not_a_trade"]=True
    effects=exit_effects(days,prices,base,overlay,decisions,cost)
    recoveries=recovery_pairs(days,prices,core,retained,overlay,vintages,codes,cost)
    s2=base["accounts"]["S2"];s3=overlay["accounts"]["S2"]
    mature=[x for x in recoveries if x["status"]=="MATURED"]
    return {"cost_multiplier":str(cost),"S0":base["accounts"]["S0"],"S1":base["accounts"]["S1"],
            "S2":s2,"S3":s3,"S3_minus_S2_cny":str(Decimal(s3["net_pnl_cny"])-Decimal(s2["net_pnl_cny"])),
            "S3_minus_S2_drawdown":str(Decimal(s3["max_drawdown"])-Decimal(s2["max_drawdown"])),
            "cross_decisions":decisions,"effective_exit_veto_pairs":effects,
            "blocked_entry_difference":base["blocked_entries"]-overlay["blocked_entries"],
            "S4_reentry_event_pairs":recoveries,
            "S4_mature_pairs":len(mature),
            "S4_mean_net_vs_cash_cny":str(sum(Decimal(x["net_vs_cash_cny"]) for x in mature)/len(mature)) if mature else None,
            "economic_gate":"INSUFFICIENT_INDEPENDENT_OUT_OF_SAMPLE_EVIDENCE"}


def run(root=ROOT):
    base=timing.run(root)
    days=[x.date().isoformat() for x in xc.get_calendar("XSHG").sessions_in_range(timing.START,timing.END)]
    extended=[x.date().isoformat() for x in xc.get_calendar("XSHG").sessions_in_range("2026-11-02",timing.END)]
    prices=timing.recover_prices(timing.read(root/timing.OUTCOMES),days)
    core,_=timing.core_events(timing.read(root/timing.MERGED),extended,root)
    entries={days.index(day):row for day,row in base["entries"].items()}
    exits={days.index(day):row for day,row in base["exit_candidates"].items()}
    vintages=load(root)
    result={name:{"base_cost":compare(days,prices,entries,exits,core,vintages,codes),
                  "double_cost":compare(days,prices,entries,exits,core,vintages,codes,cost=Decimal(2))}
            for name,codes in BASKETS.items()}
    return {"scope":"EXPLORATORY_PUBLISHED_VINTAGES_MATCHED_ABLATION",
            "freeze_date":FREEZE,"start":timing.START,"end":timing.END,
            "future_holdout_starts_after":FREEZE,"oos_independent_clusters":0,
            "S4_is_conditional_event_study_not_portfolio":True,
            "official_per_fund_publication_verified":False,"trade_authorized":False,
            "broker_orders":[],"baskets":result}


if __name__=="__main__":
    print(json.dumps(run(),ensure_ascii=False,indent=2))
