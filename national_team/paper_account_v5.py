"""EXP-0014: one daily-OHLC paper ledger for the three existing V5 policies.

Prices are precommitted OHLC execution *scenarios*, never broker confirmations.
Increment from the last persisted market session; do not backfill missed entries.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from decimal import Decimal

from national_team.left_entry_v4 import (
    CAPITAL, FEE_RATE, MAX_LOSS_PER_STOCK, SLIPPAGE_RATE,
    STAMP_SELL_RATE, STOP_DISTANCE, d, digest, plan_lots,
)
from national_team.left_entry_v5 import POLICIES, RIGHT_POLICY

ARMS = (*POLICIES, RIGHT_POLICY)
TARGET = Decimal("0.03")
MAX_POSITIONS = 2
MIN_COMMISSION = Decimal("5")


def _money(value):
    return format(value.quantize(Decimal("0.01")), "f")


def _charge(value):
    return max(MIN_COMMISSION, value * FEE_RATE)


def _buy(open_price, shares, *, etf=False):
    gross = d(open_price, "opening") * shares * (1 + SLIPPAGE_RATE)
    return gross + _charge(gross)


def _sell(price, shares, *, etf=False):
    gross = d(price, "exit") * shares * (1 - SLIPPAGE_RATE)
    return gross - _charge(gross) - (Decimal(0) if etf else gross * STAMP_SELL_RATE)


def _blank():
    return {
        "cash_cny": _money(CAPITAL), "positions": [], "closed_trades": [],
        "decisions": [], "realized_pnl_cny": "0.00",
        "s0_realized_pnl_cny": "0.00",
    }


def _time(value):
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.utcoffset() is None:
        raise ValueError("naive source clock")
    return parsed


def _quotes(events, asof, captured_at):
    bars, intents, errors = {}, [], []
    clock = _time(captured_at)
    for freeze, source in events:
        if freeze.get("trade_authorized") or not freeze.get("freeze_payload_sha256"):
            raise ValueError("unverifiable paper freeze")
        if source.get("first_observed_at") and _time(source["first_observed_at"]) > clock:
            raise ValueError("future market observation")
        if _time(freeze["freeze_time"]) > clock:
            raise ValueError("freeze after price evaluation")
        for code, rows in source.get("bars_by_symbol", {}).items():
            target = bars.setdefault(code, {})
            for item in rows:
                day = str(item["date"])[:10]
                if day > asof:
                    raise ValueError("future bar beyond asof")
                values = {k: d(item[k], k) for k in ("open", "high", "low", "close")}
                if min(values.values()) <= 0 or values["low"] > min(values["open"], values["close"]) or values["high"] < max(values["open"], values["close"]):
                    raise ValueError("invalid paper OHLC")
                if day in target and target[day] != values:
                    errors.append(f"SOURCE_CONFLICT:{code}:{day}")
                    continue  # First observed within this snapshot wins.
                target[day] = values
        for arm in ARMS:
            for order in freeze.get("paper_policies", {}).get(arm, {}).get("orders", []):
                intents.append({
                    "arm": arm, "stock": order["stock"],
                    "signal_session": freeze["signal_session"],
                    "intended_session": order["intended_session"],
                    "freeze_sha256": freeze["freeze_payload_sha256"],
                })
    intents.sort(key=lambda x: (x["intended_session"], x["signal_session"], x["arm"], x["stock"]))
    return bars, intents, errors


def _exit_order(position, bar, holding_days):
    if holding_days < 1:
        return None
    opening, low, high = (bar[k] for k in ("open", "low", "high"))
    stop = d(position["entry_open_raw"], "entry") * (1 - STOP_DISTANCE)
    target = d(position["entry_open_raw"], "entry") * (1 + TARGET)
    if opening <= stop:
        return opening, "GAP_STOP_AT_OPEN"
    if opening >= target:
        return opening, "GAP_TARGET_AT_OPEN"
    if low <= stop:  # Ambiguous same-day stop and target: stop first.
        return stop, "STOP_TOUCH_OHLC_STOP_FIRST"
    if high >= target:
        return target, "TARGET_TOUCH_OHLC"
    if holding_days >= 2:
        return bar["close"], "T_PLUS_2_PLANNED_CLOSE_PROXY"
    return None


def _close(account, pos, *, day, price, reason, etf_bar,
           late_ohlc_reconciliation=False):
    proceeds = _sell(price, pos["shares"])
    cost = d(pos["buy_total_cny"], "buy cost")
    profit = proceeds - cost
    account["cash_cny"] = _money(d(account["cash_cny"], "cash") + proceeds)
    account["realized_pnl_cny"] = _money(d(account["realized_pnl_cny"], "realized") + profit)
    s0_profit = None
    gap_open = reason in ("GAP_STOP_AT_OPEN", "GAP_TARGET_AT_OPEN")
    if pos["s0_shares"] and etf_bar:
        # The ETF opening print is the synchronized daily-bar proxy for a
        # stock gap exit. An intraday touch has no synchronized ETF print.
        s0_exit_price = etf_bar["open"] if gap_open else etf_bar["close"]
        s0_profit = _sell(s0_exit_price, pos["s0_shares"], etf=True) - d(
            pos["s0_buy_total_cny"], "s0 cost")
        account["s0_realized_pnl_cny"] = _money(
            d(account["s0_realized_pnl_cny"], "s0 realized") + s0_profit)
    # Daily bars cannot identify ETF prices at intraday stock exits.
    intraday = not gap_open and reason != "T_PLUS_2_PLANNED_CLOSE_PROXY"
    benchmark_method = ("ETF_SAME_SESSION_OPEN_PROXY" if gap_open else
                        "ETF_DAILY_CLOSE_PROXY_NOT_SAME_TIME" if intraday else
                        "ETF_SAME_SESSION_CLOSE_PROXY")
    s0_envelope = None
    if pos["s0_shares"] and etf_bar and intraday:
        low_pnl = _sell(etf_bar["low"], pos["s0_shares"], etf=True) - d(
            pos["s0_buy_total_cny"], "s0 cost")
        high_pnl = _sell(etf_bar["high"], pos["s0_shares"], etf=True) - d(
            pos["s0_buy_total_cny"], "s0 cost")
        s0_envelope = {
            "excess_if_etf_high_cny": _money(profit - high_pnl),
            "excess_if_etf_low_cny": _money(profit - low_pnl),
            "interpretation": "DAILY_BAR_BOUNDS_NOT_SYNCHRONIZED_EXECUTION",
        }
    execution_confidence = ("DAILY_OPEN_PROXY" if gap_open else
                            "DAILY_CLOSE_PROXY" if not intraday else
                            "DAILY_OHLC_STOP_FIRST_AMBIGUOUS"
                            if reason == "STOP_TOUCH_OHLC_STOP_FIRST" else
                            "DAILY_OHLC_INTRADAY_ORDER_UNKNOWN")
    # Raw yuan P&L from different round-lot notionals is not equal-capital
    # excess. Scale the net, fee-inclusive ETF return to the stock entry cost.
    equal_capital_s0 = None
    if s0_profit is not None:
        equal_capital_s0 = s0_profit * cost / d(pos["s0_buy_total_cny"], "s0 cost")
    account["closed_trades"].append({
        "id": pos["id"], "stock": pos["stock"], "entry_session": pos["entry_session"],
        "exit_session": day, "shares": pos["shares"],
        "entry_open_raw": pos["entry_open_raw"], "exit_price_raw": format(price, "f"),
        "exit_reason": reason, "net_pnl_cny": _money(profit),
        "s0_matched_net_pnl_cny": _money(s0_profit) if s0_profit is not None else None,
        "excess_s0_cny": _money(profit - s0_profit) if s0_profit is not None else None,
        "s0_equal_capital_pnl_cny": _money(equal_capital_s0) if equal_capital_s0 is not None else None,
        "excess_s0_equal_capital_cny": _money(profit - equal_capital_s0) if equal_capital_s0 is not None else None,
        "equal_capital_method": "NET_FEE_ADJUSTED_ETF_RETURN_ON_STOCK_COST_NOT_EXECUTABLE" if equal_capital_s0 is not None else None,
        "late_ohlc_reconciliation": late_ohlc_reconciliation,
        "price_method": "DAILY_OHLC_BRACKET_OR_PRECOMMITTED_CLOSE_PROXY",
        "execution_confidence": execution_confidence,
        "benchmark_exit_method": benchmark_method if etf_bar else "BENCHMARK_MISSING",
        "s0_intraday_excess_envelope_cny": s0_envelope,
        "s0_notional_entry_cny": pos.get("s0_buy_total_cny"),
        "stock_notional_entry_cny": pos["buy_total_cny"],
    })


def _enter(account, intent, stock_bar, etf_bar, day):
    key = f'{intent["signal_session"]}:{intent["arm"]}:{intent["stock"]}'
    existing = {p["id"] for p in account["positions"]}
    if key in existing or any(x["id"] == key for x in account["closed_trades"]):
        return
    reason = None
    if stock_bar is None:
        reason = "ENTRY_OHLC_MISSING_NO_RETROSPECTIVE_FILL"
    elif any(p["stock"] == intent["stock"] for p in account["positions"]):
        reason = "ALREADY_HELD"
    elif len(account["positions"]) >= MAX_POSITIONS:
        reason = "MAX_TWO_OPEN_POSITIONS"
    else:
        gross_held = sum((d(p["entry_open_raw"], "entry") * p["shares"]
                          for p in account["positions"]), Decimal(0))
        sized = plan_lots(stock_bar["open"], gross_held)
        shares = sized["shares_indicative"]
        cost = _buy(stock_bar["open"], shares) if shares else Decimal(0)
        risk = (stock_bar["open"] * shares * STOP_DISTANCE + 2 * MIN_COMMISSION
                + stock_bar["open"] * shares * (2 * SLIPPAGE_RATE + STAMP_SELL_RATE))
        if not shares or cost > d(account["cash_cny"], "cash") or risk > MAX_LOSS_PER_STOCK:
            reason = "LOT_CASH_OR_RISK_BUDGET"
        else:
            etf_shares = 0
            etf_cost = Decimal(0)
            if etf_bar:
                while etf_shares + 100 <= shares * stock_bar["open"] / etf_bar["open"]:
                    maybe = _buy(etf_bar["open"], etf_shares + 100, etf=True)
                    if maybe > cost:
                        break
                    etf_shares += 100
                    etf_cost = maybe
            account["cash_cny"] = _money(d(account["cash_cny"], "cash") - cost)
            account["positions"].append({
                "id": key, "stock": intent["stock"], "freeze_sha256": intent["freeze_sha256"],
                "entry_session": day, "entry_open_raw": format(stock_bar["open"], "f"),
                "shares": shares, "buy_total_cny": _money(cost),
                "held_sessions": 0, "last_mark_close": format(stock_bar["close"], "f"),
                "last_mark_session": day, "s0_shares": etf_shares,
                "s0_buy_total_cny": _money(etf_cost) if etf_shares else None,
            })
            account["decisions"].append({"id": key, "session": day,
                                         "status": "PAPER_OPEN_PROXY_FILLED",
                                         "shares": shares, "cash_cost_cny": _money(cost)})
            return
    account["decisions"].append({"id": key, "session": day,
                                 "status": "PAPER_ENTRY_SKIPPED", "reason": reason})


def _summary(account, last_session):
    cash = d(account["cash_cny"], "cash")
    value = Decimal(0)
    stale = False
    for pos in account["positions"]:
        if pos["last_mark_session"] != last_session:
            stale = True
        value += _sell(pos["last_mark_close"], pos["shares"])
    equity = cash + value
    trades = account["closed_trades"]
    wins = sum(d(x["net_pnl_cny"], "pnl") > 0 for x in trades)
    paired = [x for x in trades if x["excess_s0_cny"] is not None]
    account["summary"] = {
        "cash_cny": _money(cash), "equity_after_estimated_exit_cost_cny": _money(equity),
        "net_pnl_cny": _money(equity - CAPITAL), "realized_pnl_cny": account["realized_pnl_cny"],
        "open_positions": len(account["positions"]), "closed_trades": len(trades),
        "win_rate": format(Decimal(wins) / len(trades), "f") if trades else None,
        "paired_s0_trades": len(paired),
        "paired_s0_close_proxy_trades": sum(
            t.get("benchmark_exit_method") == "ETF_DAILY_CLOSE_PROXY_NOT_SAME_TIME"
            for t in paired),
        "paired_s0_open_proxy_trades": sum(
            t.get("benchmark_exit_method") == "ETF_SAME_SESSION_OPEN_PROXY"
            for t in paired),
        "paired_s0_exact_intraday_trades": 0,
        "pending_quote_sessions": sum(
            len(p.get("pending_ohlc_sessions", [])) for p in account["positions"]),
        "realized_excess_s0_cny": _money(sum(
            (d(x["excess_s0_cny"], "excess") for x in paired), Decimal(0)))
            if paired else None,
        "realized_excess_s0_equal_capital_cny": _money(sum(
            (d(x["excess_s0_equal_capital_cny"], "equal capital excess")
             for x in paired if x.get("excess_s0_equal_capital_cny") is not None),
            Decimal(0))) if paired and all(
                x.get("excess_s0_equal_capital_cny") is not None for x in paired)
            else None,
        "mark_status": "STALE_PRICE" if stale else ("CURRENT_CLOSE_PROXY" if account["positions"] else "CASH_ONLY"),
        "market_session": last_session,
    }


def _reconcile_late_quotes(accounts, bars, last):
    """Revisit missing EXIT quotes, never missed entries, in session order.

    The ETF calendar can advance ahead of stock OHLC publication. Persisting
    that calendar cursor must not permanently lose a precommitted T+2 close.
    """
    if last is None:
        return
    etf = bars.get("510300", {})
    calendar = sorted(day for day in etf if day <= last)
    for account in accounts.values():
        still_open = []
        for pos in account["positions"]:
            pending = sorted(set(pos.get("pending_ohlc_sessions", [])) | {
                day for day in calendar
                if pos["last_mark_session"] < day <= last
                and day > pos["entry_session"]
            })
            processed = 0
            closed = False
            for day in pending:
                stock = bars.get(pos["stock"], {}).get(day)
                if stock is None or day not in etf:
                    break  # Never jump over an unpriced session.
                future_sessions = sum(day < later <= last for later in calendar)
                holding_days = pos["held_sessions"] - future_sessions
                exit_candidate = _exit_order(pos, stock, holding_days)
                if exit_candidate:
                    _close(account, pos, day=day, price=exit_candidate[0],
                           reason=exit_candidate[1], etf_bar=etf[day],
                           late_ohlc_reconciliation=True)
                    closed = True
                    break
                pos["last_mark_close"] = format(stock["close"], "f")
                pos["last_mark_session"] = day
                processed += 1
            if not closed:
                if pending[processed:]:
                    pos["pending_ohlc_sessions"] = pending[processed:]
                else:
                    pos.pop("pending_ohlc_sessions", None)
                still_open.append(pos)
        account["positions"] = still_open


def advance(previous, events, *, asof, captured_at):
    """Advance the independent accounts only on newly observed market sessions."""
    if previous and previous.get("version") != "NT_V5_PAPER_ACCOUNT_EXP0014":
        raise ValueError("incompatible previous paper ledger")
    last = previous.get("last_market_session") if previous else None
    accounts = deepcopy(previous["accounts"]) if previous else {a: _blank() for a in ARMS}
    for account in accounts.values():
        account.pop("summary", None)
    bars, intents, errors = _quotes(events, asof, captured_at)
    _reconcile_late_quotes(accounts, bars, last)
    sessions = sorted(day for day in bars.get("510300", {}) if day <= asof and
                      (last is None or day > last))
    existing_ids = {
        arm: {p["id"] for p in a["positions"]} |
             {t["id"] for t in a["closed_trades"]} |
             {t["id"] for t in a["decisions"]}
        for arm, a in accounts.items()
    }
    for intent in intents:
        if last is not None and intent["intended_session"] <= last:
            key = f'{intent["signal_session"]}:{intent["arm"]}:{intent["stock"]}'
            if key not in existing_ids[intent["arm"]]:
                accounts[intent["arm"]]["decisions"].append({
                    "id": key, "session": last, "status": "LATE_INTENT_NO_BACKFILL"})
                existing_ids[intent["arm"]].add(key)
    for day in sessions:
        etf = bars["510300"][day]
        for arm, a in accounts.items():
            still_open = []
            for pos in a["positions"]:
                stock = bars.get(pos["stock"], {}).get(day)
                if day > pos["entry_session"]:
                    pos["held_sessions"] += 1
                    if stock is None or pos.get("pending_ohlc_sessions"):
                        pending = pos.setdefault("pending_ohlc_sessions", [])
                        if day not in pending:
                            pending.append(day)
                    else:
                        candidate = _exit_order(pos, stock, pos["held_sessions"])
                        if candidate:
                            _close(a, pos, day=day, price=candidate[0],
                                   reason=candidate[1], etf_bar=etf)
                            continue
                if stock and not pos.get("pending_ohlc_sessions"):
                    pos["last_mark_close"] = format(stock["close"], "f")
                    pos["last_mark_session"] = day
                still_open.append(pos)
            a["positions"] = still_open
            for intent in intents:
                if intent["arm"] != arm or intent["intended_session"] != day:
                    continue
                key = f'{intent["signal_session"]}:{arm}:{intent["stock"]}'
                if key not in existing_ids[arm]:
                    _enter(a, intent, bars.get(intent["stock"], {}).get(day), etf, day)
                    existing_ids[arm].add(key)
        last = day
    for a in accounts.values():
        _summary(a, last)
    result = {
        "schema": 1, "version": "NT_V5_PAPER_ACCOUNT_EXP0014",
        "asof": asof, "capture_time": captured_at,
        "last_market_session": last, "accounts": accounts,
        "source_event_count": len(events), "source_errors": errors,
        "execution": "OHLC_PAPER_SCENARIO_NOT_BROKER_TRADE",
        "trade_authorized": False, "broker_orders": [],
    }
    result["snapshot_sha256"] = digest(result)
    return result
