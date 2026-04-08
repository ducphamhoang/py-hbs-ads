from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

from hbs_ads.core.errors import AppError
from hbs_ads.core.outputs import CommandResult


def render_result(
    result: CommandResult,
    *,
    command: str = "",
    workspace: str = "",
) -> None:
    if result.output_mode == "quiet":
        return
    if result.output_mode == "json":
        payload = {
            "ok": True,
            "status": result.status,
            "command": command,
            "workspace": _normalize_workspace(workspace),
            "message": result.message,
            "dry_run": bool(result.data.get("dry_run", False)),
            "data": asdict(result)["data"],
        }
        print(json.dumps(payload, default=str))
        return
    print(result.message)


def render_error(
    error: AppError,
    *,
    output_mode: str = "text",
    command: str = "",
    workspace: str = "",
) -> None:
    if output_mode == "quiet":
        return
    if output_mode == "json":
        payload = {
            "ok": False,
            "status": "error",
            "command": command,
            "workspace": _normalize_workspace(workspace),
            "error": {
                "message": error.message,
                "exit_code": error.exit_code,
            },
        }
        print(json.dumps(payload, default=str))
        return
    print(error.message, file=sys.stderr)


def _normalize_workspace(workspace: str) -> str:
    if not workspace:
        return ""
    return str(Path(workspace).resolve())
