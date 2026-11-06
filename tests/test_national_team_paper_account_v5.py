"""EXP-0014 daily V5 paper-account paths: fills, T+1, cash, audit and shadows."""
import copy

import pytest

from national_team.paper_account_v5 import advance


def market(day, op="10", cl="10", low="9.9", high="10.1"):
    return {"date": day, "open": op, "close": cl, "low": low, "high": high}


def event(*, days=("2026-11-03",), source_code="600001"):
    freeze = {
        "freeze_time": "2026-11-02T18:10:00+08:00",
        "freeze_payload_sha256": "f" * 64, "signal_session": "2026-11-02",
        "trade_authorized": False,
        "paper_policies": {
            "SHALLOW_DIP": {"orders": [{"stock": "600001", "intended_session": "2026-11-03"}]},
            "DEEP_DIP": {"orders": [{"stock": "600002", "intended_session": "2026-11-03"}]},
            "R_BOUNCE": {"orders": [{"stock": "600003", "intended_session": "2026-11-03"}]},
        },
    }
    source = {
        "first_observed_at": days[-1] + "T18:20:00+08:00",
        "bars_by_symbol": {
            "510300": [market(day, "4", "4.02", "3.98", "4.04") for day in days],
            "600001": [market(day, "10", "10", "9.95", "10.05") for day in days],
            "600002": [market(day, "10", "10", "9.95", "10.05") for day in days],
            "600003": [market(day, "10", "10", "9.95", "10.05") for day in days],
        },
    }
    return freeze, source


def advance_day(previous, evt, day):
    return advance(previous, [evt], asof=day, captured_at=day + "T18:45:00+08:00")


def test_three_arms_fill_with_separate_cash_not_real_broker_orders():
    f, s = event()
    p = advance_day(None, (f, s), "2026-11-03")
    assert p["trade_authorized"] is False and p["broker_orders"] == []
    assert p["last_market_session"] == "2026-11-03"
    for policy, code in (
        ("SHALLOW_DIP", "600001"), ("DEEP_DIP", "600002"), ("R_BOUNCE", "600003")
    ):
        a = p["accounts"][policy]
        assert a["positions"][0]["stock"] == code
        assert a["positions"][0]["shares"] % 100 == 0
        assert a["summary"]["open_positions"] == 1
        assert float(a["cash_cny"]) < 30000
        assert a["closed_trades"] == []
        assert a["summary"]["mark_status"] == "CURRENT_CLOSE_PROXY"
    assert p["snapshot_sha256"]


def test_t_plus_one_target_stop_and_t_plus_two_time_close():
    f, s = event(days=("2026-11-03", "2026-11-04", "2026-11-05"))
    f1 = copy.deepcopy(s)
    for key in f1["bars_by_symbol"]:
        f1["bars_by_symbol"][key] = f1["bars_by_symbol"][key][:1]
    f1["first_observed_at"] = "2026-11-03T18:20:00+08:00"
    p1 = advance_day(None, (f, f1), "2026-11-03")
    assert all(not a["closed_trades"] for a in p1["accounts"].values())
    s2 = copy.deepcopy(s)
    for key in s2["bars_by_symbol"]:
        s2["bars_by_symbol"][key] = s2["bars_by_symbol"][key][:2]
    s2["bars_by_symbol"]["600001"][1] = market("2026-11-04", "10", "9.9", "9.65", "10.5")
    s2["bars_by_symbol"]["600002"][1] = market("2026-11-04", "10", "10.3", "9.95", "10.45")
    s2["first_observed_at"] = "2026-11-04T18:20:00+08:00"
    p2 = advance_day(p1, (f, s2), "2026-11-04")
    bad = p2["accounts"]["SHALLOW_DIP"]
    good = p2["accounts"]["DEEP_DIP"]
    right = p2["accounts"]["R_BOUNCE"]
    assert bad["closed_trades"][0]["exit_reason"] == "STOP_TOUCH_OHLC_STOP_FIRST"
    assert float(bad["closed_trades"][0]["net_pnl_cny"]) < 0
    assert good["closed_trades"][0]["exit_reason"] == "TARGET_TOUCH_OHLC"
    assert float(good["closed_trades"][0]["net_pnl_cny"]) > 0
    assert good["closed_trades"][0]["s0_matched_net_pnl_cny"] is not None
    assert good["summary"]["paired_s0_trades"] == 1
    assert right["summary"]["open_positions"] == 1
    s3 = copy.deepcopy(s)
    s3["first_observed_at"] = "2026-11-05T18:20:00+08:00"
    s3["bars_by_symbol"]["600001"][1] = s2["bars_by_symbol"]["600001"][1]
    s3["bars_by_symbol"]["600002"][1] = s2["bars_by_symbol"]["600002"][1]
    p3 = advance_day(p2, (f, s3), "2026-11-05")
    assert p3["accounts"]["R_BOUNCE"]["closed_trades"][0]["exit_reason"] == (
        "T_PLUS_2_PLANNED_CLOSE_PROXY")
    assert p3["accounts"]["R_BOUNCE"]["summary"]["open_positions"] == 0
    again = advance_day(p3, (f, s3), "2026-11-05")
    assert again["accounts"] == p3["accounts"]  # no duplicate buys, exits or cash


def test_missing_open_does_not_later_backfill_profitable_trade():
    f, s = event()
    del s["bars_by_symbol"]["600002"]
    p = advance_day(None, (f, s), "2026-11-03")
    deep = p["accounts"]["DEEP_DIP"]
    assert deep["positions"] == []
    assert deep["decisions"][0]["reason"] == "ENTRY_OHLC_MISSING_NO_RETROSPECTIVE_FILL"
    fixed = event(days=("2026-11-03", "2026-11-04"))[1]
    p2 = advance_day(p, (f, fixed), "2026-11-04")
    assert p2["accounts"]["DEEP_DIP"]["positions"] == []
    assert p2["accounts"]["DEEP_DIP"]["decisions"] == deep["decisions"]


def test_no_fresh_event_still_exposes_real_cash_balance():
    p = advance(None, [], asof="2026-11-02", captured_at="2026-11-02T18:45:00+08:00")
    assert p["source_event_count"] == 0
    assert all(x["summary"]["cash_cny"] == "30000.00" and
               x["summary"]["closed_trades"] == 0 for x in p["accounts"].values())


def test_future_source_or_freeze_cannot_enter_account():
    f, s = event()
    with pytest.raises(ValueError, match="future market"):
        advance_day(None, (f, {**s, "first_observed_at": "2026-11-04T09:00:00+08:00"}), "2026-11-03")
    with pytest.raises(ValueError, match="freeze after"):
        advance_day(None, ({**f, "freeze_time": "2026-11-04T18:00:00+08:00"}, s), "2026-11-03")


def test_account_rejects_incompatible_prior_state():
    with pytest.raises(ValueError, match="incompatible"):
        advance({"version": "LEGACY", "accounts": {}}, [], asof="2026-11-03",
                captured_at="2026-11-03T18:45:00+08:00")


def test_intraday_benchmark_is_labeled_proxy_with_ohlc_envelope():
    f, source = event(days=("2026-11-03", "2026-11-04"))
    first = copy.deepcopy(source)
    for symbol in first["bars_by_symbol"]:
        first["bars_by_symbol"][symbol] = first["bars_by_symbol"][symbol][:1]
    first["first_observed_at"] = "2026-11-03T18:20:00+08:00"
    p1 = advance_day(None, (f, first), "2026-11-03")
    source["bars_by_symbol"]["600001"][1] = market(
        "2026-11-04", "10", "9.7", "9.6", "10.4")
    source["bars_by_symbol"]["510300"][1] = market(
        "2026-11-04", "4", "4.02", "3.9", "4.1")
    p2 = advance_day(p1, (f, source), "2026-11-04")
    trade = p2["accounts"]["SHALLOW_DIP"]["closed_trades"][0]
    assert trade["benchmark_exit_method"] == "ETF_DAILY_CLOSE_PROXY_NOT_SAME_TIME"
    assert trade["execution_confidence"] == "DAILY_OHLC_STOP_FIRST_AMBIGUOUS"
    envelope = trade["s0_intraday_excess_envelope_cny"]
    assert float(envelope["excess_if_etf_high_cny"]) <= float(trade["excess_s0_cny"])
    assert float(trade["excess_s0_cny"]) <= float(envelope["excess_if_etf_low_cny"])
    assert p2["accounts"]["SHALLOW_DIP"]["summary"]["paired_s0_exact_intraday_trades"] == 0


def test_planned_close_has_same_session_close_proxy_not_intraday_claim():
    f, source = event(days=("2026-11-03", "2026-11-04", "2026-11-05"))
    source["first_observed_at"] = "2026-11-05T18:20:00+08:00"
    p = advance_day(None, (f, source), "2026-11-05")
    trade = p["accounts"]["SHALLOW_DIP"]["closed_trades"][0]
    assert trade["exit_reason"] == "T_PLUS_2_PLANNED_CLOSE_PROXY"
    assert trade["benchmark_exit_method"] == "ETF_SAME_SESSION_CLOSE_PROXY"
    assert trade["execution_confidence"] == "DAILY_CLOSE_PROXY"
    assert trade["s0_intraday_excess_envelope_cny"] is None


@pytest.mark.parametrize("stock_open,stock_low,stock_high,expected_reason", [
    ("9.5", "9.3", "9.8", "GAP_STOP_AT_OPEN"),
    ("10.5", "10.2", "10.8", "GAP_TARGET_AT_OPEN"),
])
def test_gap_exit_uses_etf_open_and_equal_capital_after_costs(
    stock_open, stock_low, stock_high, expected_reason
):
    from decimal import Decimal

    from national_team.left_entry_v4 import FEE_RATE, SLIPPAGE_RATE

    f, source = event(days=("2026-11-03", "2026-11-04"))
    first = copy.deepcopy(source)
    for symbol in first["bars_by_symbol"]:
        first["bars_by_symbol"][symbol] = first["bars_by_symbol"][symbol][:1]
    first["first_observed_at"] = "2026-11-03T18:20:00+08:00"
    p1 = advance_day(None, (f, first), "2026-11-03")
    position = p1["accounts"]["SHALLOW_DIP"]["positions"][0]
    source["bars_by_symbol"]["600001"][1] = market(
        "2026-11-04", stock_open, stock_open, stock_low, stock_high)
    # Large ETF intraday move makes an incorrect closing-price match obvious.
    source["bars_by_symbol"]["510300"][1] = market(
        "2026-11-04", "4.3", "4.9", "4.2", "5.0")
    p2 = advance_day(p1, (f, source), "2026-11-04")
    account = p2["accounts"]["SHALLOW_DIP"]
    trade = account["closed_trades"][0]
    assert trade["exit_reason"] == expected_reason
    assert trade["benchmark_exit_method"] == "ETF_SAME_SESSION_OPEN_PROXY"
    assert trade["execution_confidence"] == "DAILY_OPEN_PROXY"
    assert trade["s0_intraday_excess_envelope_cny"] is None
    shares = Decimal(position["s0_shares"])
    net_exit = Decimal("4.3") * shares * (1 - SLIPPAGE_RATE)
    net_exit -= max(Decimal("5"), net_exit * FEE_RATE)
    expected_s0 = net_exit - Decimal(position["s0_buy_total_cny"])
    assert Decimal(trade["s0_matched_net_pnl_cny"]) == expected_s0.quantize(Decimal("0.01"))
    expected_normalized = expected_s0 * Decimal(position["buy_total_cny"]) / Decimal(
        position["s0_buy_total_cny"])
    assert abs(Decimal(trade["s0_equal_capital_pnl_cny"]) - expected_normalized) < Decimal("0.01")
    assert Decimal(trade["excess_s0_equal_capital_cny"]) == (
        Decimal(trade["net_pnl_cny"]) - Decimal(trade["s0_equal_capital_pnl_cny"])
    )
    assert account["summary"]["paired_s0_open_proxy_trades"] == 1
    assert account["summary"]["paired_s0_close_proxy_trades"] == 0
    assert account["summary"]["realized_excess_s0_equal_capital_cny"] == (
        trade["excess_s0_equal_capital_cny"])


def test_equal_capital_return_is_distinct_from_raw_round_lot_pnl():
    f, source = event(days=("2026-11-03", "2026-11-04", "2026-11-05"))
    source["bars_by_symbol"]["510300"] = [
        market(day, "4.1", "4.12", "4.05", "4.15")
        for day in ("2026-11-03", "2026-11-04", "2026-11-05")]
    p = advance_day(None, (f, source), "2026-11-05")
    trade = p["accounts"]["SHALLOW_DIP"]["closed_trades"][0]
    assert trade["benchmark_exit_method"] == "ETF_SAME_SESSION_CLOSE_PROXY"
    assert trade["s0_notional_entry_cny"] != trade["stock_notional_entry_cny"]
    assert trade["equal_capital_method"] == (
        "NET_FEE_ADJUSTED_ETF_RETURN_ON_STOCK_COST_NOT_EXECUTABLE")
    assert trade["excess_s0_equal_capital_cny"] != trade["excess_s0_cny"]


def test_late_t_plus_two_stock_close_is_processed_without_new_etf_session():
    f, source = event(days=("2026-11-03", "2026-11-04", "2026-11-05"))
    first = copy.deepcopy(source)
    first["bars_by_symbol"]["600001"] = first["bars_by_symbol"]["600001"][:2]
    p1 = advance_day(None, (f, first), "2026-11-05")
    shallow = p1["accounts"]["SHALLOW_DIP"]
    assert shallow["summary"]["mark_status"] == "STALE_PRICE"
    assert shallow["summary"]["open_positions"] == 1
    # A later 18:45 archive sees the missing daily close, on the SAME market day.
    p2 = advance_day(p1, (f, source), "2026-11-05")
    shallow = p2["accounts"]["SHALLOW_DIP"]
    assert shallow["summary"]["open_positions"] == 0
    assert shallow["closed_trades"][0]["exit_session"] == "2026-11-05"
    assert shallow["closed_trades"][0]["exit_reason"] == "T_PLUS_2_PLANNED_CLOSE_PROXY"
    assert shallow["closed_trades"][0]["late_ohlc_reconciliation"] is True
    assert advance_day(p2, (f, source), "2026-11-05")["accounts"] == p2["accounts"]


def test_missing_t_plus_two_bar_cannot_be_disguised_as_next_day_exit():
    f, source = event(days=("2026-11-03", "2026-11-04", "2026-11-05", "2026-11-06"))
    missing = copy.deepcopy(source)
    missing["bars_by_symbol"]["600001"] = [
        b for b in missing["bars_by_symbol"]["600001"] if b["date"] != "2026-11-05"]
    p1 = advance_day(None, (f, missing), "2026-11-06")
    arm = p1["accounts"]["SHALLOW_DIP"]
    assert arm["closed_trades"] == []  # 11/06 quote cannot stand in for missing 11/05.
    assert arm["summary"]["mark_status"] == "STALE_PRICE"
    p2 = advance_day(p1, (f, source), "2026-11-06")
    trade = p2["accounts"]["SHALLOW_DIP"]["closed_trades"][0]
    assert trade["exit_session"] == "2026-11-05"
    assert trade["late_ohlc_reconciliation"] is True
