"""Read-only V5 economic attribution from one immutable paper ledger."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from national_team.left_entry_v4 import d, digest
from national_team.left_entry_v5 import ARMS


def audit(snapshot):
    if snapshot.get("trade_authorized") is not False or snapshot.get("broker_orders") != []:
        raise ValueError("not a research-only paper ledger")
    payload = {k: v for k, v in snapshot.items() if k != "snapshot_sha256"}
    if snapshot.get("snapshot_sha256") != digest(payload):
        raise ValueError("ledger hash mismatch")
    accounts = snapshot["accounts"]
    if set(accounts) != set(ARMS):
        raise ValueError("incomplete current V5 accounts")
    groups, skips, reentries = {}, Counter(), []
    filled, closed, open_positions = 0, 0, 0

    def collect(key, trade):
        row = groups.setdefault(key, dict(n=0, wins=0, paired=0,
            gross=Decimal(0), net=Decimal(0), friction=Decimal(0),
            paired_net=Decimal(0), benchmark=Decimal(0), excess=Decimal(0)))
        gross = (d(trade["exit_price_raw"], "exit") - d(trade["entry_open_raw"], "entry")) * trade["shares"]
        net = d(trade["net_pnl_cny"], "net")
        row["n"] += 1
        row["wins"] += int(net > 0)
        row["gross"] += gross
        row["net"] += net
        row["friction"] += gross - net
        if trade.get("excess_s0_equal_capital_cny") is not None:
            row["paired"] += 1
            row["paired_net"] += net
            row["benchmark"] += d(trade["s0_equal_capital_pnl_cny"], "S0")
            row["excess"] += d(trade["excess_s0_equal_capital_cny"], "excess")

    for arm, account in accounts.items():
        trades, positions, decisions = (account[k] for k in ("closed_trades", "positions", "decisions"))
        ids = [t["id"] for t in trades + positions]
        decision_ids = [t["id"] for t in decisions]
        fills = {t["id"] for t in decisions if t["status"] == "PAPER_OPEN_PROXY_FILLED"}
        if (len(set(ids)) != len(ids) or len(set(decision_ids)) != len(decision_ids)
                or fills != set(ids)):
            raise ValueError(f"{arm}: duplicate or unmatched fill")
        filled += len(fills)
        closed += len(trades)
        open_positions += len(positions)
        for decision in decisions:
            if decision["status"] != "PAPER_OPEN_PROXY_FILLED":
                skips[decision.get("reason") or decision["status"]] += 1
        for trade in trades:
            version = trade.get("strategy_experiment_id") or "LEGACY_V5"
            for key in ("all", arm, f"version:{version}", f"{arm}:{version}",
                        f"exit:{trade['exit_reason']}"):
                collect(key, trade)
        for trade in trades + positions:
            if any(t["id"] != trade["id"] and t["stock"] == trade["stock"]
                   and t["exit_session"] == trade["entry_session"] for t in trades):
                reentries.append({"arm": arm, "stock": trade["stock"],
                                  "session": trade["entry_session"],
                                  "net_cny": trade.get("net_pnl_cny")})

    # Benchmark sums cover only paired trades; do not make absent observations zero.
    for row in groups.values():
        if not row["paired"]:
            for key in ("paired_net", "benchmark", "excess"):
                row[key] = None
        for key, value in row.items():
            if isinstance(value, Decimal):
                row[key] = format(value.quantize(Decimal("0.01")), "f")
    return {"run_id": snapshot["github_run_id"], "snapshot_sha256": snapshot["snapshot_sha256"],
            "market_session": snapshot["last_market_session"], "filled": filled,
            "closed": closed, "open_positions": open_positions,
            "skips": dict(skips), "groups": groups, "same_day_reentries": reentries,
            "scope": "CLOSED_PAPER_TRADE_ATTRIBUTION_NOT_PORTFOLIO_RETURN_OR_CAUSAL_EFFECT",
            "friction_definition": "RAW_PRICE_PNL_MINUS_ROUNDED_NET_PNL_INCLUDES_FEES_SLIPPAGE_ROUNDING",
            "trade_authorized": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(json.loads(args.snapshot.read_text(encoding="utf-8"))),
                     ensure_ascii=False, indent=2))
