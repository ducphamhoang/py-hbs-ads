"""
Representative Asset Selection for Creative Market Research

This module implements the selection policy defined in:
docs/agent/creative-market-research/creative-market-research-representative-asset-selection.md

Core principles:
- Selection is about analysis efficiency + coverage, NOT creative quality ranking
- Variant clusters: 1 representative asset (usually)
- Concept clusters: 1-3 representatives depending on internal diversity
- Decisions must be auditable and traceable
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AssetSelectionDecision:
    """Record of why an asset was selected or skipped."""
    cluster_id: str
    cluster_type: str  # "variant" or "concept"
    selected_asset_ids: list[str]
    selection_reason: list[str]
    selection_confidence: str  # "high", "medium", "low"
    split_dimensions: list[str] = field(default_factory=list)
    fallback_used: bool = False
    excluded_asset_ids: list[str] = field(default_factory=list)
    notes: str = ""


def select_representative_for_variant_cluster(
    variant_cluster: dict[str, Any],
    assets_by_id: dict[str, dict[str, Any]],
    candidates_by_asset_id: list[dict[str, Any]],
) -> AssetSelectionDecision:
    """
    Apply rules V1-V6 to select one representative asset from a variant cluster.
    
    Rules in order:
    V1 — Prefer intact local assets
    V2 — Prefer complete creative structure
    V3 — Prefer richer metadata
    V4 — Prefer canonical source representation
    V5 — Tie-break by recency
    V6 — Fallback when best asset is unusable
    
    Returns:
        AssetSelectionDecision with the selected asset and reasoning
    """
    member_ids = variant_cluster.get("member_asset_ids", [])
    if not member_ids:
        return AssetSelectionDecision(
            cluster_id=variant_cluster["variant_cluster_id"],
            cluster_type="variant",
            selected_asset_ids=[],
            selection_reason=["no_members"],
            selection_confidence="low",
            notes="Variant cluster has no member assets",
        )
    
    # Gather candidate assets with their metadata
    candidates: list[tuple[str, dict[str, Any], int]] = []
    for asset_id in member_ids:
        asset = assets_by_id.get(asset_id)
        if asset is None:
            continue
        
        score = 0
        reasons: list[str] = []
        
        # V1 — Prefer intact local assets
        canonical_path = asset.get("canonical_path", "")
        is_local = canonical_path.startswith("/") or canonical_path.startswith("~/")
        if is_local:
            score += 100
            reasons.append("intact_local_file")
        
        # V2 — Prefer complete creative structure (heuristic: duration present + reasonable)
        duration = asset.get("duration_seconds")
        if duration and 5 <= duration <= 120:
            score += 50
            reasons.append("complete_structure")
        
        # V3 — Prefer richer metadata
        metadata_fields = [
            asset.get("first_seen_at"),
            asset.get("last_seen_at"),
            asset.get("platform"),
            asset.get("geo"),
        ]
        metadata_score = sum(1 for f in metadata_fields if f)
        if metadata_score >= 3:
            score += 30
            reasons.append("rich_metadata")
        elif metadata_score >= 1:
            score += 10
        
        # V4 — Prefer canonical source representation (heuristic: has raw_payload via candidate)
        # This is handled at candidate level, skip for now
        
        # V5 — Tie-break by recency
        last_seen = asset.get("last_seen_at", "")
        if last_seen:
            score += 5
        
        candidates.append((asset_id, asset, score))
    
    if not candidates:
        return AssetSelectionDecision(
            cluster_id=variant_cluster["variant_cluster_id"],
            cluster_type="variant",
            selected_asset_ids=[],
            selection_reason=["no_usable_assets"],
            selection_confidence="low",
            fallback_used=True,
            notes="No usable assets found in variant cluster",
        )
    
    # Sort by score descending
    candidates.sort(key=lambda x: x[2], reverse=True)
    best_asset_id = candidates[0][0]
    best_reasons = []
    
    # Reconstruct reasons from the best candidate
    best_asset = candidates[0][1]
    if best_asset.get("canonical_path", "").startswith("/"):
        best_reasons.append("intact_local_file")
    if best_asset.get("duration_seconds") and 5 <= best_asset["duration_seconds"] <= 120:
        best_reasons.append("complete_structure")
    metadata_fields = [
        best_asset.get("first_seen_at"),
        best_asset.get("last_seen_at"),
        best_asset.get("platform"),
        best_asset.get("geo"),
    ]
    if sum(1 for f in metadata_fields if f) >= 3:
        best_reasons.append("rich_metadata")
    if best_asset.get("last_seen_at"):
        best_reasons.append("recency")
    
    # Determine confidence
    confidence = "high" if candidates[0][2] >= 150 else "medium" if candidates[0][2] >= 50 else "low"
    
    excluded = [c[0] for c in candidates[1:]] if len(candidates) > 1 else []
    
    return AssetSelectionDecision(
        cluster_id=variant_cluster["variant_cluster_id"],
        cluster_type="variant",
        selected_asset_ids=[best_asset_id],
        selection_reason=best_reasons,
        selection_confidence=confidence,
        excluded_asset_ids=excluded,
    )


def select_representatives_for_concept_cluster(
    concept_cluster: dict[str, Any],
    variant_clusters_by_id: dict[str, dict[str, Any]],
    assets_by_id: dict[str, dict[str, Any]],
    candidates_by_asset_id: list[dict[str, Any]],
) -> AssetSelectionDecision:
    """
    Apply rules C1-C4 to select 1-3 representative assets from a concept cluster.
    
    Rules:
    C1 — Start with one representative per concept cluster
    C2 — Use multiple representatives when hook/format split exists
    C3 — Explicitly record why multiple assets were chosen
    C4 — Cap at 3 representatives per concept cluster
    
    Returns:
        AssetSelectionDecision with selected assets and reasoning
    """
    member_vcl_ids = concept_cluster.get("member_variant_cluster_ids", [])
    if not member_vcl_ids:
        return AssetSelectionDecision(
            cluster_id=concept_cluster["concept_cluster_id"],
            cluster_type="concept",
            selected_asset_ids=[],
            selection_reason=["no_member_variant_clusters"],
            selection_confidence="low",
            notes="Concept cluster has no member variant clusters",
        )

    candidate_by_id = {candidate.get("candidate_id", ""): candidate for candidate in candidates_by_asset_id}

    variant_clusters = [
        variant_clusters_by_id.get(vcl_id)
        for vcl_id in member_vcl_ids
        if variant_clusters_by_id.get(vcl_id)
    ]

    if not variant_clusters:
        return AssetSelectionDecision(
            cluster_id=concept_cluster["concept_cluster_id"],
            cluster_type="concept",
            selected_asset_ids=[],
            selection_reason=["no_usable_variant_clusters"],
            selection_confidence="low",
            notes="No usable variant clusters found",
        )

    def _representative_signature(variant_cluster: dict[str, Any]) -> tuple[str, str, str]:
        representative_asset_id = variant_cluster.get("representative_asset_id", "")
        asset = assets_by_id.get(representative_asset_id, {})
        primary_candidate_id = asset.get("primary_candidate_id", "")
        candidate = candidate_by_id.get(primary_candidate_id, {})
        raw_payload = candidate.get("raw_payload", {}) or {}
        return (
            raw_payload.get("hook_type", "unknown"),
            raw_payload.get("format_type", "unknown"),
            raw_payload.get("cta_style", "unknown"),
        )

    ranked_variant_clusters = sorted(
        variant_clusters,
        key=lambda vc: (vc.get("cluster_confidence", 0.0), vc.get("representative_asset_id", "")),
        reverse=True,
    )
    best_variant_cluster = ranked_variant_clusters[0]
    default_rep_id = best_variant_cluster.get("representative_asset_id", "")

    if not default_rep_id or default_rep_id not in assets_by_id:
        return AssetSelectionDecision(
            cluster_id=concept_cluster["concept_cluster_id"],
            cluster_type="concept",
            selected_asset_ids=[],
            selection_reason=["no_valid_representative"],
            selection_confidence="low",
            fallback_used=True,
        )

    split_dimensions: list[str] = []
    unique_values = {
        "hook_type": { _representative_signature(vc)[0] for vc in ranked_variant_clusters },
        "format_type": { _representative_signature(vc)[1] for vc in ranked_variant_clusters },
        "cta_style": { _representative_signature(vc)[2] for vc in ranked_variant_clusters },
    }
    for dimension, values in unique_values.items():
        meaningful_values = {value for value in values if value and value != "unknown"}
        if len(meaningful_values) > 1:
            split_dimensions.append(dimension)

    if not split_dimensions:
        confidence = "high" if len(variant_clusters) == 1 else "medium"
        return AssetSelectionDecision(
            cluster_id=concept_cluster["concept_cluster_id"],
            cluster_type="concept",
            selected_asset_ids=[default_rep_id],
            selection_reason=["single_representative_default"],
            selection_confidence=confidence,
            split_dimensions=[],
            notes="No meaningful hook/format/cta split detected across member variant clusters.",
        )

    selected_ids: list[str] = []
    seen_signatures: set[tuple[str, str, str]] = set()
    excluded_asset_ids: list[str] = []
    for variant_cluster in ranked_variant_clusters:
        representative_asset_id = variant_cluster.get("representative_asset_id", "")
        if not representative_asset_id or representative_asset_id not in assets_by_id:
            continue
        signature = _representative_signature(variant_cluster)
        if signature in seen_signatures:
            excluded_asset_ids.append(representative_asset_id)
            continue
        seen_signatures.add(signature)
        selected_ids.append(representative_asset_id)

    selection_reason = ["multi_representative_split"]
    notes = f"Multiple representatives chosen to cover split across: {', '.join(split_dimensions)}."
    if len(selected_ids) > 3:
        excluded_asset_ids.extend(selected_ids[3:])
        selected_ids = selected_ids[:3]
        selection_reason.append("representative_cap_applied")
        notes += " Cap applied at 3 representatives."

    confidence = "high" if len(split_dimensions) == 1 else "medium"
    return AssetSelectionDecision(
        cluster_id=concept_cluster["concept_cluster_id"],
        cluster_type="concept",
        selected_asset_ids=selected_ids,
        selection_reason=selection_reason,
        selection_confidence=confidence,
        split_dimensions=split_dimensions,
        excluded_asset_ids=excluded_asset_ids,
        notes=notes,
    )


def run_representative_selection(
    cluster_result: dict[str, Any],
    candidates: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Run representative selection on a clustering result.
    
    Args:
        cluster_result: Output from run_clustering() with assets, variant_clusters, concept_clusters
        candidates: Optional list of candidate records for metadata enrichment
    
    Returns:
        Dict with:
        - selected_assets: list of asset_ids to analyze
        - selection_decisions: list of AssetSelectionDecision for each cluster
        - variant_cluster_decisions: decisions for each variant cluster
        - concept_cluster_decisions: decisions for each concept cluster
    """
    assets = cluster_result.get("assets", [])
    variant_clusters = cluster_result.get("variant_clusters", [])
    concept_clusters = cluster_result.get("concept_clusters", [])
    
    # Build lookup tables
    assets_by_id: dict[str, dict[str, Any]] = {}
    for asset in assets:
        if hasattr(asset, "__dataclass_fields__"):
            from dataclasses import asdict
            assets_by_id[asset.asset_id] = asdict(asset)
        else:
            assets_by_id[asset["asset_id"]] = asset
    
    variant_clusters_by_id: dict[str, dict[str, Any]] = {}
    for vc in variant_clusters:
        if hasattr(vc, "__dataclass_fields__"):
            from dataclasses import asdict
            variant_clusters_by_id[vc.variant_cluster_id] = asdict(vc)
        else:
            variant_clusters_by_id[vc["variant_cluster_id"]] = vc
    
    # Run selection for variant clusters
    variant_decisions: list[AssetSelectionDecision] = []
    for vc in variant_clusters:
        if hasattr(vc, "__dataclass_fields__"):
            from dataclasses import asdict
            vc_dict = asdict(vc)
        else:
            vc_dict = vc
        
        decision = select_representative_for_variant_cluster(
            vc_dict,
            assets_by_id,
            candidates or [],
        )
        variant_decisions.append(decision)
    
    # Run selection for concept clusters
    concept_decisions: list[AssetSelectionDecision] = []
    for cc in concept_clusters:
        if hasattr(cc, "__dataclass_fields__"):
            from dataclasses import asdict
            cc_dict = asdict(cc)
        else:
            cc_dict = cc
        
        decision = select_representatives_for_concept_cluster(
            cc_dict,
            variant_clusters_by_id,
            assets_by_id,
            candidates or [],
        )
        concept_decisions.append(decision)
    
    # Aggregate selected assets
    all_selected: set[str] = set()
    for dec in variant_decisions:
        all_selected.update(dec.selected_asset_ids)
    for dec in concept_decisions:
        all_selected.update(dec.selected_asset_ids)
    
    return {
        "selected_assets": list(all_selected),
        "selection_decisions": variant_decisions + concept_decisions,
        "variant_cluster_decisions": variant_decisions,
        "concept_cluster_decisions": concept_decisions,
    }
