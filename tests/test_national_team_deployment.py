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
    assert "records/national_team_audits/" in line
    assert s.index("Independent red-team integrity audit")<s.index("Persist unique run evidence")

def test_derived_wiki_uses_separate_clean_checkout_and_retry():
    s=WIKI.read_text(encoding="utf-8")
    assert "git reset --hard origin/main" in s
    assert "python -m national_team.daily_report" in s
    assert "python scripts/wiki_sync.py" in s
    assert "records/national_team_daily/" in s
    assert "wiki/compiled/" in s and "wiki/indices/" in s
    assert "workflow_run:" in s
    assert "cancel-in-progress: false" in s
