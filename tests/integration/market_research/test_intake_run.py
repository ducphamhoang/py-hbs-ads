import json
from pathlib import Path

from hbs_ads.app.settings import AISettings
from hbs_ads.features.market_research.models import MarketResearchRunRequest, ResearchBrief
from hbs_ads.features.market_research.service import MarketResearchService
from hbs_ads.infra.ai.gemini_market_research import GeminiMarketResearchAnalyzer
from hbs_ads.infra.db.market_research_sqlite import MarketResearchSQLiteDB


def test_run_from_asset_files_stages_uploaded_videos_and_completes(tmp_path: Path) -> None:
    workspace = tmp_path / 'workspace'
    workspace.mkdir()

    incoming_dir = tmp_path / 'incoming'
    incoming_dir.mkdir()
    asset_path = incoming_dir / 'discord-upload.mp4'
    asset_path.write_bytes(b'fake-video')
    fixture_path = incoming_dir / 'discord-upload.mp4.market-analysis.json'
    fixture_path.write_text(json.dumps({
        'schema_version': 'creative-analysis/v1',
        'asset_ref': 'discord-upload.mp4',
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

    artifact_root = workspace / 'logs' / 'market-research'
    service = MarketResearchService(
        workspace,
        gemini_analyzer=GeminiMarketResearchAnalyzer(AISettings()),
        db=MarketResearchSQLiteDB(artifact_root / 'research.db'),
    )
    brief = ResearchBrief(
        brief_id='brief_discord_upload',
        research_goal='Analyze uploaded creative',
        market_scope={'geos': ['US'], 'platforms': ['discord'], 'date_range': {'start': '2026-04-01', 'end': '2026-04-30'}},
        competitor_scope={'mode': 'uploaded_assets'},
        creative_scope={'asset_types': ['video']},
        analysis_focus=['hook_type', 'format_type'],
        sampling_strategy='manual_upload',
        output_mode='insight_cards',
        review_mode='human',
    )

    result = service.run_from_asset_files(
        MarketResearchRunRequest(brief=brief, workspace_path=str(workspace), operator='tester'),
        asset_paths=[asset_path],
        source='discord_upload',
        collector='discord-gateway',
        query_context={'channel': 'hbs-market', 'sender': 'Ma'},
        candidate_defaults={'platform': 'discord', 'geo': 'US', 'app_name': 'Uploaded Sample'},
    )

    assert result['status'] == 'completed'
    assert result['review_status'] == 'draft_only'
    assert result['requires_human_review'] is True
    assert result['intake_manifest_path']

    intake_manifest = Path(result['intake_manifest_path'])
    assert intake_manifest.exists()
    assert (artifact_root / 'collect' / 'assets-manifest.json').exists()
    assert (artifact_root / 'collect' / 'collection-report.json').exists()
    assert (artifact_root / 'analyze' / 'creative-analysis.jsonl').exists()
