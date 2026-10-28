"""Wiki/MOC sanity checks executed by pytest on every code CI run."""
from scripts.wiki_lint import lint, frontmatter, check_local_links
from pathlib import Path
import pytest


def test_wiki_links_and_unique_metadata_in_repository():
    assert lint() == []


def test_missing_frontmatter_rejected(tmp_path):
    with pytest.raises(ValueError, match="missing frontmatter"):
        frontmatter("# no metadata", tmp_path / "unlabeled.md")


def test_bad_internal_link_found(tmp_path):
    from scripts.wiki_lint import ROOT
    page = ROOT / "wiki" / "fake-not-on-disk.md"
    failures = check_local_links(page, "[missing](no-such-relative-file.md)")
    assert len(failures) == 1
    assert "missing" in failures[0]


def test_repo_navigation_files_exist():
    from scripts.wiki_lint import REQUIRED, ROOT
    assert all((ROOT / p).is_file() for p in REQUIRED)
