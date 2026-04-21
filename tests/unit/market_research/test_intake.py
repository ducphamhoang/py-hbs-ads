import json
from pathlib import Path

from hbs_ads.features.market_research.intake import intake_asset_files


def test_intake_asset_files_stages_assets_and_writes_manifest(tmp_path: Path) -> None:
    workspace = tmp_path / 'workspace'
    workspace.mkdir()
    source_asset = tmp_path / 'incoming-video.mp4'
    source_asset.write_bytes(b'video-bytes')

    result = intake_asset_files(
        workspace_path=workspace,
        run_id='run_1',
        asset_paths=[source_asset],
        source='discord_upload',
        collector='discord-gateway',
        query_context={'channel': 'hbs-market'},
        candidate_defaults={
            'platform': 'discord',
            'geo': 'US',
            'app_name': 'Uploaded Sample',
        },
    )

    manifest_path = Path(result['manifest_path'])
    assert manifest_path.exists()

    payload = json.loads(manifest_path.read_text(encoding='utf-8'))
    assert payload['schema_version'] == 'market-collection-handoff/v1'
    assert payload['run_context']['run_id'] == 'run_1'
    assert payload['run_context']['source'] == 'discord_upload'
    assert payload['run_context']['collector'] == 'discord-gateway'
    assert len(payload['candidates']) == 1
    candidate = payload['candidates'][0]
    assert candidate['source'] == 'discord_upload'
    assert candidate['platform'] == 'discord'
    assert candidate['geo'] == 'US'
    assert candidate['app_name'] == 'Uploaded Sample'
    assert candidate['asset_url'].startswith(str(workspace / 'logs' / 'market-research' / 'collect' / 'assets'))
    assert Path(candidate['asset_url']).exists()

    assets_manifest = workspace / 'logs' / 'market-research' / 'collect' / 'assets-manifest.json'
    collection_report = workspace / 'logs' / 'market-research' / 'collect' / 'collection-report.json'
    assert assets_manifest.exists()
    assert collection_report.exists()
