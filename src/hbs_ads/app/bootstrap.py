from __future__ import annotations

from dataclasses import dataclass
import logging
import os

from hbs_ads.app.settings import ResolvedSettings
from hbs_ads.core.config import load_dotenv_file, resolve_settings
from hbs_ads.core.workspace import WorkspaceManager
from hbs_ads.features.assets.service import AssetsService
from hbs_ads.features.bootstrap.service import BootstrapService
from hbs_ads.features.competitor.service import CompetitorService
from hbs_ads.features.hooks.service import HooksService
from hbs_ads.features.ingest.service import IngestService
from hbs_ads.features.notify.service import NotifyService
from hbs_ads.features.perf.service import PerfService
from hbs_ads.features.pipeline.service import PipelineService
from hbs_ads.features.sharepoint.service import SharePointService
from hbs_ads.features.tagging.service import TaggingService
from hbs_ads.features.teams.service import TeamsService
from hbs_ads.features.trim.service import TrimService
from hbs_ads.features.variants.service import VariantsService
from hbs_ads.features.voiceover.service import VoiceoverService
from hbs_ads.infra.ai.gemini import GeminiClipAnalyzer
from hbs_ads.infra.db.sqlite import SQLiteDatabase
from hbs_ads.infra.exec.runner import CommandRunner
from hbs_ads.infra.sharepoint import FileBackedSharePointClient, M365SharePointClient
from hbs_ads.infra.teams import DirectGraphTeamsClient, M365TeamsClient


@dataclass(slots=True)
class AppServices:
    settings: ResolvedSettings
    workspace: WorkspaceManager
    command_runner: CommandRunner
    bootstrap: BootstrapService
    assets: AssetsService
    ingest: IngestService
    trim: TrimService
    tagging: TaggingService
    variants: VariantsService
    hooks: HooksService
    pipeline: PipelineService
    sharepoint: SharePointService
    teams: TeamsService
    competitor: CompetitorService
    perf: PerfService
    notify: NotifyService
    voiceover: VoiceoverService


def build_app(
    workspace_override: str | None = None,
    output_mode: str = "text",
) -> AppServices:
    settings = resolve_settings(workspace_override=workspace_override, output_mode=output_mode)
    workspace = WorkspaceManager()
    command_runner = CommandRunner()
    database = SQLiteDatabase(settings.database.path)
    clip_analyzer = GeminiClipAnalyzer(settings.ai)
    if settings.sharepoint.site_url and settings.sharepoint.tenant_id:
        sharepoint_client = M365SharePointClient(settings=settings, command_runner=command_runner)
    else:
        sharepoint_client = FileBackedSharePointClient(settings=settings)
    try:
        database.bootstrap()
    except Exception as exc:
        logging.getLogger(__name__).error("Database bootstrap failed: %s", exc)
        raise RuntimeError(f"Failed to initialise database at {settings.database.path}: {exc}") from exc
    bootstrap = BootstrapService(settings=settings, workspace=workspace, database=database)
    assets = AssetsService(workspace=workspace, settings=settings)
    ingest = IngestService(settings=settings, workspace=workspace, database=database)
    trim = TrimService(
        settings=settings,
        workspace=workspace,
        database=database,
        command_runner=command_runner,
    )
    tagging = TaggingService(database=database, analyzer=clip_analyzer)
    variants = VariantsService(
        settings=settings,
        workspace=workspace,
        database=database,
        command_runner=command_runner,
    )
    hooks = HooksService(settings=settings, workspace=workspace, database=database)
    sharepoint = SharePointService(settings=settings, workspace=workspace, client=sharepoint_client)
    graph_access_token = os.environ.get("HBS_ADS_GRAPH_ACCESS_TOKEN", "").strip()
    if not graph_access_token:
        graph_access_token = load_dotenv_file(settings.workspace.root / ".env").get("HBS_ADS_GRAPH_ACCESS_TOKEN", "").strip()
    if graph_access_token:
        teams_client = DirectGraphTeamsClient(settings=settings, access_token=graph_access_token)
    else:
        teams_client = M365TeamsClient(settings=settings, command_runner=command_runner)
    teams = TeamsService(
        settings=settings,
        workspace=workspace,
        client=teams_client,
    )
    competitor = CompetitorService(settings=settings, workspace=workspace, database=database)
    perf = PerfService(settings=settings, workspace=workspace)
    notify = NotifyService(settings=settings, workspace=workspace)
    voiceover = VoiceoverService(
        settings=settings,
        workspace=workspace,
        command_runner=command_runner,
    )
    pipeline = PipelineService(
        ingest=ingest,
        trim=trim,
        tagging=tagging,
        variants=variants,
        hooks=hooks,
    )
    return AppServices(
        settings=settings,
        workspace=workspace,
        command_runner=command_runner,
        bootstrap=bootstrap,
        assets=assets,
        ingest=ingest,
        trim=trim,
        tagging=tagging,
        variants=variants,
        hooks=hooks,
        pipeline=pipeline,
        sharepoint=sharepoint,
        teams=teams,
        competitor=competitor,
        perf=perf,
        notify=notify,
        voiceover=voiceover,
    )
