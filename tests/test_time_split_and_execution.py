"""Reproducible regression tests using synthetic fixtures only (no return claims)."""
from datetime import date

import numpy as np
import pandas as pd

from research_validation import chronological_diagnostic, summarize
from strategy import historical_trades, normalize, signal_id, candidate_at


def make_bars(n=270):
    price = 10.0 + np.arange(n) * 0.06
    raw = pd.DataFrame({
        "日期": pd.bdate_range("2024-01-02", periods=n),
        "开盘": price - 0.03, "最高": price + 0.02,
        "最低": price - 0.06, "收盘": price,
        "成交量": np.repeat(100000.0, n),
    })
    raw.loc[254, "成交量"] = 200000
    return raw


def test_frozen_id_reproducible():
    df = normalize(make_bars())
    s = candidate_at(df, 254)
    assert s is not None
    assert signal_id("600000", s) == signal_id("600000", s)
    assert signal_id("600001", s) != signal_id("600000", s)


def test_unfillable_T3_not_fake_win_or_exit():
    df = make_bars()
    j = 255
    # T=255: buy trigger crosses; T+1/T+2/T+3 one-price limit down.
    fill = float(df.loc[j - 1, "收盘"]) * 1.004
    for c in ("开盘", "收盘", "最高", "最低"):
        df.loc[j, c] = fill
    prev = fill
    for k in [j + 1, j + 2, j + 3]:
        prev = round(prev * 0.9, 2)
        for c in ("开盘", "收盘", "最高", "最低"):
            df.loc[k, c] = prev
    bars = normalize(df)
    trades = historical_trades(bars, "600000")
    censored = [t for t in trades if t.get("status") == "execution_censored"]
    assert censored, trades
    assert all(t["net_return"] is None and t["exit"] is None for t in censored)
    assert all(t["reason"] == "T+3_unfillable_limit_down_proxy" for t in censored)


def test_chronological_embargo_no_overlapping_trade():
    trades = [
        {"entry_date": "2026-01-15", "exit_date": "2026-01-20", "net_return": -0.02, "r_multiple": -1.0,
         "reason": "stop", "status": "closed_daily_proxy"},
        {"entry_date": "2026-04-26", "exit_date": "2026-04-29", "net_return": 0.02, "r_multiple": 1.8,
         "reason": "target", "status": "closed_daily_proxy"},
        {"entry_date": "2026-05-05", "exit_date": "2026-05-08", "net_return": 0.03, "r_multiple": 2.1,
         "reason": "target", "status": "closed_daily_proxy"},
    ]
    r = chronological_diagnostic(trades, date(2026, 10, 28), holdout_calendar_days=180)
    assert r["train"]["closed"] == 1
    assert r["excluded_boundary_trades"] == 1
    assert r["holdout"]["closed"] == 1
    assert r["valid_oos"] is False
    assert r["trade_authorization"] is False


def test_censored_excluded_from_win_rate():
    data = [
        {"status": "closed_daily_proxy", "net_return": -0.01, "r_multiple": -1.0, "reason": "stop"},
        {"status": "execution_censored", "net_return": None, "reason": "T+3_unfillable_limit_down_proxy"},
    ]
    result = summarize(data)
    assert result["closed"] == 1
    assert result["censored"] == 1
    assert result["win_rate"] == 0
