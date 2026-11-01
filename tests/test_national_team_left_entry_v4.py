"""EXP-0011 adversarial contracts: research gate, low-left, clocks and cash."""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import json

import pytest

from national_team.left_entry_v4 import (
    MAX_GROSS, MAX_LOSS_PER_STOCK, admission, features, freeze,
    plan_lots, weak_confirmation, digest,
)

BJ = ZoneInfo("Asia/Shanghai")
NOW = datetime.now(BJ)


def stamp(delta_days=-2):
    return (NOW + timedelta(days=delta_days)).isoformat()


def future_session():
    day = NOW.date() + timedelta(days=1)
    while day.weekday() >= 5:
        day += timedelta(days=1)
    return day.isoformat()


def bars(last=10, base=10):
    days = [(datetime(2026, 10, 10) + timedelta(days=i)).date().isoformat()
            for i in range(21)]
    rows = [{"date": day, "open": str(base), "high": str(base),
             "low": str(base), "close": str(base)} for day in days]
    rows[-1]["close"] = str(last)
    rows[-1]["high"] = str(max(last, base))
    rows[-1]["low"] = str(min(last, base))
    return rows


def fixtures():
    codes = ["000001", "600000", "601166", "601919", "300001"]
    v3 = {
        "method": {"codes": ["510300", "510310", "510330", "159919"]},
        "summary": {
            "share_proxy": {"horizons": {
                "5": {"wins": 31, "matured_events": 59},
                "10": {"hit_rate": 28 / 59},
                "20": {"hit_rate": 24 / 58}}},
            "coverage_primary": {"raw_signal_days": 0}},
        "daily": [{"date": "2026-10-30", "market_down": True,
                   "share_proxy_event": True, "net_creation_1d_cny": 8590983660,
                   "net_creation_5d_cny": 47907928530, "index_ret5": -.03,
                   "ratio_status": "DENOMINATOR_MISSING",
                   "ordinary_float_coverage_ratio": None}],
        "events": {"share_proxy": [{"signal_date": "2026-10-26"}]},
        "source_provenance": {"as_of_utc": stamp(),
                              "repo_source_commit": "baseline"}}
    watch = {
        "funding_date": "2026-10-30",
        "event_first_public_no_earlier_than": stamp(),
        "index_weight": {"kind": "CSI300_LATEST_INDEX_WEIGHT_PROXY_NOT_ETF_PCF",
                         "first_observed_at": stamp(),
                         "weights": {x: ".02" for x in codes}},
        "candidate_pool_pre_filter": codes,
        "stock_snapshots": {x: {"data_date": "2026-10-30",
                               "first_observed_at": stamp(), "adv20_cny": "900000000"}
                            for x in codes}}
    prices = {
        "stocks": {x: {"asof": "2026-10-30",
                       "first_observed_at": stamp(),
                       "bars": bars(last),
                       "source_url": "https://finance.sina.com.cn/realstock/company/",
                       "source_sha256": "a" * 64}
                   for x, last in {
                       "000001": 10, "600000": 9.9, "601166": 10.7,
                       "601919": 11.26, "300001": 9}.items()}}
    return v3, watch, prices


def execute(v3=None, watch=None, prices=None, **kwargs):
    original = fixtures()
    return freeze(v3 or original[0], watch or original[1], prices or original[2],
                  now=stamp(0), next_session=future_session(), **kwargs)


def test_50_percent_admits_not_relabel_as_stock_alpha():
    v, _, _ = fixtures()
    result = admission(v)
    assert result["pilot_admitted"] is True
    assert result["five_day_wins"] == 31
    assert result["five_day_matured"] == 59
    assert result["other_horizons_directional_rates_not_gates"]["10"] < .5
    assert "NOT_STOCK_PROFIT" in result["interpretation"]
    assert result["primary_coverage_ratio_available"] is False


def test_no_automatic_entry_when_5d_gate_fails():
    v, w, p = fixtures()
    v["summary"]["share_proxy"]["horizons"]["5"]["wins"] = 29
    result = execute(v, w, p)
    assert not result["admission"]["pilot_admitted"]
    assert result["accounts"]["F1_LEFT"]["orders"] == []


def test_fixed_four_not_three_sse_only():
    v, w, p = fixtures()
    v["method"]["codes"].remove("159919")
    with pytest.raises(ValueError, match="four fixed"):
        execute(v, w, p)


def test_rising_breakout_stocks_are_not_left_side():
    v, w, p = fixtures()
    result = execute(v, w, p)
    assert {x["stock"] for x in result["excluded_chase"]} == {"601166", "601919"}
    assert not {"601166", "601919"} & {x["stock"] for x in result["accounts"]["F1_LEFT"]["orders"]}


def test_partial_data_does_not_turn_missing_into_fake_zero():
    v, w, p = fixtures()
    del p["stocks"]["300001"]
    result = execute(v, w, p)
    assert result["universe"]["missing_count"] == 1
    assert result["missing_stock_data"]["300001"] == "NO_SOURCE_BACKED_OHLC"
    assert result["accounts"]["F1_LEFT"]["orders"]


def test_no_backdated_paper_trades_or_fake_holdings():
    v, w, p = fixtures()
    with pytest.raises(ValueError, match="backdated"):
        freeze(v, w, p, now=stamp(0), next_session="2026-10-30")
    result = execute(v, w, p)
    for order in result["accounts"]["F1_LEFT"]["orders"]:
        assert order["fill"] is None and order["paper_position"] == 0
        assert order["intended_session"] == future_session()
    assert result["broker_orders"] == [] and not result["trade_authorized"]


def test_price_known_after_freeze_not_read():
    v, w, p = fixtures()
    p["stocks"]["000001"]["first_observed_at"] = (NOW + timedelta(days=2)).isoformat()
    result = execute(v, w, p)
    assert result["missing_stock_data"]["000001"] == "OHLC_DATE_OR_PUBLICATION_MISMATCH"


def test_future_bar_excluded_from_features():
    series = bars()
    before = features(series, "2026-10-30", __import__("decimal").Decimal("-.03"))
    series.append({"date": "2026-11-02", "close": "1000", "low": "1000"})
    assert features(series, "2026-10-30", __import__("decimal").Decimal("-.03")) == before


def test_budget_board_lot_fee_risk_and_no_order_for_expensive_stock():
    leg = plan_lots("10")
    assert leg["shares_indicative"] % 100 == 0
    assert __import__("decimal").Decimal(leg["gross_indicative_cny"]) <= 5000
    assert __import__("decimal").Decimal(leg["risk_with_roundtrip_cost_cny"]) <= MAX_LOSS_PER_STOCK
    assert plan_lots("500")["shares_indicative"] == 0


def test_two_separate_accounts_and_same_time_etf_counterfactual():
    v, w, p = fixtures()
    result = execute(v, w, p)
    f1 = result["accounts"]["F1_LEFT"]
    f2 = result["accounts"]["F2_WEAK"]
    assert 1 <= len(f1["orders"]) <= 2
    assert sum(float(x["gross_indicative_cny"]) for x in f1["orders"]) <= float(MAX_GROSS)
    assert f2["same_precommitted_candidates"] == [x["stock"] for x in f1["orders"]]
    assert f2["filled"] is False and f1["filled"] is False
    assert result["accounts"]["S0_ETF"]["entry_session"] == future_session()
    assert result["accounts"]["S0_ETF"]["net_return"] is None
    assert result["accounts"]["N_NON_FLOW"]["net_return"] is None


def test_f2_requires_genuine_later_weak_confirmation():
    assert not weak_confirmation(10, 9.99, 10, 10)
    assert not weak_confirmation(10, 10, 10, 9.99)
    assert weak_confirmation(10, 10.01, 10, 10.02)


def test_source_hash_and_event_anchor_immutable():
    v, w, p = fixtures()
    result = execute(v, w, p)
    assert result["source_etf_record_sha256"] == digest(v)
    assert result["source_watch_record_sha256"] == digest(w)
    assert result["source_ohlc_snapshots_sha256"] == digest(p)
    assert result["cluster_anchor"] == "2026-10-26"
    assert result["signal_session"] == "2026-10-30"
    assert result["ohlc_price_history"] == p


def test_real_v3_negative_october_event_never_deleted():
    path = Path("records/national_team_v3/2026-11-01/41281158666-a1.json")
    if not path.exists():
        pytest.skip("retrospective immutable evidence not present in fixture checkout")
    real = json.loads(path.read_text(encoding="utf-8"))
    assert any(e["signal_date"] == "2026-10-09"
               and e["outcomes"]["5"]["index_return"] < 0
               and e["outcomes"]["10"]["index_return"] < 0
               for e in real["events"]["share_proxy"])
    assert real["events"]["share_proxy"][-1]["signal_date"] == "2026-10-26"
    assert real["events"]["share_proxy"][-1]["outcomes"]["5"] is None
