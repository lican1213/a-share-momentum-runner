"""Second/third stage counterexamples from production; fixtures are synthetic."""
from types import SimpleNamespace
import json
from pathlib import Path
from national_team.akshare_compat import sina_stock_daily,eastmoney_stock_daily
from national_team.v3_exchange_overlay import overlay
from national_team.core_flow_factors import CORE_FOUR

def test_renamed_api_preserves_raw_adjustment_and_old_api_compatibility():
    def call(**kwargs):
        assert kwargs["adjust"]==""
        return kwargs["symbol"]
    def removed(**kwargs):
        raise AssertionError("deprecated API called")
    assert sina_stock_daily(SimpleNamespace(stock_zh_a_hist_sina=call,stock_zh_a_daily=removed),
                            symbol="sh600001",adjust="")=="sh600001"
    assert sina_stock_daily(SimpleNamespace(stock_zh_a_daily=call),symbol="sh600001",adjust="")=="sh600001"
    assert eastmoney_stock_daily(SimpleNamespace(stock_zh_a_hist_em=call,stock_zh_a_hist=removed),
                                 symbol="600001",adjust="")=="600001"

def test_exchange_complete_overlap_no_future_or_partial_override(tmp_path):
    day="2026-11-13"; partial="2026-11-12"; future="2026-11-16"
    stamp="2026-11-16T15:00:00+08:00"; now="2026-11-16T18:00:00+08:00"
    def row(c,seen=stamp):
        return {"shares":100,"shares_first_observed_at":seen,"shares_source_path":"source.json",
                "nav":2,"nav_first_observed_at":seen,"nav_source_path":"source.json"}
    funds={c:row(c) for c in CORE_FOUR}
    d=tmp_path/"2026-11-16";d.mkdir()
    source={"unit":"raw_shares","capture_completed_beijing":stamp,"observations_by_date":{
        day:funds,partial:{c:row(c) for c in CORE_FOUR[:-1]},
        future:{c:row(c,"2026-11-17T09:00:00+08:00") for c in CORE_FOUR}}}
    (d/"1-a1.json").write_text(json.dumps(source))
    legacy={day:{c:90 for c in CORE_FOUR},partial:{c:80 for c in CORE_FOUR}}
    nav={day:{c:{"nav":1.9} for c in CORE_FOUR}}
    s,n,m=overlay(legacy,nav,tmp_path,observed_at=now,index_sessions={day,partial,future})
    assert s[day][CORE_FOUR[0]]==100 and legacy[day][CORE_FOUR[0]]==90
    assert s[partial]==legacy[partial] and future not in s
    assert m["complete_exchange_share_nav_dates"]==[day]
    assert n[day][CORE_FOUR[0]]["published_at"]==stamp
    assert m["external_share_disagreements"][0]["date"]==day
    source["conflicts"]=[{"date":day,"code":CORE_FOUR[0],"field":"shares"}]
    (d/"1-a1.json").write_text(json.dumps(source))
    s,n,m=overlay(legacy,nav,tmp_path,observed_at=now,index_sessions={day,partial,future})
    assert s[day]==legacy[day] and not m["complete_exchange_share_nav_dates"]

def test_workflow_chain_dispatch_does_not_add_fourth_workflow_run():
    root=Path(__file__).resolve().parents[1]/".github/workflows"
    ledger=(root/"national-team-left-outcomes-v5.yml").read_text()
    wiki=(root/"national-team-wiki-sync.yml").read_text()
    assert "gh workflow run national-team-wiki-sync.yml --ref main" in ledger
    assert ledger.index("Archive new dated feedback snapshot") < ledger.index("Request derived Wiki refresh")
    assert "actions: write" in ledger
    assert "National-team V5 future OHLC and three-arm paper accounts" not in wiki
    assert "workflow_dispatch:" in wiki and "schedule:" in wiki


def test_archived_finalized_benchmark_restores_missing_date_without_filling_holiday(tmp_path):
    from national_team.archived_ohlc_v5 import recover
    from national_team.left_entry_v4 import digest
    row={"date":"2026-11-16","open":"4.068","high":"4.075","low":"4.036","close":"4.054"}
    prior={**row,"date":"2026-11-13"}
    source={"first_observed_at":"2026-11-16T18:36:00+08:00",
            "bars_by_symbol":{"510300":[prior,row]},
            "source_url":{"510300":"https://actual.example/"},"source_sha256":{"510300":"original"}}
    d=tmp_path/"2026-11-16";d.mkdir()
    path=d/"43850315658-a1.json"
    def write(source):
        path.write_text(json.dumps({"results":[{"source_new_ohlc":source,
                                                "source_new_ohlc_sha256":digest(source)}]}))
    write(source)
    params={"start":"2026-11-06","cutoff":"2026-11-16","observed_at":"2026-11-16T18:46:00+08:00"}
    out=recover({"bars_by_symbol":{"510300":[prior]}},["510300"],tmp_path,**params)
    assert out["bars_by_symbol"]["510300"]==[prior,row]
    assert out["archived_bar_recovery"]["510300"][0]["source_sha256"]=="original"
    assert "2026-11-14" not in [r["date"] for r in out["bars_by_symbol"]["510300"]]
    write({**source,"first_observed_at":"2026-11-16T14:30:00+08:00"})
    out=recover({"bars_by_symbol":{"510300":[prior]}},["510300"],tmp_path,**params)
    assert out["bars_by_symbol"]["510300"]==[prior]
    write({**source,"first_observed_at":"2026-11-16T19:30:00+08:00"})
    out=recover({"bars_by_symbol":{"510300":[prior]}},["510300"],tmp_path,**params)
    assert out["bars_by_symbol"]["510300"]==[prior]

def test_external_reference_remains_pilot_admission_baseline():
    from national_team.left_entry_v4 import admission
    def summary(wins):
        return {"share_proxy":{"horizons":{"5":{"matured_events":60,"wins":wins},
                "10":{"hit_rate":.46},"20":{"hit_rate":.40}}},
                "coverage_primary":{"raw_signal_days":0}}
    v3={"method":{"codes":list(CORE_FOUR)},"summary":summary(29),
        "external_cache_baseline_summary":summary(32)}
    result=admission(v3)
    assert result["pilot_admitted"] and result["five_day_wins"]==32
    assert result["admission_baseline"]=="INDEPENDENT_EXTERNAL_CACHE"


def test_archive_recovery_preserves_original_source_when_reused(tmp_path):
    from national_team.archived_ohlc_v5 import recover
    from national_team.left_entry_v4 import digest
    row={"date":"2026-11-16","open":"4.068","high":"4.075","low":"4.036","close":"4.054"}
    original={"date":row["date"],"path":"original.json","source_capture_time":"2026-11-16T16:00:00+08:00",
              "source_snapshot_sha256":"original-snapshot","source_url":"https://primary.example",
              "source_sha256":"original-hash"}
    source={"first_observed_at":"2026-11-16T18:30:00+08:00","bars_by_symbol":{"510300":[row]},
            "source_url":{"510300":"https://fallback.example"},"source_sha256":{"510300":"fallback-hash"},
            "archived_bar_recovery":{"510300":[original]}}
    d=tmp_path/"2026-11-16";d.mkdir()
    (d/"2-a1.json").write_text(json.dumps({"results":[{"source_new_ohlc":source,
                                                "source_new_ohlc_sha256":digest(source)}]}))
    out=recover({},["510300"],tmp_path,start="2026-11-06",cutoff="2026-11-16",
                observed_at="2026-11-16T19:00:00+08:00")
    assert out["archived_bar_recovery"]["510300"]==[original]


def test_exp0017_outcomes_installs_preauction_calendar_dependency():
    """Regression: deployment run 44061324220 failed before ledger processing."""
    root = Path(__file__).resolve().parents[1]
    router = (root / ".github/workflows/national-team-event-router-v5.yml").read_text()
    outcomes = (root / ".github/workflows/national-team-left-outcomes-v5.yml").read_text()
    dependency = "'exchange-calendars==4.13.1'"
    assert dependency in router
    assert dependency in outcomes
    assert "tests/test_national_team_event_router_v5.py" in outcomes
