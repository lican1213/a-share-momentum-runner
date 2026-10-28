"""Paired, no-lookahead 5/10/20-day evaluation of frozen ETF-flow signals.

Uses scenario next-session OPEN to horizon-session CLOSE; not actual broker fills.
This is an evaluation primitive, not evidence of a validated strategy.
"""
from __future__ import annotations
from datetime import datetime, time
from zoneinfo import ZoneInfo
from decimal import Decimal, InvalidOperation

HORIZONS=(5,10,20)

def _num(v, name, positive=False):
    try:
        if isinstance(v,bool): raise ValueError()
        x=Decimal(str(v))
    except (ValueError,TypeError,InvalidOperation):
        raise ValueError(f"{name}: invalid value") from None
    if not x.is_finite() or (positive and x<=0):
        raise ValueError(f"{name}: invalid value")
    return x

def _net(buy,sell,fee,slip,stamp):
    return sell*(1-(fee+slip+stamp)/10000)/(buy*(1+(fee+slip)/10000))-1

def evaluate_frozen_event(event,trade_sessions,prices,*,benchmark="510300",
                          commission_bps="3",slippage_bps="5",sell_stamp_bps_stock="5"):
    """Input event: id, first_public_at ISO tz-aware, candidate_symbols list.
    Price rows indexed by stock then session: open,close,entry_blocked,exit_blocked.
    Each result is available only after the full horizon has elapsed.
    """
    event_id=str(event.get("id",""))
    names=event.get("candidate_symbols")
    if not event_id or not isinstance(names,list) or not names or len(set(names))!=len(names):
        raise ValueError("event id and unique frozen stock names required")
    if benchmark in names: raise ValueError("benchmark cannot be stock candidate")
    published=datetime.fromisoformat(str(event["first_public_at"]).replace("Z","+00:00"))
    if published.tzinfo is None: raise ValueError("publication time needs timezone")
    published=published.astimezone(ZoneInfo("Asia/Shanghai"))
    if list(trade_sessions)!=sorted(set(trade_sessions)):
        raise ValueError("exchange session list must be unique sorted")
    # For a source published before the 09:25 CN pre-open cutoff, this
    # session's OPEN may be used; otherwise use the next exchange session.
    # PCF published at 08:30 can therefore enter that day's open, whereas
    # post-close ETF net creations cannot retroactively trade the close.
    local_day = published.date().isoformat()
    today_open_eligible = published.time() <= time(9,25)
    entry_candidates = [i for i,d in enumerate(trade_sessions)
                        if d > local_day or (d == local_day and today_open_eligible)]
    if not entry_candidates:
        return {"event_id":event_id,"status":"ENTRY_NOT_YET_AVAILABLE","results":{}}
    ix=entry_candidates[0]
    entry=trade_sessions[ix]
    fee=_num(commission_bps,"commission"); slip=_num(slippage_bps,"slippage")
    stamp=_num(sell_stamp_bps_stock,"stock stamp")
    if min(fee,slip,stamp)<0:raise ValueError("costs must be nonnegative")
    bench=prices.get(benchmark,{}).get(entry)
    if not bench or bench.get("entry_blocked") is not False:
        return {"event_id":event_id,"status":"BENCHMARK_ENTRY_UNVERIFIED","results":{}}
    b0=_num(bench.get("open"),"benchmark open",positive=True)
    frozen=[]
    for stock in names:
        row=prices.get(stock,{}).get(entry)
        if row is None or row.get("entry_blocked") is not False:
            frozen.append((stock,None))
        else:
            frozen.append((stock,_num(row.get("open"),f"{stock} open",positive=True)))
    out={}
    for h in HORIZONS:
        if ix+h>=len(trade_sessions):
            out[str(h)]={"status":"NOT_MATURED"}
            continue
        end=trade_sessions[ix+h]
        b1=prices.get(benchmark,{}).get(end)
        if not b1 or b1.get("exit_blocked") is not False:
            out[str(h)]={"status":"BENCHMARK_EXIT_UNVERIFIED","exit_session":end}
            continue
        bench_return=_net(b0,_num(b1.get("close"),"benchmark exit",positive=True),fee,slip,Decimal(0))
        values=[]; blocked=[]
        for stock,buy in frozen:
            if buy is None:
                values.append(Decimal(0)) # unfilled allocation remains as cash
                continue
            row=prices.get(stock,{}).get(end)
            if not row or row.get("exit_blocked") is not False:
                blocked.append(stock)
                continue
            values.append(_net(buy,_num(row.get("close"),f"{stock} exit",positive=True),fee,slip,stamp))
        if blocked:
            out[str(h)]={"status":"STOCK_EXIT_UNVERIFIED","exit_session":end,
                          "blocked_stocks":blocked}
            continue
        sr=sum(values,Decimal(0))/len(names)
        out[str(h)]={"status":"COMPUTED_OHLC_PROXY","exit_session":end,
                     "stock_net_return":format(sr,"f"),
                     "etf_net_return":format(bench_return,"f"),
                     "paired_excess_net_return":format(sr-bench_return,"f"),
                     "filled_stock_count":sum(p is not None for _,p in frozen),
                     "unfilled_cash_allocations":sum(p is None for _,p in frozen)}
    return {"event_id":event_id,"first_public_at":published.isoformat(),
            "entry_session":entry,"status":"RESEARCH_PROXY_ONLY",
            "fill_model":"first eligible exchange session open after disclosure; same-day only if public by 09:25 CN; horizon close proxy, never actual orders",
            "cost_assumptions_bps":{"commission_each_side":str(fee),
                                      "slippage_each_side":str(slip),
                                      "stock_sell_stamp":str(stamp)},
            "independent_forward_validation":False,"results":out}
