"""Chronological diagnostic and explicit sample-quality audit.

A fixed currently-surviving universe is NOT a genuine ex-ante investable
universe. This diagnostic is NOT presented as an independent OOS backtest.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pandas as pd


def summarize(trades: list[dict[str, Any]]) -> dict:
    closed = [t for t in trades if t.get("status", "closed_daily_proxy") == "closed_daily_proxy"
              and t.get("net_return") is not None]
    censored = [t for t in trades if t.get("status") == "execution_censored"]
    if not closed:
        return {"closed": 0, "censored": len(censored), "status": "INSUFFICIENT_CLOSED_TRADES"}
    r = pd.Series([float(t["net_return"]) for t in closed])
    winners = r[r > 0]; losers = r[r < 0]
    baselines = [t for t in closed if t.get("matched_T3_passive_net") is not None]
    result = {
        "closed": len(closed), "censored": len(censored),
        "win_rate": round(float((r > 0).mean()), 6),
        "mean_net_return": round(float(r.mean()), 7),
        "median_net_return": round(float(r.median()), 7),
        "profit_factor": round(float(winners.sum() / -losers.sum()), 5) if len(losers) else None,
        "mean_r_multiple": round(sum(float(t["r_multiple"]) for t in closed) / len(closed), 6),
        "target_hit_fraction": round(sum(t["reason"].startswith("target") for t in closed) / len(closed), 6),
        "timeout_fraction": round(sum(t["reason"].startswith("T+3") for t in closed) / len(closed), 6),
        "matched_passive_baseline": {
            "n": len(baselines),
            "mean_net_return": round(sum(float(t["matched_T3_passive_net"]) for t in baselines) / len(baselines), 7)
            if baselines else None,
        },
        "status": "RESEARCH_ONLY_BIASED_UNIVERSE",
    }
    return result


def chronological_diagnostic(trades: list[dict[str, Any]], latest_date: date,
                             holdout_calendar_days: int = 180,
                             embargo_calendar_days: int = 10) -> dict:
    """Fixed six-calendar-month holdout with embargo.

    Requires complete trades, so training trades that would overlap into holdout
    are not relabelled as training. This is NOT independent blind OOS evidence
    because the universe and thresholds were selected ex post.
    """
    cutoff = latest_date - timedelta(days=holdout_calendar_days)
    train_ends_before = cutoff - timedelta(days=embargo_calendar_days)
    complete = [t for t in trades if t.get("net_return") is not None
                and t.get("exit_date") and t.get("entry_date")]
    train = [t for t in complete if date.fromisoformat(t["exit_date"]) < train_ends_before]
    holdout = [t for t in complete if date.fromisoformat(t["entry_date"]) >= cutoff]
    overlap = [t for t in complete if train_ends_before <= date.fromisoformat(t["exit_date"])
               and date.fromisoformat(t["entry_date"]) < cutoff]
    return {
        "cutoff": cutoff.isoformat(),
        "embargo_starts": train_ends_before.isoformat(),
        "train": summarize(train),
        "holdout": summarize(holdout),
        "excluded_boundary_trades": len(overlap),
        "method": "prespecified date split, no fit/tuning, non-blind historical diagnostic",
        "valid_oos": False,
        "invalidating_biases": [
            "current fixed-name universe: survivorship/look-ahead membership selection",
            "not full point-in-time A-share cross-section",
            "daily OHLC does not establish T+3 14:50 fill",
            "historical signals not deposited as contemporaneous immutable observations",
            "matched passive baseline is same selected trades, not independently benchmarked portfolio",
        ],
        "trade_authorization": False,
    }
