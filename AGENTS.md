# Agent entrypoint — national-team ETF funding and stock selection

**NEW controlling round-two audit (2026-10-30):** [AUD-R2](wiki/audits/AUD-2026-10-30-round2-independent-redteam.md) and [single status](wiki/current-status.md). Five independent red cases overturned the prior claim of full execution acceptance: undecided entry misallocated later capital, repeat partial funding event, duplicate recovered S1/S2, 14:50 interval timestamp order, V2 missing stock becoming profitable cash. Do not tune picks. Only trust new matched-SHA full pytest plus actual immutable G1, and distinguish future G2/G3/G4.

**CURRENT CANONICAL STATUS (2026-10-30):** [wiki/current-status.md](wiki/current-status.md). Read the root MOC then that status page before any edits. Four immediate P0 execution defects (unknown-data freeze, exact minute completeness, T+1/T+2 late-session exits, cross-event account ledger) are tracked there. A2/B G1 actual Oct30 freeze exists; G2/G3/G4 are not proof of trades or profits. 2026-10-28 audits below are historical, not controlling the 2026-10-30 short execution gate. No trading authorization. 

**Read before any modification:** [MOC.md](MOC.md) → [KNOWLEDGE.md](KNOWLEDGE.md) → [wiki/compiled/briefing.md](wiki/compiled/briefing.md) → [wiki/index.md](wiki/index.md).

**Historical baseline (superseded for short execution by [2026-10-30 current status](wiki/current-status.md)): [AUD-2026-10-28-E2E](wiki/audits/AUD-2026-10-28-e2e-release-gate.md)**. B11: full four-ETF dated shares/NAV recovered and verified [2026-10-28 source run 40702172792](records/national_team_etf/2026-10-28/40702172792-a1.json); independent multi-source merge [40702572594](records/national_team_merged/2026-10-28/40702572594-a1.json). Real CSI300 300-component weight and 30-stock historical ADV20 run completed. New 150-stock build + direct SSE HTTP + frozen paper events + `audit_gate` requires matching production Actions verification; do not use earlier successful runs as proof of latest code. Actual PCF and Central Huijin holdings identification remain UNVERIFIED; the 5/10/20d edge is not demonstrated. Use `national_team/index_proxy.py` as a LABELLED index-weight proxy only. NEVER trade based on the backfilled Oct27 price.

**B13 never lose paid-for research data:** The live GitHub Actions job must push immutable `records/national_team_*/` evidence **without staging `wiki/compiled/` or `wiki/indices/`**. A separate [derived Wiki sync workflow](.github/workflows/national-team-wiki-sync.yml) rebuilds and commits MOC summaries from latest main, with retries and resets; do not undo this architectural separation. Use [holder_evidence.py](national_team/holder_evidence.py) and [2024/2025 report evidence](data/national_team_holders/159919-2024H1-2025H1.json) when making real legal holder claims, distinct from [daily_report.py](national_team/daily_report.py) which reports ETF-wide flow and index-proxy stock observations. Never assign 2025 fund holder shares to 2026 account activity.

**Mandatory read after red-team 2026-10-28:** [AUD-2026-10-28](wiki/audits/AUD-2026-10-28-red-team.md) lists P0/P1 flaws, exact actual source recordings and remaining cash-flow / PCF / stock-return gaps. Current actual ETF facts are in [records/national_team_etf](records/national_team_etf), which is a DIFFERENT grain than the legacy momentum records. Never equate successful source collector job with four-ETF factor completeness. The official SSE display is in 10,000 shares but AKShare's SSE share adapter ALREADY multiplies by 10000. SZSE dated shares may fail; undated latest quotes cannot be backdated. Preserve signed negative stock exposure and independent flow-confirmed strength rankings. Evaluate next eligible open using Shanghai local time, not UTC calendar date.

**Opportunity-first operating style:** Do not let missing one stock or one ETF's PCF wipe out all research rankings. Prioritize [opportunity_scan.py](national_team/opportunity_scan.py) for best-available-time-stamped partial observations and expose numerator/fund/weight coverage, missingness and signed outflow rankings; use historical [stock_selection.py](national_team/stock_selection.py) only for full-completeness audit. Hardcoded arbitrary ADV/listing-age/relative-return gates must be risk tags, not invisible vetoes. Keep actual disclosure time and investor identity correct; do not generate made-up data. **Research/ranking is not the same as automatically submitting brokerage orders.** Report ranked observations confidently and specifically when real inputs exist.

**Primary strategy target:** [ADR-0004](wiki/decisions/ADR-0004-stock-selection-after-flow.md) and [EXP-0003](wiki/experiments/EXP-0003-etf-to-stock.md). The four-ETF funding factor is an EVENT TRIGGER only; the real question is whether PIT constituent stock selection (S1/S2) beats an equally-timed low-cost CSI300 ETF (S0) after costs over 5/10/20 sessions. Keep all candidates RESEARCH_ONLY, no specific buy instruction until real ETF/PCF/stock data and true independent forward research exist. An increase in ETF shares is not proof the named national-team entity purchased constituent shares.

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
