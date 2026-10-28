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
