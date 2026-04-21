# Agent Usage Contracts — Creative Market Research Tools

> **Purpose:** Define how a parent AI agent should call the creative market research primitives in `~/work/py-hbs-ads`.

## 1. Operating stance

The parent agent should treat these tools as:
- bounded
- reviewable
- composable
- explicit about artifacts and side effects

The parent should **not** treat the market research layer as one magical black box.

## 2. Parent contract rules

For any market research tool call, the parent should preserve:
- current `run_id` when one already exists
- exact workspace path
- exact artifact paths used as inputs
- whether the step is pure, IO-bound, or mutating
- whether human review is still required after the step

## 3. Tool-by-tool contracts

## Contract A — Brief validation

### Tool
- `validate_brief(...)`

### Parent should pass
- full brief object

### Parent should expect
- `[]` if valid
- list of structural errors if invalid

### Parent should do next
- stop and request clarification if invalid
- proceed to normalization/collection only if valid

### Safe default
- fail closed

---

## Contract B — Candidate normalization

### Tool
- `normalize_candidates(...)`

### Parent should pass
- stable `run_id`
- stable `query_id`
- raw manifest records

### Parent should expect
- canonical `AdCandidate` objects
- stable candidate ids
- dedupe keys

### Parent should do next
- optionally validate samples
- persist normalized artifact
- proceed to clustering

### Safe default
- preserve raw provenance, do not drop source fields prematurely

---

## Contract C — Clustering

### Tool
- `run_clustering(...)`

### Parent should pass
- normalized candidate records only

### Parent should expect
- assets
- candidate -> asset dedupe map
- variant clusters
- concept clusters

### Parent should do next
- inspect cluster confidence and heuristics
- select representative assets for analysis
- block or flag if concept grouping looks weak

### Safe default
- treat concept clusters as provisional unless confidence is clearly high

---

## Contract D — One-asset Gemini analysis

### Tool
- `GeminiMarketResearchAnalyzer.analyze_asset(...)`

### Parent should pass
- asset path
- run id
- asset id
- variant cluster id when available
- focused analysis dimensions when useful

### Parent should expect
- one `CreativeAnalysisResult`
- `analysis_status` of `ok`, `failed_validation`, or other explicit non-success state

### Parent should do next
- validate/inspect `quality`
- decide whether to include in synthesis
- stop or defer when validation failed or confidence is weak

### Safe default
- one asset at a time for debugging or bounded review

---

## Contract E — Analysis payload validation

### Tool
- `validate_analysis_payload(...)`
- `validate_analysis_schema.py`

### Parent should pass
- parsed analysis payload or JSON file path

### Parent should expect
- empty error list when valid
- explicit error list otherwise

### Parent should do next
- reject invalid payloads from synthesis
- request repair or human review when invalid

### Safe default
- never synthesize from invalid analysis output

---

## Contract F — Insight synthesis

### Tool
- `synthesize_insights(...)`

### Parent should pass
- validated analysis results only
- current research brief
- real `run_id`
- optional clusters

### Parent should expect
- draft `InsightCandidate` objects
- evidence refs attached to each usable insight

### Parent should do next
- validate candidate completeness
- choose review workflow
- persist only as draft until explicit approval policy says otherwise

### Safe default
- treat outputs as draft, not canon

---

## Contract G — Review transform

### Tool
- `apply_review(...)`
- `batch_approve(...)`

### Parent should pass
- explicit reviewer identity
- one of the allowed decisions
- rationale when meaningful

### Parent should expect
- updated insight status
- structured review record

### Parent should do next
- persist review decision
- decide whether reviewed output is ready for sync/export

### Safe default
- preserve review records even when rejecting

---

## Contract H — Repository persistence

### Tool
- `MarketResearchSQLiteDB.*`

### Parent should pass
- typed entities, not loose ad hoc dicts where possible
- explicit DB path under workspace `logs/market-research/research.db`

### Parent should expect
- durable local state
- simple readback helpers

### Parent should do next
- write sync report
- expose key counts/artifact paths in final handoff

### Safe default
- keep research persistence separate from existing `clips.db`

---

## Contract I — Service façade

### Tool
- `MarketResearchService`

### Parent should pass
- workspace path
- analyzer dependency when analysis is desired
- DB dependency when persistence is desired
- explicit brief/request inputs

### Parent should expect
- stage artifacts under `logs/market-research/`
- convenience orchestration, not hidden truth

### Parent should do next
- inspect artifacts and counts
- decide whether to stay stage-by-stage or use `run(...)` for smoke-test composition
- use readback helpers for bounded reuse instead of forcing full reruns
- use `debug_asset(...)` or `re_synthesize_from_saved_analyses(...)` when the task is one-asset debugging or brief-driven reuse

### Safe default
- call stage methods explicitly during debugging; use `run(...)` mainly for smoke tests and bounded local runs

---

## 4. Recommended parent output shape after each step

After using any of these tools, the parent should summarize with fields like:

- Stage
- Status
- Input Artifacts
- Output Artifacts
- Requires Human Review
- Blocking Issues
- Suggested Next Step
- Reason

## 5. Anti-drift rules

Parent agents should avoid these mistakes:

- treating draft insight synthesis as approved truth
- skipping brief validation because the request sounds obvious
- synthesizing from invalid or failed analysis payloads
- collapsing variant and concept clustering into one undifferentiated bucket
- writing research state into the existing operational clip DB during the pilot
- hiding artifact paths in the final handoff

## 6. Good default orchestration stance

For this workflow family:
- use **tool-first orchestration**
- preserve intermediate artifacts
- review high-risk interpretation explicitly
- keep the current pilot modular until the team decides to integrate it into the main app surface
