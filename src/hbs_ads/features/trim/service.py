from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from hbs_ads.app.settings import ResolvedSettings
from hbs_ads.core.errors import AppError
from hbs_ads.core.outputs import CommandResult
from hbs_ads.core.workspace import WorkspaceManager
from hbs_ads.infra.db.sqlite import ClipRecord, SQLiteDatabase
from hbs_ads.infra.exec.runner import CommandRunner


@dataclass(slots=True)
class TrimRunRequest:
    workspace_root: Path
    config_path: Path
    dry_run: bool = False


@dataclass(slots=True)
class TrimClipRequest:
    workspace_root: Path
    input_path: Path
    start: str
    end: str
    name: str
    dry_run: bool = False


class TrimService:
    def __init__(
        self,
        settings: ResolvedSettings,
        workspace: WorkspaceManager,
        database: SQLiteDatabase,
        command_runner: CommandRunner,
    ) -> None:
        self.settings = settings
        self.workspace = workspace
        self.database = database
        self.command_runner = command_runner

    def run(self, request: TrimRunRequest) -> CommandResult:
        try:
            content = json.loads(request.config_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, FileNotFoundError, UnicodeDecodeError) as e:
            raise AppError(f"failed to load trim config: {e}")
        clips = content.get("clips", content) if isinstance(content, dict) else content
        results = []
        for clip in clips:
            required_keys = ("input", "from", "to", "name")
            missing = [k for k in required_keys if k not in clip]
            if missing:
                raise AppError(f"trim config missing required keys: {missing}")
            results.append(
                self._clip_impl(
                    TrimClipRequest(
                        workspace_root=request.workspace_root,
                        input_path=Path(clip["input"]),
                        start=clip["from"],
                        end=clip["to"],
                        name=clip["name"],
                        dry_run=request.dry_run,
                    )
                ).data
            )
        return CommandResult(
            status="ok",
            message=f"trim run {'planned' if request.dry_run else 'completed'} for {len(results)} clips",
            data={"clips": results, "dry_run": request.dry_run},
        )

    def clip(self, request: TrimClipRequest) -> CommandResult:
        return self._clip_impl(request)

    def _clip_impl(self, request: TrimClipRequest) -> CommandResult:
        layout = self.workspace.initialize(self.settings)
        output_path = layout.trimmed_assets_dir / f"{request.name}{request.input_path.suffix}"
        command = [
            self.settings.tools.ffmpeg,
            "-y",
            "-i",
            str(request.input_path),
            "-ss",
            request.start,
            "-to",
            request.end,
            "-c",
            "copy",
            str(output_path),
        ]
        result = self.command_runner.run(command, cwd=layout.root, dry_run=request.dry_run)
        if result.returncode != 0:
            raise AppError(f"trim clip failed: {result.stderr or result.returncode}")
        if not request.dry_run:
            self.database.upsert_clip(
                ClipRecord(
                    path=str(output_path),
                    kind="trimmed",
                    source_path=str(request.input_path),
                    status="trimmed",
                )
            )
        return CommandResult(
            status="ok",
            message=(
                f"trim clip {'planned' if request.dry_run else 'completed'} for {request.name} "
                f"({request.start}->{request.end})"
            ),
            data={
                "input_path": str(request.input_path),
                "output_path": str(output_path),
                "start": request.start,
                "end": request.end,
                "dry_run": request.dry_run,
                "command": command,
            },
        )
