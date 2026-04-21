# Creative Market Research Tool Catalog

> **Purpose:** Define the first useful cut of creative market research in `~/work/py-hbs-ads` as a set of **agent-usable primitives**, not a single full pipeline.

## 1. Framing

For this workflow family, the first implementation target is:

- **tool-first**
- **agent-usable**
- **composable**
- **reviewable stage by stage**

It is **not**:

- one giant end-to-end command
- one opaque pipeline state machine
- one service call that hides every intermediate artifact

The practical question for V1 is:

> Can a parent AI agent call a small set of reliable primitives to do market research work in bounded steps?

## 2. Tool layers

## Layer A — Pure or mostly-pure reasoning/data tools
These should be easy to test and safe for repeated use.

- brief validation
- candidate normalization
- candidate clustering
- insight synthesis
- review-state transforms

## Layer B — IO / infrastructure tools
These perform external or persistence work.

- asset-file intake / staged upload handoff
- Gemini market research analyzer
- SQLite research repository
- artifact read/write helpers

## Layer C — Orchestration helpers
These compose the tools but should not be mistaken for the canonical unit of value.

- standalone runner script
- future CLI wrapper
- future parent orchestration recipes

## 3. Tool catalog

## Tool 1 — Brief validator

### Canonical implementation path
- `~/work/py-hbs-ads/src/hbs_ads/features/market_research/validators.py`

### Primary callable surface
- `validate_brief(brief: ResearchBrief) -> list[str]`

### Purpose
Check whether a research brief is complete enough to act on.

### Inputs
- `ResearchBrief`

### Outputs
- list of validation errors
- empty list means structurally acceptable

### Side effects
- none

### Agent use cases
- validate a user-supplied brief before collection
- reject underspecified research runs
- enforce minimum scope before downstream work

### Review risk
- low

### Notes
This is a gatekeeper tool. Parent agents should call this early.

---

## Tool 2 — Candidate normalizer

### Canonical implementation path
- `~/work/py-hbs-ads/src/hbs_ads/features/market_research/normalization.py`

### Primary callable surfaces
- `normalize_platform(raw: str) -> str`
- `normalize_date(raw: str) -> str`
- `build_dedupe_key(candidate: AdCandidate) -> str`
- `normalize_raw_record(run_id, query_id, raw, index) -> AdCandidate`
- `normalize_candidates(run_id, query_id, raw_records) -> list[AdCandidate]`

### Purpose
Convert raw collection payloads into canonical candidate records while preserving provenance.

### Inputs
- run id
- query id
- raw manifest records from browser-collected or exported source data

### Outputs
- normalized `AdCandidate` records

### Side effects
- none

### Agent use cases
- normalize one new market export
- rerun normalization after source mapping changes
- prepare inputs for clustering and persistence

### Review risk
- low to medium

### Notes
This is one of the most important tool surfaces because every downstream stage assumes the candidate contract is stable.

---

## Tool 3 — Candidate validator

### Canonical implementation path
- `~/work/py-hbs-ads/src/hbs_ads/features/market_research/validators.py`

### Primary callable surface
- `validate_candidate(candidate: AdCandidate) -> list[str]`

### Purpose
Catch structurally invalid candidate records before persistence or clustering.

### Inputs
- `AdCandidate`

### Outputs
- list of errors

### Side effects
- none

### Agent use cases
- QA a normalized manifest
- reject malformed records before write

### Review risk
- low

---

## Tool 4 — Asset/variant/concept clustering toolset

### Canonical implementation path
- `~/work/py-hbs-ads/src/hbs_ads/features/market_research/clustering.py`

### Primary callable surfaces
- `build_asset_from_candidate(candidate) -> CreativeAsset`
- `dedupe_assets(candidates) -> tuple[list[CreativeAsset], dict[str, str]]`
- `build_variant_clusters(assets, candidates, dedupe_map) -> list[VariantCluster]`
- `build_concept_clusters(variant_clusters, candidates, dedupe_map) -> list[ConceptCluster]`
- `run_clustering(candidates) -> dict[str, Any]`

### Purpose
Reduce duplicate noise and produce reusable groupings for downstream reasoning.

### Inputs
- normalized `AdCandidate` records

### Outputs
- unique assets
- candidate -> asset dedupe map
- variant clusters
- concept clusters

### Side effects
- none

### Agent use cases
- cluster one manifest before analysis
- re-cluster with updated heuristics
- select representative assets for model analysis

### Review risk
- medium

### Notes
This is not “truth.” It is heuristic grouping. Parent agents should preserve confidence and allow review for weak concept grouping.

---

## Tool 5 — Enrichment toolset

### Canonical implementation path
- `~/work/py-hbs-ads/src/hbs_ads/features/market_research/enrichment.py`

### Primary callable surfaces
- `compute_source_distribution(...)`
- `compute_platform_distribution(...)`
- `compute_geo_distribution(...)`
- `compute_publisher_distribution(...)`
- `compute_app_distribution(...)`
- `compute_cluster_metrics(...)`
- `enrich_run(...) -> dict[str, Any]`

### Purpose
Add lightweight context summaries around the sample and cluster set.

### Inputs
- normalized candidates
- variant clusters
- concept clusters

### Outputs
- distributions and cluster metrics

### Side effects
- none

### Agent use cases
- summarize what the sample actually contains
- detect narrow or biased sampling
- support synthesis and reviewer context

### Review risk
- low to medium

---

## Tool 6 — Asset-file intake adapter

### Canonical implementation path
- `~/work/py-hbs-ads/src/hbs_ads/features/market_research/intake.py`
- `~/work/py-hbs-ads/src/hbs_ads/features/market_research/service.py`
- `~/work/py-hbs-ads/scripts/market_research/run_market_research.py`

### Primary callable surfaces
- `intake_asset_files(...) -> dict[str, Any]`
- `MarketResearchService.intake_asset_files(...)`
- `MarketResearchService.run_from_asset_files(...)`
- runner stages: `intake-files`, `intake-run`

### Purpose
Turn one or more uploaded/local video files into a staged handoff manifest that the market research core can consume.

### Inputs
- workspace path
- run id or generated run id
- one or more local asset paths
- intake metadata such as source / collector / platform / geo / app_name

### Outputs
- staged asset copies under workspace collect assets
- `intake-manifest.json`
- `assets-manifest.json`
- `collection-report.json`
- optional full market-research run result when using `run_from_asset_files(...)`

### Side effects
- copies files into the workspace
- copies supported sidecar analysis fixtures when present
- writes collect-stage artifacts

### Agent use cases
- take one or more videos uploaded through chat and analyze them with the market research stack
- perform local asset intake without building browser collection first
- create a clean handoff boundary between intake sources and research core

### Review risk
- medium

### Notes
This is the first non-browser intake adapter. Browser collection should target the same handoff contract instead of bypassing the intake boundary.

---

## Tool 7 — Gemini market research analyzer

### Canonical implementation path
- `~/work/py-hbs-ads/src/hbs_ads/infra/ai/gemini_market_research.py`

### Primary callable surfaces
- `GeminiMarketResearchAnalyzer.analyze_asset(...) -> CreativeAnalysisResult`

### Purpose
Analyze one representative creative asset using the market-research-specific JSON contract.

### Inputs
- asset path
- run id
- asset id
- optional variant cluster id
- optional analysis focus

### Outputs
- `CreativeAnalysisResult`

### Side effects
- may call external Gemini API
- may upload temporary file to Gemini
- may read fixture sidecar files

### Agent use cases
- analyze one representative creative
- re-analyze after taxonomy or prompt changes
- validate whether one asset is informative enough for insight work

### Review risk
- medium to high

### Notes
This is a key bounded worker tool, not a market-wide truth engine.
Model output must remain schema-validated and review-aware.

---

## Tool 7 — Analysis payload validator

### Canonical implementation path
- `~/work/py-hbs-ads/src/hbs_ads/features/market_research/validators.py`
- `~/work/py-hbs-ads/scripts/market_research/validate_analysis_schema.py`

### Primary callable surfaces
- `validate_analysis_payload(payload) -> list[str]`
- CLI helper script

### Purpose
Validate Gemini outputs against the expected research-analysis contract.

### Inputs
- analysis payload dict or JSON file

### Outputs
- list of validation errors
- CLI returns success/failure JSON

### Side effects
- script reads local file only

### Agent use cases
- validate fresh model output
- check sample fixtures
- gate whether synthesis may continue

### Review risk
- low

---

## Tool 8 — Insight synthesis toolset

### Canonical implementation path
- `~/work/py-hbs-ads/src/hbs_ads/features/market_research/synthesis.py`

### Primary callable surfaces
- `synthesize_hook_pattern_insights(...)`
- `synthesize_format_pattern_insights(...)`
- `synthesize_insights(...) -> list[InsightCandidate]`

### Purpose
Turn validated analyses into draft insight candidates with evidence refs and scope.

### Inputs
- validated `CreativeAnalysisResult` records
- `ResearchBrief`
- run id
- optional clusters

### Outputs
- `InsightCandidate` list

### Side effects
- none

### Agent use cases
- draft reviewable insights after analysis
- rerun synthesis after brief changes
- compare pattern density across runs

### Review risk
- medium to high

### Notes
This tool drafts insights. It does not canonize truth.

---

## Tool 9 — Insight candidate validator

### Canonical implementation path
- `~/work/py-hbs-ads/src/hbs_ads/features/market_research/validators.py`

### Primary callable surface
- `validate_insight_candidate(insight) -> list[str]`

### Purpose
Ensure an insight candidate has required evidence, scope, and confidence fields.

### Inputs
- `InsightCandidate`

### Outputs
- list of errors

### Side effects
- none

### Agent use cases
- refuse to store evidence-less insights
- QA insight drafts before review or sync

### Review risk
- low

---

## Tool 10 — Review transform toolset

### Canonical implementation path
- `~/work/py-hbs-ads/src/hbs_ads/features/market_research/review.py`

### Primary callable surfaces
- `apply_review(...) -> tuple[InsightCandidate, ReviewDecision]`
- `batch_approve(...) -> tuple[list[InsightCandidate], list[ReviewDecision]]`

### Purpose
Represent and apply explicit review outcomes.

### Inputs
- insight candidate(s)
- reviewer id
- decision
- rationale

### Outputs
- updated insight candidate(s)
- review decision record(s)

### Side effects
- none

### Agent use cases
- encode human decisions into structured state
- transform draft insights into approved/rejected/deferred outputs

### Review risk
- medium

---

## Tool 11 — Research SQLite repository

### Canonical implementation path
- `~/work/py-hbs-ads/src/hbs_ads/infra/db/market_research_sqlite.py`

### Primary callable surfaces
- `bootstrap()`
- `upsert_brief(...)`
- `upsert_candidate(...)`
- `upsert_variant_cluster(...)`
- `upsert_concept_cluster(...)`
- `upsert_analysis(...)`
- `upsert_insight(...)`
- `upsert_review(...)`
- `upsert_sync_report(...)`
- `sync_run(...)`
- read helpers such as `list_candidates(...)`, `list_insights(...)`

### Purpose
Persist the research workflow state into a dedicated pilot DB.

### Inputs
- typed research entities

### Outputs
- durable SQLite state
- lightweight readback helpers

### Side effects
- writes `research.db`

### Agent use cases
- persist artifacts after each bounded stage
- retrieve prior run summaries
- separate durable research state from current operational clip DB

### Review risk
- medium

### Notes
This is a persistence primitive, not a reasoning primitive.

---

## Tool 12 — Market research service

### Canonical implementation path
- `~/work/py-hbs-ads/src/hbs_ads/features/market_research/service.py`

### Primary callable surfaces
- `store_brief(...)`
- `collect_from_manifest(...)`
- `normalize(...)`
- `cluster(...)`
- `analyze(...)`
- `enrich(...)`
- `synthesize(...)`
- `load_run_state(...)`
- `load_failures(...)`
- `load_analyses(...)`
- `load_insights(...)`
- `load_reviews(...)`
- `debug_asset(...)`
- `re_synthesize_from_saved_analyses(...)`
- `review(...)`
- `sync(...)`
- `run(...)`

### Purpose
Provide a convenience composition layer across the lower-level primitives.

### Inputs
- typed brief/request objects
- manifest path
- optional analyzer and DB dependencies

### Outputs
- stage artifacts
- sync report
- full-run summary when using `run(...)`

### Side effects
- writes artifacts under workspace `logs/market-research/`
- optionally writes to research SQLite DB

### Agent use cases
- useful for parent agents that want a stage-aware façade
- useful for runner scripts and integration tests

### Review risk
- medium

### Important note
This is **not** the primary value definition of V1.
It is a convenience orchestrator over the underlying tools.

---

## Tool 13 — Standalone runner

### Canonical implementation path
- `~/work/py-hbs-ads/scripts/market_research/run_market_research.py`

### Purpose
Expose a practical local entrypoint for the zero-touch pilot.

### Inputs
- `--workspace`
- `--brief`
- `--manifest`
- `--stage`

### Outputs
- JSON `CommandResult`

### Side effects
- creates workspace artifacts
- may create `research.db`

### Agent use cases
- useful for shell-driven orchestration
- useful for quick local smoke tests

### Review risk
- medium

### Note
This is an orchestration helper, not the architectural center of gravity.

---

## 4. Recommended default agent workflow patterns

## Pattern A — Analyze a fresh export
1. validate brief
2. normalize candidates
3. validate candidates if needed
4. cluster
5. choose representative assets
6. analyze representative assets
7. validate analysis payloads
8. synthesize insights

## Pattern B — Re-synthesize from existing analyses
1. load prior analyses from artifacts or DB
2. validate analysis payloads
3. run synthesis only
4. apply review transform if needed

## Pattern C — Debug one asset
1. call `analyze_asset(...)`
2. validate schema
3. inspect evidence/quality fields
4. decide whether re-prompt or review is needed

## 5. Prioritization for near-term evolution

If the team keeps the tool-first framing, the next improvements should prioritize:

1. stronger representative-asset selection contracts
2. better clustering heuristics with explicit confidence
3. more robust repository read/query helpers
4. better agent-facing wrappers per primitive
5. only later: a polished integrated CLI/pipeline surface

## 6. Bottom line

The first success condition is not:
- “we have a complete market research pipeline.”

The first success condition is:
- “an AI agent can reliably call a bounded set of market research primitives to do useful work.”
