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
