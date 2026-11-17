"""EXP-0012 two left-side rankings, precommitted before future OHLC exists.

SHALLOW_DIP prefers stocks still flat/down but holding closest to zero 5d;
DEEP_DIP prefers deeper 5d declines among the same observed eligible group.
Both are shadow-paper portfolios and remain separate from EXP-0011.
"""
from __future__ import annotations

from decimal import Decimal

from national_team.left_entry_v4 import d, digest, freeze as baseline_freeze, plan_lots

POLICIES = ("SHALLOW_DIP", "DEEP_DIP")
RIGHT_POLICY = "R_BOUNCE"
EARLY_POLICY = "EARLY_ENTRY"
ARMS = (*POLICIES, RIGHT_POLICY, EARLY_POLICY)
STRATEGY_EXPERIMENT = "EXP-0017"


def momentum_rank(candidates):
    """Positive absolute and relative momentum, no arbitrary +3% ceiling."""
    return sorted((x for x in candidates if d(x["r5"], "r5") > 0
                   and d(x["relative_r5"], "relative") > 0),
                  key=lambda x: (-d(x["relative_r5"], "relative"),
                                 -d(x["r5"], "r5"), x["stock"]))


def early_rank(candidates):
    """Rank available signals; missing optional inputs are not vetoes."""
    def key(x):
        near_low = x.get("distance_low20")
        votes = (int(near_low is not None and d(near_low, "low distance") <= Decimal(".03"))
                 + int(d(x["relative_r5"], "relative") > 0)
                 + int(d(x["r5"], "r5") > 0))
        return (-votes, -d(x["relative_r5"], "relative"),
                -d(x["r5"], "r5"), x["stock"])
    return sorted(candidates, key=key)


def rank(candidates, policy):
    if policy not in POLICIES:
        raise ValueError("unknown predeclared paper rank policy")

    def key(item):
        r5 = d(item["r5"], "r5")
        ma = d(item["distance_ma20"], "distance MA20")
        relative = d(item["relative_r5"], "relative")
        weight = d(item["weight_index_proxy"], "index weight")
        # Still-down prices take priority over the old +2%-3% mild-chase group.
        if policy == "SHALLOW_DIP":
            return (0 if r5 <= 0 else 1, abs(r5), abs(ma), -relative, -weight,
                    item["stock"])
        return (0 if r5 <= 0 else 1, r5, abs(ma), -relative, -weight,
                item["stock"])
    return sorted(candidates, key=key)


def _orders(ranked, next_session, *, admitted):
    if not admitted:
        return []
    selected, used = [], Decimal(0)
    for item in ranked:
        if len(selected) == 2:
            break
        sized = plan_lots(item["close"], used)
        if not sized["shares_indicative"]:
            continue
        used += d(sized["gross_indicative_cny"], "gross")
        selected.append({
            "stock": item["stock"], **sized,
            "intended_session": next_session,
            "fill": None, "paper_position": 0,
        })
    return selected


def freeze(v3, watch, prices, *, now, next_session, selected_policy):
    if selected_policy not in POLICIES:
        raise ValueError("invalid selected policy")
    from national_team.coverage_v3 import v5_decision_session, observed_funding_basis, early_funding_signal
    signal = v5_decision_session(v3) if v3 else {}
    basis, standard = observed_funding_basis(signal) if v3 else ("SHARE_PROXY", True)
    early = early_funding_signal(signal)
    result = baseline_freeze(v3, watch, prices, now=now, next_session=next_session,
                             funding_basis=basis, v5_experiment=True)
    eligible = result["candidates_ranked"]
    verified = result.pop("verified_candidates", eligible)
    admitted = result["admission"]["pilot_admitted"] and standard
    stage = "STANDARD_AND_EARLY" if standard and early else "STANDARD" if standard else "EARLY_ONLY"
    shadow = {}
    for policy in POLICIES:
        ordered = rank(eligible, policy)
        shadow[policy] = {
            "orders": _orders(ordered, next_session, admitted=admitted),
            "ranked_stocks": [x["stock"] for x in ordered],
            "up_five_day_in_top_two": sum(d(x["r5"], "r5") > 0 for x in ordered[:2]),
        }
    right = momentum_rank(verified)
    shadow[RIGHT_POLICY] = {
        "orders": _orders(right, next_session, admitted=admitted or early),
        "ranked_stocks": [x["stock"] for x in right],
        "up_five_day_in_top_two": min(2, len(right)),
        "arm_role": "ACTIVE_MOMENTUM_PAPER_COMPARATOR",
    }
    early_candidates = early_rank(verified) if early else []
    shadow[EARLY_POLICY] = {
        "orders": _orders(early_candidates, next_session, admitted=early),
        "ranked_stocks": [x["stock"] for x in early_candidates],
        "arm_role": "LARGE_ONE_DAY_FLOW_PAPER_TRIAL",
    }
    result["strategy_experiment_id"] = STRATEGY_EXPERIMENT
    result["funding_stage"] = stage
    result.setdefault("funding", {})["early_proxy_trigger"] = early
    result["momentum_candidates_ranked"] = right
    primary = shadow[selected_policy]["orders"]
    result["experiment_id"] = "EXP-0012"
    result["extension_experiment_id"] = "EXP-0013"
    result["version"] = "NT_LEFT_ENTRY_V5_EXP0017_EARLY_MOMENTUM"
    result["candidate_policy"] = selected_policy
    result["candidate_rank_reason"] = (
        "STILL_DOWN_FIRST_THEN_" + selected_policy + "_PAPER_SHADOW"
    )
    result["candidates_ranked"] = rank(eligible, selected_policy)
    result["paper_policies"] = shadow
    symbols = {p: {o["stock"] for o in arm["orders"]} for p, arm in shadow.items()}
    result["arm_comparison"] = {
        "funding_basis": basis,
        "left_identical": bool(symbols["SHALLOW_DIP"]) and symbols["SHALLOW_DIP"] == symbols["DEEP_DIP"],
        "shared_symbols": sorted(set.intersection(*(v for v in symbols.values() if v))) if any(symbols.values()) else [],
        "arm_sizes": {p: len(v) for p, v in symbols.items()},
        "interpretation": "Overlap is reported, not forced apart or counted as independent evidence",
    }
    result["accounts"]["F1_LEFT"]["orders"] = primary
    result["accounts"]["F1_LEFT"]["state"] = (
        "PAPER_NEXT_OPEN_PENDING" if primary else "NO_SIZED_CANDIDATE"
    )
    result["accounts"]["F2_WEAK"]["same_precommitted_candidates"] = [
        x["stock"] for x in primary
    ]
    result["accounts"]["S0_ETF"]["budget_cny"] = format(
        sum((d(x["gross_indicative_cny"], "gross") for x in primary), Decimal(0)), "f")
    result["measurement"]["paper_shadow_comparison"] = (
        "Legacy paired-left selection; EXP-0017 early/momentum separately evaluated"
    )
    result.pop("freeze_payload_sha256", None)
    result["freeze_payload_sha256"] = digest(result)
    return result
