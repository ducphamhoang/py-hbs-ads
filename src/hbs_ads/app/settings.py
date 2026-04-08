from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class WorkspaceSettings:
    root: Path


@dataclass(slots=True)
class ToolSettings:
    ffmpeg: str = "ffmpeg"
    ffprobe: str = "ffprobe"
    m365: str = "m365"


@dataclass(slots=True)
class DatabaseSettings:
    path: Path


@dataclass(slots=True)
class NotifySettings:
    discord_webhook_url: str = ""
    slack_webhook_url: str = ""
    dashboard_url: str = "http://localhost:7788"


@dataclass(slots=True)
class SharePointSettings:
    site_url: str = ""
    tenant_id: str = ""
    base_path: str = "Shared Documents/Variants"


@dataclass(slots=True)
class AISettings:
    provider: str = "gemini"
    gemini_api_key_env: str = "GEMINI_API_KEY"
    clip_analysis_model: str = "gemini-2.5-flash"
    variant_score_model: str = "gemini-3-flash-preview"
    competitor_model: str = "gemini-2.5-flash"


@dataclass(slots=True)
class VoiceoverSettings:
    provider: str = "elevenlabs"


@dataclass(slots=True)
class ResolvedSettings:
    workspace: WorkspaceSettings
    tools: ToolSettings
    database: DatabaseSettings
    notify: NotifySettings
    sharepoint: SharePointSettings
    ai: AISettings
    voiceover: VoiceoverSettings
    output_mode: str = "text"
