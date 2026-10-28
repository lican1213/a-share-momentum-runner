"""Synthetic regression tests: no claim of live strategy performance."""
from edge_diagnostics import diagnose

def test_gap_stop_is_separate_from_nominal_stop_and_paired_T3():
    items=[
      {"reason":"stop_gap","net_return":-0.03,"matched_T3_passive_net":-0.01},
      {"reason":"stop","net_return":-0.01,"matched_T3_passive_net":-0.02},
      {"reason":"target","net_return":0.02,"matched_T3_passive_net":0.06},
      {"reason":"unfilled","net_return":None},
    ]
    d=diagnose(items)
    assert d["closed_count"]==3
    assert d["censored_count"]==1
    assert d["gap_stop_count"]==1
    assert d["stop_count"]==2
    assert abs(d["gap_stop_share_of_absolute_losses"]-0.75)<1e-5
    assert abs(d["same_trade_T3_passive_comparison"]["mean_active_minus_passive"]-(-0.05 / 3))<1e-6
    assert d["model_release_gate"]=="RESEARCH_ONLY_UNVALIDATED"

def test_unavailable_pairs_not_credited_as_zero_returns():
    d=diagnose([{"reason":"unfilled","net_return":None}])
    assert d["closed_count"]==0
    assert d["same_trade_T3_passive_comparison"]["mean_passive_net"] is None
