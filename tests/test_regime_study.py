"""No-network H01 point-in-time validation; synthetic prices are NOT performance."""
from datetime import date
import pandas as pd

from market_context import historical_index_regimes
from regime_study import regime_study

def test_index_regime_never_uses_future_bars():
    dates=pd.bdate_range(end="2026-10-28",periods=100)
    raw=pd.DataFrame({"date":dates,"close":[100+i for i in range(100)]})
    first=historical_index_regimes(raw,date(2026,10,28))
    old_day=str(dates[-2].date())
    mutated=raw.copy()
    mutated.loc[99,"close"]=10000000
    second=historical_index_regimes(mutated,date(2026,10,28))
    assert first[old_day]==second[old_day]
    future=pd.concat([raw,pd.DataFrame({"date":[pd.Timestamp("2026-10-29")],"close":[999999]})],ignore_index=True)
    assert first==historical_index_regimes(future,date(2026,10,28))

def test_regime_study_is_research_only():
    context={"historical_regimes_by_index":{
      "CSI300":{"2026-10-27":{"above_ma20":True,"above_ma60":True},
                "2026-10-28":{"above_ma20":False,"above_ma60":False}},
      "CSI1000":{"2026-10-27":{"above_ma20":True,"above_ma60":True},
                "2026-10-28":{"above_ma20":True,"above_ma60":True}},
    }}
    trades=[
      {"signal_date":"2026-10-27","net_return":0.02},
      {"signal_date":"2026-10-28","net_return":-0.03},
      {"signal_date":"2026-10-26","net_return":-0.02},
      {"signal_date":"2026-10-27","net_return":None},
    ]
    result=regime_study(trades,context)
    assert result["by_regime"]["pass"]["n"]==1
    assert result["by_regime"]["reject"]["n"]==1
    assert result["by_regime"]["missing"]["n"]==1
    assert result["coverage"]["closed_total"]==3
    assert result["retrospective_sample_only"] is True
    assert result["eligible_for_live_trading"] is False
