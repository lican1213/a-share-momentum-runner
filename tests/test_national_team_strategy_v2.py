"""Adversarial tests for full-four, no-lookahead, independent S2 ranking."""
import copy
import json
from pathlib import Path

import pytest

from national_team.strategy_v2 import VERSION, build

ROOT = Path(__file__).resolve().parents[1]
WATCH = ROOT / "records/national_team_watch/2026-10-28/40710985962-a1.json"
MERGED = ROOT / "records/national_team_merged/2026-10-28/40710985962-a1.json"
OBSERVED = "2026-10-28T23:45:00+08:00"


def evidence():
    return (json.loads(WATCH.read_text(encoding="utf-8")),
            json.loads(MERGED.read_text(encoding="utf-8")))


def run(w=None, m=None, *, at=OBSERVED):
    if w is None or m is None:
        w, m = evidence()
    return build(w, m, observed_at=at, source_watch=str(WATCH),
                 source_merged=str(MERGED), source_commit="test-sha")


def test_actual_archived_four_fund_replay_independent_strategy():
    out = run()
    assert out["status"] == "FROZEN_PROSPECTIVE_RESEARCH"
    assert out["flow_scope"] == "FULL_CORE_FOUR"
    assert out["flow_date"] == "2026-10-27"
    assert out["stock_data_date"] == "2026-10-28"
    assert out["four_etf_flow_cny"] == "5612203530.000000"
    assert out["stock_pool_size"] == 150
    assert len(out["s1_ranked"]) == 5 and len(out["s2_ranked"]) == 5
    assert out["s2_eligible_pool_count"] >= 5
    assert all(0 < float(r["relative_strength20"]) <= 0.1 for r in out["s2_ranked"])
    ranked_s1 = {r["symbol"] for r in out["s1_ranked"]}
    assert any(r["symbol"] not in ranked_s1 for r in out["s2_ranked"])
    assert len(out["events"]) == 2
    assert all(e["first_public_at"] == OBSERVED for e in out["events"])
    assert all(e["benchmark_etf"] == "510300" for e in out["events"])
    assert all(e["broker_trades_authorized"] is False for e in out["events"])


def test_existing_top10_relative_strength_bug_is_not_repeated():
    out = run()
    # Existing old S2 incorrectly selected stocks with >10% relative strength.
    assert all(float(r["relative_strength20"]) <= .1 for r in out["s2_ranked"])
    assert all(r["symbol"] not in ("600000", "601166") for r in out["s2_ranked"])


def test_deterministic_identity_and_first_published_not_backdated():
    x, y = run(), run()
    assert [e["id"] for e in x["events"]] == [e["id"] for e in y["events"]]
    assert all(e["model_version"] == VERSION for e in x["events"])
    assert all(e["funding_underlying_day"] == "2026-10-27" for e in x["events"])
    with pytest.raises(ValueError, match="future data"):
        run(at="2026-10-27T15:01:00+08:00")


def test_no_fake_four_etf_signal_when_missing():
    w, m = evidence()
    m["funding_event"]["four_etf_factor"] = None
    out = run(w, m)
    assert out["status"] == "FOUR_ETF_NOT_COMPLETE"
    assert out["events"] == []


def test_negative_fund_flows_do_not_produce_long_cohorts():
    w, m = evidence()
    full = m["funding_event"]["four_etf_factor"]
    full["per_etf_daily_flow_proxy_cny"] = {
        k: str(-abs(float(v))) for k, v in full["per_etf_daily_flow_proxy_cny"].items()
    }
    full["daily_net_creation_proxy_cny"] = str(sum(
        float(v) for v in full["per_etf_daily_flow_proxy_cny"].values()))
    out = run(w, m)
    assert out["events"] == []
    assert out["flow_direction"] == "NET_REDEMPTION"


def test_tampering_inconsistent_headline_rejected():
    w, m = evidence()
    m["funding_event"]["four_etf_factor"]["daily_net_creation_proxy_cny"] = "999"
    with pytest.raises(ValueError, match="reconcile"):
        run(w, m)


def test_future_stock_quote_not_allowed():
    w, m = evidence()
    s = next(iter(w["stock_snapshots"]))
    w["stock_snapshots"][s]["first_observed_at"] = "2026-10-30T13:00:00+08:00"
    with pytest.raises(ValueError, match="future OHLC"):
        run(w, m)


def test_stale_old_flow_not_promoted_to_new_signal():
    out = run(at="2026-11-04T23:10:00+08:00")
    assert out["status"] == "STALE_FOUR_ETF_FACTOR"
    assert out["events"] == []


def test_no_lookahead_missing_strength_does_not_enter_s2():
    w, m = evidence()
    # Prevent S2 by making all strength null but preserve S1.
    for row in w["stock_snapshots"].values():
        row["relative_strength20"] = None
    out = run(w, m)
    assert out["s2_ranked"] == []
    assert len(out["events"]) == 1
    assert out["events"][0]["strategy_id"] == "S1_FLOW_OVER_ADV20"


def test_methodology_records_common_index_weights_no_claim_of_identity():
    out = run()
    assert out["limitations"]["index_weight_proxy_identical_for_all_four_etfs"] is True
    assert out["limitations"]["funding_only_times_entries_not_cross_sectional_rank"] is True
    assert out["trade_authorized"] is False
