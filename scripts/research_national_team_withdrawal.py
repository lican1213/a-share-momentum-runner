"""Read-only four-ETF withdrawal evidence, not trade signals or investor identity."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from national_team.core_flow_factors import CORE_FOUR, DataGateError, dec, utc_aware


def diagnose(snapshot, *, cutoff=None):
    event = snapshot["funding_event"]
    factor = event["four_etf_factor"]
    observed = max(utc_aware(snapshot["capture_completed_beijing"], "capture"),
                   utc_aware(event["first_available_at"], "available"))
    cutoff = utc_aware(cutoff, "cutoff") if cutoff is not None else observed
    if observed > cutoff:
        raise DataGateError("merged record not available at cutoff")
    if (snapshot.get("unit") != "raw_shares"
            or snapshot.get("status") != "FULL_FOUR_ETF_SHARES_NAV_OBSERVED_RESEARCH"
            or event.get("verified_consecutive_session_flow") is not True
            or snapshot.get("conflicts") != []
            or snapshot.get("conflicted_date_code_pairs") != 0
            or tuple(factor["codes"]) != CORE_FOUR):
        raise DataGateError("incomplete, conflicting or wrong-unit core basket")
    days = event["history_sessions"]
    session = factor["trade_date"]
    if (days != sorted(set(days)) or session not in days
            or any(date.fromisoformat(day).isoformat() != day
                   or date.fromisoformat(day).weekday() >= 5 for day in days)
            or event.get("latest_complete_four_etf_factor_date") != session
            or event.get("latest_available_trading_day") != session):
        raise DataGateError("invalid sessions or stale complete basket")
    pos = days.index(session)
    if pos < 5 or factor["prior_date"] != days[pos - 1]:
        raise DataGateError("missing six-session window")
    window = days[pos - 5:pos + 1]
    values, provenance = {}, {}
    for day in window:
        values[day], provenance[day] = {}, {}
        for code in CORE_FOUR:
            row = snapshot["observations_by_date"].get(day, {}).get(code)
            if not row:
                raise DataGateError(f"{day}:{code} missing shares/NAV")
            paths = [row.get(f"{k}_source_path") for k in ("shares", "nav")]
            if any(not isinstance(p, str) or not p.startswith("records/national_team_etf/")
                   for p in paths):
                raise DataGateError(f"{day}:{code} missing archived source")
            times = [utc_aware(row.get(f"{k}_first_observed_at"), k) for k in ("shares", "nav")]
            if (max(times) > observed or max(times) > cutoff
                    or any(t.astimezone(ZoneInfo("Asia/Shanghai")).date() < date.fromisoformat(day)
                           for t in times)):
                raise DataGateError(f"{day}:{code} impossible source timing")
            values[day][code] = (dec(row.get("shares"), "shares", positive=True),
                                 dec(row.get("nav"), "NAV", positive=True))
            provenance[day][code] = {"source_paths": paths,
                                     "first_observed_at": max(times).isoformat()}
    daily, anomalies = [], []
    for before, day in zip(window, window[1:]):
        flows = {}
        for code in CORE_FOUR:
            s0, n0 = values[before][code]
            s1, n1 = values[day][code]
            flows[code] = (s1 - s0) * n1
            # Large jumps require review, never automatically zero or attribute.
            if abs(s1 / s0 - 1) > Decimal("0.30"):
                anomalies.append({"session": day, "code": code,
                                  "share_change_ratio": str(s1 / s0 - 1),
                                  "split_like": (s1-s0)*(n1-n0) < 0 and
                                  abs(s1*n1/(s0*n0)-1) < Decimal("0.18")})
        total = sum(flows.values())
        aum = sum(s*n for s, n in values[before].values())
        daily.append({"session": day, "prior_session": before,
                      "net_cny": str(total), "net_to_prior_aum": str(total/aum),
                      "negative_funds": sum(v < 0 for v in flows.values()),
                      "per_fund_cny": {c: str(v) for c, v in flows.items()}})
    totals = [Decimal(row["net_cny"]) for row in daily]
    if (totals[-1] != Decimal(factor["daily_net_creation_proxy_cny"])
            or sum(totals) != Decimal(factor["five_day"]["net_creation_cny_daily_sum"])):
        raise DataGateError("recomputed flow disagrees with core factor")
    if totals[-1] < 0 and sum(totals) > 0:
        pattern = "REDEMPTION_AGAINST_POSITIVE_5D"
    elif all(x < 0 for x in totals[-3:]):
        pattern = "THREE_CONSECUTIVE_REDEMPTIONS"
    elif totals[-1] < 0:
        pattern = "LATEST_REDEMPTION"
    elif totals[-1] > 0:
        pattern = "LATEST_CREATION"
    else:
        pattern = "FLAT_LATEST"
    return {"scope": "DESCRIPTIVE_ONLY_NOT_WITHDRAWAL_CONFIRMATION",
            "source_run_id": snapshot["run_id"], "session": session,
            "first_available_at": observed.isoformat(), "cutoff": cutoff.isoformat(),
            "raw_flow_pattern": pattern,
            "net_cny_by_window": {str(n): str(sum(totals[-n:])) for n in (1,3,5)},
            "daily": daily, "anomaly_review": anomalies, "provenance": provenance,
            "corporate_actions_explicitly_verified": factor.get("corporate_actions_explicitly_verified") is True,
            "official_nav_independently_verified": False,
            "withdrawal_confirmed": False, "investor_identity_attributable": False,
            "trade_authorized": False, "broker_orders": []}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--cutoff")
    args = parser.parse_args()
    print(json.dumps(diagnose(json.loads(args.snapshot.read_text(encoding="utf-8")),
                              cutoff=args.cutoff), ensure_ascii=False, indent=2))
