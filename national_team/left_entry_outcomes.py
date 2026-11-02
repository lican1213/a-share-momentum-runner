"""EXP-0011 prospective OHLC-only paper scenarios; never represent as broker fills.

Accepts one immutable V4 freeze plus subsequently first-seen OHLC observations.
Computes F1/F2 and matched 510300 ETF return for matured days, without revising
precommitted candidate ordering. Missing observation -> unknown, never zero P&L.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from national_team.left_entry_v4 import (
    BJ, CAPITAL, FEE_RATE, SLIPPAGE_RATE, STAMP_SELL_RATE, d, digest,
    plan_lots, weak_confirmation,
)

HORIZONS = (3, 5, 10, 20)


def _iso(value):
    x = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if x.utcoffset() is None:
        raise ValueError("naive capture/publish time")
    return x


def _clean_bars(raw, until):
    seen = set()
    out = []
    for row in raw:
        day = str(row["date"])[:10]
        if day > until:
            continue
        if day in seen:
            raise ValueError("duplicate OHLC session")
        seen.add(day)
        op, cl, lo, hi = (
            d(row[k], f"{day}:{k}") for k in ("open", "close", "low", "high"))
        if min(op, cl, lo, hi) <= 0 or lo > min(op, cl, hi) or hi < max(op, cl, lo):
            raise ValueError("invalid OHLC")
        out.append({"date": day, "open": op, "close": cl, "low": lo, "high": hi})
    if [x["date"] for x in out] != sorted(seen):
        raise ValueError("unordered OHLC")
    return out


def _pnl(shares, entry_open, exit_close):
    buy = d(entry_open, "buy") * shares * (1 + SLIPPAGE_RATE) * (1 + FEE_RATE)
    sell = d(exit_close, "sell") * shares * (1 - SLIPPAGE_RATE) * (
        1 - FEE_RATE - STAMP_SELL_RATE)
    return (sell - buy) / CAPITAL


def _matched_etf(index, entry_date, amount, horizon, asof):
    days = [x["date"] for x in index]
    if entry_date not in days:
        return {"status": "BENCHMARK_ENTRY_MISSING", "net_return": None}
    start = days.index(entry_date)
    if start + horizon >= len(index):
        return {"status": "UNMATURED", "net_return": None}
    entry = index[start]
    finish = index[start + horizon]
    if finish["date"] > asof:
        return {"status": "UNMATURED", "net_return": None}
    budget = d(amount, "matched amount")
    shares = int(budget / (entry["open"] * 100 * (1 + SLIPPAGE_RATE))) * 100
    if shares <= 0:
        return {"status": "ETF_LOT_UNAVAILABLE", "net_return": None}
    return {"status": "MATURED", "shares": shares,
            "net_return": format(_pnl(shares, entry["open"], finish["close"]), "f"),
            "exit_session": finish["date"]}


def _scenario(symbol, entry_day, series, index, budget_at_freeze, asof):
    existing = {x["date"]: x for x in series}
    if entry_day not in existing:
        return {"stock": symbol, "status": "ENTRY_OHLC_UNKNOWN", "entry_session": entry_day,
                "horizons": {str(h): {"status": "UNMATURED", "excess_s0": None}
                             for h in HORIZONS}}
    opening = existing[entry_day]["open"]
    sized = plan_lots(opening)
    if sized["shares_indicative"] == 0:
        return {"stock": symbol, "status": sized["state"], "entry_session": entry_day,
                "horizons": {}}
    shares = sized["shares_indicative"]
    # Opening snapshot is an OHLC scenario, not an observed order book fill.
    result = {"stock": symbol, "status": "OHLC_OPEN_PAPER_SCENARIO",
              "entry_session": entry_day, "entry_open_raw": format(opening, "f"),
              "shares_scenario": shares, "gross_cny": sized["gross_indicative_cny"],
              "execution_proof": "NONE_NO_MINUTE_ORDERBOOK",
              "horizons": {}}
    stock_days = [x["date"] for x in series]
    j = stock_days.index(entry_day)
    for h in HORIZONS:
        if j + h >= len(series):
            result["horizons"][str(h)] = {
                "status": "UNMATURED", "after_cost_return": None, "excess_s0": None}
            continue
        exit_day = series[j + h]["date"]
        if exit_day > asof:
            result["horizons"][str(h)] = {
                "status": "UNMATURED", "after_cost_return": None, "excess_s0": None}
            continue
        pnl = _pnl(shares, opening, series[j + h]["close"])
        s0 = _matched_etf(index, entry_day, sized["gross_indicative_cny"], h, asof)
        if s0.get("exit_session") != exit_day:
            s0 = {"status": "BENCHMARK_EXIT_DATE_MISMATCH", "net_return": None}
        ret_s0 = s0["net_return"]
        path = series[j:j + h + 1]
        highest = max(path, key=lambda row: row["high"])
        lowest = min(path, key=lambda row: row["low"])
        excursions = {
            "mfe_from_entry_open": format(highest["high"] / opening - 1, "f"),
            "mae_from_entry_open": format(lowest["low"] / opening - 1, "f"),
            "mfe_session": highest["date"],
            "mae_session": lowest["date"],
            "high_low_are_daily_bounds_not_fills": True,
        }
        result["horizons"][str(h)] = {
            "path_excursions": excursions,
            "status": "PAIRED" if ret_s0 is not None else "S0_MISSING",
            "exit_session": exit_day,
            "after_cost_return": format(pnl, "f"),
            "s0": s0,
            "excess_s0": format(pnl - d(ret_s0, "s0"), "f")
            if ret_s0 is not None else None}
    return result


def track(frozen, observations, *, observed_at):
    captured = _iso(observed_at)
    frozen_at = _iso(frozen["freeze_time"])
    if captured < frozen_at:
        raise ValueError("future source cannot predate freeze")
    if frozen.get("trade_authorized") or not frozen.get("freeze_payload_sha256"):
        raise ValueError("requires immutable paper-only freeze")
    asof = captured.astimezone(BJ).date().isoformat()
    if observations.get("capture_time") and _iso(observations["capture_time"]) > captured:
        raise ValueError("future observations leaking into followup")
    if observations.get("first_observed_at") and _iso(observations["first_observed_at"]) > captured:
        raise ValueError("first seen after evaluation")
    original_date = frozen["signal_session"]
    if not original_date < asof:
        raise ValueError("cannot price future day on or before signal")
    raw = observations.get("bars_by_symbol", {})
    errors = dict(observations.get("errors", {}))
    try:
        etf = _clean_bars(raw.get("510300", []), asof)
    except (KeyError, ValueError) as exc:
        etf = []
        errors["510300"] = str(exc)
    index_dates = [x["date"] for x in etf if x["date"] >= frozen["measurement"]["next_session"]]
    actual_entry = index_dates[0] if index_dates else None
    selected = frozen["accounts"]["F1_LEFT"]["orders"]
    f1, f2 = [], []
    for order in selected:
        sym = order["stock"]
        prior = frozen.get("ohlc_price_history", {}).get("stocks", {}).get(sym, {})
        before = prior.get("bars", [])
        future = raw.get(sym, [])
        try:
            clean = _clean_bars(before + future, asof)
        except (KeyError, ValueError) as exc:
            clean = []
            errors[sym] = str(exc)
        actual = [x for x in clean if x["date"] > original_date]
        if actual_entry is None:
            f1.append({"stock": sym, "status": "NEXT_ACTUAL_SESSION_PENDING",
                       "horizons": {}})
        else:
            f1.append(_scenario(sym, actual_entry, clean, etf,
                                order["gross_indicative_cny"], asof))
        # F2 can only confirm on a *completed* later session and enter the
        # following true benchmark date. The comparison follows F2's own entry.
        confirmation = None
        previous = next((x for x in clean if x["date"] == original_date), None)
        for day in actual[:3]:
            if previous and weak_confirmation(previous["low"], day["low"],
                                              previous["close"], day["close"]):
                confirmation = day["date"]
                break
            previous = day
        eligible_next = ([day for day in index_dates if confirmation and day > confirmation])
        if eligible_next:
            outcome = _scenario(sym, eligible_next[0], clean, etf,
                                order["gross_indicative_cny"], asof)
            outcome["confirmation_day"] = confirmation
            f2.append(outcome)
        else:
            f2.append({"stock": sym, "status": ("WAIT_CONFIRMATION" if confirmation is None
                       else "WAIT_NEXT_OPEN_AFTER_CONFIRMATION"),
                       "confirmation_day": confirmation, "horizons": {}})
    result = {
        "schema": 1, "version": "NT_LEFT_ENTRY_FOLLOWUP_EXP0011",
        "source_freeze_sha256": frozen["freeze_payload_sha256"],
        "first_observed_at": captured.isoformat(), "asof": asof,
        "source_new_ohlc_sha256": digest(observations),
        "source_new_ohlc": observations,
        "first_actual_benchmark_session": actual_entry,
        "F1_LEFT": f1, "F2_WEAK": f2,
        "S0": "PER_LEG_SAME_ENTRY_TIME_AND_CASH_PAIRED_WHEN_MATURE",
        "N_NON_FLOW": "NOT_YET_MATURED_MATCHED_CONTROL",
        "errors": errors,
        "trade_authorized": False, "broker_orders": [],
        "execution_assertion": "OHLC_OPEN_SCENARIO_NOT_AN_EXECUTED_TRADE"}
    result["snapshot_sha256"] = digest(result)
    return result
