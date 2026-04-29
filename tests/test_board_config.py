from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts" / "notion_scrum"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import board_config
import template_catalog


def test_load_returns_fallback_when_no_file_present(monkeypatch) -> None:
    missing = ROOT / "config" / "notion_scrum" / "missing-board-config.json"
    monkeypatch.setattr(board_config, "CONFIG_PATH", missing)

    result = board_config.load()

    assert result == board_config.DEFAULT_BOARD_CONFIG


def test_load_merges_partial_override(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "board_config.json"
    config_path.write_text(
        json.dumps({"projects_data_source_id": "projects-override"}) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(board_config, "CONFIG_PATH", config_path)

    result = board_config.load()

    assert result["projects_data_source_id"] == "projects-override"
    assert result["tasks_data_source_id"] == board_config.DEFAULT_BOARD_CONFIG["tasks_data_source_id"]
    assert result["default_discord_chat_id"] == board_config.DEFAULT_BOARD_CONFIG["default_discord_chat_id"]


def test_template_catalog_uses_board_config_runtime_defaults(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "board_config.json"
    config_path.write_text(
        json.dumps(
            {
                "projects_data_source_id": "projects-from-config",
                "tasks_data_source_id": "tasks-from-config",
                "default_discord_chat_id": "discord-chat-from-config",
                "default_discord_channel_name": "#config-channel",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(board_config, "CONFIG_PATH", config_path)

    reloaded = importlib.reload(template_catalog)
    rendered_projects = reloaded.render_template("query_projects_not_done")
    rendered_tasks = reloaded.render_template("query_tasks_not_done")

    assert rendered_projects["profile"]["data_source_id"] == "projects-from-config"
    assert rendered_tasks["profile"]["data_source_id"] == "tasks-from-config"


def test_prompt_defaults_use_board_config_channel(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "board_config.json"
    config_path.write_text(
        json.dumps(
            {
                "projects_data_source_id": "projects-from-config",
                "tasks_data_source_id": "tasks-from-config",
                "default_discord_chat_id": "discord-chat-from-config",
                "default_discord_channel_name": "#config-channel",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(board_config, "CONFIG_PATH", config_path)

    reloaded = importlib.reload(template_catalog)
    rendered = reloaded.render_template(
        "prompt_task_due_date_request",
        variables={
            "pending_prompt_id": "pp_due_1",
            "thread_id": "thread-1",
            "assistant_message_id": "assistant-1",
            "canonical_person_key": "ma",
            "platform_user_id": "discord-user-ma",
            "project_id": "project-1",
            "project_title": "Game teaser 03",
            "task_id": "task-1",
            "task_title": "rough cut v1",
            "display_name": "Ma",
        },
    )

    assert rendered["profile"]["chat_id"] == "discord-chat-from-config"
    assert rendered["profile"]["channel_name"] == "#config-channel"
