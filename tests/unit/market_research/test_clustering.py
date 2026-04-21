from hbs_ads.features.market_research.models import AdCandidate
from hbs_ads.features.market_research.clustering import run_clustering


def _candidate(candidate_id: str, app_name: str, dedupe_key: str) -> AdCandidate:
    return AdCandidate(
        candidate_id=candidate_id,
        run_id='run_1',
        query_id='query_1',
        source='meta',
        app_name=app_name,
        platform='meta',
        asset_url=f'https://example.com/{candidate_id}.mp4',
        dedupe_key=dedupe_key,
        normalized_status='normalized',
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
