from __future__ import annotations

import json
from datetime import UTC, datetime
from dataclasses import dataclass
from pathlib import Path

from hbs_ads.app.settings import ResolvedSettings
from hbs_ads.core.outputs import CommandResult
from hbs_ads.core.workspace import WorkspaceManager


@dataclass(slots=True)
class NotifyRenderDoneRequest:
    workspace_root: Path
    variant: str = ""
    dry_run: bool = False


@dataclass(slots=True)
class NotifyProgressRequest:
    workspace_root: Path
    message: str = ""
    dry_run: bool = False


class NotifyService:
    def __init__(
        self,
        settings: ResolvedSettings,
        workspace: WorkspaceManager,
    ) -> None:
        self.settings = settings
        self.workspace = workspace

    def render_done(self, request: NotifyRenderDoneRequest) -> CommandResult:
        message = f"render complete for {request.variant or 'unspecified-variant'}"
        return self._write_event(
            workspace_root=request.workspace_root,
            action="notify render-done",
            message=message,
            dry_run=request.dry_run,
        )

    def progress(self, request: NotifyProgressRequest) -> CommandResult:
        message = request.message or "pipeline progress update"
        return self._write_event(
            workspace_root=request.workspace_root,
            action="notify progress",
            message=message,
            dry_run=request.dry_run,
        )

    def _write_event(
        self,
        *,
        workspace_root: Path,
        action: str,
        message: str,
        dry_run: bool,
    ) -> CommandResult:
        layout = self.workspace.initialize(self.settings)
        text_log = layout.logs_dir / "notify.log"
        json_log = layout.logs_dir / "notify.jsonl"
        event = {
            "action": action,
            "message": message,
            "dashboard_url": self.settings.notify.dashboard_url,
            "discord_configured": bool(self.settings.notify.discord_webhook_url),
            "slack_configured": bool(self.settings.notify.slack_webhook_url),
            "timestamp": datetime.now(UTC).isoformat(),
        }
        if not dry_run:
            import fcntl
            layout.logs_dir.mkdir(parents=True, exist_ok=True)
            with text_log.open("a", encoding="utf-8") as handle:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                try:
                    handle.write(f"{event['timestamp']} {action}: {message}\n")
                finally:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            with json_log.open("a", encoding="utf-8") as handle:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                try:
                    handle.write(json.dumps(event) + "\n")
                finally:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        return CommandResult(
            status="planned" if dry_run else "ok",
            message=f"{action} {'planned' if dry_run else 'completed'}",
            data={
                "text_log": str(text_log),
                "json_log": str(json_log),
                "event": event,
                "dry_run": dry_run,
            },
        )
