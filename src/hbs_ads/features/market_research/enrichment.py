from __future__ import annotations

from collections import Counter
from typing import Any

from hbs_ads.features.market_research.models import AdCandidate, VariantCluster, ConceptCluster


def compute_source_distribution(candidates: list[AdCandidate]) -> dict[str, int]:
    return dict(Counter(c.source for c in candidates if c.source))


def compute_platform_distribution(candidates: list[AdCandidate]) -> dict[str, int]:
    return dict(Counter(c.platform for c in candidates if c.platform))


def compute_geo_distribution(candidates: list[AdCandidate]) -> dict[str, int]:
    return dict(Counter(c.geo for c in candidates if c.geo))


def compute_publisher_distribution(candidates: list[AdCandidate]) -> dict[str, int]:
    return dict(Counter(c.publisher_name for c in candidates if c.publisher_name))


def compute_app_distribution(candidates: list[AdCandidate]) -> dict[str, int]:
    return dict(Counter(c.app_name for c in candidates if c.app_name))


def compute_cluster_metrics(
    variant_clusters: list[VariantCluster],
    concept_clusters: list[ConceptCluster],
) -> dict[str, Any]:
    return {
        "variant_cluster_count": len(variant_clusters),
        "concept_cluster_count": len(concept_clusters),
        "avg_variant_cluster_size": (
            sum(len(vc.member_asset_ids) for vc in variant_clusters) / len(variant_clusters)
            if variant_clusters else 0.0
        ),
        "low_confidence_variant_clusters": sum(
            1 for vc in variant_clusters if vc.cluster_confidence < 0.8
        ),
        "low_confidence_concept_clusters": sum(
            1 for cc in concept_clusters if cc.cluster_confidence < 0.8
        ),
    }


def enrich_run(
    candidates: list[AdCandidate],
    variant_clusters: list[VariantCluster],
    concept_clusters: list[ConceptCluster],
) -> dict[str, Any]:
    return {
        "source_distribution": compute_source_distribution(candidates),
        "platform_distribution": compute_platform_distribution(candidates),
        "geo_distribution": compute_geo_distribution(candidates),
        "publisher_distribution": compute_publisher_distribution(candidates),
        "app_distribution": compute_app_distribution(candidates),
        "total_candidates": len(candidates),
        "total_unique_assets": len({
            vc.representative_asset_id for vc in variant_clusters
        }),
        "cluster_metrics": compute_cluster_metrics(variant_clusters, concept_clusters),
    }
