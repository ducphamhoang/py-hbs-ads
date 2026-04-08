from __future__ import annotations

import argparse
from pathlib import Path

from hbs_ads.app.bootstrap import AppServices
from hbs_ads.core.outputs import CommandResult
from hbs_ads.features.assets.service import ListAssetsRequest
from hbs_ads.features.bootstrap.service import InitDBRequest, InitWorkspaceRequest
from hbs_ads.features.competitor.service import AnalyzeCompetitorRequest, CompetitorReportRequest
from hbs_ads.features.hooks.service import AssembleHookRequest
from hbs_ads.features.ingest.service import (
    IngestCronRequest,
    IngestRunRequest,
    IngestWatchRequest,
)
from hbs_ads.features.notify.service import NotifyProgressRequest, NotifyRenderDoneRequest
from hbs_ads.features.perf.service import PerfIngestRequest, PerfReportRequest
from hbs_ads.features.pipeline.service import PipelineRunRequest
from hbs_ads.features.sharepoint.service import (
    SharePointDownloadRequest,
    SharePointListRequest,
    SharePointSetupRequest,
    SharePointUploadRequest,
)
from hbs_ads.features.tagging.service import (
    ApproveTagsRequest,
    AutoTagRequest,
    PendingTagsRequest,
    TagAIRequest,
)
from hbs_ads.features.trim.service import TrimClipRequest, TrimRunRequest
from hbs_ads.features.variants.service import (
    ArchiveVariantRequest,
    AssembleVariantRequest,
    ExportVariantRequest,
    GenerateVariantsRequest,
    ValidateVariantRequest,
)
from hbs_ads.features.voiceover.service import GenerateVoiceoverRequest


def _root_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hbs-ads", description="hbs-ads Python CLI")
    parser.add_argument(
        "--workspace",
        default=".",
        help="Workspace root override for commands that operate on a workspace.",
    )
    parser.add_argument(
        "--output",
        choices=["text", "json", "quiet"],
        default="text",
        help="Output rendering mode.",
    )
    parser.add_argument(
        "--json",
        dest="output",
        action="store_const",
        const="json",
        help="Shortcut for --output json.",
    )
    return parser


def _workspace_path(args: argparse.Namespace) -> Path:
    return Path(args.workspace).resolve()


def _add_common_dry_run(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--dry-run", action="store_true", help="Preview without mutating state.")


def _result(handler):
    return handler


def build_parser() -> argparse.ArgumentParser:
    parser = _root_parser()
    subparsers = parser.add_subparsers(dest="command")

    init_parser = subparsers.add_parser("init", help="Workspace and database bootstrap commands.")
    init_sub = init_parser.add_subparsers(dest="action")

    init_workspace = init_sub.add_parser("workspace", help="Initialize a workspace.")
    init_workspace.set_defaults(
        handler=_result(
            lambda args, app: app.bootstrap.init_workspace(
                InitWorkspaceRequest(workspace_root=_workspace_path(args))
            )
        )
    )

    init_db = init_sub.add_parser("db", help="Initialize or migrate the local database.")
    init_db.add_argument("--migrate", action="store_true", help="Run migrations if supported.")
    init_db.set_defaults(
        handler=_result(
            lambda args, app: app.bootstrap.init_db(
                InitDBRequest(workspace_root=_workspace_path(args), migrate=args.migrate)
            )
        )
    )

    assets_parser = subparsers.add_parser("assets", help="Asset inventory commands.")
    assets_sub = assets_parser.add_subparsers(dest="action")
    assets_list = assets_sub.add_parser("list", help="List assets by inventory scope.")
    for flag in ["raw", "trimmed", "hooks", "variants"]:
        assets_list.add_argument(f"--{flag}", action="store_true", help=f"Show {flag} assets only.")
    assets_list.set_defaults(
        handler=_result(
            lambda args, app: app.assets.list_assets(
                ListAssetsRequest(
                    workspace_root=_workspace_path(args),
                    raw=args.raw,
                    trimmed=args.trimmed,
                    hooks=args.hooks,
                    variants=args.variants,
                )
            )
        )
    )

    ingest_parser = subparsers.add_parser("ingest", help="Ingest workflows.")
    ingest_sub = ingest_parser.add_subparsers(dest="action")
    ingest_run = ingest_sub.add_parser("run", help="Run ingest once.")
    _add_common_dry_run(ingest_run)
    ingest_run.set_defaults(
        handler=_result(
            lambda args, app: app.ingest.run(
                IngestRunRequest(workspace_root=_workspace_path(args), dry_run=args.dry_run)
            )
        )
    )
    ingest_watch = ingest_sub.add_parser("watch", help="Watch inbox for new ingest work.")
    ingest_watch.set_defaults(
        handler=_result(
            lambda args, app: app.ingest.watch(IngestWatchRequest(workspace_root=_workspace_path(args)))
        )
    )
    ingest_cron = ingest_sub.add_parser("cron", help="Manage ingest cron workflows.")
    ingest_cron_sub = ingest_cron.add_subparsers(dest="cron_action")
    for action in ("install", "remove"):
        cron_cmd = ingest_cron_sub.add_parser(action, help=f"{action.title()} ingest cron workflow.")
        cron_cmd.set_defaults(
            handler=_result(
                lambda args, app, action=action: app.ingest.cron(
                    IngestCronRequest(workspace_root=_workspace_path(args), action=action)
                )
            )
        )

    trim_parser = subparsers.add_parser("trim", help="Trim workflows.")
    trim_sub = trim_parser.add_subparsers(dest="action")
    trim_run = trim_sub.add_parser("run", help="Run trim workflow from config.")
    trim_run.add_argument("--config", default="cuts.json", help="Cuts config path.")
    _add_common_dry_run(trim_run)
    trim_run.set_defaults(
        handler=_result(
            lambda args, app: app.trim.run(
                TrimRunRequest(
                    workspace_root=_workspace_path(args),
                    config_path=Path(args.config),
                    dry_run=args.dry_run,
                )
            )
        )
    )
    trim_clip = trim_sub.add_parser("clip", help="Trim a single clip.")
    trim_clip.add_argument("--input", required=True, help="Input media path.")
    trim_clip.add_argument("--from", dest="start", required=True, help="Start timestamp.")
    trim_clip.add_argument("--to", dest="end", required=True, help="End timestamp.")
    trim_clip.add_argument("--name", required=True, help="Clip name.")
    _add_common_dry_run(trim_clip)
    trim_clip.set_defaults(
        handler=_result(
            lambda args, app: app.trim.clip(
                TrimClipRequest(
                    workspace_root=_workspace_path(args),
                    input_path=Path(args.input),
                    start=args.start,
                    end=args.end,
                    name=args.name,
                    dry_run=args.dry_run,
                )
            )
        )
    )

    tag_parser = subparsers.add_parser("tag", help="Tagging workflows.")
    tag_sub = tag_parser.add_subparsers(dest="action")
    tag_auto = tag_sub.add_parser("auto", help="Run heuristic tagging.")
    tag_auto.set_defaults(
        handler=_result(lambda args, app: app.tagging.auto(AutoTagRequest(workspace_root=_workspace_path(args))))
    )
    tag_ai = tag_sub.add_parser("ai", help="Run AI-assisted tagging.")
    tag_ai.add_argument("--only-low-confidence", action="store_true")
    tag_ai.set_defaults(
        handler=_result(
            lambda args, app: app.tagging.ai(
                TagAIRequest(
                    workspace_root=_workspace_path(args),
                    only_low_confidence=args.only_low_confidence,
                )
            )
        )
    )
    tag_approve = tag_sub.add_parser("approve", help="Approve tagged clips.")
    tag_approve.add_argument("--all", action="store_true", dest="approve_all")
    tag_approve.set_defaults(
        handler=_result(
            lambda args, app: app.tagging.approve(
                ApproveTagsRequest(
                    workspace_root=_workspace_path(args),
                    approve_all=args.approve_all,
                )
            )
        )
    )
    tag_pending = tag_sub.add_parser("pending", help="List pending tags.")
    tag_pending.set_defaults(
        handler=_result(
            lambda args, app: app.tagging.pending(PendingTagsRequest(workspace_root=_workspace_path(args)))
        )
    )

    variants_parser = subparsers.add_parser("variants", help="Variant generation workflows.")
    variants_sub = variants_parser.add_subparsers(dest="action")
    variants_generate = variants_sub.add_parser("generate", help="Generate creative variants.")
    variants_generate.add_argument("--max-body", type=int, default=None)
    _add_common_dry_run(variants_generate)
    variants_generate.set_defaults(
        handler=_result(
            lambda args, app: app.variants.generate(
                GenerateVariantsRequest(
                    workspace_root=_workspace_path(args),
                    max_body=args.max_body,
                    dry_run=args.dry_run,
                )
            )
        )
    )
    variants_assemble = variants_sub.add_parser("assemble", help="Assemble variants from config.")
    variants_assemble.add_argument("--config", required=True)
    _add_common_dry_run(variants_assemble)
    variants_assemble.set_defaults(
        handler=_result(
            lambda args, app: app.variants.assemble(
                AssembleVariantRequest(
                    workspace_root=_workspace_path(args),
                    config_path=Path(args.config),
                    dry_run=args.dry_run,
                )
            )
        )
    )
    variants_export = variants_sub.add_parser("export", help="Export a built variant.")
    variants_export.add_argument("--variant", required=True)
    _add_common_dry_run(variants_export)
    variants_export.set_defaults(
        handler=_result(
            lambda args, app: app.variants.export(
                ExportVariantRequest(
                    workspace_root=_workspace_path(args),
                    variant=args.variant,
                    dry_run=args.dry_run,
                )
            )
        )
    )
    variants_validate = variants_sub.add_parser("validate", help="Validate a variant.")
    variants_validate.add_argument("--platform", default="generic")
    variants_validate.set_defaults(
        handler=_result(
            lambda args, app: app.variants.validate(
                ValidateVariantRequest(
                    workspace_root=_workspace_path(args),
                    platform=args.platform,
                )
            )
        )
    )
    variants_archive = variants_sub.add_parser("archive", help="Archive a variant.")
    variants_archive.add_argument("--variant", required=True)
    _add_common_dry_run(variants_archive)
    variants_archive.set_defaults(
        handler=_result(
            lambda args, app: app.variants.archive(
                ArchiveVariantRequest(
                    workspace_root=_workspace_path(args),
                    variant=args.variant,
                    dry_run=args.dry_run,
                )
            )
        )
    )

    hooks_parser = subparsers.add_parser("hooks", help="Hook assembly workflows.")
    hooks_sub = hooks_parser.add_subparsers(dest="action")
    hooks_assemble = hooks_sub.add_parser("assemble", help="Assemble a hook asset.")
    hooks_assemble.add_argument("--name", required=False, default="")
    _add_common_dry_run(hooks_assemble)
    hooks_assemble.set_defaults(
        handler=_result(
            lambda args, app: app.hooks.assemble(
                AssembleHookRequest(
                    workspace_root=_workspace_path(args),
                    name=args.name,
                    dry_run=args.dry_run,
                )
            )
        )
    )

    pipeline_parser = subparsers.add_parser("pipeline", help="Pipeline orchestration workflows.")
    pipeline_sub = pipeline_parser.add_subparsers(dest="action")
    pipeline_run = pipeline_sub.add_parser("run", help="Run the common pipeline.")
    for flag in ("trim", "ingest"):
        pipeline_run.add_argument(f"--{flag}", action="store_true")
    _add_common_dry_run(pipeline_run)
    pipeline_run.set_defaults(
        handler=_result(
            lambda args, app: app.pipeline.run(
                PipelineRunRequest(
                    workspace_root=_workspace_path(args),
                    trim_only=args.trim,
                    ingest_only=args.ingest,
                    dry_run=args.dry_run,
                )
            )
        )
    )

    sharepoint_parser = subparsers.add_parser("sharepoint", help="SharePoint workflows.")
    sharepoint_sub = sharepoint_parser.add_subparsers(dest="action")
    sharepoint_setup = sharepoint_sub.add_parser("setup", help="Configure SharePoint access.")
    sharepoint_setup.set_defaults(
        handler=_result(
            lambda args, app: app.sharepoint.setup(
                SharePointSetupRequest(workspace_root=_workspace_path(args))
            )
        )
    )
    sharepoint_list = sharepoint_sub.add_parser("list", help="List remote SharePoint files.")
    sharepoint_list.add_argument("--query", "--variant", dest="query", default="")
    sharepoint_list.set_defaults(
        handler=_result(
            lambda args, app: app.sharepoint.list(
                SharePointListRequest(
                    workspace_root=_workspace_path(args),
                    query=args.query,
                )
            )
        )
    )
    sharepoint_upload = sharepoint_sub.add_parser("upload", help="Upload a file to SharePoint.")
    sharepoint_upload.add_argument("--file", required=True)
    sharepoint_upload.add_argument("--variant", required=True)
    _add_common_dry_run(sharepoint_upload)
    sharepoint_upload.set_defaults(
        handler=_result(
            lambda args, app: app.sharepoint.upload(
                SharePointUploadRequest(
                    workspace_root=_workspace_path(args),
                    file_path=Path(args.file),
                    variant=args.variant,
                    dry_run=args.dry_run,
                )
            )
        )
    )
    sharepoint_download = sharepoint_sub.add_parser("download", help="Download from SharePoint.")
    sharepoint_download.add_argument("--variant", "--query", dest="variant", required=False, default="")
    sharepoint_download.add_argument("--file", dest="file_url", required=False, default="")
    sharepoint_download.add_argument("--dest", required=False, default="")
    _add_common_dry_run(sharepoint_download)
    sharepoint_download.set_defaults(
        handler=_result(
            lambda args, app: app.sharepoint.download(
                SharePointDownloadRequest(
                    workspace_root=_workspace_path(args),
                    variant=args.variant,
                    file_url=args.file_url,
                    destination_dir=Path(args.dest) if args.dest else None,
                    dry_run=args.dry_run,
                )
            )
        )
    )

    competitor_parser = subparsers.add_parser("competitor", help="Competitor intelligence workflows.")
    competitor_sub = competitor_parser.add_subparsers(dest="action")
    competitor_analyze = competitor_sub.add_parser("analyze", help="Analyze competitor assets.")
    _add_common_dry_run(competitor_analyze)
    competitor_analyze.set_defaults(
        handler=_result(
            lambda args, app: app.competitor.analyze(
                AnalyzeCompetitorRequest(workspace_root=_workspace_path(args), dry_run=args.dry_run)
            )
        )
    )
    competitor_report = competitor_sub.add_parser("report", help="Generate competitor report.")
    competitor_report.set_defaults(
        handler=_result(
            lambda args, app: app.competitor.report(
                CompetitorReportRequest(workspace_root=_workspace_path(args))
            )
        )
    )

    perf_parser = subparsers.add_parser("perf", help="Performance ingestion and reporting.")
    perf_sub = perf_parser.add_subparsers(dest="action")
    perf_ingest = perf_sub.add_parser("ingest", help="Ingest performance CSVs.")
    _add_common_dry_run(perf_ingest)
    perf_ingest.set_defaults(
        handler=_result(
            lambda args, app: app.perf.ingest(
                PerfIngestRequest(workspace_root=_workspace_path(args), dry_run=args.dry_run)
            )
        )
    )
    perf_report = perf_sub.add_parser("report", help="Generate performance report.")
    perf_report.set_defaults(
        handler=_result(
            lambda args, app: app.perf.report(PerfReportRequest(workspace_root=_workspace_path(args)))
        )
    )

    notify_parser = subparsers.add_parser("notify", help="Notification workflows.")
    notify_sub = notify_parser.add_subparsers(dest="action")
    notify_render_done = notify_sub.add_parser("render-done", help="Send render-done notification.")
    notify_render_done.add_argument("--variant", required=False, default="")
    _add_common_dry_run(notify_render_done)
    notify_render_done.set_defaults(
        handler=_result(
            lambda args, app: app.notify.render_done(
                NotifyRenderDoneRequest(
                    workspace_root=_workspace_path(args),
                    variant=args.variant,
                    dry_run=args.dry_run,
                )
            )
        )
    )
    notify_progress = notify_sub.add_parser("progress", help="Send progress notification.")
    notify_progress.add_argument("--message", required=False, default="")
    _add_common_dry_run(notify_progress)
    notify_progress.set_defaults(
        handler=_result(
            lambda args, app: app.notify.progress(
                NotifyProgressRequest(
                    workspace_root=_workspace_path(args),
                    message=args.message,
                    dry_run=args.dry_run,
                )
            )
        )
    )

    voiceover_parser = subparsers.add_parser("voiceover", help="Voiceover workflows.")
    voiceover_sub = voiceover_parser.add_subparsers(dest="action")
    voiceover_generate = voiceover_sub.add_parser("generate", help="Generate voiceover assets.")
    voiceover_generate.add_argument("--script", required=False, default="")
    _add_common_dry_run(voiceover_generate)
    voiceover_generate.set_defaults(
        handler=_result(
            lambda args, app: app.voiceover.generate(
                GenerateVoiceoverRequest(
                    workspace_root=_workspace_path(args),
                    script=args.script,
                    dry_run=args.dry_run,
                )
            )
        )
    )

    return parser
