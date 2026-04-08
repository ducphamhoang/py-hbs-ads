from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from hbs_ads.cli.main import main


def test_root_help_lists_documented_command_groups(capsys) -> None:
    exit_code = main(["--help"])
    assert exit_code == 0
    captured = capsys.readouterr()
    for command in [
        "init",
        "assets",
        "ingest",
        "trim",
        "tag",
        "variants",
        "hooks",
        "pipeline",
        "sharepoint",
        "competitor",
        "perf",
        "notify",
        "voiceover",
    ]:
        assert command in captured.out


def test_assets_list_executes_placeholder_service(capsys) -> None:
    exit_code = main(["assets", "list", "--raw"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "assets list scaffold ready" in captured.out


def test_trim_clip_executes_placeholder_service(capsys) -> None:
    exit_code = main(
        [
            "trim",
            "clip",
            "--input",
            "inbox/material/V379.mp4",
            "--from",
            "27s",
            "--to",
            "30s",
            "--name",
            "bomb-moment",
            "--dry-run",
        ]
    )
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "trim clip planned" in captured.out


def test_pipeline_run_ingest_mode_executes(capsys, tmp_path) -> None:
    exit_code = main(["--workspace", str(tmp_path), "pipeline", "run", "--ingest", "--dry-run"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "pipeline run completed in ingest mode" in captured.out


def test_init_workspace_creates_real_workspace(tmp_path, capsys) -> None:
    exit_code = main(["--workspace", str(tmp_path), "init", "workspace"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "workspace initialized" in captured.out
    assert (tmp_path / "_ASSETS").exists()
    assert (tmp_path / "hbs-ads.yaml").exists()


def test_notify_progress_supports_dry_run(capsys, tmp_path) -> None:
    exit_code = main(
        [
            "--workspace",
            str(tmp_path),
            "notify",
            "progress",
            "--message",
            "phase-5",
            "--dry-run",
        ]
    )
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "notify progress planned" in captured.out


def test_json_output_alias_returns_machine_readable_payload(capsys, tmp_path) -> None:
    exit_code = main(["--workspace", str(tmp_path), "--json", "init", "workspace"])
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["command"] == "init workspace"
    assert payload["workspace"] == str(tmp_path.resolve())
    assert payload["data"]["config_file"].endswith("hbs-ads.yaml")


def test_json_error_output_is_machine_readable(capsys, tmp_path) -> None:
    exit_code = main(
        [
            "--workspace",
            str(tmp_path),
            "--json",
            "variants",
            "export",
            "--variant",
            "missing",
        ]
    )
    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload == {
        "ok": False,
        "status": "error",
        "command": "variants export",
        "workspace": str(tmp_path.resolve()),
        "error": {"message": "variant not found: missing", "exit_code": 1},
    }


def test_quiet_output_suppresses_success_message(capsys, tmp_path) -> None:
    exit_code = main(["--workspace", str(tmp_path), "--output", "quiet", "init", "workspace"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_module_entrypoint_help_works_via_python_m(tmp_path) -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC)
    result = subprocess.run(
        [sys.executable, "-m", "hbs_ads.cli.main", "--help"],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "pipeline" in result.stdout
