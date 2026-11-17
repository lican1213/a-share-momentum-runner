"""Track all recent EXP-0012 event freezes; compare two shadow paper rankings."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import sys
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from national_team.left_entry_outcomes import track
from national_team.left_entry_v4 import digest
from national_team.left_entry_v5 import ARMS
from national_team.ohlc_fallback_v5 import backfill_future_bars, fetch_baostock
from national_team.paper_account_v5 import advance
from national_team.archived_ohlc_v5 import recover as recover_archived_ohlc
from scripts.track_national_team_left_entry_v4 import collect, rows

BJ = ZoneInfo("Asia/Shanghai")


def recent_freezes(root, *, today, max_events=24):
    latest = {}
    for path in sorted(Path(root).glob("*/*.json")):
        obj = json.loads(path.read_text(encoding="utf-8"))
        if obj.get("experiment_id") != "EXP-0012":
            continue
        signal = obj["signal_session"]
        if signal >= today:
            continue
        if signal not in latest:
            latest[signal] = (path, obj)
    return [latest[key] for key in sorted(latest)[-max_events:]]


def finalized_cutoff(now):
    """An early source-completion trigger must not settle an intraday daily bar."""
    local = now.astimezone(BJ)
    return (local.date() if local.time() >= time(15, 5)
            else local.date() - timedelta(days=1)).isoformat()


def backup_quotes(ak, codes, start, end):
    # Baostock is only the individual-stock source. The ETF benchmark uses
    # its own independent Sina daily-price feed, not an ETF-share substitute.
    stocks = [code for code in codes if code != "510300"]
    if stocks:
        try:
            source, errors = fetch_baostock(stocks, start, end)
        except Exception as exc:
            source, errors = {}, {c: "BAOSTOCK:" + type(exc).__name__ for c in stocks}
    else:
        source, errors = {}, {}
    if "510300" in codes:
        try:
            frame = ak.fund_etf_hist_sina(symbol="sh510300")
            if frame is None or frame.empty:
                raise ValueError("empty independent benchmark")
            bars = sorted((row for row in rows(frame) if start <= row["date"] <= end),
                          key=lambda row: row["date"])
            if not bars or len({row["date"] for row in bars}) != len(bars):
                raise ValueError("missing or duplicate ETF daily bars")
            source["510300"] = {"bars": bars, "source_url": "https://finance.sina.com.cn/",
                                "source_sha256": hashlib.sha256(frame.to_csv(index=False).encode()).hexdigest()}
        except Exception as exc:
            errors["510300"] = "SINA_ETF:" + type(exc).__name__ + ":" + str(exc)[:120]
    return source, errors


def order_union(freezes):
    orders = {}
    for frozen in freezes:
        for arm in frozen["paper_policies"].values():
            for order in arm["orders"]:
                orders.setdefault(order["stock"], order)
    return list(orders.values())


def capture_batch(ak, freezes, cutoff, *, history_root=None):
    """Fetch each unique stock and 510300 only once for all active events."""
    oldest = min(freezes, key=lambda f: f["signal_session"])
    shared = copy.deepcopy(oldest)
    orders = order_union(freezes)
    shared["accounts"]["F1_LEFT"]["orders"] = orders
    seen = collect(ak, shared, cutoff)
    codes = ["510300", *sorted(o["stock"] for o in orders)]
    seen = backfill_future_bars(seen, codes,
                                oldest["signal_session"], cutoff,
                                fetcher=lambda codes,start,end: backup_quotes(ak,codes,start,end))
    seen["capture_time"] = datetime.now(BJ).isoformat()
    seen["first_observed_at"] = seen["capture_time"]
    if history_root is not None:
        seen = recover_archived_ohlc(seen, codes,
                    history_root,start=oldest["signal_session"],cutoff=cutoff,
                    observed_at=seen["capture_time"])
    seen["finalized_cutoff"] = cutoff
    return seen


def scope_event(seen, frozen):
    result = copy.deepcopy(seen)
    codes = {"510300", *(o["stock"] for o in order_union([frozen]))}
    signal = frozen["signal_session"]
    result["bars_by_symbol"] = {code:[row for row in bars
                                       if signal < row["date"] <= seen["finalized_cutoff"]]
                                for code,bars in seen.get("bars_by_symbol",{}).items()
                                if code in codes}
    for key in ("source_url","source_sha256","fallback_segments","errors","archived_bar_recovery"):
        if key in result:
            result[key] = {k:v for k,v in result[key].items() if k in codes or k.split(":")[-1] in codes}
    if "fallback_recovered_codes" in result:
        result["fallback_recovered_codes"] = [c for c in result["fallback_recovered_codes"] if c in codes]
    if "archived_bar_recovery" in result:
        result["archived_bar_recovery"]={c:[r for r in rows if signal<r["date"]<=seen["finalized_cutoff"]]
                                        for c,rows in result["archived_bar_recovery"].items()}
    result["source_range_shared_across_events"] = True
    return result


def follow_one(ak, frozen, source_path, asof, *, shared_observations=None):
    # A common OHLC snapshot for both models: no one gets more recent prices.
    active_policies = [p for p in ARMS
                       if p in frozen["paper_policies"]]
    if shared_observations is None:
        cutoff = min(asof, finalized_cutoff(datetime.now(BJ)))
        shared_observations = capture_batch(ak, [frozen], cutoff)
    seen = scope_event(shared_observations, frozen)
    observed_at = datetime.now(BJ).isoformat()
    policy_results = {}
    for policy in active_policies:
        model = copy.deepcopy(frozen)
        model["accounts"]["F1_LEFT"]["orders"] = frozen["paper_policies"][policy]["orders"]
        outcome = track(model, seen, observed_at=observed_at)
        policy_results[policy] = {
            "F1_LEFT": outcome["F1_LEFT"],
            "F2_WEAK": outcome["F2_WEAK"],
            "errors": outcome["errors"],
            "source_new_ohlc_sha256": outcome["source_new_ohlc_sha256"],
        }
    return {
        "experiment_id": "EXP-0012",
        "source_freeze_sha256": frozen["freeze_payload_sha256"],
        "freeze_path": str(source_path),
        "signal_session": frozen["signal_session"],
        "cluster_anchor": frozen["cluster_anchor"],
        "extension_experiment_id": frozen.get("extension_experiment_id"),
        "strategy_experiment_id": frozen.get("strategy_experiment_id"),
        "funding_stage": frozen.get("funding_stage"),
        "asof": asof,
        "first_observed_at": observed_at,
        "policy_results": policy_results,
        "source_new_ohlc": seen,
        "source_new_ohlc_sha256": digest(seen),
        "trade_authorized": False,
        "broker_orders": [],
        "execution": "OHLC_OPEN_SCENARIO_NOT_BROKER_FILL",
    }


def latest_paper_snapshot(root, asof):
    prior = []
    for path in Path(root).glob("*/*.json"):
        obj = json.loads(path.read_text(encoding="utf-8"))
        if obj.get("version") == "NT_V5_PAPER_ACCOUNT_EXP0014" and obj.get("asof", "") <= asof:
            prior.append((obj["capture_time"], str(path), obj))
    return max(prior)[2] if prior else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--freeze-root", default="records/national_team_left_entry_v5")
    ap.add_argument("--max-events", type=int, default=24)
    ap.add_argument("--out", required=True)
    ap.add_argument("--paper-out", help="append-only shared three-arm cash and trade snapshot")
    ap.add_argument("--paper-root", default="records/national_team_paper_accounts_v5")
    ap.add_argument("--outcomes-root", default="records/national_team_left_outcomes_v5")
    args = ap.parse_args()
    now = datetime.now(BJ)
    asof = now.date().isoformat()
    import akshare as ak
    freezes = recent_freezes(args.freeze_root, today=asof, max_events=args.max_events)
    results = []
    cutoff = finalized_cutoff(now)
    batch_source = capture_batch(ak, [f for _,f in freezes], cutoff, history_root=args.outcomes_root) if freezes else None
    for path, frozen in freezes:
        results.append(follow_one(ak, frozen, path, asof, shared_observations=batch_source))
    previous = latest_paper_snapshot(args.paper_root, asof) if args.paper_out else None
    account = advance(previous, [(frozen, result["source_new_ohlc"])
                                 for (_, frozen), result in zip(freezes, results)],
                      asof=asof, captured_at=datetime.now(BJ).isoformat()) if args.paper_out else None
    if account:
        account["github_run_id"] = os.environ.get("GITHUB_RUN_ID")
        account["github_run_attempt"] = os.environ.get("GITHUB_RUN_ATTEMPT")
        account["github_source_commit"] = os.environ.get("NT_CHECKED_OUT_SHA") or os.environ.get("GITHUB_SHA")
        account.pop("snapshot_sha256", None)
        account["snapshot_sha256"] = digest(account)
    batch = {
        "schema": 1, "version": "NT_EVENT_FOLLOWUP_V5",
        "experiment_id": "EXP-0012", "asof": asof,
        "capture_time": datetime.now(BJ).isoformat(),
        "akshare_version": getattr(ak, "__version__", "UNKNOWN"),
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "results": results,
        "tracked_freeze_count": len(results),
        "paper_account_snapshot_sha256": account["snapshot_sha256"] if account else None,
        "paper_account_summary": {k: v["summary"] for k, v in account["accounts"].items()} if account else None,
        "trade_authorized": False, "broker_orders": [],
    }
    batch["snapshot_sha256"] = digest(batch)
    out = Path(args.out)
    if out.exists():
        raise FileExistsError("refuse to overwrite outcome evidence")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(batch, indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    if args.paper_out:
        paper_path = Path(args.paper_out)
        if paper_path.exists():
            raise FileExistsError("refuse to overwrite paper account snapshot")
        paper_path.parent.mkdir(parents=True, exist_ok=True)
        paper_path.write_text(json.dumps(account, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "asof": asof, "tracked_events": len(results),
        "policies": list(ARMS),
        "paper_accounts": {k: v["summary"] for k, v in account["accounts"].items()} if account else None,
        "paired_10d": sum(any(
            h.get("status") == "PAIRED"
            for p in r["policy_results"].values()
            for item in p["F1_LEFT"]
            for h in [item.get("horizons", {}).get("10", {})]
        ) for r in results),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
