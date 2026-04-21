# Workflow Spec — Creative Market Research

## 1. Workflow summary

This workflow turns a structured research brief into evidence-backed market insights for mobile game ad creatives.

Canonical stage sequence:

1. brief
2. collect
3. normalize
4. dedupe_cluster
5. analyze
6. enrich
7. synthesize
8. review
9. sync

## 2. Stage contracts

## Stage 1 — Brief

### Purpose
Declare scope, objective, sampling logic, and desired outputs before any collection happens.

### Required input
```json
{
  "brief_id": "mr_2026_04_20_idle_us_hooks",
  "research_goal": "Find current hook and format patterns for idle game creatives in the US market.",
  "market_scope": {
    "genres": ["idle"],
    "geos": ["US"],
    "platforms": ["meta", "tiktok"],
    "date_range": {
      "start": "2026-04-01",
      "end": "2026-04-20"
    }
  },
  "competitor_scope": {
    "apps": [],
    "publishers": [],
    "mode": "broad_market"
  },
  "creative_scope": {
    "asset_types": ["video"],
    "max_candidates": 80
  },
  "analysis_focus": ["hook_type", "format_type", "core_angle", "cta_style"],
  "sampling_strategy": "recent_plus_density",
  "output_mode": "insight_cards_plus_experiments",
  "review_mode": "human_approval_required"
}
```

### Output
- `brief.json`
- validated run metadata

### Review gate
Fail fast if the brief does not define a meaningful scope.

---

## Stage 2 — Collect

### Purpose
Collect ad candidates from authenticated market sources.

### Required output fields per candidate
- `run_id`
- `source`
- `source_record_id`
- `retrieved_at`
- `query_context`
- `asset_url` or local asset path
- `thumbnail_url` if present
- `app_name`
- `publisher_name`
- `geo`
- `platform`
- `first_seen_at` / `last_seen_at` when available

### Output artifacts
- `collect/candidates.raw.json`
- `collect/assets-manifest.json`

### Review gate
Sampling validity check when sample is too small, too narrow, or skewed.

---

## Stage 3 — Normalize

### Purpose
Map heterogeneous source outputs into one canonical schema.

### Transformations
- normalize platform/source naming
- standardize date fields
- standardize competitor/app identifiers
- assign stable candidate ids
- compute provisional dedupe keys

### Output artifacts
- `normalize/candidates.normalized.json`

### Rules
- preserve raw source fields in `raw_payload` or equivalent provenance bucket
- do not discard source-native identifiers

---

## Stage 4 — Dedupe / Cluster

### Purpose
Reduce repeated uploads and group related variants/concepts.

### Required levels
1. `asset_instance`
2. `variant_cluster`
3. `concept_cluster`

### Required outputs
- `cluster/asset-dedupe.json`
- `cluster/variant-clusters.json`
- `cluster/concept-clusters.json`
- representative asset selection for each cluster

### Rules
- exact or near-exact duplicate detection should be automatic where confidence is high
- concept clustering may remain provisional and reviewable

### Review gate
Human review for weak concept-group confidence or controversial merges.

---

## Stage 5 — Analyze

### Purpose
Run strict-schema creative analysis on representative assets.

### Input
- representative asset path or asset URL
- brief focus
- controlled taxonomy definitions

### Output
- `analyze/creative-analysis.jsonl`
- one JSON object per analyzed asset, validated against the Gemini schema doc

### Rules
- parse and validate every response
- retry once on malformed JSON
- mark failures explicitly instead of silently dropping them

### Review gate
Human review required when:
- confidence is low
- analysis fails schema after repair
- evidence ranges are missing for key claims

---

## Stage 6 — Enrich

### Purpose
Add market and competitor context around the analyzed assets/clusters.

### Possible enrichment fields
- app/store category
- publisher cluster
- geo/platform distribution
- recurrence count across the sample
- appearance over time window
- related landing/store references

### Output artifacts
- `enrich/context.json`
- `enrich/cluster-metrics.json`

---

## Stage 7 — Synthesize

### Purpose
Draft insight candidates from aggregated evidence.

### Insight candidate structure
```json
{
  "insight_id": "ins_001",
  "type": "pattern",
  "title": "Fail-then-win hooks are dense in the sampled idle market",
  "signal": "Fail-then-win is one of the most repeated hooks across the sample.",
  "evidence_summary": {
    "supporting_asset_count": 16,
    "supporting_variant_cluster_count": 7,
    "supporting_concept_cluster_count": 4,
    "sources": ["tool_a", "tool_b"]
  },
  "scope": {
    "geo": ["US"],
    "platform": ["meta", "tiktok"],
    "time_window": ["2026-04-01", "2026-04-20"]
  },
  "confidence": "medium",
  "implication": "Worth testing only if differentiated execution is available.",
  "evidence_refs": ["analysis:asset_12", "cluster:variant_7", "candidate:cand_44"],
  "needs_human_review": true
}
```

### Rules
- every insight must include explicit evidence refs
- claims about the whole market must declare scope
- action recommendations must be downstream of evidence, not raw intuition

---

## Stage 8 — Review

### Purpose
Convert draft insights into approved, edited, rejected, or deferred outputs.

### Allowed review decisions
- `approve`
- `approve_with_edits`
- `reject`
- `defer_for_more_evidence`

### Required review record fields
- reviewer
- decision
- rationale
- modified confidence if changed
- timestamp

### Output artifact
- `review/review-decisions.json`

---

## Stage 9 — Sync

### Purpose
Persist durable evidence and synthesis records into research storage.

### Output artifact
- `sync/sync-report.json`

### Rules
- evidence records can sync before strategic approval if clearly marked as raw/provisional
- approved insights must preserve backlinks to evidence ids and run ids

## 3. Failure handling

### Malformed model output
- retry once with validation errors
- if still invalid, mark `analysis_failed`
- do not synthesize from invalid analysis records

### Weak sample
- mark sampling risk explicitly
- allow continuation only if the operator accepts exploratory-mode results

### Unstable clustering
- downgrade confidence
- block canonical trend or strategy claims until review

## 4. Definition of done for one workflow run

A run is complete when:

1. the brief is stored
2. collected candidates are normalized and provenance-preserving
3. representative assets are analyzed with validated JSON or explicit failure records
4. insight candidates exist with evidence refs
5. review decisions are captured
6. final sync report is written
