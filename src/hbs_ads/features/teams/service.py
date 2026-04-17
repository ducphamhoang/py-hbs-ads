from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from hbs_ads.app.settings import ResolvedSettings
from hbs_ads.core.errors import AppError
from hbs_ads.core.outputs import CommandResult
from hbs_ads.core.workspace import WorkspaceManager
from hbs_ads.infra.teams import TeamsClient


@dataclass(slots=True)
class TeamsSetupRequest:
    workspace_root: Path


@dataclass(slots=True)
class TeamsAuthCheckRequest:
    workspace_root: Path


@dataclass(slots=True)
class TeamsListChatsRequest:
    workspace_root: Path
    top: int = 10


@dataclass(slots=True)
class TeamsListMessagesRequest:
    workspace_root: Path
    chat_id: str
    top: int = 20


@dataclass(slots=True)
class TeamsSendMessageRequest:
    workspace_root: Path
    chat_id: str
    message: str
    dry_run: bool = False


class TeamsService:
    def __init__(
        self,
        settings: ResolvedSettings,
        workspace: WorkspaceManager,
        client: TeamsClient,
    ) -> None:
        self.settings = settings
        self.workspace = workspace
        self.client = client

    def setup(self, request: TeamsSetupRequest) -> CommandResult:
        layout = self.workspace.initialize(self.settings)
        result = self.client.setup()
        manifest_path = layout.teams_dir / "setup.json"
        manifest = {
            "workspace_root": str(layout.root),
            "mode": result.mode,
            "tenant_id": result.tenant_id,
            "app_id": result.app_id,
            "auth_type": result.auth_type,
            "required_scopes": result.required_scopes,
            "status": result.status,
        }
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        return CommandResult(
            status="ok",
            message=f"teams setup completed for {request.workspace_root}",
            data={
                "setup_file": str(manifest_path),
                "mode": result.mode,
                "tenant_id": result.tenant_id,
                "app_id": result.app_id,
                "auth_type": result.auth_type,
                "required_scopes": result.required_scopes,
                "permission_note": (
                    "Teams chat access depends on delegated Graph permissions in the active auth source. "
                    "When HBS_ADS_GRAPH_ACCESS_TOKEN is set, the token is used directly and is not saved."
                ),
            },
        )

    def auth_check(self, request: TeamsAuthCheckRequest) -> CommandResult:
        result = self.client.auth_check()
        ok = all(check.get("ok") is True for check in result.checks)
        return CommandResult(
            status="ok" if ok else "blocked",
            message="teams auth check passed" if ok else "teams auth check blocked by missing Graph access",
            data={
                "mode": result.mode,
                "required_scopes": result.required_scopes,
                "checks": result.checks,
            },
        )

    def list_chats(self, request: TeamsListChatsRequest) -> CommandResult:
        self._validate_top(request.top)
        chats = self.client.list_chats(top=request.top)
        return CommandResult(
            status="ok",
            message=f"teams chats found {len(chats)} chats",
            data={
                "mode": self.client.mode,
                "chats": [
                    {
                        "id": item.id,
                        "chat_type": item.chat_type,
                        "topic": item.topic,
                        "last_updated_at": item.last_updated_at,
                        "web_url": item.web_url,
                    }
                    for item in chats
                ],
            },
        )

    def list_messages(self, request: TeamsListMessagesRequest) -> CommandResult:
        if not request.chat_id.strip():
            raise AppError("teams messages requires --chat-id")
        self._validate_top(request.top)
        messages = self.client.list_messages(chat_id=request.chat_id, top=request.top)
        return CommandResult(
            status="ok",
            message=f"teams messages found {len(messages)} messages",
            data={
                "mode": self.client.mode,
                "chat_id": request.chat_id,
                "messages": [
                    {
                        "id": item.id,
                        "created_at": item.created_at,
                        "from_display_name": item.from_display_name,
                        "content": item.content,
                    }
                    for item in messages
                ],
            },
        )

    def send_message(self, request: TeamsSendMessageRequest) -> CommandResult:
        if not request.chat_id.strip():
            raise AppError("teams send requires --chat-id")
        if not request.message.strip():
            raise AppError("teams send requires --message")
        result = self.client.send_message(
            chat_id=request.chat_id,
            message=request.message,
            dry_run=request.dry_run,
        )
        return CommandResult(
            status="planned" if request.dry_run else "ok",
            message=f"teams send {'planned' if request.dry_run else 'completed'}",
            data={
                "mode": self.client.mode,
                "chat_id": result.chat_id,
                "message_id": result.message_id,
                "dry_run": result.dry_run,
            },
        )

    def _validate_top(self, top: int) -> None:
        if top < 1 or top > 50:
            raise AppError("--top must be between 1 and 50")
