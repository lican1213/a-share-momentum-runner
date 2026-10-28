"""Research-only attribution of exit mechanics and gap risk.

Computations use *completed* historical trades. There is no assumption that
trade observations are independent or that these diagnostics establish alpha.
"""
from __future__ import annotations
from collections import defaultdict
from statistics import mean, median
from typing import Any

def _metrics(items: list[dict]) -> dict:
    vals=[float(t["net_return"]) for t in items if t.get("net_return") is not None]
    if not vals: return {"n":0,"mean_net":None,"win_fraction":None}
    return {"n":len(vals),"mean_net":round(mean(vals),7),
            "win_fraction":round(sum(v>0 for v in vals)/len(vals),6)}

def diagnose(trades: list[dict[str,Any]]) -> dict[str,Any]:
    closed=[t for t in trades if t.get("net_return") is not None]
    censored=[t for t in trades if t.get("net_return") is None]
    grouped=defaultdict(list)
    for t in closed: grouped[t["reason"]].append(t)
    winners=[t for t in closed if float(t["net_return"])>0]
    losers=[t for t in closed if float(t["net_return"])<0]
    pair=[t for t in closed if t.get("matched_T3_passive_net") is not None]
    mean_win=mean(float(x["net_return"]) for x in winners) if winners else None
    mean_loss=mean(float(x["net_return"]) for x in losers) if losers else None
    breakeven=(abs(mean_loss)/(mean_win+abs(mean_loss))
               if mean_loss is not None and mean_win is not None else None)
    gap=[t for t in closed if t["reason"]=="stop_gap"]
    all_stop=[t for t in closed if t["reason"] in ("stop","stop_gap")]
    loss_sum=sum(abs(float(t["net_return"])) for t in losers)
    gap_loss_sum=sum(abs(float(t["net_return"])) for t in gap)
    d={
        "closed_count":len(closed),"censored_count":len(censored),
        "strategy":_metrics(closed),
        "exit_reason_stats":{k:_metrics(v) for k,v in sorted(grouped.items())},
        "losers_count":len(losers),"winners_count":len(winners),
        "mean_winner_return":round(mean_win,7) if mean_win is not None else None,
        "mean_loser_return":round(mean_loss,7) if mean_loss is not None else None,
        "implied_breakeven_win_fraction":round(breakeven,6) if breakeven is not None else None,
        "stop_count":len(all_stop),"gap_stop_count":len(gap),
        "gap_stop_share_of_absolute_losses":round(gap_loss_sum/loss_sum,6) if loss_sum else None,
        "same_trade_T3_passive_comparison":{
            "n_paired":len(pair),
            "mean_strategy_net":round(mean(float(x["net_return"]) for x in pair),7) if pair else None,
            "mean_passive_net":round(mean(float(x["matched_T3_passive_net"]) for x in pair),7) if pair else None,
            "mean_active_minus_passive":round(mean(float(x["net_return"])-float(x["matched_T3_passive_net"]) for x in pair),7) if pair else None,
            "note":"OHLC T+3 CLOSE proxy, not verified 14:50, no inference of trade fill and not independent OOS."
        },
        "model_release_gate":"RESEARCH_ONLY_UNVALIDATED",
        "testable_hypotheses":[
            "preknown-index-breadth regime gate may reduce next-session stop gaps; do not tune threshold to inspected holdout",
            "fixed early profit target may truncate winners versus same-entry T+3 passive; 14:50 executable prices required",
            "cost and gap slippage dominate small stops; enforce risk budgets on tail gap rather than nominal stop",
        ],
        "statistical_claims":"None: small non-independent selected-survivor sample; no uncertainty interval claimed."
    }
    return d
