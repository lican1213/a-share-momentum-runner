"""Frozen-hypothesis market-regime diagnostic, NOT a deployable trading strategy.

Only market index data available at SIGNAL-DATE close are used. Historical
comparison uses the already-inspected/current-survivor universe, hence is
exploratory and ineligible for out-of-sample validation claims.
"""
from __future__ import annotations
from collections import Counter
from edge_diagnostics import _metrics

def regime_study(trades: list[dict], market_context: dict) -> dict:
    historical = market_context.get("historical_regimes_by_index", {})
    indexes = ("CSI300", "CSI1000")
    out={"hypothesis_id":"H01_market_both_indices_above_MA20_AND_MA60",
         "prespecified_rule":"At signal_date close, both CSI300 and CSI1000 close > their trailing MA20 AND MA60",
         "retrospective_sample_only":True,
         "eligible_for_live_trading":False,
         "data_status":"UNAVAILABLE","by_regime":{},
         "coverage":{}}
    if not all(historical.get(k) for k in indexes):
        out["data_problem"]="at least one complete historical index series unavailable"
        return out
    passed,rejected,unknown=[],[],[]
    for t in trades:
        if t.get("net_return") is None:continue
        day=t.get("signal_date")
        flags=[historical[k].get(day) for k in indexes]
        if any(v is None for v in flags):
            unknown.append(t)
            continue
        if all(f["above_ma20"] and f["above_ma60"] for f in flags):
            passed.append(t)
        else:
            rejected.append(t)
    out["data_status"]="AVAILABLE_FOR_RETROSPECTIVE_DIAGNOSTIC"
    out["coverage"]={"closed_evaluable":len(passed)+len(rejected),
                     "closed_missing_index_date":len(unknown),
                     "closed_total":len(passed)+len(rejected)+len(unknown)}
    out["by_regime"]={"pass":_metrics(passed),"reject":_metrics(rejected),
                      "missing":_metrics(unknown)}
    out["interpretation_limits"]=[
        "The current 12-name universe contains survivors and is not a historical investable universe.",
        "All this historical period has already been inspected by the model developer.",
        "Do not optimize or activate this filter from these numbers.",
        "Trade timestamps use daily bars; actual 14:50 T+3 is not modeled.",
        "Historical index bars are research snapshots; live advance/decline breadth remains missing.",
    ]
    return out
