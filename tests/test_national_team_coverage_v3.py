"""Adversarial fixtures for EXP-0010. All values below are SYNTHETIC."""
import csv
import json
from datetime import date, timedelta

import pytest

from national_team.core_flow_factors import CORE_FOUR
from national_team.coverage_v3 import (
    HORIZONS, _events, _rows, read_denominators, read_nav, read_prices, read_shares,
    replay,
)


def fixture_days(n=85):
    base = date(2026, 1, 1)
    return [(base + timedelta(days=i)).isoformat() for i in range(n)]


def data(n=85, *, caps=True):
    dates = fixture_days(n)
    # Deliberately falling market and expanding shares.
    closes = {d: 5000 - i * 11 for i, d in enumerate(dates)}
    shares = {d: {c: 1_000_000 + i * 1000 for c in CORE_FOUR}
              for i, d in enumerate(dates)}
    nav = {d: {c: {"nav": 2.0, "source_url": "https://fundf10.eastmoney.com",
                   "corporate_action": "none", "published_at": None} for c in CORE_FOUR}
           for d in dates}
    float_mv = {}
    if caps:
        for d in dates:
            for kind in ("CSI300_ordinary_float_mv", "CSI300_free_float_mv"):
                float_mv[(d, kind)] = {
                    "value_cny": 100_000_000 if kind.endswith("ordinary_float_mv") else 80_000_000,
                    "source_url": "https://www.sse.com.cn/",
                    "published_at": f"{d}T20:00:00+08:00",
                }
    return dates, closes, shares, nav, float_mv


def test_four_fund_coverage_and_no_denominator_is_null():
    dates, prices, shares, nav, caps = data()
    full = replay(prices, shares, nav=nav, denominators=caps)
    assert full["data_quality"]["ratio_days"] == len(dates)
    assert full["data_quality"]["ratio_pit_verified_days"] == 0
    at = next(x for x in full["daily"] if x["date"] == dates[30])
    expect = sum(shares[dates[30]][c] * 2.0 for c in CORE_FOUR) / 100_000_000
    assert at["ordinary_float_coverage_ratio"] == pytest.approx(expect)
    assert at["free_float_coverage_ratio"] == pytest.approx(expect * 1.25)
    assert at["coverage_primary_event"] is True
    assert at["ratio_pit_verified"] is False
    no_cap = replay(prices, shares, nav=nav)
    assert no_cap["data_quality"]["ratio_days"] == 0
    assert no_cap["summary"]["coverage_primary"]["event_clusters"] == 0
    assert no_cap["summary"]["share_proxy"]["event_clusters"] > 0
    assert no_cap["summary"]["downturn_control"]["event_clusters"] > 0


def test_late_market_cap_publication_blocks_ex_post_coverage_event():
    days, prices, shares, nav, caps = data()
    for row in caps.values():
        row["published_at"] = "2026-12-31T20:00:00+08:00"
    out = replay(prices, shares, nav=nav, denominators=caps)
    assert out["data_quality"]["ratio_days"] == len(days)
    assert out["summary"]["coverage_primary"]["event_clusters"] == 0
    assert all(not x["denominator_known_by_t_plus_1"] for x in out["daily"])


def test_nav_published_after_decision_does_not_enter_coverage_signal():
    days, prices, shares, nav, caps = data()
    day = days[30]
    nav[day]["510300"]["published_at"] = "2026-12-31T20:00:00+08:00"
    report = replay(prices, shares, nav=nav, denominators=caps)
    at = next(x for x in report["daily"] if x["date"] == day)
    assert at["ordinary_float_coverage_ratio"] is not None  # hindsight arithmetic
    assert at["nav_not_known_late_by_t_plus_1"] is False
    assert at["coverage_primary_event"] is False


def test_missing_fourth_etf_never_fills_yesterday_and_blocks_signal():
    dates, prices, shares, nav, caps = data()
    del shares[dates[35]]["159919"]
    # Even a hand-constructed incomplete row must be treated as unavailable.
    internal = _rows(prices, shares, nav, caps)
    assert internal[35]["ordinary_float_coverage_ratio"] is None
    # Reader drops incomplete days, preserving an observable hole.
    shares.pop(dates[35])
    out = replay(prices, shares, nav=nav, denominators=caps)
    check = next(x for x in out["daily"] if x["date"] == dates[36])
    assert check["shares_growth_1d"] is None
    assert check["share_proxy_event"] is False


def test_suspected_split_does_not_create_primary_flow_signal():
    days, prices, shares, nav, caps = data()
    day = days[35]
    before = shares[days[34]]["510300"]
    shares[day]["510300"] = before * 2
    nav[day]["510300"]["nav"] = 1.0
    out = replay(prices, shares, nav=nav, denominators=caps)
    row = next(x for x in out["daily"] if x["date"] == day)
    assert row["net_creation_1d_cny"] is None
    assert row["coverage_primary_event"] is False


def test_duplicate_and_wrong_cap_fields_are_rejected(tmp_path):
    path = tmp_path / "caps.csv"
    fields = ["date", "kind", "value_cny", "index_code", "unit",
              "source_url", "published_at", "method"]
    def write(rows):
        with path.open("w", newline="", encoding="utf8") as fp:
            writer = csv.DictWriter(fp, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
    row = {"date": "2026-10-29", "kind": "CSI300_ordinary_float_mv",
           "value_cny": "123", "index_code": "000300.SH", "unit": "CNY",
           "source_url": "https://www.sse.com.cn/", "published_at": "2026-10-30T08:00:00+08:00",
           "method": "exchange"}
    write([row])
    assert read_denominators(path)[("2026-10-29", row["kind"])]["value_cny"] == 123
    write([row, row])
    with pytest.raises(ValueError, match="duplicate"):
        read_denominators(path)
    write([{**row, "index_code": "000001.SH"}])
    with pytest.raises(ValueError, match="000300.SH"):
        read_denominators(path)
    write([{**row, "published_at": "2026-10-30T08:00:00"}])
    with pytest.raises(ValueError, match="timezone"):
        read_denominators(path)
    write([{**row, "value_cny": "nan"}])
    with pytest.raises(ValueError, match="nonfinite"):
        read_denominators(path)


def test_share_cache_and_nav_no_forward_fill(tmp_path):
    path = tmp_path / "shares.json"
    path.write_text(json.dumps({"shares": {
        "20261029": {c: "1000" for c in CORE_FOUR},
        "20261030": {c: "1100" for c in CORE_FOUR if c != "159919"},
    }}), encoding="utf-8")
    rows = read_shares(path)
    assert set(rows) == {"2026-10-29"}
    n = tmp_path / "nav.json"
    n.write_text(json.dumps({"nav_by_date": {
        "2026-10-29": {"510300": {"nav": 2.3, "published_at": None}},
    }}), encoding="utf-8")
    assert "510300" in read_nav(n)["2026-10-29"]
    assert "159919" not in read_nav(n)["2026-10-29"]


def test_downturn_control_uses_same_complete_four_share_universe():
    days, prices, shares, nav, caps = data()
    only_late = {d: funds for d, funds in shares.items() if d >= days[40]}
    report = replay(prices, only_late, nav=nav, denominators=caps)
    assert all(e["signal_date"] >= days[45]
               for e in report["events"]["downturn_control"])
    assert report["summary"]["downturn_control"]["event_clusters"] < 10


def test_events_are_debounced_and_immature_horizons_are_unknown():
    days, prices, shares, nav, caps = data(n=32)
    out = replay(prices, shares, nav=nav, denominators=caps)
    events = out["events"]["share_proxy"]
    assert all(events[i]["signal_date"] < events[i + 1]["signal_date"]
               for i in range(len(events) - 1))
    mature = out["summary"]["share_proxy"]["horizons"]
    assert mature["20"]["matured_events"] == 0
    assert mature["10"]["matured_events"] <= mature["5"]["matured_events"]
    assert any(e["outcomes"]["20"] is None for e in events)
    assert out["trade_authorized"] is False



def test_live_csi300_incremental_cross_source_check(monkeypatch):
    import requests
    from scripts.replay_national_team_v3 import fetch_live_csi300

    class Response:
        def __init__(self, lines):
            self.lines = lines
        def raise_for_status(self):
            return None
        def json(self):
            return {"data": {"klines": self.lines}}

    old = {"2026-07-09": 4000, "2026-07-10": 4100}
    good = ["2026-07-09,4000,4000,4000,4000,100",
            "2026-07-10,4100,4100,4100,4100,100",
            "2026-07-13,4120,4120,4120,4120,100"]
    monkeypatch.setattr(requests, "get", lambda *a, **kw: Response(good))
    merged, meta = fetch_live_csi300(old)
    assert meta["status"] == "SUCCESS"
    assert meta["overlap_days"] == 2
    assert meta["added_days"] == 1
    assert merged["2026-07-10"] == 4100  # frozen original CSV preserved
    assert merged["2026-07-13"] == 4120

    bad = ["2026-07-10,5000,5000,5000,5000,100",
           "2026-07-13,4120,4120,4120,4120,100"]
    monkeypatch.setattr(requests, "get", lambda *a, **kw: Response(bad))
    retained, diagnostic = fetch_live_csi300(old)
    assert retained == old
    assert diagnostic["status"] == "FETCH_FAILED"
    assert "conflict" in diagnostic["error"]


def test_wrong_fund_counts_not_renamed_as_account_trades():
    _, prices, shares, nav, caps = data()
    report = replay(prices, shares, nav=nav, denominators=caps)
    assert report["actor_attribution"].startswith("UNVERIFIED_")
    assert report["method"]["codes"] == list(CORE_FOUR)
    assert report["summary"]["share_proxy"]["horizons"]["5"]["wilson95"] is not None
    assert HORIZONS == (5, 10, 20)
