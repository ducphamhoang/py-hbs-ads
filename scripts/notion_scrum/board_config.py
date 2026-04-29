#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_BOARD_CONFIG: dict[str, Any] = {
    "projects_data_source_id": "2e945d07-72af-8117-a240-000bf508da50",
    "tasks_data_source_id": "2e945d07-72af-81dd-821a-000b082e6e95",
    "default_discord_chat_id": "discord-channel-hbs-creative",
    "default_discord_channel_name": "#hbs-creative-sml",
}

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "notion_scrum" / "board_config.json"


def load() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return dict(DEFAULT_BOARD_CONFIG)

    text = CONFIG_PATH.read_text(encoding="utf-8").strip()
    if not text:
        return dict(DEFAULT_BOARD_CONFIG)

    data = json.loads(text)
    return {**DEFAULT_BOARD_CONFIG, **data}
