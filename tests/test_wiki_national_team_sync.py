"""LLM Wiki must prioritize actual national-team run facts over legacy momentum."""
import json
from pathlib import Path
from scripts.national_team_wiki import enumerate_records,generate

def save(root,folder,name,data):
    path=root/"records"/folder/"2026-10-28"/name
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data),encoding="utf-8")
    return path

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
            {"status": "PAPER_OPEN_PROXY_FILLED"},
            {"status": "PAPER_ENTRY_SKIPPED", "reason": "MAX_TWO_OPEN_POSITIONS"}]}}})
    generate(tmp_path, now="2026-11-20")
    brief = (tmp_path / "wiki/compiled/briefing.md").read_text()
    assert "纸面开盘入场 1、合法跳过 1" in brief
    assert "8条纸面意向拟于 2026-11-20 开盘研究" in brief
    assert "尚未证明这批意向已入场" in brief
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
    assert "8条意向，需按账户决策与未来OHLC逐条核对" in later
    assert "尚未证明这批意向已入场" not in later
