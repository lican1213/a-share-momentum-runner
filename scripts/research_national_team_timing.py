"""Read-only event replay; archived availability, never historical cache timestamps.

Core data and exit evidence are separate from third-party shadow observations.
All historical data inspected as of 2026-11-26 is exploratory.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import exchange_calendars as xc
from national_team.core_flow_factors import CORE_FOUR, dec, utc_aware
from national_team.left_entry_v4 import CAPITAL, digest
from national_team.paper_account_v5 import _buy, _sell
from national_team.archived_ohlc_v5 import _values

BJ = ZoneInfo("Asia/Shanghai")
ROOT = Path(__file__).resolve().parents[1]
MERGED = "records/national_team_merged/2026-11-26/45677832576-a1.json"
OUTCOMES = "records/national_team_left_outcomes_v5/2026-11-26/45724066760-a1.json"
START, END = "2026-11-03", "2026-11-25"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def verified(obj):
    return obj.get("snapshot_sha256") == digest({k:v for k,v in obj.items() if k!="snapshot_sha256"})


def opening(day):
    return datetime.combine(date.fromisoformat(day), time(9,30), BJ)


def next_open(days, observed):
    return next((i for i,day in enumerate(days) if opening(day)>observed),None)


def recover_prices(batch, days):
    if not verified(batch) or batch.get("trade_authorized") is not False or batch.get("broker_orders") != []:
        raise ValueError("unverified outcome batch")
    prices = {}
    for event in batch["results"]:
        source = event["source_new_ohlc"]
        if digest(source) != event["source_new_ohlc_sha256"]:
            raise ValueError("OHLC hash mismatch")
        captured = utc_aware(source["first_observed_at"],"OHLC time").astimezone(BJ)
        for row in source.get("bars_by_symbol",{}).get("510300",[]):
            day = row["date"]
            if day not in days:
                continue
            if captured < datetime.combine(date.fromisoformat(day),time(15,5),BJ):
                raise ValueError("unfinalized OHLC")
            vals = _values(row)
            if day in prices and prices[day]!=vals:
                raise ValueError("conflicting ETF prices")
            prices[day]=vals
    if set(prices)!=set(days):
        raise ValueError("missing ETF session; never jump across prices")
    return prices


def original_row(merged, day, code, root, cache):
    row = merged["observations_by_date"].get(day,{}).get(code)
    if not row:
        raise ValueError("incomplete core day")
    vals, clocks = [], []
    for key in ("shares","nav"):
        path = row.get(f"{key}_source_path","")
        if not path.startswith("records/national_team_etf/") or ".." in Path(path).parts:
            raise ValueError("invalid archived source path")
        if path not in cache:
            cache[path]=read(root/path)
        original=cache[path]
        if original.get("unit")!="raw_shares":
            raise ValueError("source unit mismatch")
        original_value=original["observations_by_date"][day][code][key]
        value=dec(row[key],key,positive=True)
        if value!=dec(original_value,key,positive=True):
            raise ValueError("source value disagreement")
        capture=utc_aware(original["capture_completed_beijing"],"original capture")
        claimed=utc_aware(row[f"{key}_first_observed_at"],"merged source capture")
        if capture < datetime.combine(date.fromisoformat(day),time(15,0),BJ):
            raise ValueError("source predates completed market session")
        vals.append(value)
        clocks.append(max(capture,claimed))
    return vals,max(clocks)


def core_events(merged, days, root):
    if merged.get("conflicts")!=[] or merged.get("conflicted_date_code_pairs")!=0:
        raise ValueError("merged source conflicts")
    result, unavailable, cache = {},{},{}
    for before,day in zip(days,days[1:]):
        try:
            old={c:original_row(merged,before,c,root,cache) for c in CORE_FOUR}
            new={c:original_row(merged,day,c,root,cache) for c in CORE_FOUR}
            flows={c:(new[c][0][0]-old[c][0][0])*new[c][0][1] for c in CORE_FOUR}
            jumps=[c for c in CORE_FOUR if abs(new[c][0][0]/old[c][0][0]-1)>Decimal("0.30")]
            if jumps:
                raise ValueError("large share jump requires independent action/source review")
            observed=max([v[1] for v in old.values()]+[v[1] for v in new.values()])
            result[day]={"observed":observed,"flow":sum(flows.values()),
                         "negative":sum(v<0 for v in flows.values()),
                         "positive":sum(v>0 for v in flows.values())}
        except (ValueError,KeyError,OSError,ArithmeticError) as exc:
            unavailable[day]=str(exc)
    return result,unavailable


def select_entries(routes, core, days):
    entries, excluded = {},[]
    seen=set()
    for r in sorted(routes,key=lambda r:utc_aware(r["observed_at"],"route time")):
        if r.get("status")!="NEW_FUNDING_EVENT":
            continue
        day=r["signal_session"]
        if day in seen or day not in days:
            continue
        seen.add(day)
        if (not verified(r) or r.get("trade_authorized") is not False or r.get("broker_orders")!=[]
                or tuple(r.get("four_etfs",[]))!=CORE_FOUR):
            raise ValueError("invalid route evidence")
        route_at=utc_aware(r["observed_at"],"route")
        if route_at < datetime.combine(date.fromisoformat(day),time(15,0),BJ):
            raise ValueError("route predates signal session")
        if day not in core or core[day]["flow"]<=0:
            excluded.append([day,"core not available or not positive"])
            continue
        observed=max(route_at,core[day]["observed"])
        i=next_open(days,observed)
        if i is None or i-days.index(day)>2:
            excluded.append([day,"pending or late beyond two market sessions"])
            continue
        entries.setdefault(i,{"signal_session":day,"route_run":r["github_run_id"],
                              "known_at":observed.isoformat()})
    return entries,excluded


def replay(days, prices, entries, exits, *, cost_multiplier=Decimal(1)):
    if not cost_multiplier.is_finite() or cost_multiplier < 1:
        raise ValueError("cost stress must be finite and >=1")
    def buy_cost(price, qty):
        gross=price*qty
        return gross+(_buy(price,qty,etf=True)-gross)*cost_multiplier
    def sell_value(price, qty):
        gross=price*qty
        return gross- (gross-_sell(price,qty,etf=True))*cost_multiplier
    # Matched non-overlapping entry windows; an early exit cannot create extra entries.
    cash={name:CAPITAL for name in ("S0","S1","S2")}
    shares={name:0 for name in cash}
    equity={name:[] for name in cash}
    trades={name:[] for name in cash}
    active=None
    window_start=None
    paired=[]
    blocked_entries=0
    early_in_window=False
    first=min(entries,default=None)
    def buy(name,i):
        op=prices[days[i]][0]
        qty=int(cash[name]/(op*100))*100
        while qty and buy_cost(op,qty)>cash[name]:
            qty-=100
        if qty:
            cash[name]-=buy_cost(op,qty)
            shares[name]=qty
            trades[name].append({"side":"BUY","session":days[i],"price":str(op),"shares":qty})
    def sell(name,i,price,reason):
        if shares[name]:
            cash[name]+=sell_value(price,shares[name])
            trades[name].append({"side":"SELL","session":days[i],"price":str(price),
                                 "shares":shares[name],"reason":reason})
            shares[name]=0
    for i,day in enumerate(days):
        op,_,_,cl=prices[day]
        if i==first:
            buy("S0",i)
        if active is not None and active<i and i in exits and shares["S2"]:
            sell("S2",i,op,"EARLY_REDEMPTION_RESEARCH")
            early_in_window=True
        if active is None and i in entries:
            active=i
            window_start={name:cash[name] for name in ("S1","S2")}
            early_in_window=False
            buy("S1",i)
            if i in exits:
                blocked_entries+=1
            else:
                buy("S2",i)
        if active is not None and i-active>=2:
            sell("S1",i,cl,"T_PLUS_2_CLOSE")
            sell("S2",i,cl,"T_PLUS_2_CLOSE")
            if early_in_window:
                delta=(cash["S2"]-window_start["S2"])-(cash["S1"]-window_start["S1"])
                paired.append({"entry":days[active],"baseline_exit":day,
                               "incremental_net_cny":str(delta.quantize(Decimal(".01"))),
                               "false_exit":delta<0})
            active=None
        for name in cash:
            equity[name].append(cash[name]+(sell_value(cl,shares[name]) if shares[name] else 0))
    result={}
    for name,curve in equity.items():
        peak=CAPITAL
        dd=Decimal(0)
        for value in curve:
            peak=max(peak,value);dd=min(dd,value/peak-1)
        result[name]={"net_pnl_cny":str((curve[-1]-CAPITAL).quantize(Decimal(".01"))),
                      "max_drawdown":str(dd),"trades":trades[name],
                      "ending_shares":shares[name],"ending_mark_is_not_fill":True}
    early=[t for t in trades["S2"] if t.get("reason")=="EARLY_REDEMPTION_RESEARCH"]
    return {"accounts":result,"early_exit_count":len(early),"blocked_entries":blocked_entries,
            "mature_early_exit_pairs":paired,"false_exits":sum(p["false_exit"] for p in paired),
            "exit_incremental_pnl_cny":str(Decimal(result["S2"]["net_pnl_cny"])-Decimal(result["S1"]["net_pnl_cny"])),
            "withdrawal_effect_status":"EXPLORATORY" if paired else "NO_MATURE_EXECUTABLE_EARLY_EXIT"}


def run(root=ROOT):
    days=[x.date().isoformat() for x in xc.get_calendar("XSHG").sessions_in_range(START,END)]
    # Include preceding session to compute first available flow.
    extended=[x.date().isoformat() for x in xc.get_calendar("XSHG").sessions_in_range("2026-11-02",END)]
    merged=read(root/MERGED)
    prices=recover_prices(read(root/OUTCOMES),days)
    core,missing=core_events(merged,extended,root)
    paths=sorted((root/"records/national_team_router").glob("*/*.json"))
    routes=[read(p) for p in paths if "2026-11-02"<=p.parent.name<="2026-11-26"]
    entries,excluded=select_entries(routes,core,days)
    exits={};pending=[]
    for day,row in core.items():
        if row["flow"]<0 and row["negative"]>=3:
            i=next_open(days,row["observed"])
            item={"signal_session":day,"known_at":row["observed"].isoformat(),
                  "flow_cny":str(row["flow"]),"negative_funds":row["negative"]}
            if i is None:
                pending.append(item)
            elif i-days.index(day)<=2:
                exits[i]=item
    result=replay(days,prices,entries,exits)
    return {"scope":"ARCHIVED_SOURCE_CLOCK_EXPLORATORY_ETF_OPEN_CLOSE_PROXY",
            "start":START,"end":END,"source_verified_core_days":len(core),
            "missing_or_anomalous":missing,"entries":{days[i]:v for i,v in entries.items()},
            "excluded":excluded,"exit_candidates":{days[i]:v for i,v in exits.items()},
            "pending_exits":pending,"third_party_shadow_used_for_history":False,
            "official_nav_actions_independently_verified":False,
            "trade_authorized":False,**result}


if __name__=="__main__":
    print(json.dumps(run(),ensure_ascii=False,indent=2))
