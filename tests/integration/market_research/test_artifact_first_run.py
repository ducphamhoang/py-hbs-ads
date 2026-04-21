import json
import sqlite3
from pathlib import Path

from hbs_ads.app.settings import AISettings
from hbs_ads.features.market_research.models import MarketResearchRunRequest, ResearchBrief
from hbs_ads.features.market_research.service import MarketResearchService
from hbs_ads.infra.ai.gemini_market_research import GeminiMarketResearchAnalyzer
from hbs_ads.infra.db.market_research_sqlite import MarketResearchSQLiteDB


def test_artifact_first_run_writes_artifacts_and_db(tmp_path: Path) -> None:
    workspace = tmp_path / 'workspace'
    workspace.mkdir()
    manifest_path = workspace / 'manifest.json'
    manifest_path.write_text(json.dumps([
        {
            'source': 'facebook',
            'id': 'ad-1',
            'app_name': 'Game One',
            'publisher_name': 'Studio One',
            'geo': 'US',
            'platform': 'facebook',
            'asset_url': str(workspace / 'asset-one.mp4'),
            'first_seen_at': '2026-04-01',
            'last_seen_at': '2026-04-02',
        },
        {
            'source': 'facebook',
            'id': 'ad-2',
            'app_name': 'Game One',
            'publisher_name': 'Studio One',
            'geo': 'US',
            'platform': 'facebook',
            'asset_url': str(workspace / 'asset-two.mp4'),
            'first_seen_at': '2026-04-03',
            'last_seen_at': '2026-04-04',
        },
    ]), encoding='utf-8')

    for asset_name in ['asset-one.mp4', 'asset-two.mp4']:
        asset_path = workspace / asset_name
        asset_path.write_bytes(b'fake-video')
        sidecar = asset_path.with_name(asset_path.name + '.market-analysis.json')
        sidecar.write_text(json.dumps({
            'schema_version': 'creative-analysis/v1',
            'asset_ref': asset_name,
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
                'text_overlay_summary': ['Play now'],
                'voiceover_type': 'human_single',
                'audio_style': 'upbeat',
                'cta_present': True,
                'cta_text': 'Play now',
                'cta_start_seconds': 8.0,
                'cta_end_seconds': 12.0,
                'offer_present': False,
                'offer_summary': None,
                'visual_notes': 'Fixture',
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
                'hypothesized_strategy': 'Reward fast',
                'why_it_might_work': ['Fast payoff'],
                'likely_target_player': 'Casual',
                'competitive_positioning_guess': 'Reward-first',
                'novelty_assessment': 'low',
            },
            'evidence': [{'type': 'hook', 'start_seconds': 0.0, 'end_seconds': 2.0, 'note': 'Hook'}],
            'quality': {'analysis_confidence': 0.8, 'needs_human_review': False, 'failure_modes': []},
        }), encoding='utf-8')

    brief = ResearchBrief(
        brief_id='brief_idle_us',
        research_goal='Find hook patterns',
        market_scope={'geos': ['US'], 'platforms': ['meta'], 'date_range': {'start': '2026-04-01', 'end': '2026-04-30'}},
        competitor_scope={'mode': 'broad_market'},
        creative_scope={'asset_types': ['video']},
        analysis_focus=['hook_type', 'format_type'],
        sampling_strategy='recent',
        output_mode='insight_cards',
        review_mode='human',
    )

    artifact_root = workspace / 'logs' / 'market-research'
    service = MarketResearchService(
        workspace,
        gemini_analyzer=GeminiMarketResearchAnalyzer(AISettings()),
        db=MarketResearchSQLiteDB(artifact_root / 'research.db'),
    )
    result = service.run(MarketResearchRunRequest(brief=brief, workspace_path=str(workspace), manifest_path=str(manifest_path), operator='tester'))

    assert result['status'] == 'completed'
    assert result['review_status'] == 'draft_only'
    assert result['requires_human_review'] is True
    assert (artifact_root / 'brief.json').exists()
    assert (artifact_root / 'normalize' / 'candidates.normalized.json').exists()
    assert (artifact_root / 'cluster' / 'variant-clusters.json').exists()
    assert (artifact_root / 'analyze' / 'creative-analysis.jsonl').exists()
    assert (artifact_root / 'synthesize' / 'insight-candidates.json').exists()
    assert (artifact_root / 'sync' / 'sync-report.json').exists()
    assert (artifact_root / 'research.db').exists()

    variant_clusters = json.loads((artifact_root / 'cluster' / 'variant-clusters.json').read_text(encoding='utf-8'))
    assert len(variant_clusters) == 1
    expected_variant_cluster_id = variant_clusters[0]['variant_cluster_id']

    with sqlite3.connect(artifact_root / 'research.db') as conn:
        run_row = conn.execute(
            "SELECT brief_id, status, operator, finished_at FROM mr_run WHERE run_id = ?",
            (result['run_id'],),
        ).fetchone()
        assert run_row == (brief.brief_id, 'completed', 'tester', result['sync_report']['created_at'])

        analysis_rows = conn.execute(
            "SELECT analysis_id, variant_cluster_id, analysis_status FROM mr_creative_analysis ORDER BY analysis_id"
        ).fetchall()

    assert analysis_rows
    assert {row[1] for row in analysis_rows} == {expected_variant_cluster_id}
    assert {row[2] for row in analysis_rows} == {'ok'}
