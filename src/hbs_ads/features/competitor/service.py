from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from hbs_ads.app.settings import ResolvedSettings
from hbs_ads.core.errors import AppError
from hbs_ads.core.outputs import CommandResult
from hbs_ads.core.workspace import WorkspaceManager
from hbs_ads.infra.db.sqlite import SQLiteDatabase


@dataclass(slots=True)
class AnalyzeCompetitorRequest:
    workspace_root: Path
    dry_run: bool = False


@dataclass(slots=True)
class CompetitorReportRequest:
    workspace_root: Path


class CompetitorService:
    def __init__(
        self,
        settings: ResolvedSettings,
        workspace: WorkspaceManager,
        database: SQLiteDatabase,
    ) -> None:
        self.settings = settings
        self.workspace = workspace
        self.database = database

    def analyze(self, request: AnalyzeCompetitorRequest) -> CommandResult:
        layout = self.workspace.initialize(self.settings)
        clips = self.database.list_clips()
        variants = self.database.list_variants()
        approved_clips = [clip for clip in clips if clip.approved]
        tag_counts: dict[str, int] = {}
        for clip in approved_clips:
            for tag in clip.tags or []:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        report = {
            "workspace_root": str(layout.root),
            "model": self.settings.ai.competitor_model,
            "asset_count": len(clips),
            "approved_asset_count": len(approved_clips),
            "variant_count": len(variants),
            "assets": [Path(clip.path).stem for clip in clips],
            "approved_assets": [Path(clip.path).stem for clip in approved_clips],
            "top_tags": sorted(
                (
                    {"tag": tag, "count": count}
                    for tag, count in tag_counts.items()
                ),
                key=lambda item: (-item["count"], item["tag"]),
            ),
        }
        report_path = layout.reports_dir / "competitor.json"
        if not request.dry_run:
            layout.reports_dir.mkdir(parents=True, exist_ok=True)
            report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        return CommandResult(
            status="planned" if request.dry_run else "ok",
            message=f"competitor analyze {'planned' if request.dry_run else 'completed'}",
            data={
                "report_file": str(report_path),
                "asset_count": report["asset_count"],
                "approved_asset_count": report["approved_asset_count"],
                "variant_count": report["variant_count"],
                "dry_run": request.dry_run,
            },
        )

    def report(self, request: CompetitorReportRequest) -> CommandResult:
        layout = self.workspace.initialize(self.settings)
        report_path = layout.reports_dir / "competitor.json"
        if not report_path.exists():
            raise AppError("competitor report not found; run competitor analyze first")
        report = json.loads(report_path.read_text(encoding="utf-8"))
        return CommandResult(
            status="ok",
            message=f"competitor report loaded from {report_path}",
            data=report,
        )
