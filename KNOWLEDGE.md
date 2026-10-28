---
id: KB-RULEBOOK
type: rulebook
status: active
updated: 2026-10-28
---
# LLM Wiki operating rulebook

Pattern adapted to an executable quantitative research repository from [Better Second Brain](https://github.com/maystudios/better-second-brain) and [Agent Knowledge LLM Wiki pattern](https://github.com/limecloud/agentknowledge/blob/main/docs/en/reference/llm-wiki-pattern.md). The template is conceptual; it is **not** an installed application or an auto-running LLM service.

## Three layers

| Layer | Local form | Writer / rule |
| --- | --- | --- |
| Immutable / append-by-ID evidence | `records/YYYY-MM-DD/phase/RUN-aATTEMPT.json`, Git history, GitHub Actions, `tests/` | Actions creates new evidence; agents **never rewrite** historical records |
| Agent-maintained linked knowledge | `wiki/` — MOC, synthesis, models, decisions, experiments, incidents, sources, questions | Agents update with source pointers and supersession history |
| Steering and validation | `AGENTS.md`, `KNOWLEDGE.md`, `scripts/wiki_lint.py`, templates | Maintained conservatively; syntax and links checked by CI |

`wiki/indices/` and `wiki/compiled/` are materialized views; rebuilt from sources, not authoritative results.

## Operations
- **Ingest:** fetch new GitHub record / commit / upstream source, verify identity, grain and timestamp, link the source, update relevant topic pages. Don't copy a raw log into an unfiltered essay.
- **Query:** begin at [MOC.md](MOC.md), then wiki; follow evidence references to records and code. Answer with run ID, code SHA and limitations.
- **Lint:** verify all internal Markdown links, required MOC paths, page IDs/frontmatter, generated run index and source existence; gate CI on failure.
- **Review:** when a new run contradicts a prior conclusion, log a contradiction and update **current** interpretation, retaining old evidence and original page history.
- **File back:** every meaningful agent investigation becomes a dated change in [wiki/log.md](wiki/log.md), with a matching page or an explicit reason no page changed.
- **Rotate/archive:** never delete historical decisions; older run details remain in `records/` and generated indices, while summary pages stay short.

## Page metadata
Every maintained `wiki/**/*.md` page except auto-generated views begins with:
```yaml
---
id: EXP-0001
type: experiment
status: observed
updated: 2026-10-28
---
```
Allowed types: moc, overview, log, model-registry, decision, experiment, incident, data-contract, sources, open-questions, operations, template. Status values: active, observed, rejected, superseded, unverified, maintained. When updating, retain historical claims with dates and reason for supersession.

## Evidence and upgrade rule
Each model claim requires: **model/run version**, data provider, data cutoff, sample/grain, exact metric, what was executed, accepted limitations and links to the relevant `records/` JSON or Actions run. Experiment pages are observations; **not** release approval. Negative results must be preserved.

For new model logic: stable EXP-ID → hypothesis, parameter delta, baseline SHA, frozen validation boundary, predeclared metrics → actual results → conclusion or explicit unverified status → back-reference from MOC and log. Registry entry must list status and a code SHA; no free-floating `v2` claims without a Git commit.

Knowledge contradictions must be **resolved with evidence or left OPEN**, not rhetorically smoothed over. See [wiki/open-questions.md](wiki/open-questions.md).

## Automation versus memory
GitHub Actions can auto-write source-backed run indices, not reinterpret evidence intelligently or guarantee external personal memory. Agent memory here is the versioned Markdown files; any other AI Agent reading this repository can reconstruct the work without private ChatGPT memory.
