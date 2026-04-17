from __future__ import annotations

from dataclasses import dataclass
import json
import subprocess
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from hbs_ads.app.settings import ResolvedSettings
from hbs_ads.core.errors import AppError
from hbs_ads.infra.exec.runner import CommandRunner


GRAPH_ROOT = "https://graph.microsoft.com/v1.0"


@dataclass(slots=True)
class TeamsSetupResult:
    mode: str
    tenant_id: str
    app_id: str
    auth_type: str
    required_scopes: list[str]
    status: dict[str, Any]


@dataclass(slots=True)
class TeamsAuthCheckResult:
    mode: str
    required_scopes: list[str]
    checks: list[dict[str, Any]]


@dataclass(slots=True)
class TeamsChat:
    id: str
    chat_type: str
    topic: str = ""
    last_updated_at: str = ""
    web_url: str = ""


@dataclass(slots=True)
class TeamsMessage:
    id: str
    created_at: str = ""
    from_display_name: str = ""
    content: str = ""


@dataclass(slots=True)
class TeamsSendResult:
    chat_id: str
    message_id: str = ""
    dry_run: bool = False


class TeamsClient(Protocol):
    mode: str

    def setup(self) -> TeamsSetupResult: ...

    def auth_check(self) -> TeamsAuthCheckResult: ...

    def list_chats(self, *, top: int) -> list[TeamsChat]: ...

    def list_messages(self, *, chat_id: str, top: int) -> list[TeamsMessage]: ...

    def send_message(self, *, chat_id: str, message: str, dry_run: bool) -> TeamsSendResult: ...


@dataclass(slots=True)
class DirectGraphTeamsClient:
    settings: ResolvedSettings
    access_token: str

    @property
    def mode(self) -> str:
        return "graph-token"

    def setup(self) -> TeamsSetupResult:
        return TeamsSetupResult(
            mode=self.mode,
            tenant_id=self.settings.teams.tenant_id or self.settings.sharepoint.tenant_id,
            app_id="",
            auth_type="accessToken",
            required_scopes=self.settings.teams.scope_list(),
            status={"token_source": "HBS_ADS_GRAPH_ACCESS_TOKEN"},
        )

    def auth_check(self) -> TeamsAuthCheckResult:
        checks = [
            self._check_request("me", f"{GRAPH_ROOT}/me"),
            self._check_request("me/chats", f"{GRAPH_ROOT}/me/chats?$top=1"),
        ]
        return TeamsAuthCheckResult(
            mode=self.mode,
            required_scopes=self.settings.teams.scope_list(),
            checks=checks,
        )

    def list_chats(self, *, top: int) -> list[TeamsChat]:
        payload = self._request_json("GET", f"{GRAPH_ROOT}/me/chats?$top={top}")
        return [self._chat_from_payload(item) for item in self._value_list(payload)]

    def list_messages(self, *, chat_id: str, top: int) -> list[TeamsMessage]:
        payload = self._request_json("GET", f"{GRAPH_ROOT}/chats/{chat_id}/messages?$top={top}")
        return [self._message_from_payload(item) for item in self._value_list(payload)]

    def send_message(self, *, chat_id: str, message: str, dry_run: bool) -> TeamsSendResult:
        if dry_run:
            return TeamsSendResult(chat_id=chat_id, dry_run=True)
        payload = self._request_json(
            "POST",
            f"{GRAPH_ROOT}/chats/{chat_id}/messages",
            body={
                "body": {
                    "contentType": "text",
                    "content": message,
                }
            },
        )
        return TeamsSendResult(chat_id=chat_id, message_id=str(payload.get("id", "")), dry_run=False)

    def _check_request(self, name: str, url: str) -> dict[str, Any]:
        try:
            self._request_json("GET", url)
            return {"name": name, "ok": True}
        except AppError as exc:
            return {"name": name, "ok": False, "error": str(exc)}

    def _request_json(self, method: str, url: str, *, body: dict[str, Any] | None = None) -> Any:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
        }
        if body is not None:
            headers["Content-Type"] = "application/json"
        request = Request(url, data=data, headers=headers, method=method.upper())
        try:
            with urlopen(request, timeout=120) as response:
                payload = response.read().decode("utf-8")
        except HTTPError as exc:
            message = exc.read().decode("utf-8", errors="replace")
            raise AppError(f"Graph request failed with HTTP {exc.code}: {message}") from exc
        except URLError as exc:
            raise AppError(f"Graph request failed: {exc.reason}") from exc
        if not payload:
            return {}
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            return {}

    def _value_list(self, payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, dict) and isinstance(payload.get("value"), list):
            return [item for item in payload["value"] if isinstance(item, dict)]
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        return []

    def _chat_from_payload(self, payload: dict[str, Any]) -> TeamsChat:
        return TeamsChat(
            id=str(payload.get("id", "")),
            chat_type=str(payload.get("chatType", "")),
            topic=str(payload.get("topic") or ""),
            last_updated_at=str(payload.get("lastUpdatedDateTime") or ""),
            web_url=str(payload.get("webUrl") or ""),
        )

    def _message_from_payload(self, payload: dict[str, Any]) -> TeamsMessage:
        body = payload.get("body") if isinstance(payload.get("body"), dict) else {}
        sender = payload.get("from") if isinstance(payload.get("from"), dict) else {}
        user = sender.get("user") if isinstance(sender.get("user"), dict) else {}
        return TeamsMessage(
            id=str(payload.get("id", "")),
            created_at=str(payload.get("createdDateTime") or ""),
            from_display_name=str(user.get("displayName") or ""),
            content=str(body.get("content") or ""),
        )


@dataclass(slots=True)
class M365TeamsClient:
    settings: ResolvedSettings
    command_runner: CommandRunner

    @property
    def mode(self) -> str:
        return "live"

    def setup(self) -> TeamsSetupResult:
        self._run_m365_login()
        return TeamsSetupResult(
            mode=self.mode,
            tenant_id=self._tenant_id(),
            app_id=self.settings.teams.app_id,
            auth_type=self.settings.teams.auth_type,
            required_scopes=self.settings.teams.scope_list(),
            status=self._m365_status(),
        )

    def auth_check(self) -> TeamsAuthCheckResult:
        checks = [
            self._check_request("me", f"{GRAPH_ROOT}/me"),
            self._check_request("me/chats", f"{GRAPH_ROOT}/me/chats?$top=1"),
        ]
        return TeamsAuthCheckResult(
            mode=self.mode,
            required_scopes=self.settings.teams.scope_list(),
            checks=checks,
        )

    def list_chats(self, *, top: int) -> list[TeamsChat]:
        payload = self._request_json("GET", f"{GRAPH_ROOT}/me/chats?$top={top}")
        return [self._chat_from_payload(item) for item in self._value_list(payload)]

    def list_messages(self, *, chat_id: str, top: int) -> list[TeamsMessage]:
        payload = self._request_json("GET", f"{GRAPH_ROOT}/chats/{chat_id}/messages?$top={top}")
        return [self._message_from_payload(item) for item in self._value_list(payload)]

    def send_message(self, *, chat_id: str, message: str, dry_run: bool) -> TeamsSendResult:
        if dry_run:
            return TeamsSendResult(chat_id=chat_id, dry_run=True)
        payload = self._request_json(
            "POST",
            f"{GRAPH_ROOT}/chats/{chat_id}/messages",
            body={
                "body": {
                    "contentType": "text",
                    "content": message,
                }
            },
        )
        return TeamsSendResult(chat_id=chat_id, message_id=str(payload.get("id", "")), dry_run=False)

    def _run_m365_login(self) -> None:
        args = [
            self.settings.tools.m365,
            "login",
            "--authType",
            self.settings.teams.auth_type,
        ]
        tenant_id = self._tenant_id()
        if tenant_id:
            args.extend(["--tenant", tenant_id])
        if self.settings.teams.app_id:
            args.extend(["--appId", self.settings.teams.app_id])

        result = subprocess.run(
            args,
            cwd=str(self.settings.workspace.root),
            timeout=300,
            check=False,
        )
        if result.returncode != 0:
            raise AppError(f"teams setup failed: m365 login exited with code {result.returncode}")

    def _m365_status(self) -> dict[str, Any]:
        result = self.command_runner.run(
            [self.settings.tools.m365, "status", "--output", "json"],
            cwd=self.settings.workspace.root,
            timeout=60,
        )
        if result.returncode != 0:
            raise AppError(f"m365 status failed: {self._error_text(result.stdout, result.stderr)}")
        return self._parse_json_payload(result.stdout)

    def _check_request(self, name: str, url: str) -> dict[str, Any]:
        result = self.command_runner.run(
            [self.settings.tools.m365, "request", "--method", "get", "--url", url, "--output", "json"],
            cwd=self.settings.workspace.root,
            timeout=60,
        )
        if result.returncode == 0:
            return {"name": name, "ok": True}
        return {
            "name": name,
            "ok": False,
            "error": self._error_text(result.stdout, result.stderr),
        }

    def _request_json(self, method: str, url: str, *, body: dict[str, Any] | None = None) -> Any:
        args = [
            self.settings.tools.m365,
            "request",
            "--method",
            method.lower(),
            "--url",
            url,
            "--output",
            "json",
        ]
        if body is not None:
            args.extend(["--body", json.dumps(body), "--content-type", "application/json"])
        result = self.command_runner.run(args, cwd=self.settings.workspace.root, timeout=120)
        if result.returncode != 0:
            raise AppError(
                "m365 Graph request failed: "
                f"{self._error_text(result.stdout, result.stderr)}. "
                "Verify the Entra app used by m365 has delegated Teams chat permissions: "
                f"{', '.join(self.settings.teams.scope_list())}."
            )
        return self._parse_json_payload(result.stdout)

    def _tenant_id(self) -> str:
        return self.settings.teams.tenant_id or self.settings.sharepoint.tenant_id

    def _value_list(self, payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, dict) and isinstance(payload.get("value"), list):
            return [item for item in payload["value"] if isinstance(item, dict)]
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        return []

    def _chat_from_payload(self, payload: dict[str, Any]) -> TeamsChat:
        return TeamsChat(
            id=str(payload.get("id", "")),
            chat_type=str(payload.get("chatType", "")),
            topic=str(payload.get("topic") or ""),
            last_updated_at=str(payload.get("lastUpdatedDateTime") or ""),
            web_url=str(payload.get("webUrl") or ""),
        )

    def _message_from_payload(self, payload: dict[str, Any]) -> TeamsMessage:
        body = payload.get("body") if isinstance(payload.get("body"), dict) else {}
        sender = payload.get("from") if isinstance(payload.get("from"), dict) else {}
        user = sender.get("user") if isinstance(sender.get("user"), dict) else {}
        return TeamsMessage(
            id=str(payload.get("id", "")),
            created_at=str(payload.get("createdDateTime") or ""),
            from_display_name=str(user.get("displayName") or ""),
            content=str(body.get("content") or ""),
        )

    def _parse_json_payload(self, text: str) -> Any:
        stripped = text.strip()
        if not stripped:
            return {}
        try:
            return json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise AppError(f"m365 returned non-JSON output: {stripped[:200]}") from exc

    def _error_text(self, stdout: str, stderr: str) -> str:
        return (stderr.strip() or stdout.strip() or "unknown error")[:800]
