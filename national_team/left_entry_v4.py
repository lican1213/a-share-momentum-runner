"""EXP-0011: source-anchored 50% exploratory left-side ETF-flow paper freeze.

The 50% gate is a historical CSI300 directional rate, NOT a calibrated stock
profit probability. No physical orders or backdated fills are produced.
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_FLOOR
from zoneinfo import ZoneInfo

from national_team.core_flow_factors import CORE_FOUR

VERSION = "NT_LEFT_ENTRY_V4_EXP0011"
CAPITAL = Decimal("30000")
MAX_GROSS = Decimal("10000")
MAX_PER_STOCK = Decimal("5000")
MAX_LOSS_PER_STOCK = Decimal("150")
FEE_RATE = Decimal("0.0003")
SLIPPAGE_RATE = Decimal("0.0005")
STAMP_SELL_RATE = Decimal("0.0005")
STOP_DISTANCE = Decimal("0.03")
BJ = ZoneInfo("Asia/Shanghai")


def d(value, label):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(f"{label}: not numeric") from None
    if not result.is_finite():
        raise ValueError(f"{label}: nonfinite")
    return result


def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def _when(value):
    stamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if stamp.utcoffset() is None:
        raise ValueError("naive publication time")
    return stamp


def admission(v3, *, threshold=Decimal("0.50")):
    if tuple(v3.get("method", {}).get("codes", ())) != CORE_FOUR:
        raise ValueError("four fixed CSI300 ETFs are mandatory")
    p = v3["summary"]["share_proxy"]["horizons"]["5"]
    n, wins = int(p["matured_events"]), int(p["wins"])
    if n <= 0 or not 0 <= wins <= n:
        raise ValueError("invalid matured event counts")
    observed = Decimal(wins) / Decimal(n)
    other = {h: v3["summary"]["share_proxy"]["horizons"][h]["hit_rate"]
             for h in ("10", "20")}
    return {"pilot_admitted": observed >= threshold, "threshold": str(threshold),
            "five_day_wins": wins, "five_day_matured": n,
            "five_day_historical_directional_hit_rate": format(observed, "f"),
            "other_horizons_directional_rates_not_gates": other,
            "interpretation": "RETROSPECTIVE_INDEX_DIRECTION_NOT_STOCK_PROFIT_PROBABILITY",
            "primary_coverage_ratio_available": bool(v3["summary"]["coverage_primary"]["raw_signal_days"])}


def features(bars, asof, index_r5):
    """Daily raw OHLC bars in ascending date order through asof; no forward bars."""
    if not isinstance(bars, list):
        raise ValueError("bars required")
    clean = []
    for item in bars:
        day = str(item["date"])[:10]
        if day > asof:
            continue
        close = d(item["close"], "close")
        low = d(item.get("low", item["close"]), "low")
        if close <= 0 or low <= 0 or low > close * Decimal("1.5"):
            raise ValueError("invalid price/low")
        clean.append((day, close, low))
    if len(clean) < 21:
        raise ValueError("need 21 actual sessions")
    if [x[0] for x in clean] != sorted(set(x[0] for x in clean)):
        raise ValueError("unsorted or duplicate trading dates")
    if clean[-1][0] != asof:
        raise ValueError("stock price missing on asof date")
    close = clean[-1][1]
    r5 = close / clean[-6][1] - 1
    ma20 = sum((x[1] for x in clean[-20:]), Decimal(0)) / 20
    ma_gap = close / ma20 - 1
    recent_low = min(x[2] for x in clean[-20:])
    chase = r5 > Decimal(".05") or ma_gap > Decimal(".05")
    left = (Decimal("-.08") <= r5 <= Decimal(".03")
            and r5 - index_r5 >= 0
            and Decimal("-.08") <= ma_gap <= Decimal(".03"))
    return {"close": format(close, "f"), "r5": format(r5, "f"),
            "relative_r5": format(r5 - index_r5, "f"),
            "ma20": format(ma20, "f"), "distance_ma20": format(ma_gap, "f"),
            "distance_low20": format(close / recent_low - 1, "f"),
            "chase_risk_high": chase, "left_entry_eligible": left and not chase}


def plan_lots(close, current_gross=Decimal(0)):
    """As-of close sizing only; NOT a future open execution or owned shares."""
    price = d(close, "close")
    if price <= 0:
        raise ValueError("invalid price")
    budget = min(MAX_PER_STOCK, MAX_GROSS - current_gross)
    lots = int((budget / (price * 100 * (1 + SLIPPAGE_RATE))).to_integral_value(rounding=ROUND_FLOOR))
    while lots > 0:
        shares = lots * 100
        gross = price * shares
        expected_cost = gross * (FEE_RATE * 2 + SLIPPAGE_RATE * 2 + STAMP_SELL_RATE)
        risk = gross * STOP_DISTANCE + expected_cost
        if risk <= MAX_LOSS_PER_STOCK and gross * (1 + SLIPPAGE_RATE) <= budget:
            return {"shares_indicative": shares, "last_close": str(price),
                    "gross_indicative_cny": format(gross, "f"),
                    "risk_with_roundtrip_cost_cny": format(risk, "f"),
                    "state": "WAIT_FUTURE_OPEN_FOR_PAPER_FILL"}
        lots -= 1
    return {"shares_indicative": 0, "last_close": str(price),
            "gross_indicative_cny": "0", "risk_with_roundtrip_cost_cny": "0",
            "state": "BOARD_LOT_OR_RISK_BUDGET_UNAVAILABLE"}


def weak_confirmation(prev_low, current_low, prev_close, current_close):
    """Only test *completed*, later real bars; future confirmation must stay pending."""
    return (d(current_low, "low") >= d(prev_low, "prev_low")
            and d(current_close, "close") >= d(prev_close, "prev_close"))


def freeze(v3, watch, prices, *, now, next_session, stock_limit=2):
    time = _when(now)
    if time > datetime.now(timezone.utc).astimezone(time.tzinfo):
        raise ValueError("freeze cannot be future-dated")
    if not 1 <= stock_limit <= 2:
        raise ValueError("initial pilot can hold at most two stocks")
    admit = admission(v3)
    asof = v3["daily"][-1]["date"]
    signal = v3["daily"][-1]
    if not all((signal.get("market_down"), signal.get("share_proxy_event"),
                d(signal.get("net_creation_1d_cny"), "net creation") > 0,
                d(signal.get("net_creation_5d_cny"), "5d net creation") > 0)):
        raise ValueError("latest complete-four session has no down-market positive event")
    if watch.get("funding_date") != asof:
        raise ValueError("watch and four-ETF signal dates differ")
    if watch.get("index_weight", {}).get("kind") not in (
        "CSI300_LATEST_INDEX_WEIGHT_PROXY_NOT_ETF_PCF", "CSI300_INDEX_PROXY_NOT_ETF_PCF"):
        raise ValueError("index weight provenance missing")
    if date.fromisoformat(next_session) <= time.astimezone(BJ).date():
        raise ValueError("no backdated/instant entry; future session required")
    src_times = [v3["source_provenance"]["as_of_utc"],
                 watch["event_first_public_no_earlier_than"],
                 watch["index_weight"]["first_observed_at"]]
    if any(_when(t) > time for t in src_times):
        raise ValueError("published source after frozen decision time")
    index_r5 = d(signal["index_ret5"], "index r5")
    candidates, missing = [], {}
    pool = watch.get("candidate_pool_pre_filter", [])
    weights = watch["index_weight"]["weights"]
    snapshots = watch.get("stock_snapshots", {})
    bars_map = prices.get("stocks", {})
    for code in pool:
        item = snapshots.get(code)
        market = bars_map.get(code)
        if not item or not market:
            missing[code] = "NO_SOURCE_BACKED_OHLC"
            continue
        if item.get("data_date") != asof or _when(item.get("first_observed_at")) > time:
            missing[code] = "WATCH_DATE_OR_PUBLICATION_MISMATCH"
            continue
        if market.get("asof") != asof or _when(market.get("first_observed_at")) > time:
            missing[code] = "OHLC_DATE_OR_PUBLICATION_MISMATCH"
            continue
        try:
            f = features(market["bars"], asof, index_r5)
            turnover = d(item["adv20_cny"], "adv20")
            if turnover <= 0:
                raise ValueError("zero liquidity")
            weight = d(weights[code], "index weight")
            entry = {"stock": code, "weight_index_proxy": format(weight, "f"),
                     "adv20_cny": str(item["adv20_cny"]),
                     "ohlc_source": market["source_url"],
                     "ohlc_source_sha256": market["source_sha256"],
                     "first_observed_at": market["first_observed_at"], **f}
            entry["reason"] = ("CHASE_RISK_HIGH" if f["chase_risk_high"]
                               else "LOW_LEFT_PASS" if f["left_entry_eligible"]
                               else "LEFT_FILTER_MISS")
            candidates.append(entry)
        except (ValueError, KeyError, TypeError) as exc:
            missing[code] = f"PRICE_VALIDATION:{str(exc)[:120]}"
    eligible = [x for x in candidates if x["left_entry_eligible"]]
    eligible.sort(key=lambda x: (
        -d(x["relative_r5"], "relative"), abs(d(x["r5"], "r5")),
        abs(d(x["distance_ma20"], "MA20")), -d(x["weight_index_proxy"], "weight"), x["stock"]))
    orders, used = [], Decimal(0)
    if admit["pilot_admitted"]:
        for item in eligible:
            if len(orders) >= stock_limit:
                break
            proposal = plan_lots(item["close"], used)
            if proposal["shares_indicative"] == 0:
                continue
            used += d(proposal["gross_indicative_cny"], "gross")
            orders.append({"stock": item["stock"], **proposal,
                           "intended_session": next_session, "fill": None,
                           "paper_position": 0})
    cluster = v3["events"]["share_proxy"][-1]
    if cluster["signal_date"] > asof:
        raise ValueError("cluster anchor cannot follow signal")
    s0 = {"instrument": "510300", "budget_cny": format(used, "f"),
          "status": "AWAIT_BENCHMARK_OPEN_AND_SAME_ENTRY_TIME",
          "entry_session": next_session, "filled_shares": 0, "net_return": None}
    result = {
        "schema": 1, "version": VERSION, "experiment_id": "EXP-0011",
        "freeze_time": time.isoformat(), "signal_session": asof,
        "cluster_anchor": cluster["signal_date"],
        "source_etf_record_sha256": digest(v3), "source_watch_record_sha256": digest(watch),
        "source_ohlc_snapshots_sha256": digest(prices),
        "ohlc_price_history": prices,
        "source_repo_sha": v3["source_provenance"].get("repo_source_commit"),
        "funding": {"codes": list(CORE_FOUR),
                    "primary_ratio_status": signal["ratio_status"],
                    "primary_ordinary_float_ratio": signal["ordinary_float_coverage_ratio"],
                    "positive_1d_cny_proxy": signal["net_creation_1d_cny"],
                    "positive_5d_cny_proxy": signal["net_creation_5d_cny"],
                    "index_ret5": str(index_r5),
                    "attribution": "FOUR_ETF_ALL_HOLDERS_NOT_STATE_TEAM_ACCOUNT"},
        "admission": admit,
        "universe": {"pool": len(pool), "ohlc_verified": len(candidates),
                     "low_left_eligible": len(eligible),
                     "missing_count": len(missing),
                     "weight_source": "CSI300_INDEX_PROXY_NOT_ETF_PCF"},
        "candidates_ranked": eligible,
        "excluded_chase": [x for x in candidates if x["chase_risk_high"]],
        "other_rejected_count": len(candidates) - len(eligible)
                                  - sum(x["chase_risk_high"] for x in candidates),
        "missing_stock_data": missing,
        "accounts": {
            "F1_LEFT": {"capital_cny": str(CAPITAL), "gross_cap_cny": str(MAX_GROSS),
                        "orders": orders, "filled": False,
                        "state": "PAPER_NEXT_OPEN_PENDING" if orders else "NO_SIZED_CANDIDATE"},
            "F2_WEAK": {"capital_cny": str(CAPITAL), "same_precommitted_candidates":
                        [x["stock"] for x in orders],
                        "confirmation_rule": "within 3 actual later sessions: low>=prev_low and close>=prev_close; enter following session",
                        "state": "WAIT_1_TO_3_ACTUAL_SESSIONS", "filled": False},
            "S0_ETF": s0,
            "N_NON_FLOW": {"state": "MATCHED_DOWNTURN_NON_EVENT_CONTROL_PENDING",
                           "selection": "same left filter on first future down day WITHOUT four-ETF positive event",
                           "net_return": None},
            "M_OLD": {"state": "OLD_A2_B_FROZEN_EXTERNAL_CONTROL_NOT_REWRITTEN",
                      "net_return": None}},
        "measurement": {"primary": "10d after-cost F1/F2 minus same-time S0; compare also N",
                        "secondary": ["5d", "20d", "T+3", "MAE", "fill_rate"],
                        "labels": "UNMATURED_NO_ENTRY",
                        "next_session": next_session,
                        "no_hypothetical_backdated_fills": True},
        "trade_authorized": False, "broker_orders": [],
        "no_claim_of_50pct_stock_profit_probability": True
    }
    result["freeze_payload_sha256"] = digest(result)
    return result
