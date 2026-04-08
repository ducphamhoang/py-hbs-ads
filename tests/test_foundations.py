from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from hbs_ads.core.config import resolve_settings
from hbs_ads.core.workspace import WorkspaceManager
from hbs_ads.infra.db.sqlite import SQLiteDatabase
from hbs_ads.infra.exec.runner import CommandRunner


def test_settings_precedence_file_env_cli(tmp_path, monkeypatch) -> None:
    (tmp_path / "hbs-ads.yaml").write_text(
        "database:\n  path: from-file.db\ntools:\n  ffmpeg: ffmpeg-file\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("HBS_ADS_DATABASE_PATH", "from-env.db")
    settings = resolve_settings(workspace_override=tmp_path, output_mode="json")
    assert settings.workspace.root == tmp_path.resolve()
    assert settings.database.path == tmp_path.resolve() / "from-env.db"
    assert settings.tools.ffmpeg == "ffmpeg-file"
    assert settings.output_mode == "json"


def test_workspace_manager_initializes_layout(tmp_path) -> None:
    settings = resolve_settings(workspace_override=tmp_path)
    layout = WorkspaceManager().initialize(settings)
    assert layout.assets_dir.exists()
    assert layout.logs_dir.exists()
    assert layout.config_file.exists()


def test_sqlite_bootstrap_creates_schema(tmp_path) -> None:
    path = tmp_path / "clips.db"
    result = SQLiteDatabase(path).bootstrap()
    assert path.exists()
    assert "0001_initial" in result.applied_migrations
    assert "0004_clip_analysis" in result.applied_migrations
    with sqlite3.connect(path) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        clip_columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(clips)").fetchall()
        }
    assert "schema_migrations" in tables
    assert "operation_logs" in tables
    assert {"confidence", "gemini_tagged", "analysis_json"} <= clip_columns


def test_command_runner_dry_run() -> None:
    result = CommandRunner().run(["echo", "hi"], dry_run=True)
    assert result.dry_run is True
    assert result.returncode == 0
    assert result.args == ["echo", "hi"]
