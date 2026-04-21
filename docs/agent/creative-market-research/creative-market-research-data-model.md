# Data Model — Creative Market Research

## 1. Modeling principles

1. Preserve provenance from source query to final insight.
2. Separate evidence entities from synthesis entities.
3. Model clustering explicitly instead of flattening all ads into one table.
4. Keep AI interpretation reviewable and replaceable without losing raw observations.

## 2. Core entities

## 2.1 `market_research_run`
Represents one execution of a research brief.

Suggested fields:
- `run_id`
- `brief_id`
- `status`
- `created_at`
- `started_at`
- `finished_at`
- `operator`
- `review_mode`
- `sampling_risk`
- `notes`

## 2.2 `research_brief`
Defines the contract for one run.

Suggested fields:
- `brief_id`
- `research_goal`
- `market_scope_json`
- `competitor_scope_json`
- `creative_scope_json`
- `analysis_focus_json`
- `sampling_strategy`
- `output_mode`
- `review_mode`
- `created_at`
- `created_by`

## 2.3 `market_query`
Stores one source query or browser pull slice inside a run.

Suggested fields:
- `query_id`
- `run_id`
- `source`
- `query_context_json`
- `retrieved_at`
- `collector_identity`
- `raw_export_path`
- `status`

## 2.4 `ad_candidate`
Represents one collected source record before heavy normalization loss.

Suggested fields:
- `candidate_id`
- `run_id`
- `query_id`
- `source`
- `source_record_id`
- `source_url`
- `app_name`
- `publisher_name`
- `geo`
- `platform`
- `first_seen_at`
- `last_seen_at`
- `asset_url`
- `thumbnail_url`
- `landing_url`
- `raw_payload_json`
- `normalized_status`
- `dedupe_key`

## 2.5 `creative_asset`
Canonical asset-level entity after normalization.

Suggested fields:
- `asset_id`
- `primary_candidate_id`
- `asset_type`
- `canonical_path`
- `content_sha256`
- `perceptual_hash`
- `duration_seconds`
- `aspect_ratio`
- `audio_present`
- `ocr_text_excerpt`
- `asset_quality_flags_json`

## 2.6 `asset_instance`
Connects source-specific candidate sightings to a canonical asset.

Suggested fields:
- `asset_instance_id`
- `asset_id`
- `candidate_id`
- `source`
- `source_record_id`
- `seen_at`
- `instance_notes`

## 2.7 `variant_cluster`
Groups close edits or re-uploads of effectively the same creative variant.

Suggested fields:
- `variant_cluster_id`
- `cluster_label`
- `representative_asset_id`
- `cluster_confidence`
- `clustering_method`
- `review_status`
- `review_notes`

## 2.8 `concept_cluster`
Groups assets/variants that share the same higher-level creative concept.

Suggested fields:
- `concept_cluster_id`
- `cluster_label`
- `representative_variant_cluster_id`
- `concept_summary`
- `cluster_confidence`
- `review_status`
- `review_notes`

## 2.9 `creative_analysis_result`
Stores the validated output of Gemini or another analyzer for one representative asset.

Suggested fields:
- `analysis_id`
- `run_id`
- `asset_id`
- `variant_cluster_id`
- `concept_cluster_id`
- `model_provider`
- `model_name`
- `schema_version`
- `observable_json`
- `taxonomy_tags_json`
- `interpretation_json`
- `evidence_json`
- `quality_json`
- `analysis_status`
- `created_at`

## 2.10 `research_enrichment`
Stores contextual facts added after raw analysis.

Suggested fields:
- `enrichment_id`
- `run_id`
- `target_type`
- `target_id`
- `source`
- `payload_json`
- `created_at`

## 2.11 `insight_candidate`
Draft synthesis output before final approval.

Suggested fields:
- `insight_candidate_id`
- `run_id`
- `insight_type`
- `title`
- `signal`
- `evidence_summary_json`
- `scope_json`
- `confidence`
- `implication`
- `needs_human_review`
- `status`
- `created_at`

## 2.12 `insight_evidence_link`
Join table from insight candidates or approved insights back to evidence.

Suggested fields:
- `link_id`
- `insight_id`
- `insight_kind`  
- `evidence_type`
- `evidence_id`
- `relevance_score`
- `note`

## 2.13 `review_decision`
Stores human review for clusters, analyses, or insights.

Suggested fields:
- `review_id`
- `run_id`
- `target_type`
- `target_id`
- `reviewer`
- `decision`
- `rationale`
- `updated_confidence`
- `created_at`

## 2.14 `approved_insight`
Canonized synthesis artifact after review.

Suggested fields:
- `insight_id`
- `source_candidate_id`
- `run_id`
- `insight_type`
- `title`
- `statement`
- `scope_json`
- `confidence`
- `implication`
- `status`
- `approved_at`
- `approved_by`

## 2.15 `competitor_snapshot`
Durable competitor-oriented research summary.

Suggested fields:
- `snapshot_id`
- `run_id`
- `competitor_key`
- `time_window_json`
- `dominant_formats_json`
- `dominant_hooks_json`
- `messaging_angles_json`
- `production_style_json`
- `novelty_score`
- `supporting_evidence_json`

## 2.16 `trend_snapshot`
Durable market trend summary for a declared scope window.

Suggested fields:
- `trend_snapshot_id`
- `run_id`
- `scope_json`
- `rising_patterns_json`
- `saturated_patterns_json`
- `regional_deltas_json`
- `supporting_evidence_json`

## 3. Relationships

Recommended relationship map:

- one `research_brief` -> many `market_research_run`
- one `market_research_run` -> many `market_query`
- one `market_query` -> many `ad_candidate`
- many `ad_candidate` -> one or more `creative_asset` sightings through `asset_instance`
- many `creative_asset` -> one `variant_cluster`
- many `variant_cluster` -> one `concept_cluster`
- one representative `creative_asset` -> one or more `creative_analysis_result`
- many `creative_analysis_result` + cluster facts -> many `insight_candidate`
- approved insights -> many evidence links through `insight_evidence_link`

## 4. Suggested identifiers

Recommended prefixes:
- `brief_*`
- `run_*`
- `query_*`
- `cand_*`
- `asset_*`
- `ainst_*`
- `vcl_*`
- `ccl_*`
- `analysis_*`
- `enrich_*`
- `inscand_*`
- `ins_*`
- `review_*`
- `csnap_*`
- `tsnap_*`

## 5. Controlled vocabulary anchors

At minimum, keep controlled vocabularies for:
- `hook_type`
- `format_type`
- `core_angle`
- `gameplay_visibility`
- `creator_presence`
- `cta_style`
- `offer_type`
- `emotion_target`
- `production_style`
- `funnel_stage_guess`

## 6. Minimal SQL-oriented cut for V1

If we want a lighter first implementation, keep these as required durable tables first:

- `research_brief`
- `market_research_run`
- `market_query`
- `ad_candidate`
- `creative_asset`
- `variant_cluster`
- `concept_cluster`
- `creative_analysis_result`
- `insight_candidate`
- `review_decision`
- `approved_insight`
- `insight_evidence_link`

Everything else can begin as JSON artifacts if needed.
