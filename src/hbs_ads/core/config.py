from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any

from hbs_ads.app.settings import (
    AISettings,
    DatabaseSettings,
    NotifySettings,
    ResolvedSettings,
    SharePointSettings,
    ToolSettings,
    VoiceoverSettings,
    WorkspaceSettings,
)

DEFAULT_CONFIG: dict[str, Any] = {
    "workspace": {"root": "."},
    "tools": {"ffmpeg": "ffmpeg", "ffprobe": "ffprobe", "m365": "m365"},
    "database": {"path": "clips.db"},
    "notify": {
        "discord_webhook_url": "",
        "slack_webhook_url": "",
        "dashboard_url": "http://localhost:7788",
    },
    "sharepoint": {"site_url": "", "tenant_id": "", "base_path": "Shared Documents/Variants"},
    "ai": {
        "provider": "gemini",
        "gemini_api_key_env": "GEMINI_API_KEY",
        "clip_analysis_model": "gemini-2.5-flash",
        "variant_score_model": "gemini-3-flash-preview",
        "competitor_model": "gemini-2.5-flash",
    },
    "voiceover": {"provider": "elevenlabs"},
}

ENV_MAPPING = {
    "HBS_ADS_WORKSPACE_ROOT": ("workspace", "root"),
    "HBS_ADS_DATABASE_PATH": ("database", "path"),
    "HBS_ADS_TOOLS_FFMPEG": ("tools", "ffmpeg"),
    "HBS_ADS_TOOLS_FFPROBE": ("tools", "ffprobe"),
    "HBS_ADS_TOOLS_M365": ("tools", "m365"),
    "HBS_ADS_NOTIFY_DISCORD_WEBHOOK_URL": ("notify", "discord_webhook_url"),
    "HBS_ADS_NOTIFY_SLACK_WEBHOOK_URL": ("notify", "slack_webhook_url"),
    "HBS_ADS_NOTIFY_DASHBOARD_URL": ("notify", "dashboard_url"),
    "HBS_ADS_SHAREPOINT_SITE_URL": ("sharepoint", "site_url"),
    "HBS_ADS_SHAREPOINT_TENANT_ID": ("sharepoint", "tenant_id"),
    "HBS_ADS_SHAREPOINT_BASE_PATH": ("sharepoint", "base_path"),
    "HBS_ADS_AI_PROVIDER": ("ai", "provider"),
    "HBS_ADS_AI_GEMINI_API_KEY_ENV": ("ai", "gemini_api_key_env"),
    "HBS_ADS_AI_CLIP_ANALYSIS_MODEL": ("ai", "clip_analysis_model"),
    "HBS_ADS_AI_VARIANT_SCORE_MODEL": ("ai", "variant_score_model"),
    "HBS_ADS_AI_COMPETITOR_MODEL": ("ai", "competitor_model"),
    "HBS_ADS_VOICEOVER_PROVIDER": ("voiceover", "provider"),
    # Legacy .env variable names (from MyGame_ADS)
    "SP_SITE_URL": ("sharepoint", "site_url"),
    "SP_TENANT_ID": ("sharepoint", "tenant_id"),
    "SP_BASE_PATH": ("sharepoint", "base_path"),
    "DISCORD_WEBHOOK_URL": ("notify", "discord_webhook_url"),
    "GEMINI_API_KEY": ("ai", "gemini_api_key_env"),
}


def resolve_settings(
    workspace_override: str | Path | None = None,
    output_mode: str = "text",
    env: dict[str, str] | None = None,
) -> ResolvedSettings:
    environment = dict(os.environ if env is None else env)
    
    # Load .env file if it exists (legacy MyGame_ADS compatibility)
    base_root = Path(workspace_override or environment.get("HBS_ADS_WORKSPACE_ROOT", ".")).resolve()
    env_file = base_root / ".env"
    if env_file.exists():
        env_vars = load_dotenv_file(env_file)
        # Merge .env variables into environment (lower priority than explicit env vars)
        environment = {**env_vars, **environment}
    
    base_root = Path(workspace_override or environment.get("HBS_ADS_WORKSPACE_ROOT", ".")).resolve()

    merged = deepcopy(DEFAULT_CONFIG)
    file_config = load_config_file(base_root / "hbs-ads.yaml")
    merged = deep_merge(merged, file_config)
    merged = apply_env_overrides(merged, environment)
    if workspace_override is not None:
        merged["workspace"]["root"] = str(base_root)

    return to_settings(merged, output_mode=output_mode)


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def apply_env_overrides(config: dict[str, Any], env: dict[str, str]) -> dict[str, Any]:
    merged = deepcopy(config)
    for env_name, path in ENV_MAPPING.items():
        if env_name not in env:
            continue
        target = merged
        for key in path[:-1]:
            target = target.setdefault(key, {})
        target[path[-1]] = env[env_name]
    return merged


def load_config_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        return json.loads(text)
    return parse_simple_yaml(text)


def load_dotenv_file(path: Path) -> dict[str, str]:
    """Load .env file with KEY=VALUE format (legacy MyGame_ADS compatibility).
    
    Handles:
    - KEY=VALUE
    - KEY = VALUE (with spaces)
    - Comments (#)
    - Empty lines
    """
    env_vars: dict[str, str] = {}
    if not path.exists():
        return env_vars
    
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        # Remove surrounding quotes if present
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        env_vars[key] = value
    
    return env_vars


def parse_simple_yaml(text: str) -> dict[str, Any]:
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]

    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        line = raw_line.strip()
        if ":" not in line:
            continue
        key, raw_value = line.split(":", 1)
        value = raw_value.strip()
        while indent <= stack[-1][0]:
            stack.pop()
        current = stack[-1][1]
        if value == "":
            nested: dict[str, Any] = {}
            current[key] = nested
            stack.append((indent, nested))
        else:
            current[key] = parse_scalar(value)
    return root


def parse_scalar(value: str) -> Any:
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if value.isdigit():
        return int(value)
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    return value


def to_settings(config: dict[str, Any], output_mode: str) -> ResolvedSettings:
    workspace_root = Path(str(config["workspace"]["root"])).resolve()
    database_path = Path(str(config["database"]["path"]))
    if not database_path.is_absolute():
        database_path = workspace_root / database_path

    return ResolvedSettings(
        workspace=WorkspaceSettings(root=workspace_root),
        tools=ToolSettings(**config["tools"]),
        database=DatabaseSettings(path=database_path),
        notify=NotifySettings(**config["notify"]),
        sharepoint=SharePointSettings(**config["sharepoint"]),
        ai=AISettings(**config["ai"]),
        voiceover=VoiceoverSettings(**config["voiceover"]),
        output_mode=output_mode,
    )
