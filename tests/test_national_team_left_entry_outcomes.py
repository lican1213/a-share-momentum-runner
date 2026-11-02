"""EXP-0011 forward OHLC red cases: future clock, paired benchmark, no hidden fills."""
from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo
import pytest
from national_team.left_entry_outcomes import _pnl, track

BJ = ZoneInfo("Asia/Shanghai")


def sessions():
    day = datetime(2026, 11, 2)
    dates = []
    while len(dates) < 18:
        if day.weekday() < 5:
            dates.append(day.date().isoformat())
        day += timedelta(days=1)
    return dates


def bar(day, open_price="10", close="10.2", low="9.8", high="10.4"):
    return {"date": day, "open": open_price, "close": close, "low": low,
            "high": high}


def sample():
    original = bar("2026-10-30", "10", "10", "9.5", "10.1")
    initial = {
        "freeze_time": "2026-11-01T15:00:00+08:00",
        "signal_session": "2026-10-30", "measurement": {"next_session": "2026-11-02"},
        "trade_authorized": False, "freeze_payload_sha256": "b" * 64,
        "accounts": {"F1_LEFT": {"orders": [
            {"stock": "000001", "gross_indicative_cny": "4000"}]}},
        "ohlc_price_history": {"stocks": {"000001": {"bars": [original]}}}}
    days = sessions()
    future = [bar(day) for day in days]
    etf = [bar(day, "4.0", "4.08", "3.96", "4.12") for day in days]
    source = {
        "capture_time": "2026-11-27T18:00:00+08:00",
        "first_observed_at": "2026-11-27T18:00:00+08:00",
        "bars_by_symbol": {"000001": future, "510300": etf},
        "errors": {}}
    return initial, source


def test_f1_and_f2_are_separate_forward_scenarios_with_same_entry_s0():
    f, p = sample()
    result = track(f, p, observed_at="2026-11-27T18:01:00+08:00")
    f1, f2 = result["F1_LEFT"][0], result["F2_WEAK"][0]
    assert f1["status"] == "OHLC_OPEN_PAPER_SCENARIO"
    assert f1["entry_session"] == "2026-11-02"
    assert f2["confirmation_day"] == "2026-11-02"
    assert f2["entry_session"] == "2026-11-03"
    assert f1["horizons"]["5"]["status"] == "PAIRED"
    assert f1["horizons"]["5"]["path_excursions"]["mfe_from_entry_open"] == "0.04"
    assert f1["horizons"]["5"]["path_excursions"]["mae_from_entry_open"] == "-0.02"
    assert f2["horizons"]["5"]["path_excursions"]["mfe_session"] >= f2["entry_session"]
    assert f2["horizons"]["5"]["status"] == "PAIRED"
    assert f1["horizons"]["5"]["s0"]["exit_session"] == "2026-11-09"
    assert f2["horizons"]["5"]["s0"]["exit_session"] == "2026-11-10"
    assert result["trade_authorized"] is False and not result["broker_orders"]
    assert result["execution_assertion"] == "OHLC_OPEN_SCENARIO_NOT_AN_EXECUTED_TRADE"


def test_never_claim_matured_return_without_future_sessions():
    f, p = sample()
    p["bars_by_symbol"] = {"510300": p["bars_by_symbol"]["510300"][:1],
                           "000001": p["bars_by_symbol"]["000001"][:1]}
    p["capture_time"] = "2026-11-02T18:00:00+08:00"
    p["first_observed_at"] = p["capture_time"]
    result = track(f, p, observed_at="2026-11-02T18:01:00+08:00")
    assert result["F1_LEFT"][0]["horizons"]["5"]["after_cost_return"] is None
    assert "path_excursions" not in result["F1_LEFT"][0]["horizons"]["5"]
    assert result["F2_WEAK"][0]["status"] == "WAIT_NEXT_OPEN_AFTER_CONFIRMATION"


def test_missing_etf_refuses_fake_zero_excess():
    f, p = sample()
    del p["bars_by_symbol"]["510300"]
    result = track(f, p, observed_at="2026-11-27T18:01:00+08:00")
    assert result["first_actual_benchmark_session"] is None
    assert result["F1_LEFT"][0]["status"] == "NEXT_ACTUAL_SESSION_PENDING"


def test_publication_clock_cannot_precede_freeze():
    f, p = sample()
    with pytest.raises(ValueError, match="predate freeze"):
        track(f, p, observed_at="2026-10-31T18:00:00+08:00")


def test_same_day_selling_not_in_any_horizon():
    f, p = sample()
    r = track(f, p, observed_at="2026-11-27T18:01:00+08:00")
    for horizon in ["3", "5", "10"]:
        assert r["F1_LEFT"][0]["horizons"][horizon]["exit_session"] > "2026-11-02"
    assert _pnl(400, "10", "10") < 0  # all-in paper roundtrip costs matter


def test_missing_stock_session_breaks_pair_not_fabricated_profit():
    f, p = sample()
    p["bars_by_symbol"]["000001"].pop(5)
    r = track(f, p, observed_at="2026-11-27T18:01:00+08:00")
    assert r["F1_LEFT"][0]["horizons"]["5"]["status"] == "S0_MISSING"
    assert r["F1_LEFT"][0]["horizons"]["5"]["excess_s0"] is None
