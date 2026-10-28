"""Tests for normalizing AKShare's already normalized ETF shares."""
import pandas as pd
import pytest

from national_team.live_etf_sources import as_canonical_shares, normalized_day, history_nav


def test_sse_akshare_already_converts_ten_thousand_shares_to_shares():
    # Official SSE website could display 3272988.77 10,000 shares,
    # but AKShare source *ALREADY multiplies by 10000.
    df = pd.DataFrame({
        "基金代码":["510300","510310","510330"],
        "统计日期":["2026-10-22"]*3,
        "基金份额":[32729887700,17115044000,10532949800],
    })
    result=normalized_day(df,"2026-10-22",{"510300","510310","510330"},
                          "akshare.sse.normalized_shares")
    assert result["510300"]=="32729887700"
    assert result["510310"]=="17115044000"
    assert result["510330"]=="10532949800"


def test_szse_is_raw_shares_and_date_is_required():
    df=pd.DataFrame({"基金代码":["159919"],
                     "日期":["2026-10-22"],
                     "基金份额":["23,000,000"]})
    x=normalized_day(df,"2026-10-22",{"159919"},"akshare.szse.raw_shares")
    assert x["159919"]=="23000000"
    assert normalized_day(df,"2026-10-23",{"159919"},"akshare.szse.raw_shares")=={}


def test_duplicate_or_invalid_or_unsupported_units_fail():
    df=pd.DataFrame({"基金代码":["159919","159919"],
                     "日期":["2026-10-22"]*2,
                     "基金份额":[20000000,20000001]})
    with pytest.raises(ValueError,match="duplicate"):
        normalized_day(df,"2026-10-22",{"159919"},"akshare.szse.raw_shares")
    with pytest.raises(ValueError,match="unsupported source"):
        as_canonical_shares(200, "official.sse.ten_thousand_shares")
    with pytest.raises(ValueError,match="nonfinite"):
        as_canonical_shares("NaN","akshare.sse.normalized_shares")


def test_nav_date_must_match_shares_exactly():
    df=pd.DataFrame({"净值日期":["2026-10-21","2026-10-22"],
                     "单位净值":[3.95,4.1]})
    r=history_nav(df,"510300",{"2026-10-22"})
    assert r=={"2026-10-22":"4.1"}


def test_undated_szse_fallback_is_never_backdated_to_exchange_daily_series(tmp_path,monkeypatch):
    from datetime import date
    from national_team.live_etf_sources import collect
    # All unit tests must remain offline, including newer JSON fallbacks.
    import national_team.szse_json as endpoint
    def offline_failure(*args,**kwargs):
        raise ConnectionError('mocked SZSE JSON unavailable')
    monkeypatch.setattr(endpoint,'fetch_one_szse_fund',offline_failure)

    class BlockedDaily:
        def fund_scale_daily_szse(self, **kwargs):
            raise ConnectionError("official historic daily endpoint unavailable")
        def fund_etf_scale_szse(self):
            return pd.DataFrame({"基金代码":["159919"],"基金份额":[10396116676]})
        def fund_etf_scale_sse(self, **kwargs):
            return pd.DataFrame(columns=["基金代码","统计日期","基金份额"])
        def fund_etf_fund_info_em(self, **kwargs):
            return pd.DataFrame(columns=["净值日期","单位净值"])

    path,r=collect(BlockedDaily(),date(2026,10,28),"909001","1",tmp_path)
    assert path.exists()
    assert r["latest_undated_szse_snapshot"]["shares"]=="10396116676"
    assert r["latest_undated_szse_snapshot"]["observation_exchange_trading_date"] is None
    assert r["observations_by_date"]=={}
    assert r["status"]=="ATTEMPTED_NO_COMPLETE_FACTOR"
    assert not r["factor_arithmetic_possible"]
