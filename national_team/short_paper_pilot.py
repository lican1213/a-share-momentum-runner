"""EXP-0005: precommitted one-week national-team short paper pilot.

No broker orders. Daily OHLC-based fills are scenarios, not executable proof.
Freeze must be persisted BEFORE first possible entry. Unavailable data -> no fill.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from datetime import datetime, date, time
from pathlib import Path
from zoneinfo import ZoneInfo

BJ = ZoneInfo("Asia/Shanghai")
ENTRY = "2026-10-30"
FREEZE = "2026-10-29"
VERSION = "NT_SHORT_EXP0005_V1"
RANKS = {
    "S1": ["601825", "600000", "601229", "601166", "600519"],
    "S2": ["600309", "601919", "600660", "601012", "601838"],
}
ACCOUNT = 30000.0
MAX_GROSS = 10000.0
MAX_POSITION = 5000.0
MAX_RISK = 150.0
FEE = 0.0003
SLIP = 0.0005
STAMP = 0.0005
FREEZE_PATH = Path("records/national_team_short_pilot/freeze-20261029.json")


def h256(obj):
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def round_up_tick(x):
    return math.ceil(float(x) * 100.0 - 1e-9) / 100.0


def round_down_tick(x):
    return math.floor(float(x) * 100.0 + 1e-9) / 100.0


def one_way_fee(notional, sell=False, etf=False):
    return max(5.0, notional * FEE) + (notional * STAMP if sell and not etf else 0.0)


def stock_rows(ak, symbol, end):
    raw = ak.stock_zh_a_hist(symbol=symbol, period="daily",
                              start_date="20250101", end_date=end, adjust="")
    return normalize(raw, symbol, "EASTMONEY_STOCK_UNADJUSTED")


def etf_rows(ak, end):
    raw = ak.fund_etf_hist_em(symbol="510300", period="daily",
                               start_date="20250101", end_date=end, adjust="")
    return normalize(raw, "510300", "EASTMONEY_ETF_UNADJUSTED")


def normalize(raw, symbol, source):
    columns = {"日期": "date", "开盘": "open", "最高": "high",
               "最低": "low", "收盘": "close", "成交量": "volume"}
    if not all(k in raw.columns for k in columns):
        raise ValueError(f"{symbol}: daily OHLCV schema incomplete")
    ordered = raw.sort_values("日期")
    out = []
    for _, line in ordered.iterrows():
        bar = {new: (str(line[old])[:10] if new == "date" else float(line[old]))
               for old, new in columns.items()}
        o, h, l, c, v = (bar[k] for k in ("open", "high", "low", "close", "volume"))
        if not all(math.isfinite(x) for x in (o, h, l, c, v)) or min(o,h,l,c)<=0 or v<0 or not (l<=min(o,c)<=max(o,c)<=h):
            raise ValueError(f"{symbol}: invalid OHLCV on {bar['date']}")
        if out and bar["date"] <= out[-1]["date"]:
            raise ValueError(f"{symbol}: nonascending dates")
        out.append(bar)
    return {"source":source, "sha256":h256(out), "bars":out}


def indicators(rows, ref, day=FREEZE):
    b = rows["bars"]
    index = next((i for i, r in enumerate(b) if r["date"] == day), None)
    if index is None or index < 251:
        raise ValueError("at least 250 completed sessions required before freeze")
    base = b[index]
    past = b[index-59:index+1]
    ma20 = sum(x["close"] for x in b[index-19:index+1])/20
    ma60 = sum(x["close"] for x in past)/60
    prior10high = max(x["high"] for x in b[index-10:index])
    prior20vol = sum(x["volume"] for x in b[index-20:index])/20
    rb = ref["bars"]
    ref_index = next((i for i, r in enumerate(rb) if r["date"] == day), None)
    if ref_index is None or ref_index < 20:
        raise ValueError("benchmark reference history missing")
    if rb[ref_index-20]["date"] != b[index-20]["date"]:
        raise ValueError("20-session benchmark date alignment mismatch")
    rel20 = base["close"]/b[index-20]["close"]-rb[ref_index]["close"]/rb[ref_index-20]["close"]
    tr = []
    for j in range(index-13, index+1):
        prev = b[j-1]["close"]
        tr.append(max(b[j]["high"]-b[j]["low"], abs(b[j]["high"]-prev),
                      abs(b[j]["low"]-prev)))
    atr = sum(tr)/14
    eligible = (base["close"] > ma20 and base["close"] > ma60
                and base["close"] >= round_up_tick(prior10high+0.01)
                and rel20 > 0 and prior20vol>0
                and base["volume"] >= 1.2*prior20vol)
    return {"date": day, "close":base["close"], "ma20":ma20, "ma60":ma60,
            "breakout_trigger": round_up_tick(prior10high+0.01),
            "rel20":rel20, "relvol":base["volume"]/prior20vol if prior20vol else None,
            "atr14":atr, "eligible":eligible}


def freeze_candidates(ak, today):
    if today < FREEZE:
        raise ValueError("cannot freeze before protocol day")
    if today > FREEZE:
        raise ValueError("late freeze prohibited; no retrospective stock choices")
    ref = etf_rows(ak, today.replace("-",""))
    name_frame = ak.stock_info_a_code_name()
    names = {str(v["code"]).zfill(6):str(v["name"]) for _,v in name_frame.iterrows()}
    selected = []
    checked = []
    for cohort, symbols in RANKS.items():
        accepted = None
        for code in symbols:
            label = names.get(code)
            if not label:
                raise ValueError(f"{code}: official-list-derived name missing; no skip")
            if "ST" in label.upper() or "退" in label:
                checked.append({"code":code, "cohort":cohort, "result":"EXCLUDED_ST_DELIST"})
                continue
            src = stock_rows(ak, code, today.replace("-",""))
            d = indicators(src, ref)
            risk_max = max(1.5*d["atr14"], 0.02*d["close"])
            one_lot_worst = 100*(risk_max + d["close"]*0.0013)+10
            maxlot_cost = 100*d["close"]*1.02*1.0005+5
            verdict = "ELIGIBLE" if d["eligible"] and one_lot_worst<=MAX_RISK and maxlot_cost<=MAX_POSITION else "NO_BREAKOUT_OR_LOT_RISK"
            checked.append({"code":code, "cohort":cohort, "name":label,
                            "verdict":verdict, "indicators":d,
                            "input_hash":src["sha256"], "source":src["source"]})
            if verdict == "ELIGIBLE":
                accepted = checked[-1]
                break
        if accepted:
            selected.append(accepted)
    return {"kind":"PREENTRY_FREEZE", "version":VERSION,
            "freeze_session":FREEZE, "first_eligible_open":ENTRY,
            "created_at":datetime.now(BJ).isoformat(),
            "ref_hash":ref["sha256"], "ref_source":ref["source"],
            "selected":selected, "checked":checked,
            "initial_account":ACCOUNT, "max_total_notional":MAX_GROSS,
            "max_position":MAX_POSITION,"max_per_trade_risk":MAX_RISK,
            "actual_broker_trades":0,
            "no_guaranteed_execution":True}


def sessions(iso_day, until):
    import exchange_calendars as xc
    cal = xc.get_calendar("XSHG")
    s = cal.sessions_in_range(iso_day, until)
    return [x.strftime("%Y-%m-%d") for x in s]


def find_bar(rows, day):
    return next((b for b in rows["bars"] if b["date"]==day), None)


def minute_bars_to_1450(ak, code, day):
    """Actual one-minute rows up to and INCLUDING 14:50, never 15:00 OHLC."""
    start=f"{day} 09:30:00"
    end=f"{day} 14:51:00"
    if code == "510300":
        df=ak.fund_etf_hist_min_em(symbol=code,period="1",start_date=start,end_date=end,adjust="")
    else:
        df=ak.stock_zh_a_hist_min_em(symbol=code, period="1",start_date=start,end_date=end,adjust="")
    required=("时间","开盘","最高","最低","收盘")
    if not all(k in df.columns for k in required):
        raise ValueError("missing minute OHLC schema")
    out=[]
    for _,line in df.iterrows():
        stamp=str(line["时间"])[:16]
        if not (f"{day} 09:30"<=stamp<=f"{day} 14:50"):
            continue
        bar={"minute":stamp, "open":float(line["开盘"]),"high":float(line["最高"]),
             "low":float(line["最低"]),"close":float(line["收盘"])}
        if not (0<bar["low"]<=min(bar["open"],bar["close"])<=max(bar["open"],bar["close"])<=bar["high"]):
            raise ValueError("inconsistent minute high/low")
        out.append(bar)
    if not out or out[-1]["minute"]!=f"{day} 14:50":
        raise ValueError(f"{code}: missing final 14:50 one-minute OHLC")
    if len({x["minute"] for x in out})!=len(out):
        raise ValueError("duplicate minute bars")
    return {"bars":out,"source":"EASTMONEY_1MIN_UP_TO_1450",
            "raw_sha256":h256(out)}


def minute_exit_1450(ak, code, day):
    m=minute_bars_to_1450(ak,code,day)
    return {"price":m["bars"][-1]["open"],"source":m["source"],
            "hash":m["raw_sha256"]}


def minute_order_outcome(minute_snapshot, stop, target):
    """Conservative first touch; if same bar both touch, STOP precedes TARGET."""
    for b in minute_snapshot["bars"]:
        if b["open"]<=stop: return "GAP_STOP",b["open"]
        if b["low"]<=stop:return "STOP_FIRST",stop
        if b["open"]>=target:return "TARGET_GAP",b["open"]
        if b["high"]>=target:return "TARGET",target
    return "T_PLUS_3_1450_TIME",minute_snapshot["bars"][-1]["open"]

def portfolio(ak, frozen, today):
    if today < ENTRY:
        return {"status":"ENTRY_NOT_YET_AVAILABLE","records":[]}
    ss = sessions(ENTRY, today)
    if not ss or ss[0]!=ENTRY:
        return {"status":"ENTRY_SESSION_NOT_VERIFIED","records":[]}
    bsrc = etf_rows(ak, today.replace("-",""))
    refentry = find_bar(bsrc, ENTRY)
    if refentry is None:
        return {"status":"BENCHMARK_ENTRY_UNAVAILABLE","records":[]}
    recs = []
    invested=0.0
    for selection in frozen["selected"]:
        code=selection["code"]
        hist = stock_rows(ak, code, today.replace("-",""))
        prior=find_bar(hist, FREEZE)
        entr=find_bar(hist, ENTRY)
        d=selection["indicators"]
        rec={"signal_id":f"EXP0005-{code}-{ENTRY}","code":code,
             "name":selection["name"],"cohort":selection["cohort"],
             "entry_session":ENTRY,"signal_frozen_at":frozen["created_at"],
             "freeze_input_sha":selection["input_hash"],
             "evaluation_source_sha":hist["sha256"],
             "simulation_only":True}
        if prior is None or abs(prior["close"]-d["close"])>0.000001:
            rec["status"]="DATA_REVISION_BLOCKED";recs.append(rec);continue
        if entr is None:
            rec["status"]="ENTRY_OPEN_NOT_YET_VERIFIED";recs.append(rec);continue
        limit_gap = entr["open"]/prior["close"]-1
        if entr["volume"]<=0 or abs(entr["high"]-entr["low"])<0.0000001 or limit_gap>=0.098:
            rec["status"]="ENTRY_EXECUTION_BLOCKED";recs.append(rec);continue
        if not (entr["open"]>=d["breakout_trigger"] and 0<=limit_gap<=0.02):
            rec["status"]="ENTRY_PRICE_GATE_REJECTED";recs.append(rec);continue
        entry_px=round_up_tick(entr["open"]*(1+SLIP))
        rps=max(1.5*d["atr14"],0.02*entry_px)
        stop=round_down_tick(entry_px-rps)
        target=round_up_tick(entry_px+2*(entry_px-stop))
        candidates=[]
        for n in range(100,1+int(MAX_POSITION/entry_px),100):
            gross=n*entry_px
            if gross>MAX_POSITION or invested+gross>MAX_GROSS:continue
            risk = n*(entry_px-stop)+one_way_fee(gross)+one_way_fee(n*stop,True)+n*(entry_px+stop)*SLIP
            if risk<=MAX_RISK:candidates.append((n,risk))
        if not candidates:
            rec["status"]="LOT_RISK_TOO_LARGE";recs.append(rec);continue
        qty,risk = candidates[-1]
        invested+=qty*entry_px
        rec.update(status="PAPER_ENTRY_OHLC_SCENARIO", entry_price=entry_px, initial_stop=stop,
                   initial_target=target, qty=qty, estimated_max_initial_risk=risk,
                   initial_notional=qty*entry_px,entry_date=ENTRY)
        if len(ss)<2:
            rec["status"]="PAPER_ENTRY_PENDING_T_PLUS_1"
            recs.append(rec);continue
        # T+1 sellable; whenever high and low cross same day, stop wins.
        for d_index in range(1,min(len(ss),4)):
            day=ss[d_index]
            bar=find_bar(hist,day)
            if bar is None:
                rec["status"]="EXIT_DATA_MISSING";rec["blocked_day"]=day;break
            if bar["volume"]<=0 or abs(bar["high"]-bar["low"])<1e-9:
                rec["status"]="EXIT_BLOCKED_OR_ONE_PRICE";rec["blocked_day"]=day;break
            reason=None;px=None
            if d_index==3:
                try:
                    minute=minute_bars_to_1450(ak,code,day)
                    rec["time_exit_minute_source"]={"source":minute["source"],
                                                   "hash":minute["raw_sha256"]}
                    reason,px=minute_order_outcome(minute,stop,target)
                except Exception as ex:
                    rec["status"]="TIME_EXIT_1450_UNVERIFIED"
                    rec["error"]=f"{type(ex).__name__}:{str(ex)[:120]}"
                    break
            elif bar["open"] <= stop:
                reason="GAP_STOP";px=bar["open"]
            elif bar["low"] <= stop:
                reason="STOP_FIRST";px=stop
            elif bar["open"] >= target:
                reason="TARGET_GAP";px=bar["open"]
            elif bar["high"] >= target:
                reason="TARGET";px=target
            if reason is None:
                rec["status"]="PAPER_OPEN_EXIT_PENDING";continue
            px=round_down_tick(px*(1-SLIP))
            proceeds=qty*px
            paid=qty*entry_px
            fees=one_way_fee(paid)+one_way_fee(proceeds,sell=True)
            pnl=proceeds-paid-fees
            rec.update(status="PAPER_EXIT_OHLC_SCENARIO",exit_reason=reason,
                       exit_date=day,exit_price=px,net_pnl=pnl,net_r=pnl/risk,
                       assumed_fees=fees,execution_not_confirmed=True)
            break
        recs.append(rec)
    # S0 ETF is evaluated on the identical open-to-T+3 14:50 window;
    # never substitute the 15:00 daily close for 14:50.
    benchmark={"status":"NOT_MATURED"}
    if len(ss)>=4:
        exitday=ss[3]
        try:
            etf_m=minute_exit_1450(ak,"510300",exitday)
            etf_buy=round_up_tick(refentry["open"]*(1+SLIP))
            etf_sell=round_down_tick(etf_m["price"]*(1-SLIP))
            n=math.floor(MAX_GROSS/(etf_buy*100))*100
            if n<100:
                benchmark={"status":"ETF_LOT_UNAFFORDABLE"}
            else:
                paid=etf_buy*n;received=etf_sell*n
                charges=one_way_fee(paid,etf=True)+one_way_fee(received,sell=True,etf=True)
                benchmark={"status":"S0_ETF_1450_OHLC_SCENARIO","entry_date":ENTRY,
                           "exit_date":exitday,"quantity":n,
                           "buy_price":etf_buy,"exit_price":etf_sell,
                           "costs":charges,"net_pnl":received-paid-charges,
                           "source":etf_m}
        except Exception as ex:
            benchmark={"status":"BENCHMARK_EXIT_1450_UNVERIFIED",
                       "error":f"{type(ex).__name__}:{str(ex)[:160]}"}
    nonfilled={"ENTRY_EXECUTION_BLOCKED","ENTRY_PRICE_GATE_REJECTED",
               "LOT_RISK_TOO_LARGE"}
    final_trade_states={"PAPER_EXIT_OHLC_SCENARIO"}|nonfilled
    matured=(len(ss)>=4 and all(r["status"] in final_trade_states for r in recs)
             and benchmark.get("status")=="S0_ETF_1450_OHLC_SCENARIO")
    if matured:
        stocks_net=sum(r.get("net_pnl",0.0) for r in recs)
        benchmark_net=benchmark["net_pnl"]
        paired={"status":"MATURED_OHLC_SCENARIO_NOT_BROKER_PNL",
                "stock_strategy_net_pnl_cny":stocks_net,
                "S0_etf_net_pnl_cny":benchmark_net,
                "stock_strategy_minus_S0_cny":stocks_net-benchmark_net,
                "stock_account_return":stocks_net/ACCOUNT,
                "S0_account_return":benchmark_net/ACCOUNT,
                "real_trades_confirmed":0}
    else:
        paired={"status":"NOT_MATURED_OR_EXIT_UNVERIFIED","reason":
                "open exit, missing OHLC or minute 14:50, or calendar insufficient"}
    return {"status":"PAPER_OHLC_SCENARIOS_ONLY","records":recs,
            "cash_initial":ACCOUNT,"cash_unallocated_at_entry":ACCOUNT-invested,
            "initial_gross_invested":invested,"benchmark_etf":"510300",
            "benchmark_entry_open":refentry["open"],
            "S0_benchmark":benchmark, "paired_scenario":paired}


def selftest():
    assert round_up_tick(9.121)==9.13 and round_down_tick(9.129)==9.12
    assert one_way_fee(3000)==5.0 and one_way_fee(3000,True)>5
    assert h256({"a":1})==h256({"a":1})
    assert len(RANKS["S1"])==5 and len(RANKS["S2"])==5
    print("PAPER_PILOT_UNIT_SMOKE_PASS")


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--out",default="records/national_team_short_pilot")
    args=ap.parse_args()
    if args.selftest:return selftest()
    now=datetime.now(BJ)
    rid=os.getenv("GITHUB_RUN_ID","local")
    att=os.getenv("GITHUB_RUN_ATTEMPT","1")
    base=Path(args.out)
    output=base/now.date().isoformat()/f"{rid}-a{att}.json"
    if output.exists():
        raise FileExistsError(str(output))
    output.parent.mkdir(parents=True,exist_ok=True)
    record={"version":VERSION,"captured_at":now.isoformat(),
            "github_run_id":rid,"github_sha":os.getenv("GITHUB_SHA"),
            "experiment":"EXP-0005", "real_broker_trades":0,"errors":[]}
    try:
        import akshare as ak
        import exchange_calendars
        record["versions"]={"akshare":getattr(ak,"__version__","unknown"),
                            "exchange_calendars":getattr(exchange_calendars,"__version__","unknown")}
        if now.date().isoformat()==FREEZE and now.time()>=time(17,30) and not FREEZE_PATH.exists():
            frozen=freeze_candidates(ak,now.date().isoformat())
            FREEZE_PATH.parent.mkdir(parents=True,exist_ok=True)
            FREEZE_PATH.write_text(json.dumps(frozen,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
            record.update(status="PREENTRY_FROZEN",freeze_path=str(FREEZE_PATH),
                          selected_count=len(frozen["selected"]),
                          freeze_hash=h256(frozen))
        elif FREEZE_PATH.exists():
            frozen=json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
            record["freeze_hash"]=h256(frozen)
            record["result"]=portfolio(ak,frozen,now.date().isoformat())
            record["status"]=record["result"]["status"]
        else:
            record["status"]="FREEZE_NOT_YET_READY_OR_MISSED"
    except Exception as exc:
        record["status"]="PAPER_PILOT_UNAVAILABLE"
        record["errors"].append(f"{type(exc).__name__}: {str(exc)[:320]}")
    output.write_text(json.dumps(record,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":record["status"],"path":str(output),
                      "error_count":len(record["errors"])},ensure_ascii=False))

if __name__=="__main__":
    main()
