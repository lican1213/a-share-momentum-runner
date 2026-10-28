"""Original 2026-10-27 four-ETF national-team FLOW PROXY indicators.

Strict, source-aware, point-in-time arithmetic. Pure functions; NO invented data,
NO network calls, NO inference of which investor subscribed/redeemed ETF shares.

The original FOUR CSI300 ETFs always form the headline series. Any expanded
basket requires a different name and must not be concatenated into it.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping, Sequence

CORE_FOUR = ("510300", "510310", "510330", "159919")
EXPANDED_ONLY = ("510050", "510500", "512500", "512100", "159845")
CORE_VERSION = "NT-CORE4-20261027-v1.0"
FLOW_THRESHOLD = Decimal("0.03")


class DataGateError(ValueError):
    """Missing/inconsistent source data: no metric and no signal authorized."""


def dec(value: Any, label: str, *, positive: bool = False) -> Decimal:
    if isinstance(value, bool):
        raise DataGateError(f"{label}: boolean is not a financial value")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise DataGateError(f"{label}: missing / malformed numeric value") from None
    if not result.is_finite() or (positive and result <= 0) or (not positive and result < 0):
        raise DataGateError(f"{label}: invalid sign or nonfinite")
    return result


def utc_aware(value: Any, label: str) -> datetime:
    try:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        raise DataGateError(f"{label}: invalid ISO8601 publication time") from None
    if result.tzinfo is None or result.utcoffset() is None:
        raise DataGateError(f"{label}: timestamp must include timezone offset")
    return result


def validate_observation(row: Mapping[str, Any], code: str, date: str,
                         cutoff: datetime | None) -> dict:
    if row.get("share_unit") != "shares" or row.get("nav_unit") != "CNY/share":
        raise DataGateError(f"{code} {date}: requires raw shares and CNY/share, not lots or 100m shares")
    if row.get("corporate_action") not in (None, False, "none"):
        raise DataGateError(f"{code} {date}: split/consolidation unresolved")
    if not row.get("source_url") or not str(row.get("source_url")).startswith("https://"):
        raise DataGateError(f"{code} {date}: missing original source URL")
    if not row.get("nav_source_url") or not str(row.get("nav_source_url")).startswith("https://"):
        raise DataGateError(f"{code} {date}: missing NAV source URL")
    shares = dec(row.get("shares"), f"{code} {date} shares")
    nav = dec(row.get("nav"), f"{code} {date} nav", positive=True)
    published_at = utc_aware(row.get("published_at"), f"{code} {date} shares")
    nav_published_at = utc_aware(row.get("nav_published_at"), f"{code} {date} NAV")
    if cutoff is not None and max(published_at, nav_published_at) > cutoff:
        raise DataGateError(f"{code} {date}: shares/NAV not public before inference cutoff")
    if row.get("aum") is not None:
        if not str(row.get("aum_source_url", "")).startswith("https://"):
            raise DataGateError(f"{code} {date}: official AUM requires a source URL")
        aum_published = utc_aware(row.get("aum_published_at"), f"{code} {date} AUM")
        if cutoff is not None and aum_published > cutoff:
            raise DataGateError(f"{code} {date}: AUM not public before inference cutoff")
        aum = dec(row["aum"], f"{code} {date} aum")
    else:
        aum = shares * nav
    return {
        "shares": shares, "nav": nav, "aum": aum,
        "aum_is_estimate": row.get("aum") is None,
        "corporate_action_explicitly_checked": row.get("corporate_action") is not None,
        "published_at": published_at,
        "nav_published_at": nav_published_at,
        "source_url": str(row["source_url"]),
        "nav_source_url": str(row["nav_source_url"]),
    }


def validate_market_denominator(row: Mapping[str, Any] | None, date: str,
                                expected_kind: str, cutoff: datetime | None) -> Decimal | None:
    if row is None:
        return None
    if row.get("date") != date or row.get("kind") != expected_kind:
        raise DataGateError(f"{expected_kind}: denominator date/type mismatch")
    if row.get("unit") != "CNY" or not str(row.get("source_url", "")).startswith("https://"):
        raise DataGateError(f"{expected_kind}: expected CNY with traceable source")
    pub = utc_aware(row.get("published_at"), f"{expected_kind} publication")
    if cutoff is not None and pub > cutoff:
        raise DataGateError(f"{expected_kind}: denominator unavailable at cutoff")
    return dec(row.get("value"), f"{expected_kind} value", positive=True)


def calculate(
    panel: Mapping[str, Mapping[str, Mapping[str, Any]]],
    trading_dates: Sequence[str],
    date: str,
    *,
    basket: Sequence[str] = CORE_FOUR,
    basket_name: str = "core_csi300_four",
    decision_cutoff: str | None = None,
    ordinary_float_mv: Mapping[str, Any] | None = None,
    free_float_mv: Mapping[str, Any] | None = None,
) -> dict:
    """Shares are in raw units; NAV CNY/share; AUM and market cap CNY.

    1-day: sum_i[(Shares_t - Shares_t-1) * NAV_t].
    PRIMARY 5-day: sum over each of five consecutive daily 1-day proxies.
    SECONDARY 5-day endpoint: sum_i[(Shares_t - Shares_t-5) * NAV_t].
    Difference is due to NAV timing. Neither equals verified investor cash flow.
    """
    codes = tuple(basket)
    if not codes or len(set(codes)) != len(codes) or any(x not in CORE_FOUR + EXPANDED_ONLY for x in codes):
        raise DataGateError("basket must contain unique, predeclared ETF codes")
    if basket_name == "core_csi300_four" and codes != CORE_FOUR:
        raise DataGateError("original four-ETF indicator cannot be silently expanded or reordered")
    if tuple(trading_dates) != tuple(sorted(set(trading_dates))) or date not in trading_dates:
        raise DataGateError("dates must be unique chronological exchange sessions including target")
    cutoff = utc_aware(decision_cutoff, "decision_cutoff") if decision_cutoff is not None else None
    at = trading_dates.index(date)
    unverified_actions = set()
    if at < 1:
        raise DataGateError("at least prior one actual trading session is required")

    def rows(day: str) -> dict[str, dict]:
        result = {}
        for code in codes:
            data = panel.get(day, {}).get(code)
            if data is None:
                raise DataGateError(f"{code} {day}: missing ETF shares/NAV, no basket imputation")
            result[code] = validate_observation(data, code, day, cutoff)
            if not result[code]["corporate_action_explicitly_checked"]:
                unverified_actions.add(f"{day}:{code}")
        return result

    today = rows(date)
    previous = rows(trading_dates[at - 1])
    day_delta = {code: today[code]["shares"] - previous[code]["shares"] for code in codes}
    one_day = sum((day_delta[c] * today[c]["nav"] for c in codes), Decimal(0))
    current_aum = sum((today[c]["aum"] for c in codes), Decimal(0))
    current_aum_proxy = sum((today[c]["shares"] * today[c]["nav"] for c in codes), Decimal(0))
    aum_estimated = any(today[c]["aum_is_estimate"] for c in codes)
    d_ord = validate_market_denominator(ordinary_float_mv, date, "CSI300_ordinary_float_mv", cutoff)
    d_free = validate_market_denominator(free_float_mv, date, "CSI300_free_float_mv", cutoff)
    if basket_name != "core_csi300_four" and (d_ord is not None or d_free is not None):
        raise DataGateError("CSI300-only float denominator cannot be attached to expanded mixed-index basket")

    def fmt(x: Decimal | None) -> str | None:
        return None if x is None else format(x, "f")

    five_day = None
    if at >= 5:
        start = trading_dates[at - 5]
        start_rows = rows(start)
        five_sum = Decimal(0)
        for pos in range(at - 4, at + 1):
            d = trading_dates[pos]
            cur = rows(d)
            prev = rows(trading_dates[pos - 1])
            five_sum += sum(((cur[c]["shares"] - prev[c]["shares"]) * cur[c]["nav"] for c in codes), Decimal(0))
        initial_aum = sum((start_rows[c]["aum"] for c in codes), Decimal(0))
        if initial_aum <= 0:
            raise DataGateError("initial 5d AUM zero")
        endpoint_sum = sum(((today[c]["shares"] - start_rows[c]["shares"]) * today[c]["nav"] for c in codes), Decimal(0))
        ratio = five_sum / initial_aum
        five_day = {
            "start": start,
            "end": date,
            "net_creation_cny_daily_sum": fmt(five_sum),
            "net_creation_cny_endpoint_nav": fmt(endpoint_sum),
            "initial_aum_cny": fmt(initial_aum),
            "net_creation_pct_initial_aum": fmt(ratio),
            "endpoint_pct_initial_aum": fmt(endpoint_sum / initial_aum),
            "hypothetical_abs_3pct_alert": abs(ratio) >= FLOW_THRESHOLD,
            "threshold_is_unvalidated": True,
            "method_difference_warning": "daily NAV-weighted flow and endpoint-NAV flow are different proxies; retain both",
        }

    return {
        "indicator_version": CORE_VERSION if basket_name == "core_csi300_four" else f"EXTENDED:{basket_name}",
        "basket_name": basket_name,
        "codes": list(codes),
        "trade_date": date,
        "prior_date": trading_dates[at - 1],
        "decision_cutoff": decision_cutoff,
        "unit_money": "CNY",
        "fund_aum_cny": fmt(current_aum),
        "aum_is_partially_estimated": aum_estimated,
        "shares_times_nav_estimate_cny": fmt(current_aum_proxy),
        "ordinary_float_coverage_ratio": fmt(current_aum / d_ord) if d_ord else None,
        "free_float_coverage_ratio": fmt(current_aum / d_free) if d_free else None,
        "coverage_ratios_are_not_national_team_holdings": True,
        "corporate_actions_explicitly_verified": not bool(unverified_actions),
        "corporate_action_unknown_dates_codes": sorted(unverified_actions),
        "daily_share_changes": {c: fmt(day_delta[c]) for c in codes},
        "per_etf_daily_flow_proxy_cny": {c: fmt(day_delta[c] * today[c]["nav"]) for c in codes},
        "daily_net_creation_proxy_cny": fmt(one_day),
        "five_day": five_day,
        "investor_identity_attributable": False,
        "trade_signal_authorized": False,
        "missing_denominator_is_null": True,
        "method_note": "ETF-wide primary issuance/redemption proxy; no investor identity or actual broker cash flow proven",
    }
