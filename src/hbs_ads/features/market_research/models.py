from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ResearchBrief:
    brief_id: str
    research_goal: str
    market_scope: dict[str, Any]
    competitor_scope: dict[str, Any]
    creative_scope: dict[str, Any]
    analysis_focus: list[str]
    sampling_strategy: str
    output_mode: str
    review_mode: str
    created_at: str = ""
    created_by: str = ""


@dataclass
class MarketResearchRunRequest:
    brief: ResearchBrief
    workspace_path: str
    manifest_path: str = ""
    stage: str = "all"
    operator: str = "system"


@dataclass
class MarketQueryRecord:
    query_id: str
    run_id: str
    source: str
    query_context: dict[str, Any]
    retrieved_at: str
    collector_identity: str = ""
    raw_export_path: str = ""
    status: str = "collected"


@dataclass
class AdCandidate:
    candidate_id: str
    run_id: str
    query_id: str
    source: str
    source_record_id: str = ""
    source_url: str = ""
    app_name: str = ""
    publisher_name: str = ""
    geo: str = ""
    platform: str = ""
    first_seen_at: str = ""
    last_seen_at: str = ""
    asset_url: str = ""
    thumbnail_url: str = ""
    landing_url: str = ""
    raw_payload: dict[str, Any] = field(default_factory=dict)
    normalized_status: str = "raw"
    dedupe_key: str = ""


@dataclass
class CreativeAsset:
    asset_id: str
    primary_candidate_id: str
    asset_type: str = "video"
    canonical_path: str = ""
    content_sha256: str = ""
    perceptual_hash: str = ""
    duration_seconds: float | None = None
    aspect_ratio: str = ""
    audio_present: bool = True
    ocr_text_excerpt: str = ""
    asset_quality_flags: list[str] = field(default_factory=list)


@dataclass
class VariantCluster:
    variant_cluster_id: str
    cluster_label: str
    representative_asset_id: str
    member_asset_ids: list[str] = field(default_factory=list)
    cluster_confidence: float = 1.0
    clustering_method: str = "exact_dedupe_key"
    review_status: str = "provisional"
    review_notes: str = ""


@dataclass
class ConceptCluster:
    concept_cluster_id: str
    cluster_label: str
    representative_variant_cluster_id: str
    member_variant_cluster_ids: list[str] = field(default_factory=list)
    concept_summary: str = ""
    cluster_confidence: float = 0.7
    review_status: str = "provisional"
    review_notes: str = ""


@dataclass
class CreativeAnalysisResult:
    analysis_id: str
    run_id: str
    asset_id: str
    variant_cluster_id: str = ""
    concept_cluster_id: str = ""
    model_provider: str = "gemini"
    model_name: str = ""
    schema_version: str = "creative-analysis/v1"
    observable: dict[str, Any] = field(default_factory=dict)
    taxonomy_tags: dict[str, Any] = field(default_factory=dict)
    interpretation: dict[str, Any] = field(default_factory=dict)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    quality: dict[str, Any] = field(default_factory=dict)
    analysis_status: str = "ok"
    created_at: str = ""


@dataclass
class InsightCandidate:
    insight_candidate_id: str
    run_id: str
    insight_type: str
    title: str
    signal: str
    evidence_summary: dict[str, Any] = field(default_factory=dict)
    scope: dict[str, Any] = field(default_factory=dict)
    confidence: str = "medium"
    implication: str = ""
    evidence_refs: list[str] = field(default_factory=list)
    needs_human_review: bool = True
    status: str = "draft"
    created_at: str = ""


@dataclass
class ReviewDecision:
    review_id: str
    run_id: str
    target_type: str
    target_id: str
    reviewer: str
    decision: str
    rationale: str = ""
    updated_confidence: str = ""
    created_at: str = ""


@dataclass
class SyncReport:
    run_id: str
    synced_candidates: int = 0
    synced_assets: int = 0
    synced_clusters: int = 0
    synced_analyses: int = 0
    synced_insights: int = 0
    synced_reviews: int = 0
    errors: list[str] = field(default_factory=list)
    created_at: str = ""
