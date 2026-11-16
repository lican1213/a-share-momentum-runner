"""EXP-0012 dispatcher, feedback and not-yet-risen selection regression."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from national_team.event_router_v5 import paper_feedback, route
from national_team.left_entry_v5 import rank
import national_team.left_entry_v5 as left_v5


def write(root, name, item):
    path = root / "2026-11-02" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(item), encoding="utf-8")
    return path


def item(code, r5, ma=0, relative=.03):
    return {"stock": code, "r5": str(r5), "distance_ma20": str(ma),
            "relative_r5": str(relative), "weight_index_proxy": "1",
            "close": "10"}


def test_unrisen_first_and_two_distinct_dip_policies():
    candidates = [
        item("600001", ".029"), item("600002", "-.002"),
        item("600003", "-.025"), item("600004", "-.010"),
    ]
    shallow = [x["stock"] for x in rank(candidates, "SHALLOW_DIP")]
    deep = [x["stock"] for x in rank(candidates, "DEEP_DIP")]
    assert shallow == ["600002", "600004", "600003", "600001"]
    assert deep == ["600003", "600004", "600002", "600001"]
    with pytest.raises(ValueError):
        rank(candidates, "OLD_CHASE_FIRST")


def test_freeze_shadow_paper_not_broker_order(monkeypatch):
    original = {
        "experiment_id": "EXP-0011", "version": "OLD",
        "admission": {"pilot_admitted": True},
        "candidates_ranked": [
            item("600001", ".029"), item("600002", "-.002"),
            item("600003", "-.025")],
        "accounts": {
            "F1_LEFT": {"orders": [], "state": "PAPER_NEXT_OPEN_PENDING"},
            "F2_WEAK": {"same_precommitted_candidates": []},
            "S0_ETF": {"budget_cny": "0"},
        },
        "measurement": {}, "broker_orders": [], "trade_authorized": False,
        "freeze_payload_sha256": "prior",
    }
    monkeypatch.setattr(left_v5, "baseline_freeze", lambda *args, **kwargs: original)
    result = left_v5.freeze({}, {}, {}, now="2026-11-02T18:00:00+08:00",
                            next_session="2026-11-03",
                            selected_policy="SHALLOW_DIP")
    assert result["experiment_id"] == "EXP-0012"
    assert result["freeze_payload_sha256"] != "prior"
    primary = [x["stock"] for x in result["accounts"]["F1_LEFT"]["orders"]]
    shadow = [x["stock"] for x in result["paper_policies"]["DEEP_DIP"]["orders"]]
    assert primary == ["600002", "600003"]
    assert shadow == ["600003", "600002"]
    assert [o["stock"] for o in result["paper_policies"]["R_BOUNCE"]["orders"]] == ["600001"]
    assert result["extension_experiment_id"] == "EXP-0013"
    assert all(x["fill"] is None and x["paper_position"] == 0 for x in
               result["accounts"]["F1_LEFT"]["orders"])
    assert result["broker_orders"] == []
    assert result["trade_authorized"] is False


def test_router_routes_real_session_once_and_never_old_weekend(tmp_path):
    v3_root, watch_root = tmp_path / "v3", tmp_path / "watch"
    freeze_root, result_root = tmp_path / "freeze", tmp_path / "follow"
    signal = {"date": "2026-11-02", "market_down": True,
              "share_proxy_event": True, "net_creation_1d_cny": 100,
              "net_creation_5d_cny": 300, "ratio_status": "DENOMINATOR_MISSING",
              "ordinary_float_coverage_ratio": None, "index_ret5": -.03}
    write(v3_root, "v3.json", {
        "method": {"codes": ["510300", "510310", "510330", "159919"]},
        "daily": [signal],
        "data_quality": {"last_full_four_share_day": "2026-11-02"},
        "source_provenance": {"as_of_utc": "2026-11-02T09:10:00+00:00"},
    })
    write(watch_root, "watch.json", {
        "funding_date": "2026-11-02", "collector_capture_time": "2026-11-02T17:00:00+08:00",
        "candidate_pool_pre_filter": ["600002"],"stock_snapshots":{"600002":{"data_date":"2026-11-02"}}})
    args = (v3_root, watch_root, freeze_root, result_root)
    fresh = route(*args, now="2026-11-02T18:10:00+08:00")
    assert fresh["status"] == "NEW_FUNDING_EVENT"
    assert fresh["selected_policy"] == "SHALLOW_DIP"
    assert fresh["watch_path"].endswith("watch.json")
    assert fresh["funding"]["ordinary_float_coverage_ratio"] is None
    write(freeze_root, "freeze.json", {
        "experiment_id": "EXP-0012", "signal_session": "2026-11-02"})
    assert route(*args, now="2026-11-02T18:11:00+08:00")["status"] == (
        "ALREADY_FROZEN_FOR_SESSION")
    assert route(*args, now="2026-11-06T18:10:00+08:00")["status"] == (
        "WAIT_FRESH_FOUR_ETF_SESSION")


def test_feedback_is_unique_per_event_and_maturity_changes_policy(tmp_path):
    root = tmp_path / "outcomes"
    def event(sha, day, deep, shallow):
        return {"experiment_id": "EXP-0012", "source_freeze_sha256": sha,
                "asof": day, "policy_results": {
                    "DEEP_DIP": {"F1_LEFT": [{"horizons": {
                        "10": {"status": "PAIRED", "excess_s0": str(deep)}}}]},
                    "SHALLOW_DIP": {"F1_LEFT": [{"horizons": {
                        "10": {"status": "PAIRED", "excess_s0": str(shallow)}}}]},
                }}
    for n in range(7):
        write(root, f"out-{n}.json", {"results": [
            event(f"freeze{n}", "2026-11-02", ".01", "-.01")]})
    wait = paper_feedback(root)
    assert wait["paired_10d_events"] == 7
    assert wait["selected_policy"] == "SHALLOW_DIP"
    write(root, "last.json", {"results": [
        event("freeze7", "2026-11-02", ".01", "-.01"),
        event("freeze0", "2026-11-01", ".01", "-.01")]})
    ready = paper_feedback(root)
    assert ready["paired_10d_events"] == 8
    assert ready["selected_policy"] == "DEEP_DIP"
    assert ready["mean_10d_excess_s0"]["DEEP_DIP"] == "0.01"


def test_no_marked_profit_for_unmatured_pair(tmp_path):
    root = tmp_path / "outcomes"
    write(root, "wait.json", {"results": [{
        "experiment_id": "EXP-0012", "source_freeze_sha256": "a",
        "asof": "2026-11-02",
        "policy_results": {
            "DEEP_DIP": {"F1_LEFT": [{"horizons": {
                "10": {"status": "UNMATURED", "excess_s0": None}}}]},
            "SHALLOW_DIP": {"F1_LEFT": []},
        },
    }]})
    feedback = paper_feedback(root)
    assert feedback["paired_10d_events"] == 0
    assert feedback["mean_10d_excess_s0"]["SHALLOW_DIP"] is None



def test_consecutive_sessions_in_one_funding_cluster_do_not_double_count(tmp_path):
    root = tmp_path / "followups"
    rows = []
    for i in range(8):
        rows.append({
            "experiment_id": "EXP-0012", "source_freeze_sha256": f"sha{i}",
            "signal_session": f"2026-11-{i+2:02d}",
            "cluster_anchor": "2026-11-02",
            "asof": "2026-12-02",
            "policy_results": {
                policy: {"F1_LEFT": [{"horizons": {
                    "10": {"status": "PAIRED", "excess_s0": ".02"}}}]}
                for policy in ("SHALLOW_DIP", "DEEP_DIP")
            },
        })
    write(root, "cluster.json", {"results": rows})
    feedback = paper_feedback(root)
    assert feedback["paired_10d_events"] == 1
    assert feedback["selected_policy"] == "SHALLOW_DIP"



def test_independent_right_reference_does_not_change_left_policy(tmp_path):
    root = tmp_path / "outcomes"
    def arm(v):
        return {"F1_LEFT": [{"horizons": {"10": {
            "status": "PAIRED", "excess_s0": str(v)}}}]}
    write(root, "right.json", {"results": [{
        "experiment_id": "EXP-0012", "source_freeze_sha256": "right-event",
        "signal_session": "2026-11-02", "cluster_anchor": "2026-11-02",
        "asof": "2026-12-01",
        "policy_results": {
            "SHALLOW_DIP": arm(".01"), "DEEP_DIP": arm(".02"),
            "R_BOUNCE": arm(".03")}}]})
    fb = paper_feedback(root)
    assert fb["selected_policy"] == "SHALLOW_DIP"  # only one left mature cluster
    assert fb["right_side_reference"]["paired_10d_clusters"] == 1
    assert fb["right_side_reference"]["mean_R_minus_SHALLOW_excess_s0"] == "0.02"

def test_newest_non_signal_or_missing_session_never_replays_old_signal(tmp_path):
    roots = [tmp_path / k for k in ("v3", "watch", "freeze", "outcomes")]
    older = {"date": "2026-11-02", "market_down": True, "share_proxy_event": True,
             "net_creation_1d_cny": 100, "net_creation_5d_cny": 300}
    payload = {"method": {"codes": ["510300","510310","510330","159919"]},
               "daily": [older], "data_quality": {"last_index_day": "2026-11-03",
               "last_full_four_share_day": "2026-11-03"}}
    write(roots[0], "legacy.json", payload)
    result = route(*roots, now="2026-11-03T18:00:00+08:00")
    assert result["signal_session"] == "2026-11-03"
    assert result["status"] == "WAIT_LATEST_SESSION_EVIDENCE"
    payload["latest_session"] = {**older, "date": "2026-11-03", "market_down": False}
    write(roots[0], "new.json", payload)
    result = route(*roots, now="2026-11-03T18:00:00+08:00")
    assert result["status"] == "NO_NEW_FUNDING_EVENT"


def test_primary_ratio_precedes_proxy_when_complete():
    from national_team.coverage_v3 import observed_funding_basis
    sig = {"market_down": True, "share_proxy_event": True,
           "net_creation_1d_cny": 10, "net_creation_5d_cny": 20,
           "ordinary_float_coverage_ratio": .05,
           "coverage_change_1d": -.01, "coverage_change_5d": .02}
    assert observed_funding_basis(sig) == ("PRIMARY_COVERAGE_OBSERVED", False)
    sig.update(coverage_change_1d=.01, share_proxy_event=False)
    assert observed_funding_basis(sig) == ("PRIMARY_COVERAGE_OBSERVED", True)
    sig["coverage_change_1d"] = None
    sig["share_proxy_event"] = True
    assert observed_funding_basis(sig) == ("SHARE_PROXY", True)


def test_identical_left_stock_sets_do_not_count_as_learning(tmp_path):
    entry = {"stock":"600001", "horizons":{"10":{"status":"PAIRED","excess_s0":".01"}}}
    write(tmp_path, "same.json", {"results":[{"experiment_id":"EXP-0012",
        "source_freeze_sha256":"same", "cluster_anchor":"2026-11-02",
        "signal_session":"2026-11-02","asof":"2026-11-30",
        "policy_results":{p:{"F1_LEFT":[entry]} for p in ("SHALLOW_DIP","DEEP_DIP")}}]})
    result = paper_feedback(tmp_path)
    assert result["paired_10d_events"] == 0
    assert result["indistinguishable_left_clusters"] == 1


def test_delayed_complete_funding_can_route_without_reviving_older_events(tmp_path):
    from national_team.coverage_v3 import decision_funding_session
    roots = [tmp_path / k for k in ("v3", "watch", "freeze", "outcomes")]
    old = {"date":"2026-11-13", "market_down":True, "share_proxy_event":True,
           "net_creation_1d_cny":100, "net_creation_5d_cny":300}
    latest = {"date":"2026-11-16", "net_creation_1d_cny":None, "net_creation_5d_cny":None}
    payload = {"method":{"codes":["510300","510310","510330","159919"]},
               "daily":[old,latest],"latest_session":latest,
               "data_quality":{"last_index_day":"2026-11-16","last_full_four_share_day":"2026-11-13"}}
    write(roots[0],"new.json",payload)
    write(roots[1],"watch.json",{"funding_date":"2026-11-13",
          "collector_capture_time":"2026-11-16T16:00:00+08:00","candidate_pool_pre_filter":["600001"],
          "stock_snapshots":{"600001":{"data_date":"2026-11-13"}}})
    now="2026-11-16T18:00:00+08:00"
    record=route(*roots,now=now)
    assert decision_funding_session(payload)["date"] == record["signal_session"] == "2026-11-13"
    assert record["latest_index_session"]=="2026-11-16" and record["funding_lags_index"]
    assert record["status"]=="NEW_FUNDING_EVENT"
    assert route(*roots,now="2026-11-17T18:00:00+08:00")["status"]=="WAIT_FRESH_FOUR_ETF_SESSION"
    write(roots[2],"freeze.json",{"experiment_id":"EXP-0012","signal_session":"2026-11-13"})
    assert route(*roots,now=now)["status"]=="ALREADY_FROZEN_FOR_SESSION"
    # A newer complete negative day must supersede an older positive day.
    latest.update(net_creation_1d_cny=-1, net_creation_5d_cny=-10)
    write(roots[0],"new.json",payload)
    assert route(*roots,now=now)["status"]=="NO_NEW_FUNDING_EVENT"
    latest.update(net_creation_1d_cny=None, net_creation_5d_cny=None)
    payload["daily"].insert(1,{**old,"date":"2026-11-15","net_creation_1d_cny":-1})
    assert decision_funding_session(payload)["date"]=="2026-11-16"


def test_watch_requires_actual_matching_liquidity_not_empty_candidate_pool(tmp_path):
    from national_team.event_router_v5 import matching_watch
    row={"funding_date":"2026-11-16","candidate_pool_pre_filter":["600001"],
         "collector_capture_time":"2026-11-16T17:00:00+08:00","stock_snapshots":{}}
    write(tmp_path,"empty.json",row)
    assert matching_watch(tmp_path,"2026-11-16")== (None,None)
    row["stock_snapshots"]={"600001":{"data_date":"2026-11-13"}}
    write(tmp_path,"wrong.json",row)
    assert matching_watch(tmp_path,"2026-11-16")== (None,None)
    row["stock_snapshots"]["600001"]["data_date"]="2026-11-16"
    write(tmp_path,"ready.json",row)
    assert matching_watch(tmp_path,"2026-11-16")[0].name=="ready.json"
