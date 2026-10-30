"""Read-only readiness probe must never create a trade or leak an unfinished session."""
from datetime import datetime
from zoneinfo import ZoneInfo
from national_team import short_probe as p
from national_team import short_ab_engine as x

BJ=ZoneInfo("Asia/Shanghai")
def t(value):return datetime.fromisoformat(value).replace(tzinfo=BJ)

def test_before_stock_close_probe_only_yesterday(monkeypatch):
    monkeypatch.setattr(x,"calendar_sessions",lambda a,b:["2026-10-29"])
    monkeypatch.setattr(x,"source_flow",lambda now:{"day":"2026-10-28"})
    monkeypatch.setattr(x,"strategy_snapshot",lambda now:{"path":"V2"})
    def no_market(*args):raise ConnectionError("read only source unavailable")
    monkeypatch.setattr(x,"prices",no_market)
    out=p.read_only_probe(object(),t("2026-10-30T15:00:00"))
    assert out["asof_session"]=="2026-10-29"
    assert out["status"]=="DIAGNOSTIC_ONLY_NO_FREEZE_NO_ORDER"
    assert out["real_broker_orders"]==0 and out["paper_positions_created"]==0
    assert out["candidates"]==[] and "BENCHMARK:" in out["warnings"][-1]

def test_after_stock_close_probe_only_today_and_source_missing_is_reported(monkeypatch):
    monkeypatch.setattr(x,"calendar_sessions",lambda a,b:["2026-10-30"])
    monkeypatch.setattr(x,"source_flow",lambda now:(_ for _ in ()).throw(ValueError("fund source blocked")))
    monkeypatch.setattr(x,"strategy_snapshot",lambda now:{"path":"V2"})
    monkeypatch.setattr(x,"prices",lambda ak,code,day:{"bars":[{"date":day,"close":4.}],"raw_sha256":"raw"})
    class Names:
        def iterrows(self):return iter([])
    class FakeAK:
        def stock_info_a_code_name(self):return Names()
    monkeypatch.setattr(x,"minute_rows",lambda *args,**kwargs:{"sha256":"one-min","bars":[1,2]})
    out=p.read_only_probe(FakeAK(),t("2026-10-30T16:40:00"))
    assert out["asof_session"]=="2026-10-30"
    assert out["candidate_pool"]==[code for _,code in x.RANK_ORDER]
    assert len(out["candidates"])==10
    assert out["groups"]["B"]["indicative_eligible"]==0
    assert all(row["status"]=="UNVERIFIED" for row in out["candidates"])
    assert out["minute_source_checks"]["510300"]["ok"]
    assert "FOUR_ETF:" in out["warnings"][0]
    assert "selected" not in out and "signal_sha256" not in out

def test_stock_quote_probe_still_checks_stocks_when_510300_stale(monkeypatch):
    from national_team import short_ab_engine as x
    monkeypatch.setattr(x,"calendar_sessions",lambda a,b:["2026-10-30"])
    monkeypatch.setattr(x,"source_flow",lambda now:{"day":"2026-10-29"})
    monkeypatch.setattr(x,"strategy_snapshot",lambda now:{"path":"V2"})
    monkeypatch.setattr(x,"stock_names",lambda ak:({code:"SAFE" for _,code in x.RANK_ORDER},"MOCK_SSE"))
    def price(ak,code,day):
        if code=="510300":raise ValueError("ETF_SOURCE_STALE")
        return {"bars":[{"date":day,"close":10.}],"raw_sha256":"stocks","kind":"SINA_TEST"}
    monkeypatch.setattr(x,"prices",price)
    monkeypatch.setattr(x,"minute_rows",lambda *a,**k:{"bars":[1],"sha256":"minute"})
    result=p.read_only_probe(object(),t("2026-10-30T16:40:00"))
    assert result["groups"]["A2"]["data_verified"]==10
    assert result["groups"]["B"]["indicative_eligible"]==0
    assert all(row["status"]=="DAILY_STOCK_VERIFIED_BENCHMARK_MISSING"
               for row in result["candidates"])
    assert "BENCHMARK:" in result["warnings"][0]
    assert result["paper_positions_created"]==0
