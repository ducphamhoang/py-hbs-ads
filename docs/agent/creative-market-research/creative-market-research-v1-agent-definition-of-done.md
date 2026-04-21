# Creative Market Research — V1 Agent Definition of Done

> **Purpose:** Restate V1 in the practical terms that matter for the current pilot: can a parent agent use the market research layer as a bounded, reviewable set of primitives?

## 1. Product stance

V1 is **not** "complete market research automation."

V1 **is**:
- a tool-first, agent-usable pilot
- artifact-first rather than UI-first
- workspace-scoped rather than globally integrated
- strong enough for parent-agent orchestration and iterative review

This means V1 should be judged by whether an agent can reliably perform useful market research work from a brief + bounded candidate set, not by whether every later collector/review/storage surface is already production-complete.

## 2. Current status snapshot (2026-04-21)

## Implemented enough for V1
- research brief model + validation
- manifest/handoff-based candidate ingest
- normalization
- asset/variant/concept clustering
- representative asset selection
- strict-schema Gemini market-research analysis
- evidence-backed synthesis
- workspace artifacts under `logs/market-research/`
- pilot-local SQLite persistence in `research.db`
- examples and passing pilot tests

## Present but still thin
- review transform primitives (`apply_review`, `batch_approve`)
- enrichment stage
- runner/orchestrator convenience script

## Intentionally deferred for post-V1
- fully integrated authenticated browser collector inside the package
- rich manual review workflow and full reviewed-output lifecycle
- canonical long-term research repository/query product surface
- polished first-class CLI/bootstrap integration into the main app

## 3. V1 done criteria

V1 is done when **all** of the following are true.

### D1. Brief-first execution works
A parent agent can start from a structured brief and fail closed when the brief is invalid.

### D2. Bounded candidate ingest works
A parent agent can ingest a bounded export/handoff manifest and preserve enough provenance for later inspection.

Minimum acceptable provenance for V1:
- source
- source/native id when available
- retrieved/seen timestamps when available
- query or handoff context
- asset path or asset URL

### D3. Mid-pipeline artifacts are durable and inspectable
The workflow writes stage artifacts that let a parent agent inspect, retry, or resume work without recomputing everything mentally.

Minimum expected artifacts:
- `brief.json`
- `run-state.json`
- `collect/candidates.raw.json`
- `normalize/candidates.normalized.json`
- `cluster/asset-dedupe.json`
- `cluster/variant-clusters.json`
- `cluster/concept-clusters.json`
- `cluster/representative-selection.json`
- `analyze/creative-analysis.jsonl`
- `analyze/failures.json`
- `synthesize/insight-candidates.json`
- `sync/sync-report.json`
- `research.db`

### D4. Representative analysis is usable by agents
The system can analyze representative assets with the market-research Gemini schema and record explicit success/failure state.

Minimum acceptable behavior:
- validate/parse model output
- write failures explicitly
- keep invalid outputs out of synthesis by policy

### D5. Synthesis stays evidence-backed
The system can generate draft insights that remain traceable to analyses/clusters/candidates.

Minimum acceptable behavior:
- each usable insight has explicit evidence refs
- scope is declared when making pattern claims
- outputs are draft unless explicitly reviewed/approved by policy

### D6. Parent-agent usage patterns are supported
At least these patterns are practically supported:
1. analyze a fresh export
2. re-synthesize from prior analyses/artifacts
3. debug one asset or one failed analysis

### D7. Persistence is good enough for pilot reuse
The pilot DB does not need the full long-term product schema yet, but it must preserve enough state to support readback, counts, and reruns inside the same workspace.

### D8. Verification exists
There is at least one artifact-first integration path and focused unit coverage for the core primitives.

## 4. What is *not* required to call V1 done

These are valuable, but not blockers for agent-first V1:
- built-in browser automation that directly collects from authenticated sources
- full approve/edit/reject/defer human workflow in the service façade
- canonical approved-insight product model
- competitor snapshot and trend snapshot completeness
- robust cross-run research retrieval/query UX
- perfect clustering quality
- main-app bootstrap/CLI wiring

## 5. Remaining gaps before we should call it done

As of this review, the main gaps are:

1. **State/readback still needs tightening**
   - make sure parent agents can reliably reload prior analyses/artifacts/DB rows instead of only writing them

2. **Review boundary needs to be stated cleanly**
   - V1 currently has review primitives, not a full review workflow
   - docs and handoff language should keep calling insights `draft` unless explicitly approved

3. **Verification should stay centered on agent use cases**
   - tests should emphasize fresh-export, re-synthesis, and one-asset debug flows

## 6. Recommended review question for the team

When reviewing V1, ask:

> Can a parent agent take a brief plus a bounded export, run the useful middle of the market research pipeline, inspect artifacts, and hand back evidence-backed draft insights without pretending the later product layers already exist?

If the answer is yes, V1 is on target.
If the answer is no, fix that before expanding scope.
