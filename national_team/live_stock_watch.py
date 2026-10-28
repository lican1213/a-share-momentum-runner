"""Live CSI300-index-proxy stock watchlist after official ETF share collection.

PIT semantics: event is first available after the latest required data capture,
never on a historical exchange date just because a provider can query history.
ETF-specific PCF and investor identities are NOT supplied by this module.
"""
from __future__ import annotations
import argparse,hashlib,json,os
from pathlib import Path
from datetime import datetime,date,timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo
from national_team.index_proxy import validate_index_weights,partial_flow_to_stocks

BEIJING=ZoneInfo("Asia/Shanghai")
WEIGHTS_SOURCE="https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/file/autofile/closeweight/000300closeweight.xls"
HIST_EASTMONEY="https://quote.eastmoney.com/"
HIST_SINA="https://finance.sina.com.cn/realstock/company/"

def summarize_stock_history(frame,code,event_date,source,first_observed_at,index_return=None):
    """Exactly 20 past trading sessions in CNY amount; no following-date rows."""
    if "日期" in frame.columns:
        date_col="日期"; amount_col="成交额"; close_col="收盘"
    else:
        date_col="date"; amount_col="amount"; close_col="close"
    if not all(c in frame.columns for c in (date_col,amount_col,close_col)):
        raise ValueError("unknown OHLC amount columns")
    selected=frame.copy()
    selected["parsed_day"]=selected[date_col].astype(str).str[:10]
    selected=selected[selected["parsed_day"]<=event_date].sort_values("parsed_day")
    if selected["parsed_day"].duplicated().any():
        raise ValueError("duplicate share trading date in OHLC")
    if len(selected)<21:
        raise ValueError("fewer than 21 days of stock history")
    last=selected.tail(21)
    if last.iloc[-1]["parsed_day"]!=event_date:
        raise ValueError("stock close and ETF funding event dates differ")
    amounts=[Decimal(str(v)) for v in last[amount_col].tail(20)]
    closes=[Decimal(str(v)) for v in last[close_col]]
    if any((not x.is_finite() or x<=0) for x in amounts+closes):
        raise ValueError("invalid price or turnover")
    adv=sum(amounts,Decimal(0))/20
    ret=closes[-1]/closes[0]-1
    strength=ret-index_return if index_return is not None else None
    return {"adv20_cny":format(adv,"f"),"relative_strength20":format(strength,"f") if strength is not None else None,
            "data_date":event_date,"first_observed_at":first_observed_at,
            "source_url":HIST_EASTMONEY if source=="EASTMONEY" else HIST_SINA,
            "stock_close20_return":format(ret,"f"),
            "source":source}

def index_20_return(ak,asof):
    df=ak.stock_zh_index_daily(symbol="sh000300")
    if "date" not in df.columns or "close" not in df.columns:
        raise ValueError("index quote schema invalid")
    rows=df.copy()
    rows["day"]=rows["date"].astype(str).str[:10]
    rows=rows[rows["day"]<=asof].sort_values("day")
    if len(rows)<21 or rows.iloc[-1]["day"]!=asof:
        raise ValueError("CSI300 index close not yet available for funding event day")
    close=[Decimal(str(v)) for v in rows.tail(21)["close"]]
    if any(x<=0 or not x.is_finite() for x in close):
        raise ValueError("CSI300 invalid close")
    return close[-1]/close[0]-1

def collect(ak,etf_record,out_root,max_stocks=30):
    if not 1<=max_stocks<=120:
        raise ValueError("max stocks must be 1..120")
    now=datetime.now(BEIJING)
    raw=json.loads(Path(etf_record).read_text(encoding="utf-8"))
    source_session=(raw.get("funding_event") or {}).get("latest_available_trading_day")
    if not source_session:
        part=raw.get("partial_SSE_three_only")
        if part:source_session=part["period"][-1]
    if not source_session:
        raise ValueError("no dated ETF funding event available; cannot select stocks")
    out={"schema":1,"run_id":raw.get("run_id"),"run_attempt":raw.get("run_attempt"),
         "collector_capture_time":now.isoformat(),"etf_evidence_path":str(etf_record),
         "etf_run_status":raw.get("status"),"funding_date":source_session,
         "event_first_public_no_earlier_than":None,
         "index_source":WEIGHTS_SOURCE,"kind":"CSI300_INDEX_PROXY_NOT_ETF_PCF",
         "errors":[],"stock_errors":{},"raw_input_hashes":{},
         "no_broker_orders":True,"no_assertion_about_huijin_stock_buying":True}
    fund=raw.get("funding_event") or {}
    if not fund.get("partial_funding") and not fund.get("four_etf_factor") and not raw.get("partial_SSE_three_only"):
        raise ValueError("no paired dated shares and NAV; cannot map investment exposure")
    try:
        df=ak.index_stock_cons_weight_csindex(symbol="000300")
        stamp=datetime.now(BEIJING).isoformat()
        weights=validate_index_weights(df,stamp)
        out["index_weight"]=weights
        out["raw_input_hashes"]["CSINDEX_WEIGHTS"]=hashlib.sha256(df.to_csv(index=False).encode()).hexdigest()
    except Exception as exc:
        out["errors"].append(f"CSI300_WEIGHT:{type(exc).__name__}:{str(exc)[:240]}")
        out["status"]="NO_RELIABLE_INDEX_WEIGHTS"
        return out

    try:
        ret=index_20_return(ak,source_session)
        out["index_ret20"]=format(ret,"f")
    except Exception as exc:
        ret=None
        out["errors"].append(f"CSI300_INDEX_RETURN:{type(exc).__name__}:{str(exc)[:180]}")
    ordered=sorted(weights["weights"],key=lambda c:Decimal(weights["weights"][c]),reverse=True)
    pool=ordered[:max_stocks]
    out["candidate_pool_pre_filter"]=pool
    out["pool_weight_coverage"]=format(sum((Decimal(weights["weights"][c]) for c in pool),Decimal(0)),"f")
    out["pool_preselection_rule"]="largest CSI300 benchmark weights BEFORE stock liquidity; not all 300"
    sampled={}
    start=(date.fromisoformat(source_session)-timedelta(days=90)).strftime("%Y%m%d")
    end=source_session.replace("-","")
    for code in pool:
        data=None
        for label in ("EASTMONEY","SINA"):
            try:
                if label=="EASTMONEY":
                    data=ak.stock_zh_a_hist(symbol=code,period="daily",start_date=start,end_date=end,adjust="")
                else:
                    prefix="sh" if code.startswith(("6","9")) else "sz"
                    data=ak.stock_zh_a_daily(symbol=prefix+code,start_date=start,end_date=end,adjust="")
                if data is None or len(data)==0:raise ValueError("empty daily OHLC")
                stock_time=datetime.now(BEIJING).isoformat()
                sample=summarize_stock_history(data,code,source_session,label,stock_time,ret)
                sampled[code]=sample
                out["raw_input_hashes"][f"STOCK:{code}:{label}"]=hashlib.sha256(
                    data.to_csv(index=False).encode()).hexdigest()
                break
            except Exception as exc:
                out["stock_errors"][f"{code}:{label}"]=f"{type(exc).__name__}:{str(exc)[:150]}"
    out["stock_snapshots"]=sampled
    latest=datetime.now(BEIJING).isoformat()
    out["event_first_public_no_earlier_than"]=latest
    ranking=partial_flow_to_stocks(raw,weights,sampled,top_n=10)
    ranking["first_possible_ranking_time"]=latest
    out["research_ranking"]=ranking
    out["status"]=ranking["status"]
    return out

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--source",required=True)
    parser.add_argument("--out",default="records/national_team_watch")
    parser.add_argument("--max-stocks",type=int,default=30)
    args=parser.parse_args()
    src=Path(args.source)
    raw=json.loads(src.read_text(encoding="utf-8"))
    run=str(raw.get("run_id") or os.environ.get("GITHUB_RUN_ID","local"))
    attempt=str(raw.get("run_attempt") or os.environ.get("GITHUB_RUN_ATTEMPT","1"))
    target=Path(args.out)/raw["asof_requested"]/f"{run}-a{attempt}.json"
    if target.exists():raise FileExistsError(f"refuse to rewrite old evidence: {target}")
    target.parent.mkdir(parents=True,exist_ok=True)
    try:
        import akshare as ak
        result=collect(ak,src,Path(args.out),max_stocks=args.max_stocks)
    except Exception as exc:
        result={"status":"WATCHLIST_BUILD_UNAVAILABLE","errors":[f"{type(exc).__name__}:{str(exc)[:300]}"],
                "input_etf_record":str(src),"capture_time":datetime.now(BEIJING).isoformat(),
                "no_broker_orders":True}
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"stock_status":result["status"],"records":str(target),
                      "scanned":len(result.get("stock_snapshots",{})),
                      "errors":len(result.get("errors",[]))},ensure_ascii=False))

if __name__=="__main__":
    main()
