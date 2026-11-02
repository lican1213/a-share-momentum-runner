"""Deployment architecture regression: successful research runs must persist."""

from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
LIVE=ROOT/".github/workflows/national-team-live.yml"
WIKI=ROOT/".github/workflows/national-team-wiki-sync.yml"

def test_no_more_cancelled_market_evidence_due_to_model_pushes():
    s=LIVE.read_text(encoding="utf-8")
    assert "cancel-in-progress: false" in s
    assert "'national_team/**'" not in s
    assert "'tests/test_national_team_*.py'" not in s

def test_production_evidence_commits_only_append_only_records():
    s=LIVE.read_text(encoding="utf-8")
    line=next(x for x in s.splitlines() if "git add -- records/national_team_etf/" in x)
    assert "wiki/compiled" not in line and "wiki/indices" not in line
    assert "records/national_team_watch/" in line
    assert "records/national_team_merged/" in line
    assert "records/national_team_pcf/" in line
    assert "records/national_team_events/" not in line
    assert "records/national_team_paper/" not in line
    assert "git restore -- wiki/indices/ wiki/compiled/" in s
    assert s.index("Build real CSI300 index-weight stock watchlist") < s.index(
        "Persist unique run evidence")
    assert "Freeze first-observed S1 and S2 paper events" not in s
    assert "python -m national_team.live_paper_tracker" not in s

def test_derived_wiki_uses_separate_clean_checkout_and_retry():
    s=WIKI.read_text(encoding="utf-8")
    assert "git reset --hard origin/main" in s
    assert "python -m national_team.daily_report" in s
    assert "python scripts/wiki_sync.py" in s
    assert "records/national_team_daily/" in s
    assert "wiki/compiled/" in s and "wiki/indices/" in s
    assert "workflow_run:" in s
    assert "cancel-in-progress: false" in s



def test_retired_legacy_workflows_stay_out_of_the_daily_runner():
    retired = (
        "ashare.yml",
        "national-team-short-paper-week.yml",
        "national-team-short-probe.yml",
        "national-team-strategy-v2.yml",
        "national-team-left-entry-v4.yml",
    )
    assert all(not (ROOT / ".github/workflows" / name).exists()
               for name in retired)
    assert (ROOT / ".github/workflows/national-team-event-router-v5.yml").exists()
    assert (ROOT / ".github/workflows/national-team-left-outcomes-v5.yml").exists()


def test_only_v5_owns_new_daily_paper_events():
    workflows = ROOT / ".github/workflows"
    for name in ("national-team-short-a2.yml", "national-team-short-b.yml"):
        s = (workflows / name).read_text(encoding="utf-8")
        assert "workflow_dispatch:" in s
        assert "\n  push:" not in s
        assert "\n  schedule:" not in s
    router = (workflows / "national-team-event-router-v5.yml").read_text(encoding="utf-8")
    outcomes = (workflows / "national-team-left-outcomes-v5.yml").read_text(encoding="utf-8")
    assert "cron: '5 10 * * 1-5'" in router
    assert "cron: '45 10 * * 1-5'" in outcomes
