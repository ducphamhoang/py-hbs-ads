import json
import sqlite3
from pathlib import Path

from hbs_ads.app.settings import AISettings
from hbs_ads.features.market_research.models import MarketResearchRunRequest, ResearchBrief
from hbs_ads.features.market_research.service import MarketResearchService
from hbs_ads.infra.ai.gemini_market_research import GeminiMarketResearchAnalyzer
from hbs_ads.infra.db.market_research_sqlite import MarketResearchSQLiteDB


def _make_brief(brief_id: str, *, analysis_focus: list[str] | None = None) -> ResearchBrief:
    return ResearchBrief(
        brief_id=brief_id,
        research_goal='Find hook patterns',
        market_scope={'geos': ['US'], 'platforms': ['meta'], 'date_range': {'start': '2026-04-01', 'end': '2026-04-30'}},
        competitor_scope={'mode': 'broad_market'},
        creative_scope={'asset_types': ['video']},
        analysis_focus=analysis_focus or ['hook_type', 'format_type'],
        sampling_strategy='recent',
        output_mode='insight_cards',
        review_mode='human',
    )


def _write_valid_fixture(sidecar: Path) -> None:
    sidecar.write_text(json.dumps({
        'schema_version': 'creative-analysis/v1',
        'asset_ref': sidecar.stem,
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


def _build_service_with_completed_run(tmp_path: Path) -> tuple[MarketResearchService, Path, dict[str, object]]:
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
        _write_valid_fixture(asset_path.with_name(asset_path.name + '.market-analysis.json'))

    artifact_root = workspace / 'logs' / 'market-research'
    service = MarketResearchService(
        workspace,
        gemini_analyzer=GeminiMarketResearchAnalyzer(AISettings()),
        db=MarketResearchSQLiteDB(artifact_root / 'research.db'),
    )
    result = service.run(
        MarketResearchRunRequest(
            brief=_make_brief('brief_initial'),
            workspace_path=str(workspace),
            manifest_path=str(manifest_path),
            operator='tester',
        )
    )
    return service, artifact_root, result


def test_re_synthesize_from_saved_analyses_creates_new_draft_run(tmp_path: Path) -> None:
    service, artifact_root, initial_result = _build_service_with_completed_run(tmp_path)

    rerun = service.re_synthesize_from_saved_analyses(
        _make_brief('brief_resynth', analysis_focus=['format_type']),
        source_run_id=initial_result['run_id'],
        operator='resynth-tester',
    )

    assert rerun['status'] == 'completed'
    assert rerun['source_run_id'] == initial_result['run_id']
    assert rerun['review_status'] == 'draft_only'
    assert rerun['requires_human_review'] is True
    assert rerun['insight_count'] > 0

    with sqlite3.connect(artifact_root / 'research.db') as conn:
        rerun_row = conn.execute(
            'SELECT brief_id, status, operator FROM mr_run WHERE run_id = ?',
            (rerun['run_id'],),
        ).fetchone()
        insight_rows = conn.execute(
            'SELECT status, needs_human_review FROM mr_insight_candidate WHERE run_id = ? ORDER BY insight_candidate_id',
            (rerun['run_id'],),
        ).fetchall()

    assert rerun_row == ('brief_resynth', 'resynthesized', 'resynth-tester')
    assert insight_rows
    assert {row[0] for row in insight_rows} == {'draft'}
    assert {row[1] for row in insight_rows} == {1}


def test_debug_asset_writes_explicit_failed_validation_artifact(tmp_path: Path) -> None:
    service, artifact_root, initial_result = _build_service_with_completed_run(tmp_path)

    broken_asset = tmp_path / 'workspace' / 'broken.mp4'
    broken_asset.write_bytes(b'fake-video')
    broken_sidecar = broken_asset.with_name(broken_asset.name + '.market-analysis.json')
    broken_sidecar.write_text(json.dumps({
        'schema_version': 'creative-analysis/v1',
        'observable': {},
        'taxonomy_tags': {},
        'interpretation': {},
        'evidence': [],
        'quality': {'analysis_confidence': 0.0, 'needs_human_review': True, 'failure_modes': []},
    }), encoding='utf-8')

    result = service.debug_asset(
        asset_path=broken_asset,
        run_id=initial_result['run_id'],
        asset_id='asset_broken',
        variant_cluster_id='vcl_debug',
    )

    assert result.analysis_status == 'failed_validation'
    debug_artifact = artifact_root / 'debug' / 'asset_broken.debug-analysis.json'
    assert debug_artifact.exists()

    payload = json.loads(debug_artifact.read_text(encoding='utf-8'))
    assert payload['analysis_status'] == 'failed_validation'
    assert payload['variant_cluster_id'] == 'vcl_debug'


def test_readback_helpers_expose_run_and_analysis_state(tmp_path: Path) -> None:
    service, artifact_root, initial_result = _build_service_with_completed_run(tmp_path)

    analyses = service.load_analyses(run_id=initial_result['run_id'], from_db=True, analysis_status='ok')
    runs = service.db.list_runs() if service.db is not None else []
    run = service.db.get_run(initial_result['run_id']) if service.db is not None else None
    failures = service.load_failures()

    assert analyses
    assert all(analysis.analysis_status == 'ok' for analysis in analyses)
    assert run is not None
    assert run['run_id'] == initial_result['run_id']
    assert any(item['run_id'] == initial_result['run_id'] for item in runs)
    assert failures == []
