"""Local deterministic tests for data validation and no-lookahead signal boundaries.

These synthetic fixtures test code correctness, NOT investment performance or
a real-market historical backtest.
"""
import numpy as np
import pandas as pd
import pytest

from strategy import candidate_at, historical_trades, normalize


def fixture_bars(n=270):
    dates = pd.bdate_range("2024-01-02", periods=n)
    price = 10 + np.arange(n) * 0.06
    vol = np.full(n, 100000.0)
    vol[-1] = 200000.0
    return pd.DataFrame({
        "日期": dates, "开盘": price - .03,
        "最高": price + .02, "最低": price - .06,
        "收盘": price, "成交量": vol,
    })


def test_valid_sample_has_no_future_dependency():
    df = normalize(fixture_bars())
    last = candidate_at(df, len(df) - 1)
    assert last is not None
    # Future bar modification must not change an already-emitted signal.
    future = df.iloc[-1:].copy()
    future["close"] = 999
    future["high"] = 1000
    with_future = pd.concat([df, future], ignore_index=True)
    assert candidate_at(with_future, len(df) - 1) == last
    assert last["target"] > last["trigger"] > last["stop"]
    assert last["max_chase"] >= last["trigger"]


def test_duplicate_day_refused():
    raw = fixture_bars()
    raw.loc[1, "日期"] = raw.loc[0, "日期"]
    with pytest.raises(ValueError, match="duplicate"):
        normalize(raw)


def test_bad_high_low_refused():
    raw = fixture_bars()
    raw.loc[0, "最高"] = 0.01
    with pytest.raises(ValueError, match="OHLC"):
        normalize(raw)


def test_historical_replay_has_three_day_upper_horizon():
    df = normalize(fixture_bars(330))
    trades = historical_trades(df, "600000")
    assert all(1 <= t["hold_sessions"] <= 3 for t in trades)
    assert all(t["exit_date"] > t["entry_date"] for t in trades)
