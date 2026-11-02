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
from national_team.left_entry_v4 import digest

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
        if quality.get("last_full_four_share_day", "") < daily[-1]["date"]:
            continue
        found.append(((daily[-1]["date"],
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
        if not item.get("candidate_pool_pre_filter"):
            continue
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
                               item.get("asof", "") >= latest[freeze_sha].get("asof", "")):
                latest[freeze_sha] = item
    # Consecutive down-market funding days can belong to one event cluster.
    # Evaluate the earliest paper freeze per cluster to avoid fake independence.
    clusters = {}
    for item in latest.values():
        anchor = (item.get("cluster_anchor") or item.get("signal_session")
                  or item["source_freeze_sha256"])
        existing = clusters.get(anchor)
        if (existing is None or item.get("signal_session", "") <
                existing.get("signal_session", "")):
            clusters[anchor] = item
    paired = []
    for item in clusters.values():
        by_policy = {}
        for policy in POLICIES:
            entries = item.get("policy_results", {}).get(policy, {}).get("F1_LEFT", [])
            excess = []
            for entry in entries:
                horizon = entry.get("horizons", {}).get("10", {})
                if horizon.get("status") == "PAIRED" and horizon.get("excess_s0") is not None:
                    excess.append(Decimal(str(horizon["excess_s0"])))
            if excess:
                by_policy[policy] = sum(excess) / len(excess)
        if len(by_policy) == len(POLICIES):
            paired.append(by_policy)
    count = len(paired)
    means = {policy: (sum(x[policy] for x in paired) / count if count else None)
             for policy in POLICIES}
    best = "SHALLOW_DIP"
    if (count >= MIN_PAIRED_EVENTS and
            means["DEEP_DIP"] - means["SHALLOW_DIP"] >= SWITCH_MARGIN):
        best = "DEEP_DIP"
    return {
        "paired_10d_events": count,
        "mean_10d_excess_s0": {k: (format(v, "f") if v is not None else None)
                               for k, v in means.items()},
        "selected_policy": best,
        "policy_rule": "8 distinct event clusters with paired 10d outcomes; DEEP_DIP +0.2pct",
        "not_a_calibrated_profit_probability": True,
    }


def route(v3_root, watch_root, freeze_root, followup_root, *, now,
          legacy_freeze_root="records/national_team_left_entry"):
    observed = datetime.fromisoformat(now)
    if observed.utcoffset() is None:
        raise ValueError("router requires timezone-aware observation")
    today = observed.astimezone(BJ).date()
    v3_path, v3 = latest_v3(v3_root)
    signal = v3["daily"][-1]
    asof = signal["date"]
    age = (today - date.fromisoformat(asof)).days
    feedback = paper_feedback(followup_root)
    status = "NO_NEW_FUNDING_EVENT"
    watch_path = None
    if age < 0:
        status = "FUTURE_SOURCE_SESSION"
    elif age > MAX_SOURCE_LAG_CALENDAR_DAYS:
        status = "WAIT_FRESH_FOUR_ETF_SESSION"
    elif (asof in frozen_sessions(freeze_root) or
          asof in frozen_sessions(legacy_freeze_root, "EXP-0011")):
        status = "ALREADY_FROZEN_FOR_SESSION"
    elif (signal.get("market_down") and signal.get("share_proxy_event")
          and Decimal(str(signal.get("net_creation_1d_cny") or 0)) > 0
          and Decimal(str(signal.get("net_creation_5d_cny") or 0)) > 0):
        watch_path, watch = matching_watch(watch_root, asof)
        status = "NEW_FUNDING_EVENT" if watch is not None else "WAIT_MATCHING_STOCK_WATCH"
    return {
        "schema": 1, "version": "NT_EVENT_ROUTER_V5",
        "experiment_id": "EXP-0012",
        "observed_at": observed.isoformat(),
        "event_id": "ETF4_DOWNFLOW_" + asof,
        "signal_session": asof,
        "signal_age_calendar_days": age,
        "status": status,
        "four_etfs": list(CORE_FOUR),
        "v3_path": str(v3_path),
        "watch_path": str(watch_path) if watch_path else None,
        "selected_policy": feedback["selected_policy"],
        "feedback": feedback,
        "funding": {
            "net_creation_1d_cny_proxy": signal.get("net_creation_1d_cny"),
            "net_creation_5d_cny_proxy": signal.get("net_creation_5d_cny"),
            "ordinary_float_coverage_ratio": signal.get("ordinary_float_coverage_ratio"),
            "ratio_status": signal.get("ratio_status"),
            "index_ret5": signal.get("index_ret5"),
            "share_proxy_not_state_account_trade": True,
        },
        "dispatcher": "FREEZE_LEFT_SIDE_RESEARCH" if status == "NEW_FUNDING_EVENT"
                      else "NO_NEW_PAPER_FREEZE",
        "trade_authorized": False, "broker_orders": [],
    }


def with_digest(route_record):
    result = dict(route_record)
    result["snapshot_sha256"] = digest(result)
    return result
