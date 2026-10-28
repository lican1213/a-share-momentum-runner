"""Research-only bridge: four core CSI300 ETF creations -> beneficiary stock watchlists.

The output is NOT observed Huijin stock purchases, ETF AP executions, a validated
stock alpha, or permission to place orders. Effective flow-through depends on
actual PCF substitution, inventory and arbitrage; see wiki/experiments/EXP-0003.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Mapping

from national_team.core_flow_factors import CORE_FOUR, DataGateError, dec, utc_aware


def _stamp(value: Any, label: str, cutoff: datetime) -> datetime:
    result = utc_aware(value, label)
    if result > cutoff:
        raise DataGateError(f"{label}: not public by decision cutoff")
    return result


def _url(value: Any, label: str) -> str:
    result = str(value or "")
    if not result.startswith("https://"):
        raise DataGateError(f"{label}: missing source URL")
    return result


def research_stock_watchlists(
    core_metrics: Mapping[str, Any],
    baskets: Mapping[str, Mapping[str, Any]],
    stock_snapshots: Mapping[str, Mapping[str, Any]],
    *,
    decision_cutoff: str,
    top_n: int = 5,
) -> dict:
    """Use source-timestamped basket weights and stock liquidity.

    baskets[ETF] = {asof_date, published_at, source_url, representation,
                    weights:{stock:decimal}, cash_substitution_unresolved:bool}
    stock_snapshots[stock] = {asof_date, published_at, source_url,
                    adv20_cny, freefloat_mv_cny, rel_strength20,
                    is_st, suspended, listing_sessions, limit_up_locked}

    W_i = sum_e ETF_flow_proxy_e * basket_weight_ei,
    impact_capacity_proxy = W_i / stock_20day_average_turnover.
    No synthetic flows, holdings, equities or inference-time forward data.
    """
    if tuple(core_metrics.get("codes", ())) != CORE_FOUR or core_metrics.get("basket_name") != "core_csi300_four":
        raise DataGateError("only original fixed four CSI300 ETFs are allowed as baseline")
    trade_date = core_metrics.get("trade_date")
    try:
        date.fromisoformat(str(trade_date))
    except ValueError:
        raise DataGateError("missing core indicator trading date") from None
    cutoff = utc_aware(decision_cutoff, "decision_cutoff")
    _stamp(core_metrics.get("decision_cutoff"), "source original factor decision cutoff", cutoff)
    if cutoff.date() < date.fromisoformat(trade_date):
        raise DataGateError("decision cutoff precedes flow observation trading date")
    if not isinstance(top_n, int) or not 1 <= top_n <= 20:
        raise DataGateError("top_n must be between 1 and 20")
    if not core_metrics.get("five_day"):
        raise DataGateError("missing complete five-session original four-ETF funding intensity")
    five_ratio = Decimal(str(core_metrics["five_day"]["net_creation_pct_initial_aum"]))
    flow_raw = core_metrics.get("per_etf_daily_flow_proxy_cny")
    if not isinstance(flow_raw, Mapping) or set(flow_raw) != set(CORE_FOUR):
        raise DataGateError("per-ETF same-date flow contributions absent; no allocation imputation")
    flows: dict[str, Decimal] = {}
    for etf in CORE_FOUR:
        raw_value = flow_raw[etf]
        # Negative flows are allowed; unlike "shares" they are signed.
        try:
            value = Decimal(str(raw_value))
        except Exception:
            raise DataGateError(f"{etf}: invalid signed net-flow number") from None
        if not value.is_finite():
            raise DataGateError(f"{etf}: nonfinite net-flow number")
        flows[etf] = value
    total = sum(flows.values(), Decimal(0))
    if total != Decimal(str(core_metrics.get("daily_net_creation_proxy_cny"))):
        raise DataGateError("sum of four ETF shares-flow contributions != declared headline total")
    if set(baskets) != set(CORE_FOUR):
        raise DataGateError("need four current PIT constituent/PCF snapshots; no subset imputation")

    weight_matrix: dict[str, dict[str, Decimal]] = {}
    representation: dict[str, str] = {}
    unresolved = []
    source_urls = {}
    for etf in CORE_FOUR:
        entry = baskets[etf]
        _url(entry.get("source_url"), f"{etf} basket source")
        _stamp(entry.get("published_at"), f"{etf} basket publication", cutoff)
        effective_date = entry.get("asof_date")
        if effective_date != trade_date:
            raise DataGateError(f"{etf}: need composition applicable to precise signal trading date")
        typ = entry.get("representation")
        if typ not in ("ETF_PORTFOLIO_WEIGHT", "PCF_VALUE_ESTIMATE"):
            raise DataGateError(f"{etf}: unsupported weight source representation")
        weights = entry.get("weights")
        if not isinstance(weights, Mapping) or not weights:
            raise DataGateError(f"{etf}: missing full basket weights")
        parsed = {str(stock): dec(w, f"{etf} {stock} basket weight") for stock, w in weights.items()}
        if any(len(stock) != 6 or not stock.isdigit() for stock in parsed):
            raise DataGateError(f"{etf}: invalid A-share stock code")
        total_weight = sum(parsed.values(), Decimal(0))
        # Cash and substitution create residuals; however tiny disclosed subsets
        # cannot masquerade as a near-complete ETF basket.
        if not Decimal("0.90") <= total_weight <= Decimal("1.01"):
            raise DataGateError(f"{etf}: insufficient/full-basket weight coverage {total_weight}")
        weight_matrix[etf] = parsed
        representation[etf] = typ
        source_urls[etf] = entry["source_url"]
        if entry.get("cash_substitution_unresolved"):
            unresolved.append(etf)

    all_stocks = sorted(set().union(*(set(v) for v in weight_matrix.values())))
    if not all_stocks:
        raise DataGateError("empty union of four ETF constituent baskets")
    missing = sorted(set(all_stocks).difference(stock_snapshots))
    if missing:
        raise DataGateError(f"missing point-in-time stock snapshots: {len(missing)} instruments")
    stocks = []
    excluded = []
    for stock in all_stocks:
        row = stock_snapshots[stock]
        _url(row.get("source_url"), f"{stock} stock source")
        _stamp(row.get("published_at"), f"{stock} stock publication", cutoff)
        if row.get("asof_date") != trade_date:
            raise DataGateError(f"{stock}: stale stock liquidity / state snapshot")
        adv = dec(row.get("adv20_cny"), f"{stock} 20d turnover", positive=True)
        float_mv = dec(row.get("freefloat_mv_cny"), f"{stock} freefloat value", positive=True)
        try:
            relative_strength = Decimal(str(row.get("rel_strength20")))
        except Exception:
            raise DataGateError(f"{stock}: missing relative strength") from None
        if not relative_strength.is_finite():
            raise DataGateError(f"{stock}: nonfinite relative strength")
        pressure = sum((flows[etf] * weight_matrix[etf].get(stock, Decimal(0))
                        for etf in CORE_FOUR), Decimal(0))
        reasons = []
        if row.get("is_st") is not False:
            reasons.append("ST_OR_UNKNOWN")
        if row.get("suspended") is not False:
            reasons.append("SUSPENDED_OR_UNKNOWN")
        if row.get("limit_up_locked") is not False:
            reasons.append("LIMIT_UP_LOCKED_OR_UNKNOWN")
        if not isinstance(row.get("listing_sessions"), int) or row["listing_sessions"] < 250:
            reasons.append("IPO_HISTORY_INSUFFICIENT")
        if adv < Decimal("100000000"):
            reasons.append("BELOW_PRESET_100M_CNY_ADV20")
        if pressure <= 0:
            reasons.append("NO_POSITIVE_IMPLIED_BASKET_EXPOSURE")
        item = {
            "symbol": stock, "implied_basket_exposure_cny": format(pressure, "f"),
            "potential_exposure_over_adv20": format(pressure / adv, "f"),
            "potential_exposure_over_freefloat_mv": format(pressure / float_mv, "f"),
            "relative_strength20": format(relative_strength, "f"),
            "input_source_url": row["source_url"],
            "screen_rejections": reasons,
        }
        if reasons:
            excluded.append(item)
        else:
            stocks.append(item)
    # Important: four funds track effectively the SAME benchmark. Exposure
    # scaled by freefloat can be almost constant, so never label that as alpha.
    by_mechanical_pressure = sorted(
        stocks, key=lambda x: (-Decimal(x["potential_exposure_over_adv20"]), x["symbol"]))[:top_n]
    confirmation = [x for x in stocks if Decimal(0) < Decimal(x["relative_strength20"]) <= Decimal("0.10")]
    by_relative_confirmation = sorted(
        confirmation, key=lambda x: (-Decimal(x["relative_strength20"]),
                                     -Decimal(x["potential_exposure_over_adv20"]), x["symbol"]))[:top_n]
    status = "PIT_RESEARCH_WATCHLIST_ONLY"
    if five_ratio <= 0 or total <= 0:
        status = "NO_POSITIVE_CORE_FUNDING_EVENT"
        by_mechanical_pressure, by_relative_confirmation = [], []
    return {
        "status": status,
        "source_basket": "core_csi300_four",
        "trade_date": trade_date, "decision_cutoff": decision_cutoff,
        "core_total_daily_flow_proxy_cny": format(total, "f"),
        "core_five_day_flow_ratio": format(five_ratio, "f"),
        "basket_representation": representation, "basket_sources": source_urls,
        "cash_substitution_unresolved_etfs": unresolved,
        "stock_coverage": len(all_stocks),
        "eligible_stock_count": len(stocks),
        "rejected_stock_count": len(excluded),
        "top_by_implied_flow_over_turnover": by_mechanical_pressure,
        "top_by_relative_price_confirmation": by_relative_confirmation,
        "excluded_diagnostics": excluded,
        "etf_hold_baseline": "core CSI300 ETF / low-cost replication to be tested as primary alternative",
        "identifies_investor": False,
        "is_actual_stock_purchase": False,
        "is_ap_execution_evidence": False,
        "out_of_sample_validated": False,
        "broker_trade_authorized": False,
        "release_reason": (
            "Daily ETF share flow is ETF-wide, not attributable to state-owned investors. "
            "ETF shares may be created in kind or via cash substitution; basket exposure is NOT "
            "actual stock order flow. Cross-sectional alpha and executable 5/10/20d excess "
            "returns versus direct ETF holding remain unvalidated."
        ),
    }
