"""Synthetic index weights and stock-history tests, no unearned alpha claims."""
from datetime import datetime
from decimal import Decimal
import pandas as pd
import pytest
from national_team.index_proxy import validate_index_weights,partial_flow_to_stocks
from national_team.live_stock_watch import summarize_stock_history

CAP="2026-10-28T21:00:00+08:00"

def weights_frame(n=300):
    return pd.DataFrame({"日期":["2026-10-20"]*n,
        "成分券代码":[f"{600000+i:06d}" for i in range(n)],
        "权重":[100/n]*n})

def test_100_percent_index_weight_not_fraction_divided_twice():
    w=validate_index_weights(weights_frame(),CAP)
    assert w["weight_count"]==300
    assert abs(Decimal(w["total_weight"])-1)<Decimal(".000001")
    assert abs(Decimal(w["weights"]["600000"])-Decimal("0.0033333333333333333"))<Decimal(".0000001")
    assert w["kind"].endswith("NOT_ETF_PCF")

def test_duplicate_or_future_weights_rejected():
    df=weights_frame()
    df.loc[0,"成分券代码"]=df.loc[1,"成分券代码"]
    with pytest.raises(ValueError,match="duplicate"):
        validate_index_weights(df,CAP)
    df=weights_frame()
    df["日期"]="2026-10-29"
    with pytest.raises(ValueError,match="future"):
        validate_index_weights(df,CAP)

def test_partial_three_fund_flow_uses_only_known_etfs():
    w=validate_index_weights(weights_frame(),CAP)
    raw={"capture_completed_beijing":CAP,
         "funding_event":{"partial_funding":{
             "per_fund_proxy_cny":{"510300":"10000000","510310":"-3000000","510330":"4000000"}}}}
    rows={"600000":{"adv20_cny":"20000000","source_url":"https://example.org/stock",
                     "data_date":"2026-10-27","first_observed_at":CAP}}
    result=partial_flow_to_stocks(raw,w,rows)
    assert result["missing_funds"]==["159919"]
    assert result["data_scope"]=="PARTIAL_SSE_THREE_EXCLUDES_159919"
    assert result["ranked_from_n_stocks"]==1
    assert result["candidates"][0]["implied_index_exposure_cny"]!="0"
    assert result["not_actual_ETF_PCF"] is True
    assert result["not_investor_identity"] is True

def test_stock_history_requires_21_trading_days_through_exact_event_date():
    dates=pd.date_range("2026-09-28",periods=21,freq="B")
    df=pd.DataFrame({"日期":dates.strftime("%Y-%m-%d"),"成交额":[20000000]*21,
                     "收盘":[10+i*.02 for i in range(21)]})
    asof=dates[-1].date().isoformat()
    z=summarize_stock_history(df,"600000",asof,"EASTMONEY",CAP,Decimal("0.01"))
    assert Decimal(z["adv20_cny"])==20000000
    assert z["data_date"]==asof
    with pytest.raises(ValueError,match="differ"):
        summarize_stock_history(df,"600000",(dates[-1]+pd.Timedelta(days=1)).date().isoformat(),
                                "EASTMONEY",CAP)


def test_current_akshare_source_names_and_exact_day_stock_watch(monkeypatch,tmp_path):
    import json
    from types import SimpleNamespace
    from national_team.live_stock_watch import collect
    from national_team.akshare_compat import exchange_nav_history
    from national_team.live_etf_sources import history_nav
    day="2026-11-13"
    days=pd.bdate_range(end=day,periods=21)
    frame=pd.DataFrame({"date":days,"close":[10]*21,"amount":[20000000]*21})
    weights=weights_frame()
    weight_code=weights.iloc[0]["成分券代码"]
    nav=pd.DataFrame({"净值日期":[day],"单位净值":[4.2]})
    seen=[]
    def stock(**kwargs):
        seen.append(kwargs)
        return frame
    ak=SimpleNamespace(index_stock_cons_weight_csindex=lambda **kw:weights,
                       index_zh_daily_sina=lambda **kw:frame,
                       stock_zh_a_hist_sina=stock,
                       fund_exchange_nav_hist_em=lambda **kw:nav)
    assert history_nav(exchange_nav_history(ak,fund="510300",start_date="20261113",end_date="20261113"),
                       "510300",{day})=={day:"4.2"}
    raw={"capture_completed_beijing":"2026-11-16T16:00:00+08:00",
         "funding_event":{"latest_available_trading_day":day,
               "four_etf_factor":{"trade_date":"2026-11-12",
                  "per_etf_daily_flow_proxy_cny":{"510300":"100"}}}}
    path=tmp_path/"merged.json"
    path.write_text(json.dumps(raw))
    out=collect(ak,path,tmp_path,max_stocks=1)
    assert len(seen)==1 and len(out["stock_snapshots"])==1
    assert out["stock_snapshots"][weight_code]["data_date"]==day
    assert out["status"]=="STOCK_LIQUIDITY_READY_V3_PROXY_ONLY"
    assert out["research_ranking"]["source_flow_date"]=="2026-11-12"
    assert not out["research_ranking"]["candidates"]


def test_official_weight_timeout_reuses_only_bounded_original_archive(tmp_path):
    import json
    from datetime import datetime
    from types import SimpleNamespace
    from national_team.live_stock_watch import archived_weights,collect
    day="2026-11-13"
    now=datetime.fromisoformat("2026-11-16T20:00:00+08:00")
    weights=validate_index_weights(weights_frame().assign(日期="2026-10-30"),"2026-11-13T16:00:00+08:00")
    root=tmp_path/"watch"; archive=root/"2026-11-13";archive.mkdir(parents=True)
    path=archive/"1-a1.json"
    record={"index_weight":weights,"raw_input_hashes":{"CSINDEX_WEIGHTS":"a"*64}}
    path.write_text(json.dumps(record))
    found=archived_weights(root,day,now)
    assert found[0]==weights and found[1]=="a"*64
    assert found[2]["original_first_observed_at"]==weights["first_observed_at"]
    assert archived_weights(root,"2026-12-15",datetime.fromisoformat("2026-12-15T20:00:00+08:00")) is None
    record["index_weight_source_mode"]="ARCHIVED_MONTHLY_PROXY";path.write_text(json.dumps(record))
    assert archived_weights(root,day,now) is None
    record.pop("index_weight_source_mode");path.write_text(json.dumps(record))
    def fail(**kw):
        raise TimeoutError("simulated CSI timeout")
    frame=pd.DataFrame({"date":pd.bdate_range(end=day,periods=21),"close":[10]*21,"amount":[20000000]*21})
    ak=SimpleNamespace(index_stock_cons_weight_csindex=fail,index_zh_daily_sina=lambda **kw:frame,
                       stock_zh_a_hist_sina=lambda **kw:frame)
    src=tmp_path/"merged.json"
    src.write_text(json.dumps({"capture_completed_beijing":"2026-11-16T16:00:00+08:00",
        "funding_event":{"latest_available_trading_day":day,"four_etf_factor":{"trade_date":day,
                         "per_etf_daily_flow_proxy_cny":{"510300":"100"}}}}))
    # Freeze the clock only for the synthetic archived weight age check.
    import national_team.live_stock_watch as watch
    from unittest.mock import patch
    with patch.object(watch,"archived_weights",return_value=found):
        out=collect(ak,src,root,max_stocks=1)
    assert out["index_weight_source_mode"]=="ARCHIVED_MONTHLY_PROXY"
    assert len(out["stock_snapshots"])==1
    assert out["index_weight"]["first_observed_at"]==weights["first_observed_at"]
    assert out["errors"][0].startswith("CSI300_WEIGHT:TimeoutError")
