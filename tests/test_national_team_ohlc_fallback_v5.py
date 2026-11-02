"""No network needed: dated Baostock fallback, incomplete session and provenance."""
from __future__ import annotations

from datetime import date, timedelta

from national_team.ohlc_fallback_v5 import (
    fetch_baostock, backfill_asof_prices, backfill_future_bars,
)


class FakeResult:
    error_code = "0"
    error_msg = ""
    def __init__(self, rows):
        self.rows, self.i = rows, -1
    def next(self):
        self.i += 1
        return self.i < len(self.rows)
    def get_row_data(self):
        return self.rows[self.i]


class FakeBS:
    calls = 0
    logged_out = False
    def login(self):
        self.calls += 1
        return FakeResult([])
    def logout(self):
        self.logged_out = True
    def query_history_k_data_plus(self, symbol, fields, start_date, end_date,
                                  frequency, adjustflag):
        assert fields == "date,open,high,low,close"
        assert frequency == "d" and adjustflag == "3"
        rows = []
        day = date.fromisoformat(start_date)
        while day <= date.fromisoformat(end_date):
            if day.weekday() < 5:
                rows.append([day.isoformat(), "10", "10.4", "9.8", "10.2"])
            day += timedelta(days=1)
        return FakeResult(rows)


def test_one_login_fetches_multiple_symbols_and_honors_raw_dates():
    bs = FakeBS()
    source, errors = fetch_baostock(["600001", "000001"],
                                   "2026-10-01", "2026-10-30", backend=bs)
    assert len(source) == 2 and not errors
    assert bs.calls == 1 and bs.logged_out
    assert source["600001"]["vendor"] == "BAOSTOCK"
    assert source["600001"]["source_sha256"]
    assert source["600001"]["bars"][-1]["date"] == "2026-10-30"


def test_asof_fallback_only_accepts_true_same_day_full_history():
    def valid(codes, start, end):
        bs = FakeBS()
        source, errors = fetch_baostock(codes, start, end, backend=bs)
        return source, errors
    prices = {"universe": ["600001"], "stocks": {}, "collection_errors": {}}
    filled = backfill_asof_prices(prices, "2026-10-30", fetcher=valid)
    assert filled["stocks"]["600001"]["asof"] == "2026-10-30"
    assert filled["fallback_recovered_codes"] == ["600001"]
    assert len(filled["stocks"]["600001"]["bars"]) >= 21
    stale = {"universe": ["600001"], "stocks": {}, "collection_errors": {}}
    def old(codes, start, end):
        src, err = valid(codes, start, end)
        src["600001"]["bars"] = src["600001"]["bars"][:-1]
        return src, err
    ignored = backfill_asof_prices(stale, "2026-10-30", fetcher=old)
    assert ignored["stocks"] == {}
    assert "BAOSTOCK:600001" in ignored["collection_errors"]


def test_future_fallback_recovers_missing_symbol_without_faking_etf():
    data = {"bars_by_symbol": {"510300": [], "600001": []},
            "errors": {"600001": "SINA_TEMPORARY_FAILURE"},
            "source_sha256": {}, "source_url": {}}
    def partial(codes, start, end):
        assert start == "2026-11-03"
        return ({
            "600001": {"bars": [{"date": "2026-11-03", "open": "10",
                                "high": "10.4", "low": "9.7", "close": "10.2"}],
                       "source_sha256": "realhash", "source_url": "http://baostock.com"}},
            {"510300": "UNAVAILABLE"})
    out = backfill_future_bars(data, ["510300", "600001"], "2026-11-02",
                               "2026-11-05", fetcher=partial)
    assert out["bars_by_symbol"]["600001"][0]["date"] == "2026-11-03"
    assert out["bars_by_symbol"]["510300"] == []
    assert out["errors"]["600001"] == "SINA_TEMPORARY_FAILURE"
    assert out["errors"]["BAOSTOCK:510300"] == "UNAVAILABLE"
    assert out["fallback_recovered_codes"] == ["600001"]



def test_forward_tracker_evaluates_after_source_capture(monkeypatch):
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from scripts import track_national_team_left_entry_v5 as tracker
    now = datetime.now(ZoneInfo("Asia/Shanghai")).isoformat()
    seen = {"bars_by_symbol": {"510300": [{"date": "2026-11-02"}]},
            "capture_time": now, "first_observed_at": now, "errors": {}}
    monkeypatch.setattr(tracker, "collect", lambda ak, frozen, asof: dict(seen))
    checked = []
    def observed_after_source(frozen, observations, *, observed_at):
        assert datetime.fromisoformat(observed_at) >= datetime.fromisoformat(
            observations["capture_time"])
        checked.append(1)
        return {"F1_LEFT": [], "F2_WEAK": [], "errors": {},
                "source_new_ohlc_sha256": "observed"}
    monkeypatch.setattr(tracker, "track", observed_after_source)
    frozen = {"paper_policies": {"SHALLOW_DIP": {"orders": []},
                                  "DEEP_DIP": {"orders": []}},
              "accounts": {"F1_LEFT": {"orders": []}},
              "signal_session": "2026-10-30", "cluster_anchor": "2026-10-26",
              "freeze_payload_sha256": "sha"}
    event = tracker.follow_one(object(), frozen, "freeze.json",
                               datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat())
    assert len(checked) == 2
    assert event["source_freeze_sha256"] == "sha"
