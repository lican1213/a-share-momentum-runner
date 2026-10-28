"""V2 national-team ETF flow -> independently ranked point-in-time stock cohorts.

Four fixed ETFs are a timing signal; CSI300 weights are an *index proxy*, not
actual PCF or evidence of the state investor's stock purchases. All ranking
uses information first observed before the prospective entry session.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from zoneinfo import ZoneInfo

from national_team.core_flow_factors import CORE_FOUR, utc_aware

VERSION = "NT_FLOW_PIT_V2_20261028"
BEIJING = ZoneInfo("Asia/Shanghai")
BENCHMARK = "510300"
TOP_N = 5


def number(v, label):
    try:
        x = Decimal(str(v))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(f"{label}: invalid decimal") from None
    if not x.is_finite():
        raise ValueError(f"{label}: nonfinite")
    return x


def build(watch, merged, *, observed_at, source_watch, source_merged, source_commit):
    """Return an auditable full-four signal; partial three-fund inputs do not masquerade as four."""
    timestamp = utc_aware(observed_at, "version publication").astimezone(BEIJING)
    watch_public = utc_aware(watch["event_first_public_no_earlier_than"], "watch publication")
    merged_public = utc_aware(merged["capture_completed_beijing"], "ETF publication")
    if max(watch_public, merged_public) > timestamp:
        raise ValueError("future data: fund/stock data first observed after strategy build")
    if watch.get("run_id") != merged.get("run_id"):
        raise ValueError("merged ETF data and stock watchlist are from different runs")
    if watch.get("status") != "INDEX_PROXY_RESEARCH_WATCHLIST":
        raise ValueError("watchlist not source-backed")
    weight = watch["index_weight"]
    if weight.get("kind") != "CSI300_LATEST_INDEX_WEIGHT_PROXY_NOT_ETF_PCF":
        raise ValueError("unclassified basket source")
    if utc_aware(weight["first_observed_at"], "index captured") > timestamp:
        raise ValueError("future index weights")
    raw_weights = weight["weights"]
    weights = {k: number(v, k) for k, v in raw_weights.items()}
    if not 250 <= len(weights) <= 400 or not Decimal(".97") <= sum(weights.values()) <= Decimal("1.01"):
        raise ValueError("CSI300 weights coverage invalid")
    full = (merged.get("funding_event") or {}).get("four_etf_factor")
    scope = "FULL_CORE_FOUR"
    if not full:
        return {"status": "FOUR_ETF_NOT_COMPLETE", "model_version": VERSION,
                "reported_partial_scope": (merged.get("funding_event") or {}).get("partial_funding"),
                "events": [], "trade_authorized": False}
    if tuple(full.get("codes", [])) != CORE_FOUR:
        raise ValueError("four-ETF constituent set changed")
    flows_raw = full["per_etf_daily_flow_proxy_cny"]
    if set(flows_raw) != set(CORE_FOUR):
        raise ValueError("missing one of the original four ETF flows")
    flows = {k: number(v, k) for k, v in flows_raw.items()}
    total = sum(flows.values())
    if total != number(full["daily_net_creation_proxy_cny"], "headline flow"):
        raise ValueError("ETF sum does not reconcile with total")
    intensity = number(full["five_day"]["net_creation_pct_initial_aum"], "five-day strength")
    fund_date = date.fromisoformat(full["trade_date"])
    stock_date = date.fromisoformat(watch["funding_date"])
    if not fund_date <= stock_date <= timestamp.date():
        raise ValueError("future fund/stock session or reversed observation dates")
    if (timestamp.date() - fund_date).days > 4:
        return {"status": "STALE_FOUR_ETF_FACTOR", "model_version": VERSION,
                "flow_date": fund_date.isoformat(), "events": [], "trade_authorized": False}
    rows = watch.get("stock_snapshots") or {}
    coverage = sum((weights.get(symbol, Decimal(0)) for symbol in rows), Decimal(0))
    if coverage <= 0:
        raise ValueError("no covered stocks")
    ranked = []
    missing_strength = []
    for symbol, row in rows.items():
        if symbol not in weights:
            continue
        if row.get("data_date") != stock_date.isoformat():
            raise ValueError(f"{symbol}: stock snapshot is not from decision session")
        if utc_aware(row["first_observed_at"], f"{symbol} price observed") > timestamp:
            raise ValueError(f"{symbol}: future OHLC")
        if not str(row.get("source_url", "")).startswith("https://"):
            raise ValueError(f"{symbol}: no provider URL")
        adv = number(row["adv20_cny"], f"{symbol} ADV20")
        if adv <= 0:
            continue
        pressure = total * weights[symbol] / adv
        if pressure <= 0:
            continue
        strength = row.get("relative_strength20")
        if strength is None:
            missing_strength.append(symbol)
        else:
            strength = number(strength, f"{symbol} relative strength")
        ranked.append({"symbol": symbol,
                       "benchmark_weight": str(weights[symbol]),
                       "signed_exposure_over_adv20": str(pressure),
                       "relative_strength20": str(strength) if strength is not None else None,
                       "adv20_cny": str(adv),
                       "stock_data_date": row["data_date"]})
    ranked.sort(key=lambda r: (-Decimal(r["signed_exposure_over_adv20"]), r["symbol"]))
    # S1 is purely mechanical exposure/turnover, no price-strength prescreen.
    s1 = ranked[:TOP_N]
    # S2 MUST search the entire eligible sample, NOT S1 top-5/10/30.
    # The 0..10% relative-strength range was registered in EXP-0003.
    s2_pool = [r for r in ranked if r["relative_strength20"] is not None
               and Decimal(0) < Decimal(r["relative_strength20"]) <= Decimal("0.10")]
    s2_pool.sort(key=lambda r: (-Decimal(r["relative_strength20"]),
                                -Decimal(r["signed_exposure_over_adv20"]), r["symbol"]))
    s2 = s2_pool[:TOP_N]
    events = []
    direction = "NET_CREATION" if total > 0 else ("NET_REDEMPTION" if total < 0 else "FLAT")
    valid = total > 0 and intensity > 0
    if valid:
        cohort = hashlib.sha256(
            f"{VERSION}|{fund_date}|{stock_date}|{scope}".encode()).hexdigest()[:20]
        for sid, picks in (("S1_FLOW_OVER_ADV20", s1),
                           ("S2_INDEPENDENT_RELATIVE_CONFIRMATION", s2)):
            if not picks:
                continue
            events.append({
                "id": f"NT2-{cohort}-{sid}",
                "strategy_id": sid,
                "model_version": VERSION,
                "candidate_symbols": [r["symbol"] for r in picks],
                "first_public_at": timestamp.isoformat(),
                "frozen_by_commit": source_commit,
                "funding_underlying_day": fund_date.isoformat(),
                "stock_data_day": stock_date.isoformat(),
                "benchmark_etf": BENCHMARK,
                "source_watch": source_watch,
                "source_merged": source_merged,
                "source_kind": "CSI300_INDEX_PROXY_NOT_ETF_PCF",
                "ETF_PCF_verified": False,
                "central_huijin_order_verified": False,
                "broker_trades_authorized": False,
                "portfolio_weight_rule": "EQUAL_WEIGHT_INITIAL_FIVE; UNFILLED_ALLOCATION_STAYS_CASH",
                "planned_entry": "FIRST_EXCHANGE_OPEN_AFTER_FIRST_PUBLIC_AVAILABILITY",
                "holding_sessions": [5, 10, 20],
                "paper_cost_model": "3bps EACH_SIDE COMMISSION + 5bps EACH_SIDE SLIPPAGE + STOCK 5bps SELL STAMP"
            })
    return {
        "status": "FROZEN_PROSPECTIVE_RESEARCH" if events else "NO_VALID_POSITIVE_FLOW_OR_S2",
        "model_version": VERSION, "flow_scope": scope,
        "flow_date": fund_date.isoformat(), "stock_data_date": stock_date.isoformat(),
        "strategy_first_public_at": timestamp.isoformat(),
        "four_etf_flow_cny": str(total), "five_day_flow_intensity": str(intensity),
        "flow_direction": direction, "stock_pool_size": len(rows),
        "rankable_count": len(ranked), "missing_price_strength_count": len(missing_strength),
        "covered_index_weight": str(coverage),
        "s1_ranked": s1, "s2_ranked": s2, "s2_eligible_pool_count": len(s2_pool),
        "events": events, "source_watch": source_watch, "source_merged": source_merged,
        "source_sha": source_commit,
        "limitations": {
            "actual_etf_pcf": False, "state_actor_stock_purchase_verified": False,
            "index_weight_proxy_identical_for_all_four_etfs": True,
            "funding_only_times_entries_not_cross_sectional_rank": True,
            "backtest_alpha_claimed": False, "broker_execution": False
        },
        "benchmark": BENCHMARK, "paper_only": True, "trade_authorized": False
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--watch", required=True)
    parser.add_argument("--merged", required=True)
    parser.add_argument("--strategy-out", default="records/national_team_strategy")
    parser.add_argument("--event-out", default="records/national_team_events")
    args = parser.parse_args()
    watch = json.loads(Path(args.watch).read_text(encoding="utf-8"))
    merged = json.loads(Path(args.merged).read_text(encoding="utf-8"))
    now = datetime.now(BEIJING)
    report = build(watch, merged, observed_at=now.isoformat(),
                   source_watch=args.watch, source_merged=args.merged,
                   source_commit=os.environ.get("GITHUB_SHA", "local"))
    existing = set()
    for path in Path(args.event_out).glob("*/*.json"):
        try:
            existing.update(e["id"] for e in json.loads(path.read_text(encoding="utf-8")).get("events", []))
        except (OSError, ValueError, KeyError, TypeError):
            continue
    generated = report.pop("events")
    new_events = [e for e in generated if e["id"] not in existing]
    report["frozen_candidate_cohorts"] = generated
    report["new_event_count"] = len(new_events)
    report["previously_frozen_event_count"] = len(generated) - len(new_events)
    run = os.environ.get("GITHUB_RUN_ID", "local")
    attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
    day = now.date().isoformat()
    filename = f"{run}-a{attempt}-v2.json"
    strategy_file = Path(args.strategy_out) / day / filename
    event_file = Path(args.event_out) / day / filename
    for target, obj in ((strategy_file, report), (event_file, {
            "status": "FROZEN_V2_PROSPECTIVE" if new_events else "NO_NEW_V2_EVENTS",
            "model_version": VERSION, "source_strategy": str(strategy_file),
            "events": new_events, "duplicate_previously_frozen": len(generated)-len(new_events),
            "no_broker_orders": True})):
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            raise FileExistsError(str(target))
        target.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "new_events": len(new_events),
                      "S1": [r["symbol"] for r in report.get("s1_ranked", [])],
                      "S2": [r["symbol"] for r in report.get("s2_ranked", [])],
                      "source_flow_date": report.get("flow_date"),
                      "strategy_record": str(strategy_file)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
