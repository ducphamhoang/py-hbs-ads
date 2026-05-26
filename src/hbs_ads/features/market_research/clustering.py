from __future__ import annotations

import hashlib
from collections import defaultdict
from typing import Any

from hbs_ads.features.market_research.models import (
    AdCandidate,
    ConceptCluster,
    CreativeAsset,
    VariantCluster,
)


def build_asset_from_candidate(candidate: AdCandidate) -> CreativeAsset:
    asset_id = "asset_" + hashlib.sha256(
        (candidate.candidate_id + candidate.asset_url).encode()
    ).hexdigest()[:12]
    return CreativeAsset(
        asset_id=asset_id,
        primary_candidate_id=candidate.candidate_id,
        asset_type="video",
        canonical_path=candidate.asset_url,
        content_sha256="",
        perceptual_hash="",
    )


def dedupe_assets(
    candidates: list[AdCandidate],
) -> tuple[list[CreativeAsset], dict[str, str]]:
    """Return (unique_assets, dedupe_map: candidate_id -> asset_id)."""
    seen: dict[str, CreativeAsset] = {}
    dedupe_map: dict[str, str] = {}

    for cand in candidates:
        key = cand.dedupe_key or cand.candidate_id
        if key not in seen:
            asset = build_asset_from_candidate(cand)
            seen[key] = asset
        dedupe_map[cand.candidate_id] = seen[key].asset_id

    return list(seen.values()), dedupe_map


def build_variant_clusters(
    assets: list[CreativeAsset],
    candidates: list[AdCandidate],
    dedupe_map: dict[str, str],
) -> list[VariantCluster]:
    """Group assets by app_name+platform as a simple variant-family heuristic."""
    asset_lookup = {a.asset_id: a for a in assets}
    cand_by_asset: dict[str, list[AdCandidate]] = defaultdict(list)
    for cand in candidates:
        aid = dedupe_map.get(cand.candidate_id)
        if aid:
            cand_by_asset[aid].append(cand)

    groups: dict[tuple[str, str], list[str]] = defaultdict(list)
    for asset in assets:
        rep_cand = cand_by_asset.get(asset.asset_id, [])
        if rep_cand:
            c = rep_cand[0]
            key = (c.app_name.lower(), c.platform.lower())
        else:
            key = ("unknown", "unknown")
        groups[key].append(asset.asset_id)

    clusters: list[VariantCluster] = []
    for (app, platform), asset_ids in groups.items():
        if not asset_ids:
            continue
        vcl_id = "vcl_" + hashlib.sha256(f"{app}|{platform}".encode()).hexdigest()[:10]
        clusters.append(
            VariantCluster(
                variant_cluster_id=vcl_id,
                cluster_label=f"{app}/{platform}",
                representative_asset_id=asset_ids[0],
                member_asset_ids=asset_ids,
                cluster_confidence=1.0 if len(asset_ids) == 1 else 0.8,
                clustering_method="app_platform_heuristic",
                review_status="provisional",
            )
        )
    return clusters


def build_concept_clusters(
    variant_clusters: list[VariantCluster],
    candidates: list[AdCandidate],
    dedupe_map: dict[str, str],
) -> list[ConceptCluster]:
    """Group variant clusters by app_name as a rough concept-family."""
    asset_to_app: dict[str, str] = {}
    for cand in candidates:
        aid = dedupe_map.get(cand.candidate_id, "")
        if aid and cand.app_name:
            asset_to_app[aid] = cand.app_name.lower()

    groups: dict[str, list[str]] = defaultdict(list)
    for vc in variant_clusters:
        app = asset_to_app.get(vc.representative_asset_id, "unknown")
        groups[app].append(vc.variant_cluster_id)

    clusters: list[ConceptCluster] = []
    for app, vcl_ids in groups.items():
        if not vcl_ids:
            continue
        ccl_id = "ccl_" + hashlib.sha256(app.encode()).hexdigest()[:10]
        clusters.append(
            ConceptCluster(
                concept_cluster_id=ccl_id,
                cluster_label=app,
                representative_variant_cluster_id=vcl_ids[0],
                member_variant_cluster_ids=vcl_ids,
                concept_summary=f"Ads for {app}",
                cluster_confidence=0.7 if len(vcl_ids) > 1 else 1.0,
                review_status="provisional",
            )
        )
    return clusters


def run_clustering(
    candidates: list[AdCandidate],
) -> dict[str, Any]:
    assets, dedupe_map = dedupe_assets(candidates)
    variant_clusters = build_variant_clusters(assets, candidates, dedupe_map)
    concept_clusters = build_concept_clusters(variant_clusters, candidates, dedupe_map)
    return {
        "assets": assets,
        "dedupe_map": dedupe_map,
        "variant_clusters": variant_clusters,
        "concept_clusters": concept_clusters,
    }
