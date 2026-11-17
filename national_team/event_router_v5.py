"""EXP-0012: event-driven four-ETF research router and paper feedback loop.

Each daily run is an immutable observation. A fresh down-market funding day
dispatches a paper freeze; later *paired* 10-session outcomes choose between
two predeclared left-side rankings. No model edits or brokerage execution.
"""
from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from national_team.core_flow_factors import CORE_FOUR
from national_team.coverage_v3 import (latest_observed_session, v5_decision_session,
                                      observed_funding_basis, early_funding_signal)
from national_team.left_entry_v4 import digest
from national_team.policy_overlay import summarize as summarize_policy

BJ = ZoneInfo("Asia/Shanghai")
POLICIES = ("SHALLOW_DIP", "DEEP_DIP")
MIN_PAIRED_EVENTS = 8
MAX_SOURCE_LAG_CALENDAR_DAYS = 3
SWITCH_MARGIN = Decimal("0.002")


def _files(root):
    return sorted(Path(root).glob("*/*.json"))


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def latest_v3(root):
    found = []
    for path in _files(root):
        item = _read(path)
        if tuple(item.get("method", {}).get("codes", ())) != CORE_FOUR:
            continue
        daily = item.get("daily") or []
        if not daily:
            continue
        quality = item.get("data_quality") or {}
        signal = latest_observed_session(item)
        found.append(((signal["date"],
                       item.get("source_provenance", {}).get("as_of_utc", "")),
                      path, item))
    if not found:
        raise ValueError("no sourced V3 four-ETF record")
    found.sort(key=lambda row: row[0])
    _, path, item = found[-1]
    return path, item


def matching_watch(root, asof):
    found = []
    for path in _files(root):
        item = _read(path)
        if item.get("funding_date") != asof:
            continue
        pool = item.get("candidate_pool_pre_filter") or []
        snapshots = item.get("stock_snapshots") or {}
        if not any(snapshots.get(code, {}).get("data_date") == asof for code in pool):
            continue  # Empty watch must not consume the only freeze for this day.
        found.append((item.get("collector_capture_time", ""), path, item))
    if not found:
        return None, None
    found.sort(key=lambda row: row[0])
    _, path, item = found[-1]
    return path, item


def frozen_sessions(root, experiment_id="EXP-0012"):
    sessions = set()
    for path in _files(root):
        item = _read(path)
        if item.get("experiment_id") == experiment_id:
            sessions.add(item["signal_session"])
    return sessions


def paper_feedback(root):
    """Latest immutable snapshot per freeze; only genuinely paired 10d excess."""
    latest = {}
    for path in _files(root):
        batch = _read(path)
        for item in batch.get("results", [batch]):
            if item.get("experiment_id") != "EXP-0012":
                continue
            freeze_sha = item.get("source_freeze_sha256")
            if freeze_sha and (freeze_sha not in latest or
                               (item.get("asof", ""), item.get("first_observed_at", "")) >=
                               (latest[freeze_sha].get("asof", ""), latest[freeze_sha].get("first_observed_at", ""))):
                latest[freeze_sha] = item
    # Consecutive down-market funding days can belong to one event cluster.
    # Evaluate the earliest paper freeze per cluster to avoid fake independence.
    clusters = {}
    for item in latest.values():
        if item.get("funding_stage") == "EARLY_ONLY":
            continue
        anchor = (item.get("cluster_anchor") or item.get("signal_session")
                  or item["source_freeze_sha256"])
        existing = clusters.get(anchor)
        if (existing is None or item.get("signal_session", "") <
                existing.get("signal_session", "")):
            clusters[anchor] = item
    paired = []
    right_minus_left = []
    indistinguishable_clusters = 0
    for item in clusters.values():
        by_policy = {}
        names = [set(e["stock"] for e in item.get("policy_results", {}).get(p, {}).get("F1_LEFT", [])
                     if e.get("stock")) for p in POLICIES]
        if names[0] and names[0] == names[1]:
            indistinguishable_clusters += 1
            continue
        for policy in POLICIES:
            entries = item.get("policy_results", {}).get(policy, {}).get("F1_LEFT", [])
            excess = []
            for entry in entries:
                horizon = entry.get("horizons", {}).get("10", {})
                if horizon.get("status") == "PAIRED" and horizon.get("excess_s0") is not None:
                    excess.append(Decimal(str(horizon["excess_s0"])))
            if excess and len(excess) == len(entries):
                by_policy[policy] = sum(excess) / len(excess)
        if len(by_policy) == len(POLICIES):
            paired.append(by_policy)
            right_entries = item.get("policy_results", {}).get("R_BOUNCE", {}).get("F1_LEFT", [])
            right_excess = [Decimal(str(h["excess_s0"])) for entry in right_entries
                            for h in [entry.get("horizons", {}).get("10", {})]
                            if h.get("status") == "PAIRED" and h.get("excess_s0") is not None]
            if (item.get("strategy_experiment_id") != "EXP-0017"
                    and right_excess and len(right_excess) == len(right_entries)):
                right_minus_left.append(sum(right_excess) / len(right_excess)
                                        - by_policy["SHALLOW_DIP"])
    # Each new arm is evaluated on its earliest eligible freeze in each
    # funding cluster, even if that freeze never matures. No hindsight fallback.
    cohort = {}
    def paired_value(entries, horizon):
        values = [entry.get("horizons", {}).get(horizon, {}) for entry in entries]
        if values and all(v.get("status") == "PAIRED" and v.get("excess_s0") is not None for v in values):
            return sum(Decimal(str(v["excess_s0"])) for v in values) / len(values)
        return None

    for policy in ("EARLY_ENTRY", "R_BOUNCE"):
        first = {}
        for item in sorted(latest.values(), key=lambda x: x.get("signal_session", "")):
            if item.get("strategy_experiment_id") != "EXP-0017":
                continue
            anchor = item.get("cluster_anchor") or item.get("signal_session")
            entries = item.get("policy_results", {}).get(policy, {}).get("F1_LEFT", [])
            if anchor and entries:
                first.setdefault(anchor, item)
        per_horizon = {}
        for h in ("3", "10"):
            values, differences = [], []
            for item in first.values():
                results = item["policy_results"]
                entries = results[policy]["F1_LEFT"]
                excess = paired_value(entries, h)
                if excess is None:
                    continue
                values.append(excess)
                left = results.get("SHALLOW_DIP", {}).get("F1_LEFT", [])
                left_excess = paired_value(left, h)
                if left_excess is not None and {x.get("stock") for x in entries} != {x.get("stock") for x in left}:
                    differences.append(excess - left_excess)
            per_horizon[h] = {
                "eligible_clusters": len(first),
                "matured_clusters": len(values),
                "mean_excess_s0": format(sum(values)/len(values), "f") if values else None,
                "positive_clusters": sum(v > 0 for v in values),
                "distinct_paired_vs_shallow_clusters": len(differences),
                "mean_excess_difference_vs_shallow": format(sum(differences)/len(differences), "f") if differences else None,
            }
        cohort[policy] = per_horizon
    count = len(paired)
    means = {policy: (sum(x[policy] for x in paired) / count if count else None)
             for policy in POLICIES}
    best = "SHALLOW_DIP"
    if (count >= MIN_PAIRED_EVENTS and
            means["DEEP_DIP"] - means["SHALLOW_DIP"] >= SWITCH_MARGIN):
        best = "DEEP_DIP"
    return {
        "paired_10d_events": count,
        "exp0017_cohort": cohort,
        "indistinguishable_left_clusters": indistinguishable_clusters,
        "mean_10d_excess_s0": {k: (format(v, "f") if v is not None else None)
                               for k, v in means.items()},
        "selected_policy": best,
        "right_side_reference": {
            "paired_10d_clusters": len(right_minus_left),
            "mean_R_minus_SHALLOW_excess_s0": (
                format(sum(right_minus_left) / len(right_minus_left), "f")
                if right_minus_left else None),
            "not_used_to_gate_left_side_research": True,
        },
        "policy_rule": "8 distinct event clusters with paired 10d outcomes; DEEP_DIP +0.2pct",
        "not_a_calibrated_profit_probability": True,
    }


def route(v3_root, watch_root, freeze_root, followup_root, *, now,
          legacy_freeze_root="records/national_team_left_entry", policy_snapshot=None):
    observed = datetime.fromisoformat(now)
    if observed.utcoffset() is None:
        raise ValueError("router requires timezone-aware observation")
    today = observed.astimezone(BJ).date()
    v3_path, v3 = latest_v3(v3_root)
    signal = v5_decision_session(v3)
    index_session = latest_observed_session(v3)["date"]
    asof = signal["date"]
    age = (today - date.fromisoformat(asof)).days
    feedback = paper_feedback(followup_root)
    status = "NO_NEW_FUNDING_EVENT"
    watch_path = None
    funding_basis, active = observed_funding_basis(signal)
    early = early_funding_signal(signal)
    flow_active = (active or early) and 0 <= age <= MAX_SOURCE_LAG_CALENDAR_DAYS
    stage = "STANDARD_AND_EARLY" if active and early else "STANDARD" if active else "EARLY_ONLY" if early else "NO_ACTIVE_FLOW"
    if age < 0:
        status = "FUTURE_SOURCE_SESSION"
    elif age > MAX_SOURCE_LAG_CALENDAR_DAYS:
        status = "WAIT_FRESH_FOUR_ETF_SESSION"
    elif signal.get("latest_session_missing") or (
            not early and (signal.get("net_creation_1d_cny") is None or signal.get("net_creation_5d_cny") is None)):
        status = "WAIT_LATEST_SESSION_EVIDENCE"
    elif (asof in frozen_sessions(freeze_root) or
          asof in frozen_sessions(legacy_freeze_root, "EXP-0011")):
        status = "ALREADY_FROZEN_FOR_SESSION"
    elif flow_active:
        watch_path, watch = matching_watch(watch_root, asof)
        status = "NEW_FUNDING_EVENT" if watch is not None else "WAIT_MATCHING_STOCK_WATCH"
    return {
        "schema": 1, "version": "NT_EVENT_ROUTER_V5",
        "experiment_id": "EXP-0012",
        "observed_at": observed.isoformat(),
        "event_id": "ETF4_DOWNFLOW_" + asof,
        "signal_session": asof,
        "signal_age_calendar_days": age,
        "latest_index_session": index_session,
        "funding_lags_index": asof < index_session,
        "status": status,
        "four_etfs": list(CORE_FOUR),
        "v3_path": str(v3_path),
        "watch_path": str(watch_path) if watch_path else None,
        "selected_policy": feedback["selected_policy"],
        "strategy_experiment_id": "EXP-0017",
        "funding_stage": stage,
        "feedback": feedback,
        "funding": {
            "net_creation_1d_cny_proxy": signal.get("net_creation_1d_cny"),
            "net_creation_5d_cny_proxy": signal.get("net_creation_5d_cny"),
            "ordinary_float_coverage_ratio": signal.get("ordinary_float_coverage_ratio"),
            "ratio_status": signal.get("ratio_status"),
            "index_ret5": signal.get("index_ret5"),
            "funding_basis": funding_basis,
            "early_proxy_trigger": early,
            "exchange_shares_complete": signal.get("exchange_shares_complete"),
            "exchange_nav_complete": signal.get("exchange_nav_complete"),
            "latest_session_evidence_missing": bool(signal.get("latest_session_missing")),
            "share_proxy_not_state_account_trade": True,
        },
        "policy_overlay": summarize_policy(policy_snapshot, now=now, funding_day=asof,
                                           etf_flow_active=flow_active),
        "dispatcher": "FREEZE_LEFT_SIDE_RESEARCH" if status == "NEW_FUNDING_EVENT"
                      else "NO_NEW_PAPER_FREEZE",
        "trade_authorized": False, "broker_orders": [],
    }


def with_digest(route_record):
    result = dict(route_record)
    result["snapshot_sha256"] = digest(result)
    return result
