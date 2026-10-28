"""Opportunity-first ETF funding to stock research scanner.

Ranks available, timestamp-verified evidence even when some ETF baskets or
stock rows are missing. Coverage and gaps remain explicit. No order submission.
This complements rather than replaces the strict accounting audit.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from national_team.core_flow_factors import CORE_FOUR, DataGateError, utc_aware


def _number(value: Any, label: str, positive=False) -> Decimal:
    try:
        if isinstance(value, bool):
            raise ValueError("boolean")
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise DataGateError(f"{label}: invalid numeric value") from None
    if not result.is_finite() or (positive and result <= 0):
        raise DataGateError(f"{label}: invalid sign/nonfinite")
    return result


def scan_opportunities(
    core_metrics: Mapping[str, Any],
    etf_baskets: Mapping[str, Mapping[str, Any]],
    stock_data: Mapping[str, Mapping[str, Any]],
    *,
    decision_cutoff: str,
    top_n: int = 10,
    max_basket_lag_days: int = 10,
    max_stock_lag_days: int = 7,
) -> dict:
    """Screen funds-to-equities with graceful per-source failure.

    ETF basket and stock rows must be published by decision cutoff. An older
    *still available* snapshot may be used in a research scan, with age shown.
    A missing ETF basket is not silently scaled up to the full four-fund flow.
    No hard-coded return window, stock age or turnover gate filters research.
    """
    if tuple(core_metrics.get("codes", [])) != CORE_FOUR or core_metrics.get("basket_name") != "core_csi300_four":
        raise DataGateError("the fixed four-ETF core baseline is required")
    try:
        event_day = date.fromisoformat(str(core_metrics["trade_date"]))
    except (ValueError, KeyError):
        raise DataGateError("missing/invalid core trade date") from None
    cutoff = utc_aware(decision_cutoff, "decision_cutoff")
    if cutoff.date() < event_day:
        raise DataGateError("decision is before ETF trade day")
    original_cutoff = utc_aware(core_metrics.get("decision_cutoff"), "original core factor cutoff")
    if original_cutoff > cutoff:
        raise DataGateError("core ETF data was not available at decision time")
    raw = core_metrics.get("per_etf_daily_flow_proxy_cny")
    if not isinstance(raw, Mapping) or set(raw) != set(CORE_FOUR):
        raise DataGateError("four ETF flow attribution is required")
    flows = {c: _number(raw[c], f"{c} flow") for c in CORE_FOUR}
    if sum(flows.values(), Decimal(0)) != _number(core_metrics.get("daily_net_creation_proxy_cny"), "daily total"):
        raise DataGateError("four ETF individual flows do not sum to headline")
    if not isinstance(top_n, int) or not (1 <= top_n <= 30):
        raise DataGateError("top_n must be an integer from 1 to 30")

    accepted = {}
    basket_failures = {}
    for etf in CORE_FOUR:
        item = etf_baskets.get(etf)
        try:
            if not isinstance(item, Mapping):
                raise DataGateError("basket missing")
            if not str(item.get("source_url", "")).startswith("https://"):
                raise DataGateError("basket source missing")
            stamp = utc_aware(item.get("published_at"), "basket publication")
            if stamp > cutoff:
                raise DataGateError("basket published after cutoff")
            asof = date.fromisoformat(str(item["asof_date"]))
            age = (event_day - asof).days
            if not 0 <= age <= max_basket_lag_days:
                raise DataGateError(f"basket stale: {age} days")
            weights_raw = item.get("weights")
            if not isinstance(weights_raw, Mapping) or not weights_raw:
                raise DataGateError("weights missing")
            weights = {str(s): _number(v, f"{etf} {s} weight") for s, v in weights_raw.items()}
            if any(len(s) != 6 or not s.isdigit() for s in weights):
                raise DataGateError("bad stock symbol")
            if any(weight < 0 for weight in weights.values()):
                raise DataGateError("negative ETF constituent weights are invalid")
            total_weight = sum(weights.values(), Decimal(0))
            if not Decimal("0.70") <= total_weight <= Decimal("1.01"):
                raise DataGateError(f"weight coverage insufficient: {total_weight}")
            accepted[etf] = {
                "weights": weights, "source": item["source_url"], "age_days": age,
                "weight_coverage": total_weight,
                "cash_substitution_unresolved": bool(item.get("cash_substitution_unresolved", False)),
            }
        except (ValueError, KeyError, DataGateError) as exc:
            basket_failures[etf] = str(exc)

    covered_flow = sum((abs(flows[e]) for e in accepted), Decimal(0))
    all_flow = sum((abs(v) for v in flows.values()), Decimal(0))
    coverage = covered_flow / all_flow if all_flow else Decimal(0)
    effective_coverage = (sum((abs(flows[e]) * accepted[e]["weight_coverage"] for e in accepted), Decimal(0)) / all_flow) if all_flow else Decimal(0)
    potential: dict[str, Decimal] = {}
    for etf, rec in accepted.items():
        for symbol, weight in rec["weights"].items():
            potential[symbol] = potential.get(symbol, Decimal(0)) + flows[etf] * weight

    ranked = []
    skipped = []
    for symbol, money in potential.items():
        row = stock_data.get(symbol)
        if not isinstance(row, Mapping):
            skipped.append({"symbol": symbol, "reason": "stock_snapshot_missing"})
            continue
        try:
            if not str(row.get("source_url", "")).startswith("https://"):
                raise DataGateError("stock source missing")
            t = utc_aware(row.get("published_at"), "stock release time")
            if t > cutoff:
                raise DataGateError("stock row published after cutoff")
            asof = date.fromisoformat(str(row["asof_date"]))
            stock_age = (cutoff.date() - asof).days
            if not 0 <= stock_age <= max_stock_lag_days:
                raise DataGateError(f"stock observation stale: {stock_age} days")
            adv = _number(row.get("adv20_cny"), "ADV20", positive=True)
            strength = _number(row.get("rel_strength20"), "relative strength")
            float_raw = row.get("freefloat_mv_cny")
            float_val = _number(float_raw, "free float", positive=True) if float_raw is not None else None
        except (ValueError, KeyError, DataGateError) as exc:
            skipped.append({"symbol": symbol, "reason": str(exc)})
            continue
        labels = []
        if row.get("is_st") is True:
            labels.append("ST")
        if row.get("suspended") is True:
            labels.append("SUSPENDED")
        if row.get("limit_up_locked") is True:
            labels.append("LIMIT_UP")
        if row.get("is_st") is None or row.get("suspended") is None or row.get("limit_up_locked") is None:
            labels.append("TRADE_STATUS_UNKNOWN")
        if adv < Decimal("100000000"):
            labels.append("LOW_LIQUIDITY_WATCH")
        n = row.get("listing_sessions")
        if n is None:
            labels.append("LISTING_AGE_UNKNOWN")
        elif isinstance(n, int) and n < 250:
            labels.append("RECENT_IPO_WATCH")
        if strength > Decimal("0.10"):
            labels.append("EXTENDED_PRICE_WATCH")
        if strength < 0:
            labels.append("NEGATIVE_RELATIVE_STRENGTH")
        if any(accepted[e]["cash_substitution_unresolved"] for e in accepted if symbol in accepted[e]["weights"]):
            labels.append("PCF_CASH_SUBSTITUTION_UNRESOLVED")
        ranked.append({
            "symbol": symbol,
            "signed_implied_exposure_cny": format(money, "f"),
            "signed_exposure_to_adv20": format(money / adv, "f"),
            "relative_strength20": format(strength, "f"),
            "freefloat_exposure_ratio": format(money / float_val, "f") if float_val else None,
            "data_age_days": stock_age,
            "risk_tags": labels,
            "tradability_known_blocked": any(x in labels for x in ("ST", "SUSPENDED", "LIMIT_UP")),
            "source_url": row["source_url"],
        })
    candidates = [x for x in ranked if not x["tradability_known_blocked"]]
    positive_exposure = [x for x in candidates if Decimal(x["signed_implied_exposure_cny"]) > 0]
    negative_exposure = [x for x in candidates if Decimal(x["signed_implied_exposure_cny"]) < 0]
    by_exposure = sorted(positive_exposure, key=lambda r: (
        -Decimal(r["signed_exposure_to_adv20"]), r["symbol"]))[:top_n]
    # Direction-specific candidate ranking. A stock with net NEGATIVE implied
    # fund pressure must never appear as a flow-confirmed inflow candidate.
    by_strength = sorted(candidates, key=lambda r: (
        -Decimal(r["relative_strength20"]),
        -Decimal(r["signed_exposure_to_adv20"]), r["symbol"]))[:top_n]
    inflow_confirmed_strength = sorted(positive_exposure, key=lambda r: (
        -Decimal(r["relative_strength20"]),
        -Decimal(r["signed_exposure_to_adv20"]), r["symbol"]))[:top_n]
    outflow_risk = sorted(negative_exposure, key=lambda r: (
        Decimal(r["signed_exposure_to_adv20"]), r["symbol"]))[:top_n]
    total = sum(flows.values(), Decimal(0))
    partial_total = sum((flows[e] for e in accepted), Decimal(0))
    missing_total = total - partial_total
    full_coverage = len(accepted) == len(CORE_FOUR) and all(
        r["weight_coverage"] >= Decimal("0.999") for r in accepted.values()
    )
    if not accepted:
        status = "NO_VERIFIABLE_BASKET_EXPOSURE"
    elif total > 0:
        status = "INFLOW_RESEARCH_SCAN"
    elif total < 0:
        status = "OUTFLOW_RESEARCH_SCAN"
    else:
        status = "MIXED_FLOW_RESEARCH_SCAN"
    return {
        "status": status, "trade_date": event_day.isoformat(),
        "decision_cutoff": decision_cutoff,
        "four_etf_net_flow_cny": format(total, "f"),
        "four_etf_5d_flow_intensity": str((core_metrics.get("five_day") or {}).get("net_creation_pct_initial_aum")),
        "accepted_etf_baskets": sorted(accepted),
        "basket_source_age_days": {e: rec["age_days"] for e, rec in accepted.items()},
        "missing_or_rejected_baskets": basket_failures,
        "abs_flow_coverage_ratio": format(coverage, "f") if all_flow else None,
        "estimated_weighted_coverage_ratio": format(effective_coverage, "f") if all_flow else None,
        "basket_count_coverage": f"{len(accepted)}/{len(CORE_FOUR)}",
        "is_complete_four_etf_weight_mapping": full_coverage,
        "mapped_etf_signed_flow_cny": format(partial_total, "f"),
        "unmapped_etf_signed_flow_cny": format(missing_total, "f"),
        "mapped_flow_sign_conflicts_with_full_basket": (partial_total * total < 0),
        "coverage_warning": "partial fund and constituent exposures are NOT scaled to all four ETFs",
        "stock_scan_count": len(ranked), "stock_skipped": len(skipped),
        "stock_skipped_details": skipped[:50],
        "potential_inflow_watchlist": by_exposure if total > 0 else [],
        "inflow_confirmed_relative_strength_watchlist": inflow_confirmed_strength if total > 0 else [],
        "relative_strength_watchlist": by_strength,
        "relative_strength_watchlist_is_flow_agnostic": True,
        "potential_outflow_watchlist": outflow_risk,
        "ranking_scope": "mapped subset only, exposure can be revised by missing constituent weights",
        "research_ranking_ready": bool(ranked),
        "benchmark_returns_verified": False,
        "risk_tags_are_ranking_metadata_not_arbitrary_universal_exclusions": True,
        "live_broker_orders": False, "investor_identity_inferred": False,
        "evaluation_goal": "paired after-cost 5/10/20 day excess return vs direct CSI300 ETF holding",
    }
