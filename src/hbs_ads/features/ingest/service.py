from __future__ import annotations

from dataclasses import dataclass
import shutil
from pathlib import Path

from hbs_ads.app.settings import ResolvedSettings
from hbs_ads.core.outputs import CommandResult
from hbs_ads.core.workspace import WorkspaceManager
from hbs_ads.infra.db.sqlite import ClipRecord, SQLiteDatabase


@dataclass(slots=True)
class IngestRunRequest:
    workspace_root: Path
    dry_run: bool = False


@dataclass(slots=True)
class IngestWatchRequest:
    workspace_root: Path


@dataclass(slots=True)
class IngestCronRequest:
    workspace_root: Path
    action: str


class IngestService:
    def __init__(
        self,
        settings: ResolvedSettings,
        workspace: WorkspaceManager,
        database: SQLiteDatabase,
    ) -> None:
        self.settings = settings
        self.workspace = workspace
        self.database = database

    def run(self, request: IngestRunRequest) -> CommandResult:
        layout = self.workspace.initialize(self.settings)
        inbox_files = [path for path in sorted(layout.inbox_dir.iterdir()) if path.is_file()]
        existing = {clip.path: clip for clip in self.database.list_clips()}
        actions = []
        for source in inbox_files:
            destination = layout.raw_assets_dir / source.name
            actions.append({"source": str(source), "destination": str(destination)})
            if request.dry_run:
                continue
            shutil.copy2(source, destination)
            current = existing.get(str(destination))
            self.database.upsert_clip(
                ClipRecord(
                    path=str(destination),
                    kind="raw",
                    source_path=str(source),
                    status="ingested",
                    tags=current.tags if current else None,
                    approved=current.approved if current else False,
                )
            )
        return CommandResult(
            status="ok",
            message=f"ingest {'planned' if request.dry_run else 'completed'} for {len(actions)} files",
            data={"files": actions, "dry_run": request.dry_run},
        )

    def watch(self, request: IngestWatchRequest) -> CommandResult:
        return CommandResult(
            status="planned",
            message=f"ingest watch scaffold ready for {request.workspace_root}",
        )

    def cron(self, request: IngestCronRequest) -> CommandResult:
        return CommandResult(
            status="planned",
            message=f"ingest cron {request.action} scaffold ready for {request.workspace_root}",
        )
