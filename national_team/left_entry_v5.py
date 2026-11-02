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
    result = baseline_freeze(v3, watch, prices, now=now, next_session=next_session)
    eligible = result["candidates_ranked"]
    admitted = result["admission"]["pilot_admitted"]
    shadow = {}
    for policy in POLICIES:
        ordered = rank(eligible, policy)
        shadow[policy] = {
            "orders": _orders(ordered, next_session, admitted=admitted),
            "ranked_stocks": [x["stock"] for x in ordered],
            "up_five_day_in_top_two": sum(d(x["r5"], "r5") > 0 for x in ordered[:2]),
        }
    # The independent right-side arm observes mild rebounds, never replaces
    # the two left-side policies or their automatic feedback threshold.
    right = sorted((x for x in eligible if Decimal(0) < d(x["r5"], "r5")
                    <= Decimal(".03")),
                   key=lambda x: (d(x["r5"], "r5"),
                                  -d(x["relative_r5"], "relative"),
                                  x["stock"]))
    shadow[RIGHT_POLICY] = {
        "orders": _orders(right, next_session, admitted=admitted),
        "ranked_stocks": [x["stock"] for x in right],
        "up_five_day_in_top_two": min(2, len(right)),
        "arm_role": "INDEPENDENT_RIGHT_SIDE_REFERENCE_NOT_LEFT_POLICY_GATE",
    }
    primary = shadow[selected_policy]["orders"]
    result["experiment_id"] = "EXP-0012"
    result["extension_experiment_id"] = "EXP-0013"
    result["version"] = "NT_LEFT_ENTRY_V5_EXP0013_PATH_OBSERVATION"
    result["candidate_policy"] = selected_policy
    result["candidate_rank_reason"] = (
        "STILL_DOWN_FIRST_THEN_" + selected_policy + "_PAPER_SHADOW"
    )
    result["candidates_ranked"] = rank(eligible, selected_policy)
    result["paper_policies"] = shadow
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
        "SHALLOW_DIP_vs_DEEP_DIP paired 10d S0; R_BOUNCE independent "
        "same-event reference; rank promotion remains left-side only"
    )
    result.pop("freeze_payload_sha256", None)
    result["freeze_payload_sha256"] = digest(result)
    return result
