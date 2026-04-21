from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from hbs_ads.core.config import resolve_settings
from hbs_ads.core.outputs import CommandResult
from hbs_ads.core.workspace import WorkspaceManager
from hbs_ads.features.market_research.models import MarketResearchRunRequest, ResearchBrief
from hbs_ads.features.market_research.service import MarketResearchService
from hbs_ads.infra.ai.gemini_market_research import GeminiMarketResearchAnalyzer
from hbs_ads.infra.db.market_research_sqlite import MarketResearchSQLiteDB


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding='utf-8'))


def _load_brief(path: Path) -> ResearchBrief:
    payload = _load_json(path)
    return ResearchBrief(**payload)


def _parse_analysis_focus(raw: str) -> list[str] | None:
    values = [part.strip() for part in raw.split(',') if part.strip()]
    return values or None


def _result(status: str, message: str, **data: Any) -> CommandResult:
    return CommandResult(status=status, message=message, data=data)


def build_service(workspace_root: Path) -> MarketResearchService:
    settings = resolve_settings(workspace_override=workspace_root, output_mode='json')
    workspace = WorkspaceManager()
    workspace.initialize(settings)
    artifact_root = settings.workspace.root / 'logs' / 'market-research'
    db = MarketResearchSQLiteDB(artifact_root / 'research.db')
    analyzer = GeminiMarketResearchAnalyzer(settings.ai)
    return MarketResearchService(settings.workspace.root, gemini_analyzer=analyzer, db=db)


def main() -> int:
    parser = argparse.ArgumentParser(description='Run the zero-touch creative market research pilot.')
    parser.add_argument('--workspace', required=True, help='Absolute or relative workspace path')
    parser.add_argument('--brief', default='', help='Path to research brief JSON')
    parser.add_argument('--manifest', default='', help='Path to candidate manifest JSON')
    parser.add_argument(
        '--stage',
        default='run',
        choices=['run', 'brief', 'resynthesize', 'debug-asset', 'inspect-run'],
        help='Pilot stage to execute',
    )
    parser.add_argument('--source-run-id', default='', help='Existing run_id for readback/resynthesis/inspection')
    parser.add_argument('--asset-path', default='', help='Asset path for debug-asset stage')
    parser.add_argument('--asset-id', default='', help='Asset id for debug-asset stage')
    parser.add_argument('--variant-cluster-id', default='', help='Optional variant cluster id for debug-asset stage')
    parser.add_argument('--analysis-focus', default='', help='Comma-separated analysis focus for debug-asset stage')
    args = parser.parse_args()

    workspace_root = Path(args.workspace).expanduser().resolve()
    brief_path = Path(args.brief).expanduser().resolve() if args.brief else None
    manifest_path = Path(args.manifest).expanduser().resolve() if args.manifest else None

    service = build_service(workspace_root)
    brief = _load_brief(brief_path) if brief_path else None

    if args.stage == 'brief':
        if brief is None:
            raise ValueError('--brief is required for stage=brief')
        output_path = service.store_brief(brief)
        result = _result('ok', 'brief stored', brief_path=str(output_path))
    elif args.stage == 'resynthesize':
        if brief is None:
            raise ValueError('--brief is required for stage=resynthesize')
        report = service.re_synthesize_from_saved_analyses(
            brief,
            source_run_id=args.source_run_id,
            operator='runner',
        )
        payload = dict(report)
        payload.pop('status', None)
        result = _result('ok', 'market research re-synthesis completed', **payload)
    elif args.stage == 'debug-asset':
        if not args.asset_path or not args.asset_id:
            raise ValueError('--asset-path and --asset-id are required for stage=debug-asset')
        debug_result = service.debug_asset(
            asset_path=Path(args.asset_path).expanduser().resolve(),
            run_id=args.source_run_id or service.load_run_state().get('run_id', ''),
            asset_id=args.asset_id,
            variant_cluster_id=args.variant_cluster_id,
            analysis_focus=_parse_analysis_focus(args.analysis_focus),
        )
        result = _result('ok', 'asset debug analysis completed', analysis=asdict(debug_result))
    elif args.stage == 'inspect-run':
        target_run_id = args.source_run_id or service.load_run_state().get('run_id', '')
        db_run = service.db.get_run(target_run_id) if service.db is not None and hasattr(service.db, 'get_run') else None
        analyses = service.load_analyses(run_id=target_run_id, from_db=service.db is not None)
        insights = service.load_insights(run_id=target_run_id, from_db=service.db is not None)
        reviews = service.load_reviews(run_id=target_run_id, from_db=service.db is not None)
        payload = {
            'run': db_run,
            'analysis_count': len(analyses),
            'insight_count': len(insights),
            'review_count': len(reviews),
            'analysis_statuses': sorted({analysis.analysis_status for analysis in analyses}),
            'insight_statuses': sorted({insight.status for insight in insights}),
            'failures': service.load_failures(),
        }
        result = _result('ok', 'market research run inspected', **payload)
    else:
        if brief is None:
            raise ValueError('--brief is required for stage=run')
        request = MarketResearchRunRequest(
            brief=brief,
            workspace_path=str(workspace_root),
            manifest_path=str(manifest_path) if manifest_path else '',
            stage='all',
            operator='runner',
        )
        run_result = service.run(request)
        payload = dict(run_result)
        payload.pop('status', None)
        result = _result('ok', 'market research run completed', **payload)

    print(json.dumps(asdict(result), indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
