"""LLM Wiki must prioritize actual national-team run facts over legacy momentum."""
import json
from pathlib import Path
from scripts.national_team_wiki import enumerate_records,generate
from national_team.left_entry_v4 import digest

def save(root,folder,name,data):
    path=root/"records"/folder/"2026-10-28"/name
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data),encoding="utf-8")
    return path

def seal(obj):
    obj['snapshot_sha256'] = digest({k: v for k, v in obj.items() if k != 'snapshot_sha256'})
    return obj

def test_latest_failed_run_and_latest_complete_research_are_distinct(tmp_path):
    (tmp_path/"wiki"/"indices").mkdir(parents=True)
    (tmp_path/"wiki"/"compiled").mkdir(parents=True)
    save(tmp_path,"national_team_etf","910-a1.json",
         {"run_id":"910","asof_requested":"2026-10-28",
          "status":"ATTEMPTED_NO_COMPLETE_FACTOR"})
    save(tmp_path,"national_team_merged","909-a1.json",
         {"run_id":"909","asof_requested":"2026-10-28",
          "status":"FULL_FOUR_ETF_SHARES_NAV_OBSERVED_RESEARCH",
          "funding_event":{"four_etf_factor":{
            "trade_date":"2026-10-27","daily_net_creation_proxy_cny":"5612203530",
            "five_day":{"net_creation_pct_initial_aum":"0.291066"}}}})
    save(tmp_path,"national_team_watch","908-a1.json",
         {"run_id":"908","status":"INDEX_PROXY_RESEARCH_WATCHLIST",
          "funding_date":"2026-10-27","pool_weight_coverage":"0.42",
          "research_ranking":{"ranked_from_n_stocks":30}})
    observed=enumerate_records(tmp_path)
    out=generate(tmp_path,now="2026-10-28",records=observed)
    assert out["last_complete_four_run"]=="909"
    text=(tmp_path/"wiki"/"compiled"/"briefing.md").read_text()
    assert "run 910" in text and "run 909" in text
    assert "5612203530" in text
    assert "run 908" in text
    assert "指数权重非ETF真实PCF" in text
    assert text.startswith("---\nid: COMPILED-BRIEFING")
    assert "historical alpha confirmed" not in text
    index=(tmp_path/"wiki"/"indices"/"national-team.md").read_text()
    assert "records/national_team" in index
    assert "909-a1.json" in index
    out2=generate(tmp_path,now="2026-10-28")
    assert out2["national_team_records"]==3
    assert text==(tmp_path/"wiki"/"compiled"/"briefing.md").read_text()

def test_no_source_records_never_create_false_success(tmp_path):
    out=generate(tmp_path,now="2026-10-28")
    assert out["last_complete_four_run"] is None
    brief=(tmp_path/"wiki"/"compiled"/"briefing.md").read_text()
    assert "无可复核持久化记录" in brief
    assert "独立样本外净超额收益" in brief

def test_v5_briefing_reports_pending_intents_without_false_fills(tmp_path):
    save(tmp_path, "national_team_merged", "900-a1.json",
         {"funding_event": {"four_etf_factor": {
             "trade_date": "2026-11-18", "daily_net_creation_proxy_cny": "100",
             "five_day": {}}}})
    save(tmp_path, "national_team_router", "901-a1.json", {
        "signal_session": "2026-11-19", "selected_policy": "SHALLOW_DIP",
        "status": "NEW_FUNDING_EVENT",
        "funding": {"funding_basis": "SHARE_PROXY",
                    "exchange_shares_complete": False, "exchange_nav_complete": False},
        "feedback": {"paired_10d_events": 1, "exp0017_cohort": {
            "EARLY_ENTRY": {"10": {"matured_clusters": 0}},
            "R_BOUNCE": {"10": {"matured_clusters": 0}}}}})
    save(tmp_path, "national_team_left_entry_v5", "902-a1.json", {
        "signal_session": "2026-11-19",
        "measurement": {"next_session": "2026-11-20"},
        "paper_policies": {arm: {"orders": [{"stock": "600000"}, {"stock": "600001"}]}
                           for arm in ("SHALLOW_DIP", "DEEP_DIP", "R_BOUNCE", "EARLY_ENTRY")}})
    save(tmp_path, "national_team_paper_accounts_v5", "903-a1.json", {
        "last_market_session": "2026-11-19", "source_event_count": 8,
        "accounts": {"SHALLOW_DIP": {"decisions": [
            {"id": "2026-11-18:SHALLOW_DIP:600003", "status": "PAPER_OPEN_PROXY_FILLED"},
            {"id": "2026-11-18:SHALLOW_DIP:600004", "status": "PAPER_ENTRY_SKIPPED",
             "reason": "MAX_TWO_OPEN_POSITIONS"}]}}})
    generate(tmp_path, now="2026-11-20")
    brief = (tmp_path / "wiki/compiled/briefing.md").read_text()
    assert "纸面开盘入场 1、合法跳过 1" in brief
    assert "最新冻结 2026-11-19：8条意向，已纸面入场 0、按规则跳过 0、迟到不补单 0、无账户决策 8" in brief
    assert "执行日待读回：预定 2026-11-20" in brief
    assert "不能在收盘归档前宣称已执行" in brief
    assert "最近源端完整日 2026-11-18" in brief
    assert "早期 0、追涨 0" in brief
    assert "默认组 SHALLOW_DIP" in brief

    # Later capture cannot turn the old frozen order into an executed fill.
    path = tmp_path / "records/national_team_paper_accounts_v5/2026-10-28/903-a1.json"
    obj = json.loads(path.read_text())
    obj["last_market_session"] = "2026-11-20"
    path.write_text(json.dumps(obj))
    generate(tmp_path, now="2026-11-20")
    later = (tmp_path / "wiki/compiled/briefing.md").read_text()
    assert "8条意向，已纸面入场 0、按规则跳过 0、迟到不补单 0、无账户决策 8" in later
    assert "生产缺口：冻结拟执行日已到" in later

def test_v5_provenance_readback_with_all_four_accounts(tmp_path):
    summary = {"cash_cny": "25000", "open_positions": 2}
    arms = ("SHALLOW_DIP", "DEEP_DIP", "R_BOUNCE", "EARLY_ENTRY")
    accounts = {arm: {"summary": summary, "decisions": []} for arm in arms}
    accounts["SHALLOW_DIP"]["decisions"] = [
        {"id": f"2026-11-19:SHALLOW_DIP:{stock}", "status": "PAPER_OPEN_PROXY_FILLED"}
        for stock in ("600958", "600999")]
    accounts["DEEP_DIP"]["decisions"] = [
        {"id": "2026-11-19:DEEP_DIP:000792", "status": "PAPER_ENTRY_SKIPPED",
         "reason": "ENTRY_OHLC_MISSING_NO_RETROSPECTIVE_FILL"}]
    save(tmp_path, "national_team_left_entry_v5", "902-a1.json", {
        "signal_session": "2026-11-19", "measurement": {"next_session": "2026-11-20"},
        "paper_policies": {
            "SHALLOW_DIP": {"orders": [{"stock": "600958"}, {"stock": "600999"}]},
            "DEEP_DIP": {"orders": [{"stock": "000792"}]}}})
    ledger = seal({"github_run_id": "903", "trade_authorized": False,
                   "broker_orders": [], "last_market_session": "2026-11-20",
                   "accounts": accounts})
    save(tmp_path, "national_team_paper_accounts_v5", "903-a1.json", ledger)
    outcome = seal({"github_run_id": "903", "trade_authorized": False,
                    "broker_orders": [], "capture_time": "2026-11-21T02:50:00+08:00",
                    "paper_account_snapshot_sha256": ledger["snapshot_sha256"],
                    "paper_account_summary": {arm: summary for arm in arms},
                    "results": [{"policy_results": {"DEEP_DIP": {
                        "errors": {"510300": "rate limit"}}}}]})
    saved = save(tmp_path, "national_team_left_outcomes_v5", "903-a1.json", outcome)
    save(tmp_path, "national_team_router", "901-a1.json", {
        "github_run_id": "901", "observed_at": "2026-11-21T02:24:00+08:00",
        "status": "ALREADY_FROZEN_FOR_SESSION"})
    generate(tmp_path, now="2026-11-22")
    brief = (tmp_path/"wiki/compiled/briefing.md").read_text()
    assert "3条意向，已纸面入场 2、按规则跳过 1、迟到不补单 0、无账户决策 0" in brief
    assert "MATCHED_SNAPSHOT" in brief
    assert "本次OHLC跟踪来源异常（全批次）：510300" in brief
    assert "后续路由反馈读回仍待验收" in brief
    assert "NO_STATUS_FIELD" in (tmp_path/"wiki/indices/national-team.md").read_text()
    # Matching run and account summary are NOT sufficient when hash link is wrong.
    outcome["paper_account_snapshot_sha256"] = "wrong"
    saved.write_text(json.dumps(seal(outcome)))
    generate(tmp_path, now="2026-11-22")
    assert "NOT_VERIFIED" in (tmp_path/"wiki/compiled/briefing.md").read_text()


def test_v5_stale_ledger_at_future_due_and_overdue_dates(tmp_path):
    save(tmp_path, "national_team_left_entry_v5", "101-a1.json", {
        "signal_session": "2026-11-20", "measurement": {"next_session": "2026-11-23"},
        "paper_policies": {"SHALLOW_DIP": {"orders": [{"stock": "600958"}]}}})
    paper = save(tmp_path, "national_team_paper_accounts_v5", "102-a1.json", {
        "last_market_session": "2026-11-20",
        "accounts": {"SHALLOW_DIP": {"summary": {}, "decisions": []}}})
    generate(tmp_path, now="2026-11-22")
    assert "预定市场日尚未到达" in (tmp_path/"wiki/compiled/briefing.md").read_text()
    generate(tmp_path, now="2026-11-23")
    assert "执行日待读回" in (tmp_path/"wiki/compiled/briefing.md").read_text()
    generate(tmp_path, now="2026-11-24")
    overdue = (tmp_path/"wiki/compiled/briefing.md").read_text()
    assert "OVERDUE_MARKET_READBACK" in overdue
    assert "预定市场日尚未到达" not in overdue
    # Late intent is an explicit negative decision, never an unfilled open intent.
    ledger = json.loads(paper.read_text())
    ledger["last_market_session"] = "2026-11-23"
    ledger["accounts"]["SHALLOW_DIP"]["decisions"] = [{
        "id": "2026-11-20:SHALLOW_DIP:600958",
        "status": "LATE_INTENT_NO_BACKFILL"}]
    paper.write_text(json.dumps(ledger))
    generate(tmp_path, now="2026-11-24")
    assert "迟到不补单 1、无账户决策 0" in (tmp_path/"wiki/compiled/briefing.md").read_text()


def test_v5_duplicate_decision_and_duplicate_freeze_are_not_green(tmp_path):
    account = {"summary": {}, "decisions": [
        {"id": "2026-11-19:SHALLOW_DIP:600958", "status": "PAPER_OPEN_PROXY_FILLED"},
        {"id": "2026-11-19:SHALLOW_DIP:600958", "status": "PAPER_ENTRY_SKIPPED"}]}
    frozen = {"signal_session": "2026-11-19", "measurement": {"next_session": "2026-11-20"},
              "paper_policies": {"SHALLOW_DIP": {"orders": [{"stock": "600958"}]}}}
    path = save(tmp_path, "national_team_left_entry_v5", "101-a1.json", frozen)
    arms = ("SHALLOW_DIP", "DEEP_DIP", "R_BOUNCE", "EARLY_ENTRY")
    ledger = seal({"github_run_id": "102", "trade_authorized": False, "broker_orders": [],
                   "last_market_session": "2026-11-20",
                   "accounts": {arm: account if arm=="SHALLOW_DIP"
                                else {"summary": {}, "decisions": []} for arm in arms}})
    save(tmp_path, "national_team_paper_accounts_v5", "102-a1.json", ledger)
    outcome = seal({"github_run_id": "102", "trade_authorized": False, "broker_orders": [],
                    "paper_account_snapshot_sha256": ledger["snapshot_sha256"],
                    "paper_account_summary": {arm: {} for arm in arms}})
    save(tmp_path, "national_team_left_outcomes_v5", "102-a1.json", outcome)
    generate(tmp_path, now="2026-11-21")
    brief = (tmp_path/"wiki/compiled/briefing.md").read_text()
    assert "EVIDENCE_CONFLICT" in brief
    assert "NOT_VERIFIED" in brief and "MATCHED_SNAPSHOT" not in brief
    assert "已纸面入场 1、按规则跳过 0" not in brief
    frozen["paper_policies"]["SHALLOW_DIP"]["orders"].append({"stock": "600958"})
    path.write_text(json.dumps(frozen))
    generate(tmp_path, now="2026-11-21")
    assert "最新冻结意向重复" in (tmp_path/"wiki/compiled/briefing.md").read_text()


def test_v5_mutated_hash_and_missing_arm_are_not_green(tmp_path):
    arms = ("SHALLOW_DIP", "DEEP_DIP", "R_BOUNCE", "EARLY_ENTRY")
    ledger = seal({"github_run_id": "102", "trade_authorized": False, "broker_orders": [],
                   "accounts": {arm: {"summary": {"open_positions": 0}, "decisions": []}
                                for arm in arms}})
    paper = save(tmp_path, "national_team_paper_accounts_v5", "102-a1.json", ledger)
    outcome = seal({"github_run_id": "102", "trade_authorized": False, "broker_orders": [],
                    "paper_account_snapshot_sha256": ledger["snapshot_sha256"],
                    "paper_account_summary": {arm: ledger["accounts"][arm]["summary"] for arm in arms}})
    saved = save(tmp_path, "national_team_left_outcomes_v5", "102-a1.json", outcome)
    generate(tmp_path, now="2026-11-22")
    assert "MATCHED_SNAPSHOT" in (tmp_path/"wiki/compiled/briefing.md").read_text()
    # Tamper a decision without changing the declared digest or summary.
    ledger["accounts"]["SHALLOW_DIP"]["decisions"].append({
        "id": "2026-11-20:SHALLOW_DIP:600958", "status": "PAPER_OPEN_PROXY_FILLED"})
    paper.write_text(json.dumps(ledger))
    generate(tmp_path, now="2026-11-22")
    assert "NOT_VERIFIED" in (tmp_path/"wiki/compiled/briefing.md").read_text()
    # Even internally consistent checksums cannot compensate for a missing fourth account.
    del ledger["accounts"]["EARLY_ENTRY"]
    seal(ledger)
    paper.write_text(json.dumps(ledger))
    outcome["paper_account_snapshot_sha256"] = ledger["snapshot_sha256"]
    del outcome["paper_account_summary"]["EARLY_ENTRY"]
    saved.write_text(json.dumps(seal(outcome)))
    generate(tmp_path, now="2026-11-22")
    assert "MATCHED_SNAPSHOT" not in (tmp_path/"wiki/compiled/briefing.md").read_text()


def test_v5_all_batch_errors_and_later_router_without_provenance(tmp_path):
    outcome = seal({"github_run_id": "110", "capture_time": "2026-11-21T02:50:00+08:00",
                    "results": [{"policy_results": {"DEEP_DIP": {"errors": {"510300": "rate limit"}}}},
                                {"policy_results": {"DEEP_DIP": {"errors": {}}}}],
                    "trade_authorized": False, "broker_orders": []})
    save(tmp_path, "national_team_left_outcomes_v5", "110-a1.json", outcome)
    route_path = save(tmp_path, "national_team_router", "111-a1.json", {
        "observed_at": "2026-11-21T03:00:00+08:00", "github_run_id": "111"})
    generate(tmp_path, now="2026-11-22")
    brief = (tmp_path/"wiki/compiled/briefing.md").read_text()
    assert "本次OHLC跟踪来源异常（全批次）：510300" in brief
    assert "UNVERIFIED_SOURCE_SNAPSHOT" in brief
    assert "MATCHED_SOURCE_SNAPSHOT" not in brief
    route = json.loads(route_path.read_text())
    route["feedback_source_outcomes_snapshot_sha256"] = outcome["snapshot_sha256"]
    route_path.write_text(json.dumps(route))
    generate(tmp_path, now="2026-11-22")
    assert "MATCHED_SOURCE_SNAPSHOT" in (tmp_path/"wiki/compiled/briefing.md").read_text()
