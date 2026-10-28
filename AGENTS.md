# Agent entrypoint — A-share momentum research

**Read before any modification:** [MOC.md](MOC.md) → [KNOWLEDGE.md](KNOWLEDGE.md) → [wiki/compiled/briefing.md](wiki/compiled/briefing.md) → [wiki/index.md](wiki/index.md).

**Mandatory original-factor continuity:** read [original 2026-10-27 fixed four-ETF factor contract](wiki/data/original-four-etf-indicator.md) BEFORE changing any national-team monitoring code. Never quietly replace the four CSI300 ETF factor series with an expanded nine-index basket; preserve separate AUM/ordinary-float/free-float ratios and distinguish daily NAV-weighted sums from endpoint NAV. Fund-wide subscriptions do not identify a particular investor. Synthetic arithmetic tests do not prove live ETF data collection.

**Project P0 was changed on 2026-10-28 to evidence-based national-team ownership and ETF subscription/redemption tracking**, per [ADR-0003](wiki/decisions/ADR-0003-national-team-pivot.md) and [Issue #3](https://github.com/lican1213/a-share-momentum-runner/issues/3). The original 3-session momentum prototype is a historical side experiment. **No validated tradable strategy and no broker execution.** Never attribute whole-ETF net creations/redemptions to Central Huijin without holder-level disclosure. Do not turn research candidates into recommendations.

## Source hierarchy
1. Authoritative evidence: per-run [records/](records/) JSON, code at its `source_commit_sha`, GitHub Actions job logs, tests, issues. Each record is a snapshot, not an actual fill.
2. Maintained synthesis: [wiki/](wiki/), version registry, experiments, ADRs, incidents, MOC.
3. Derived/navigation: [wiki/indices/](wiki/indices/), [wiki/compiled/](wiki/compiled/). Regenerable and **not** evidence replacing (1).

When statements conflict, prefer source snapshots and distinguish *known*, *inferred*, *hypothesis*, *not yet verified*. Always cite full repository paths / run IDs. A green CI run is not proof of alpha.

## Mandatory change protocol
1. **Discover:** read MOC and the relevant ADR, model registry and recorded baseline; inspect actual source and current GitHub run.
2. **Plan:** give each proposed model change a distinct experiment ID, frozen hypothesis, baseline version SHA, data period, evaluation metric and failure gate.
3. **Execute:** modify code, add tests, run CI; preserve prior rules and evidence; never modify old `records/` files or historical observations.
4. **Verify:** inspect completed Actions and exact SHA, archived run JSON, data timestamps, signal authorization and failure reasons. A queued or cancelled job is not success.
5. **File back:** update [wiki/log.md](wiki/log.md), [wiki/models/registry.md](wiki/models/registry.md) when code/logic changes, the matching `wiki/experiments/` or `wiki/incidents/` page, [wiki/index.md](wiki/index.md) and [wiki/open-questions.md](wiki/open-questions.md) if needed. When decisions change, add an ADR; never silently alter previous decisions.
6. **Check:** `python scripts/wiki_lint.py`; `python -m pytest -q`; inspect new successful CI run and [wiki/indices/runs.md](wiki/indices/runs.md).

For significant source changes, **documentation and evidence updates are part of completion, not optional**. If CI, data retrieval, or a link fails, log the failure and leave status unverified.

## Non-negotiable gates
- Distinguish ACTUAL_CODE_EXECUTION from ACTUAL_TRADES; exploratory daily-OHLC fills are hypothetical transactions, not live broker fills.
- Historical holdout from today's 12-name survivor basket is **not untouched out-of-sample evidence**.
- A-share T+1, board-specific limit rules, jump gaps, unfilled exits, tax/commissions, timestamp quality and point-in-time universe must be validated before deployment.
- `RESEARCH_ONLY_NOT_TRADE_AUTHORIZED`: zero executable trade signals.
- Do not sweep parameters across the inspected 45-trade sample and claim future performance.

Agent handoff details: [wiki/operations/handoff.md](wiki/operations/handoff.md). Other agent loaders: [CLAUDE.md](CLAUDE.md), [GEMINI.md](GEMINI.md), [Copilot instructions](.github/copilot-instructions.md); this file remains canonical. 
