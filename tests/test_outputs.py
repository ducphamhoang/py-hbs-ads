from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from hbs_ads.cli.renderers import render_error, render_result
from hbs_ads.core.errors import AppError
from hbs_ads.core.outputs import CommandResult


def test_render_result_json_payload_is_stable(capsys, tmp_path) -> None:
    render_result(
        CommandResult(
            status="ok",
            message="workspace initialized",
            output_mode="json",
            data={"created_paths": ["a"], "dry_run": False},
        ),
        command="init workspace",
        workspace=str(tmp_path),
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload == {
        "ok": True,
        "status": "ok",
        "command": "init workspace",
        "workspace": str(tmp_path.resolve()),
        "message": "workspace initialized",
        "dry_run": False,
        "data": {"created_paths": ["a"], "dry_run": False},
    }


def test_render_error_json_payload_is_stable(capsys, tmp_path) -> None:
    render_error(
        AppError("variant not found", exit_code=7),
        output_mode="json",
        command="variants export",
        workspace=str(tmp_path),
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload == {
        "ok": False,
        "status": "error",
        "command": "variants export",
        "workspace": str(tmp_path.resolve()),
        "error": {"message": "variant not found", "exit_code": 7},
    }


def test_render_result_quiet_mode_suppresses_output(capsys) -> None:
    render_result(CommandResult(status="ok", message="hidden", output_mode="quiet"))
    assert capsys.readouterr().out == ""
