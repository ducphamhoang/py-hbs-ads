from hbs_ads.features.market_research.normalization import normalize_candidates


def test_normalize_candidates_standardizes_platform_and_geo() -> None:
    raw = [{
        'source': 'facebook',
        'id': '123',
        'app_name': 'My Game',
        'publisher_name': 'Studio',
        'geo': 'us',
        'platform': 'ig',
        'asset_url': 'https://example.com/video.mp4',
        'first_seen_at': '2026-04-01',
    }]
    candidates = normalize_candidates('run_1', 'query_1', raw)
    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.source == 'meta'
    assert candidate.platform == 'meta'
    assert candidate.geo == 'US'
    assert candidate.normalized_status == 'normalized'
    assert candidate.dedupe_key
