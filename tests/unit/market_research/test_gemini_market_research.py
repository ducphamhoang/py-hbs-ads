import json
from pathlib import Path

from hbs_ads.app.settings import AISettings
from hbs_ads.infra.ai.gemini_market_research import GeminiMarketResearchAnalyzer


def test_gemini_market_research_uses_fixture_sidecar(tmp_path: Path) -> None:
    asset_path = tmp_path / 'sample.mp4'
    asset_path.write_bytes(b'not-a-real-video')
    sidecar = asset_path.with_name(asset_path.name + '.market-analysis.json')
    sidecar.write_text(json.dumps({
        'schema_version': 'creative-analysis/v1',
        'asset_ref': 'asset_1',
        'observable': {
            'duration_seconds': 12.0,
            'aspect_ratio': '9:16',
            'scene_count_estimate': 3,
            'contains_gameplay': True,
            'gameplay_visibility': 'full',
            'creator_presence': 'none',
            'character_presence': True,
            'facecam_presence': False,
            'device_frame_presence': False,
            'text_overlay_present': True,
            'text_overlay_summary': ['Download now'],
            'voiceover_type': 'human_single',
            'audio_style': 'upbeat',
            'cta_present': True,
            'cta_text': 'Download now',
            'cta_start_seconds': 8.0,
            'cta_end_seconds': 12.0,
            'offer_present': False,
            'offer_summary': None,
            'visual_notes': 'Test payload',
        },
        'taxonomy_tags': {
            'hook_type': 'fail_then_win',
            'format_type': 'raw_gameplay',
            'core_angle': 'progression_reward',
            'emotion_target': 'satisfaction',
            'visual_device': [],
            'proof_type': 'on_screen_result',
            'cta_style': 'direct_download',
            'audience_hint': ['casual'],
            'funnel_stage_guess': 'prospecting',
        },
        'interpretation': {
            'hypothesized_strategy': 'Show payoff quickly',
            'why_it_might_work': ['Clear reward'],
            'likely_target_player': 'Casual players',
            'competitive_positioning_guess': 'Reward-forward',
            'novelty_assessment': 'low',
        },
        'evidence': [{'type': 'cta', 'start_seconds': 8.0, 'end_seconds': 12.0, 'note': 'CTA'}],
        'quality': {'analysis_confidence': 0.8, 'needs_human_review': False, 'failure_modes': []},
    }), encoding='utf-8')

    analyzer = GeminiMarketResearchAnalyzer(AISettings())
    result = analyzer.analyze_asset(asset_path=asset_path, run_id='run_1', asset_id='asset_1')
    assert result.analysis_status == 'ok'
    assert result.asset_id == 'asset_1'
    assert result.taxonomy_tags['hook_type'] == 'fail_then_win'


def test_gemini_market_research_invalid_fixture_returns_failed_validation(tmp_path: Path) -> None:
    asset_path = tmp_path / 'broken.mp4'
    asset_path.write_bytes(b'not-a-real-video')
    sidecar = asset_path.with_name(asset_path.name + '.market-analysis.json')
    sidecar.write_text(json.dumps({
        'schema_version': 'creative-analysis/v1',
        'observable': {},
        'taxonomy_tags': {},
        'interpretation': {},
        'evidence': [],
        'quality': {'analysis_confidence': 0.0, 'needs_human_review': True, 'failure_modes': []},
    }), encoding='utf-8')

    analyzer = GeminiMarketResearchAnalyzer(AISettings())
    result = analyzer.analyze_asset(asset_path=asset_path, run_id='run_1', asset_id='asset_broken')

    assert result.analysis_status == 'failed_validation'
    assert result.asset_id == 'asset_broken'
    assert result.quality['needs_human_review'] is True
