"""Deterministic, no-network lint for the repository LLM Wiki/MOC.

Checks required entrypoints, page IDs, YAML-like frontmatter and local Markdown
links. Does NOT pretend to validate financial results or GitHub job conclusions.
"""
from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
WIKI = ROOT / "wiki"
REQUIRED = (
    "MOC.md", "AGENTS.md", "KNOWLEDGE.md", "wiki/index.md",
    "wiki/log.md", "wiki/overview.md", "wiki/models/registry.md",
    "wiki/compiled/briefing.md", "wiki/indices/runs.md",
    "wiki/indices/commits.md", "wiki/open-questions.md",
    "wiki/operations/handoff.md",
)
LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
META = ("id", "type", "status", "updated")


def frontmatter(text: str, source: Path) -> dict:
    if not text.startswith("---\n"):
        raise ValueError(f"{source}: missing frontmatter")
    parts = text.split("\n---\n", 1)
    if len(parts) != 2:
        raise ValueError(f"{source}: malformed frontmatter")
    meta = {}
    for line in parts[0].splitlines()[1:]:
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip()
    missing = [k for k in META if not meta.get(k)]
    if missing:
        raise ValueError(f"{source}: missing metadata {missing}")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", meta["updated"]):
        raise ValueError(f"{source}: invalid updated date")
    return meta


def md_without_fences(text: str) -> str:
    out, fenced = [], False
    for line in text.splitlines():
        if line.lstrip().startswith((chr(96) * 3, "~~~")):
            fenced = not fenced
            continue
        if not fenced:
            out.append(line)
    return "\n".join(out)


def check_local_links(path: Path, content: str) -> list[str]:
    errors = []
    for m in LINK.finditer(md_without_fences(content)):
        target = m.group(1).strip()
        if not target or target.startswith(("#", "mailto:", "data:")):
            continue
        if target.startswith("<") and target.endswith(">"):
            target = target[1:-1]
        if urlsplit(target).scheme or target.startswith("//"):
            continue
        target = unquote(target.split("#")[0].split("?")[0])
        if not target:
            continue
        dest = (path.parent / target).resolve()
        try:
            dest.relative_to(ROOT.resolve())
        except ValueError:
            errors.append(f"{path.relative_to(ROOT)} -> {target}: leaves repository")
            continue
        if not dest.exists():
            errors.append(f"{path.relative_to(ROOT)} -> {target}: missing")
    return errors


def lint() -> list[str]:
    problems = []
    for item in REQUIRED:
        if not (ROOT / item).is_file():
            problems.append(f"Required document missing: {item}")
    if not WIKI.exists():
        return problems + ["wiki/ is missing"]
    ids = {}
    docs = list(WIKI.rglob("*.md"))
    docs.extend(ROOT / item for item in ("MOC.md", "AGENTS.md", "KNOWLEDGE.md"))
    for path in docs:
        if not path.is_file():
            continue
        source = path.relative_to(ROOT)
        content = path.read_text(encoding="utf-8")
        if path.is_relative_to(WIKI):
            try:
                meta = frontmatter(content, source)
                existing = ids.get(meta["id"])
                if existing:
                    problems.append(f"duplicate wiki id {meta['id']}: {existing}, {source}")
                else:
                    ids[meta["id"]] = source
            except ValueError as exc:
                problems.append(str(exc))
        problems.extend(check_local_links(path, content))
    if (ROOT / "MOC.md").exists():
        moc = (ROOT / "MOC.md").read_text(encoding="utf-8")
        for link in ("AGENTS.md", "KNOWLEDGE.md", "wiki/index.md", "wiki/models/registry.md"):
            if link not in moc:
                problems.append(f"Root MOC lacks navigation to {link}")
    return problems


def main() -> int:
    problems = lint()
    if problems:
        print("WIKI_LINT_FAILED", len(problems))
        for msg in problems:
            print(" -", msg)
        return 1
    total = len(list(WIKI.rglob("*.md")))
    print(f"WIKI_LINT_OK pages={total} ids_unique=true all_internal_links_present=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
