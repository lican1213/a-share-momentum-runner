"""Rebuild read-only LLM Wiki views from actual, immutable-by-filename evidence.

Usage: python scripts/wiki_sync.py
Source records are NEVER edited. Curated knowledge and chronological human
decision logs are NOT silently synthesized or overwritten by this script.
"""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
RECORDS = ROOT / "records"
WIKI = ROOT / "wiki"
BASE = "https://github.com/lican1213/a-share-momentum-runner"
TZ = ZoneInfo("Asia/Shanghai")


def page(page_id: str, page_type: str, heading: str, body: str, asof: str) -> str:
    return (f"---\nid: {page_id}\ntype: {page_type}\nstatus: maintained\n"
            f"updated: {asof}\n---\n# {heading}\n\n{body.rstrip()}\n")


def record_rows() -> list[tuple[Path, dict]]:
    found = []
    for path in sorted(RECORDS.glob("*/*/*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                continue
            if not all(k in data for k in ("github_run_id", "source_commit_sha", "audit")):
                continue
            found.append((path, data))
        except (OSError, ValueError):
            # Malformed source must be visible to CI lint, not silently marked green:
            raise RuntimeError(f"Cannot parse record: {path}")
    found.sort(key=lambda p: (p[1].get("collected_beijing_time", ""), p[1].get("github_run_id", "")), reverse=True)
    return found


def save_run_index(records: list[tuple[Path, dict]], now: str) -> None:
    head = ("Automatically regenerated from **actual recorded JSON files**, newest first. "
            "A recorded JSON is an execution observation and not an independently confirmed green Actions result.\n\n"
            "[返回MOC](../../MOC.md) · [原始记录目录](../../records/)\n\n"
            "| Recorded Beijing time | Phase | Run / attempt | Audit status | Validated symbols | Research signals | File |\n"
            "| --- | --- | --- | --- | ---: | ---: | --- |\n")
    rows = []
    for path, obj in records:
        audit = obj.get("audit") or {}
        sig = obj.get("signals") or {}
        n_signals = len(sig.get("signals") or [])
        try:
            rel = Path(os.path.relpath(path, WIKI / "indices")).as_posix()
        except ValueError:
            rel = str(path)
        attempt = obj.get("github_run_attempt", 1)
        cells = [obj.get("collected_beijing_time", "unknown"),
                 obj.get("phase", "unknown"),
                 f'{obj["github_run_id"]}-a{attempt}',
                 audit.get("status", "UNKNOWN"),
                 str(audit.get("verified_symbols", "—")), str(n_signals),
                 f"[source]({rel})"]
        rows.append("| " + " | ".join(str(x).replace("|", r"\|") for x in cells) + " |")
    if not rows:
        rows = ["No verified persistent records found in this checkout."]
    (WIKI / "indices" / "runs.md").write_text(
        page("GENERATED-RUNS", "log", "实际运行记录目录", head + "\n".join(rows), now),
        encoding="utf-8")


def save_git_index(now: str) -> None:
    doc = ("This file lists **every commit available in this checkout**, not merely curated upgrades. "
           "Each commit is a code/history event; it does not prove that the associated Actions passed.\n\n"
           "[返回MOC](../../MOC.md) · [模型语义版本](../models/registry.md)\n\n"
           "| Date | Commit | Author | Change |\n| --- | --- | --- | --- |\n")
    try:
        result = subprocess.run(
            ["git", "log", "--date=short", "--pretty=format:%H%x1f%ad%x1f%an%x1f%s",
             "--all", "--no-decorate"],
            cwd=ROOT, capture_output=True, check=True, text=True, timeout=15)
        lines = result.stdout.splitlines()
    except (OSError, subprocess.SubprocessError):
        lines = []
    hist = []
    seen = set()
    for line in lines:
        parts = line.split("\x1f", 3)
        if len(parts) != 4:
            continue
        sha, day, author, subject = parts
        if sha in seen:
            continue
        seen.add(sha)
        safe = [v.replace("|", r"\|").replace("\n", " ") for v in (day, author, subject)]
        hist.append(f"| {safe[0]} | [{sha[:10]}]({BASE}/commit/{sha}) | {safe[1]} | {safe[2]} |")
    if not hist:
        hist = ["History not available locally; run on a full GitHub Actions checkout."]
    (WIKI / "indices" / "commits.md").write_text(
        page("GENERATED-COMMITS", "log", "全部Git提交历史（自动索引）",
             doc + "\n".join(hist), now), encoding="utf-8")


def save_briefing(records: list[tuple[Path, dict]], now: str) -> None:
    intro = ("[返回根MOC](../../MOC.md) · [全量运行记录](../indices/runs.md) · "
             "[模型台账](../models/registry.md) · [开放问题](../open-questions.md)\n\n"
             "**硬性交易授权：未通过；任何研究观察不构成买入指令。**\n\n"
             "本页由实际run JSON生成，**不包含未曾执行的回测，也不承诺GitHub任务此刻在线**。\n\n")
    if not records:
        body = intro + "没有找到有效的持久化run JSON；不能提供收益/行情结论。"
    else:
        path, obj = records[0]
        audit = obj.get("audit") or {}
        sig = obj.get("signals") or {}
        model = audit.get("model_validation") or {}
        hist = audit.get("exploratory_history") or {}
        context = audit.get("market_context") or {}
        rel = Path(os.path.relpath(path, WIKI / "compiled")).as_posix()
        body = intro + "\n".join([
            f"- 最新持久化run：[{obj.get('github_run_id')}]({rel})；时段 {obj.get('phase')}；记录时间 {obj.get('collected_beijing_time')}.",
            f"- 输入代码SHA：[{str(obj.get('source_commit_sha'))[:12]}]({BASE}/commit/{obj.get('source_commit_sha')})；不保证等于当前HEAD.",
            f"- 审计执行状态：`{audit.get('status', 'UNKNOWN')}`；截止行情：{audit.get('required_history_date', 'not checked')}.",
            f"- 有效个股数：{audit.get('verified_symbols', 'unknown')}；研究回放完成交易：{hist.get('closed', 'unknown')}；执行截断：{hist.get('censored','unknown')}.",
            f"- 历史代理交易平均净收益：{hist.get('mean_net_return', 'unavailable')}；历史胜率：{hist.get('win_rate', 'unavailable')}（为比例值，非百分数）.",
            f"- 大盘数据门槛：{context.get('passes_market_data_gate', 'unverified')}；历史股票池偏差解决：{model.get('survivorship_bias_addressed', False)}；独立OOS验证通过：{model.get('out_of_sample_passed', False)}.",
            f"- 正式交易信号：{len(sig.get('signals') or [])}；信号状态：`{sig.get('status', 'UNAVAILABLE')}`.",
            "- 研究结论：基于当前固定存续股票池的历史日K代理，非真实成交，且不可推断未来盈利。要评估改动，读EXP/ADR/INC与对应run JSON。",
        ])
        if audit.get("status") not in ("COMPUTED_RESEARCH_ONLY", "COMPUTED_WITH_LIMITATIONS"):
            body += "\n\n**最近一次记录不是完整正常回放；不得把先前的报告冒充当期结果。**"
    (WIKI / "compiled" / "briefing.md").write_text(
        page("COMPILED-BRIEFING", "overview", "Agent自动简报（最新实际留档）", body, now),
        encoding="utf-8")


def main() -> None:
    for name in ("indices", "compiled"):
        (WIKI / name).mkdir(parents=True, exist_ok=True)
    today = datetime.now(TZ).date().isoformat()
    entries = record_rows()
    save_run_index(entries, today)
    save_git_index(today)
    save_briefing(entries, today)
    print(f"WIKI_SYNC_OK records={len(entries)} views=3 date={today}")


if __name__ == "__main__":
    main()
