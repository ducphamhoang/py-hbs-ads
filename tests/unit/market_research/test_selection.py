from dataclasses import asdict

from hbs_ads.features.market_research.models import AdCandidate
from hbs_ads.features.market_research.clustering import run_clustering
from hbs_ads.features.market_research.selection import (
    run_representative_selection,
    select_representative_for_variant_cluster,
)


def _candidate(
    candidate_id: str,
    app_name: str,
    dedupe_key: str,
    asset_url: str = "",
    *,
    platform: str = 'meta',
    raw_payload: dict | None = None,
) -> AdCandidate:
    return AdCandidate(
        candidate_id=candidate_id,
        run_id='run_1',
        query_id='query_1',
        source='meta',
        app_name=app_name,
        platform=platform,
        asset_url=asset_url or f'https://example.com/{candidate_id}.mp4',
        dedupe_key=dedupe_key,
        normalized_status='normalized',
        last_seen_at='2026-04-20T12:00:00Z',
        raw_payload=raw_payload or {},
    )


def test_run_clustering_groups_duplicates_and_concepts() -> None:
    candidates = [
        _candidate('cand_a', 'Game A', 'same-key'),
        _candidate('cand_b', 'Game A', 'same-key'),
        _candidate('cand_c', 'Game B', 'other-key'),
    ]
    result = run_clustering(candidates)
    assert len(result['assets']) == 2
    assert len(result['variant_clusters']) == 2
    assert len(result['concept_clusters']) == 2


def test_representative_selection_selects_one_per_variant_cluster() -> None:
    candidates = [
        _candidate('cand_a', 'Game A', 'same-key'),
        _candidate('cand_b', 'Game A', 'same-key'),
        _candidate('cand_c', 'Game B', 'other-key'),
    ]
    cluster_result = run_clustering(candidates)
    
    selection_result = run_representative_selection(cluster_result)
    
    # Should select one asset per variant cluster
    assert len(selection_result['selected_assets']) == 2
    assert len(selection_result['variant_cluster_decisions']) == 2
    assert len(selection_result['concept_cluster_decisions']) == 2
    
    # Each variant cluster should have exactly one representative
    for dec in selection_result['variant_cluster_decisions']:
        assert len(dec.selected_asset_ids) == 1
        assert dec.selection_confidence in ['high', 'medium', 'low']


def test_representative_selection_records_reasoning() -> None:
    candidates = [
        _candidate('cand_a', 'Game A', 'same-key'),
    ]
    cluster_result = run_clustering(candidates)
    
    selection_result = run_representative_selection(cluster_result)
    
    assert len(selection_result['variant_cluster_decisions']) == 1
    dec = selection_result['variant_cluster_decisions'][0]
    
    assert dec.cluster_type == 'variant'
    assert len(dec.selected_asset_ids) == 1
    assert isinstance(dec.selection_reason, list)
    assert dec.selection_confidence in ['high', 'medium', 'low']


def test_concept_cluster_selection_uses_multiple_reps_for_meaningful_splits() -> None:
    candidates = [
        _candidate(
            'cand_meta',
            'Game A',
            'key-meta',
            platform='meta',
            raw_payload={'hook_type': 'fail_then_win', 'format_type': 'raw_gameplay', 'cta_style': 'direct_download'},
        ),
        _candidate(
            'cand_tiktok',
            'Game A',
            'key-tiktok',
            platform='tiktok',
            raw_payload={'hook_type': 'direct_benefit', 'format_type': 'ugc_selfie', 'cta_style': 'reward_claim'},
        ),
    ]
    cluster_result = run_clustering(candidates)

    selection_result = run_representative_selection(
        cluster_result,
        [asdict(candidate) for candidate in candidates],
    )

    concept_decision = selection_result['concept_cluster_decisions'][0]
    assert len(concept_decision.selected_asset_ids) == 2
    assert set(concept_decision.split_dimensions) >= {'hook_type', 'format_type', 'cta_style'}
    assert 'multi_representative_split' in concept_decision.selection_reason


def test_concept_cluster_selection_caps_representatives_at_three() -> None:
    candidates = [
        _candidate(
            'cand_meta',
            'Game A',
            'key-meta',
            platform='meta',
            raw_payload={'hook_type': 'fail_then_win', 'format_type': 'raw_gameplay', 'cta_style': 'direct_download'},
        ),
        _candidate(
            'cand_tiktok',
            'Game A',
            'key-tiktok',
            platform='tiktok',
            raw_payload={'hook_type': 'direct_benefit', 'format_type': 'ugc_selfie', 'cta_style': 'reward_claim'},
        ),
        _candidate(
            'cand_unity',
            'Game A',
            'key-unity',
            platform='unity',
            raw_payload={'hook_type': 'challenge', 'format_type': 'gameplay_plus_overlay', 'cta_style': 'limited_offer'},
        ),
        _candidate(
            'cand_ironsource',
            'Game A',
            'key-ironsource',
            platform='ironsource',
            raw_payload={'hook_type': 'curiosity_gap', 'format_type': 'meme_edit', 'cta_style': 'wishlist'},
        ),
    ]
    cluster_result = run_clustering(candidates)

    selection_result = run_representative_selection(
        cluster_result,
        [asdict(candidate) for candidate in candidates],
    )

    concept_decision = selection_result['concept_cluster_decisions'][0]
    assert len(concept_decision.selected_asset_ids) == 3
    assert 'representative_cap_applied' in concept_decision.selection_reason
