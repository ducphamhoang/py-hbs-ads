from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re

from hbs_ads.app.settings import ResolvedSettings
from hbs_ads.core.errors import AppError
from hbs_ads.core.outputs import CommandResult
from hbs_ads.core.workspace import WorkspaceManager
from hbs_ads.infra.db.sqlite import ClipRecord, SQLiteDatabase


@dataclass(slots=True)
class AssembleHookRequest:
    workspace_root: Path
    name: str = ""
    dry_run: bool = False


class HooksService:
    def __init__(
        self,
        settings: ResolvedSettings,
        workspace: WorkspaceManager,
        database: SQLiteDatabase,
    ) -> None:
        self.settings = settings
        self.workspace = workspace
        self.database = database

    def assemble(self, request: AssembleHookRequest) -> CommandResult:
        layout = self.workspace.initialize(self.settings)
        target = request.name or "default-hook"
        source = self._select_source(target)
        output_path = layout.hooks_dir / f"{self._slugify(target)}.mp4"
        manifest_path = layout.hooks_dir / f"{self._slugify(target)}.json"
        if not request.dry_run:
            output_path.write_text(
                "\n".join([f"hook={target}", f"source={source.path}"]) + "\n",
                encoding="utf-8",
            )
            manifest_path.write_text(
                json.dumps(
                    {"hook": target, "source_path": source.path, "tags": source.tags or []},
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            self.database.upsert_clip(
                ClipRecord(
                    path=str(output_path),
                    kind="hook",
                    source_path=source.path,
                    status="hook-assembled",
                    tags=source.tags,
                    approved=True,
                )
            )
        return CommandResult(
            status="ok",
            message=f"hooks assemble {'planned' if request.dry_run else 'completed'} for {target}",
            data={
                "hook": target,
                "output_path": str(output_path),
                "source_path": source.path,
                "dry_run": request.dry_run,
            },
        )

    def _select_source(self, target: str) -> ClipRecord:
        approved = [clip for clip in self.database.list_clips() if clip.approved]
        if not approved:
            raise AppError("hooks assemble requires approved clips")
        tokens = {part for part in re.split(r"[^a-zA-Z0-9]+", target.lower()) if part}
        for clip in approved:
            searchable = f"{Path(clip.path).stem} {' '.join(clip.tags or [])}".lower()
            if tokens and all(token in searchable for token in tokens):
                return clip
        for clip in approved:
            searchable = f"{Path(clip.path).stem} {' '.join(clip.tags or [])}".lower()
            if "hook" in searchable or "question" in searchable or "intro" in searchable:
                return clip
        return approved[0]

    def _slugify(self, value: str) -> str:
        return re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower() or "hook"
