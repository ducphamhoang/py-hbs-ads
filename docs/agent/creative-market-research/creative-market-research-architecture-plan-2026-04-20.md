# Architecture Plan — Creative Market Research Workflow

> **Goal:** Define a practical architecture for adding a creative market research workflow to `py-hbs-ads` without confusing current canonical code boundaries.

## 1. Design stance

This should be built as a **layered extension** on top of the current rewrite architecture, not as an entirely separate system.

Grounding from the current repo:

- `docs/architecture.md` already defines the main code boundaries: `cli -> app -> features -> core/infra`
- `docs/agent/README.md` already defines the parent orchestrator plus bounded-worker model
- current implementation already has useful anchors:
  - `PipelineService`
  - `TaggingService`
  - `GeminiClipAnalyzer`
  - `CompetitorService`
  - workspace + SQLite state

The new workflow should reuse those ideas, but the current implementations are still too narrow for market research.

## 2. Current-state assessment

### What already exists and is reusable
- a stable composition root and feature-first structure
- workspace management and SQLite operational state
- JSON-friendly command outputs
- Gemini integration through `ClipAnalyzer`
- a parent/worker orchestration model in docs

### What is missing
- a research-brief abstraction
- candidate ingestion from authenticated market tools
- durable source/query provenance for market collection
- dedupe and cluster layers beyond current clip records
- evidence-backed insight synthesis
- a distinct research storage contract for evidence vs synthesis

### Important limitation in current code
Current `TaggingService` + `GeminiClipAnalyzer` are optimized for narrow clip tagging, especially CTA-oriented analysis. That is not enough for market research because we need:
- richer taxonomies
- evidence references
- interpretation vs observation separation
- reviewable synthesis outputs

## 3. Architectural principle

Use **three layers of responsibility**:

1. **Operator/browser collection layer**
   - authenticated market-tool interaction
   - source export capture
   - run-level provenance

2. **Research workflow layer**
   - normalization
   - dedupe/clustering
   - representative analysis
   - enrichment
   - synthesis
   - review gates

3. **Durable storage layer**
   - evidence records
   - synthesis records
   - review history
   - queryable research artifacts

## 4. Proposed system components

## 4.1 Parent orchestrator
Owns:
- brief resolution
- run lifecycle
- stage ordering
- artifact paths
- review-gate preservation
- final sync

Should not:
- manually perform open-ended pattern reasoning inline
- bypass review gates
- let workers self-chain

## 4.2 Worker roles

### Market Collector worker
Responsibilities:
- interact with authenticated browser tools
- collect raw ad candidate metadata
- download or reference assets
- emit normalized intake artifacts

### Normalization/Dedupe worker
Responsibilities:
- convert heterogeneous source records into a common schema
- assign dedupe keys
- build asset/variant/concept cluster candidates
- nominate representative assets

### Creative Analysis worker
Responsibilities:
- call Gemini with strict schema instructions
- validate and repair JSON responses
- attach evidence ranges and quality flags

### Enrichment worker
Responsibilities:
- connect candidates and clusters to app/store/competitor context
- compute useful distributions and recurrence summaries

### Insight Synthesis worker
Responsibilities:
- aggregate evidence
- draft insight candidates
- state scope, support, and confidence

### Research Sync worker
Responsibilities:
- write evidence artifacts
- write synthesis artifacts
- preserve backlinks and provenance

## 5. Proposed code-layer fit

The cleanest long-term fit is a new feature family rather than overloading existing `competitor` or `tagging` modules.

Recommended future package shape:

```text
src/hbs_ads/features/market_research/
├── service.py
├── models.py
├── normalization.py
├── clustering.py
├── enrichment.py
├── synthesis.py
├── validators.py
├── repository.py
└── prompts/
```

Supporting infra additions likely needed:

```text
src/hbs_ads/infra/
├── ai/
│   └── gemini_market_research.py
├── browser/
│   └── market_capture.py        # if browser-capture logic becomes internalized later
└── db/
    └── research_repository.py
```

### Why not just extend `TaggingService`?
Because market research is not just tagging clips. It adds:
- market-run provenance
- source normalization
- multi-level clustering
- synthesis and review lifecycle
- durable insight entities

That is a distinct workflow capability.

## 6. Runtime architecture

## 6.1 Parent-controlled state machine
Recommended stage order:

1. `brief`
2. `collect`
3. `normalize`
4. `cluster`
5. `analyze`
6. `enrich`
7. `synthesize`
8. `review`
9. `sync`

The parent should persist stage results in a run state artifact such as:

```text
<workspace>/logs/market-research/run-state.json
```

Each stage should write its own artifact directory.

Example:

```text
<workspace>/logs/market-research/
  brief.json
  collect/candidates.raw.json
  normalize/candidates.normalized.json
  cluster/variant-clusters.json
  cluster/concept-clusters.json
  analyze/creative-analysis.jsonl
  enrich/context.json
  synthesize/insight-candidates.json
  review/review-decisions.json
  sync/sync-report.json
```

## 6.2 Evidence vs synthesis storage
Do not merge these concerns.

### Evidence layer
Stores:
- research briefs
- source queries
- ad candidates
- assets
- clusters
- analysis results
- enrichment facts

### Synthesis layer
Stores:
- insight candidates
- reviewed insights
- competitor snapshots
- trend snapshots
- experiment recommendations

## 6.3 Review-aware progression
Recommended rules:
- `collect` may proceed automatically once the brief is valid
- `cluster` may require review when concept-grouping confidence is weak
- `synthesize` must not auto-canonize high-scope claims
- `sync` of reviewed synthesis should occur only after review decisions are explicit

## 7. Storage strategy

## 7.1 Workspace layer
Use workspace for run-scoped state and generated artifacts.

Recommended example path:

```text
<workspace>/logs/market-research/
```

## 7.2 Shared research store
Use a durable store for cross-run retrieval.

This can start as:
- SQLite tables in the existing local operational DB, or
- hybrid JSON/SQLite if iteration speed matters in V1

But the model should be treated as durable from day one.

## 8. Contracts between layers

### Parent -> worker envelope
Each worker should receive:
- role
- workspace path
- stage
- research brief summary
- authoritative input artifact paths
- exact question
- success condition
- stop conditions

### Worker -> parent handoff
Each worker should return:
- Stage
- Status
- Authoritative Artifacts
- Requires Human Review
- Review Gate
- Allowed Next Stages
- Blocking Issues
- Summary
- Suggested Next Role
- Suggested Next Action
- Reason
- Context For Parent

## 9. Validation and guardrails

### Guardrail A — Provenance first
No candidate, analysis result, or insight should exist without a parent run id and source lineage.

### Guardrail B — Taxonomy control
Prompted analysis must map major fields to controlled vocabularies.

### Guardrail C — Review separation
Observable evidence and interpretation should be stored separately so review can dispute conclusions without losing raw extraction.

### Guardrail D — Sync discipline
A reviewed insight should link back to the exact evidence records that supported it at the time of approval.

## 10. Phased implementation plan

### Phase 0 — Docs and schemas
Deliver:
- PRD
- architecture plan
- workflow spec
- data model
- Gemini prompt/schema contract

### Phase 1 — Artifact-first pilot
Implement:
- research brief artifact
- candidate collection artifact schema
- normalized candidate schema
- Gemini analysis schema + validator
- insight candidate artifact

No need to build final polished CLI surface yet.

### Phase 2 — Durable repository layer
Implement:
- research evidence tables/repository
- reviewed insight tables/repository
- sync/reporting contract

### Phase 3 — First-class feature integration
Implement:
- `market_research` feature package
- CLI entrypoints or orchestrator-compatible commands
- richer review/report commands

## 11. Recommended default

Default recommendation:

- keep the orchestration parent/worker split from existing docs
- add a new `market_research` feature family over time
- start V1 as an artifact-first, review-heavy workflow
- optimize first for traceability and operator trust, not total automation
