from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from hbs_ads.app.settings import ResolvedSettings
from hbs_ads.core.errors import AppError


WORKSPACE_DIRS = [
    "_ASSETS",
    "_HOOKS",
    "_SEQUENCES",
    "VARIANTS",
    "generated_variants",
    "inbox",
    "archive",
    "logs",
    "docs",
    "reports",
    "sharepoint",
    "teams",
    "voiceover",
]


DEFAULT_CONFIG_TEXT = """workspace:
  root: .
tools:
  ffmpeg: ffmpeg
  ffprobe: ffprobe
  m365: m365
database:
  path: clips.db
notify:
  discord_webhook_url: ""
  slack_webhook_url: ""
  dashboard_url: http://localhost:7788
sharepoint:
  site_url: ""
  tenant_id: ""
  base_path: Shared Documents/Variants
teams:
  tenant_id: ""
  app_id: ""
  auth_type: deviceCode
  required_scopes: User.Read,Chat.ReadBasic,Chat.Read,ChatMessage.Send
ai:
  provider: gemini
  gemini_api_key_env: GEMINI_API_KEY
  variant_score_model: gemini-3-flash-preview
  competitor_model: gemini-2.5-flash
voiceover:
  provider: elevenlabs
"""


@dataclass(slots=True)
class WorkspaceLayout:
    root: Path
    assets_dir: Path
    raw_assets_dir: Path
    trimmed_assets_dir: Path
    hooks_dir: Path
    sequences_dir: Path
    variants_dir: Path
    generated_variants_dir: Path
    inbox_dir: Path
    archive_dir: Path
    logs_dir: Path
    docs_dir: Path
    reports_dir: Path
    perf_inbox_dir: Path
    sharepoint_dir: Path
    sharepoint_library_dir: Path
    sharepoint_downloads_dir: Path
    teams_dir: Path
    voiceover_dir: Path
    config_file: Path
    database_file: Path


class WorkspaceManager:
    def from_settings(self, settings: ResolvedSettings) -> WorkspaceLayout:
        root = settings.workspace.root
        return WorkspaceLayout(
            root=root,
            assets_dir=root / "_ASSETS",
            raw_assets_dir=root / "_ASSETS" / "raw",
            trimmed_assets_dir=root / "_ASSETS" / "trimmed",
            hooks_dir=root / "_HOOKS",
            sequences_dir=root / "_SEQUENCES",
            variants_dir=root / "VARIANTS",
            generated_variants_dir=root / "generated_variants",
            inbox_dir=root / "inbox",
            archive_dir=root / "archive",
            logs_dir=root / "logs",
            docs_dir=root / "docs",
            reports_dir=root / "reports",
            perf_inbox_dir=root / "inbox" / "perf",
            sharepoint_dir=root / "sharepoint",
            sharepoint_library_dir=root / "sharepoint" / "library",
            sharepoint_downloads_dir=root / "sharepoint" / "downloads",
            teams_dir=root / "teams",
            voiceover_dir=root / "voiceover",
            config_file=root / "hbs-ads.yaml",
            database_file=settings.database.path,
        )

    def initialize(self, settings: ResolvedSettings) -> WorkspaceLayout:
        layout = self.from_settings(settings)
        dirs_to_create = [
            layout.root,
            *(layout.root / dirname for dirname in WORKSPACE_DIRS),
            layout.raw_assets_dir,
            layout.trimmed_assets_dir,
            layout.perf_inbox_dir,
            layout.sharepoint_library_dir,
            layout.sharepoint_downloads_dir,
            layout.teams_dir,
            layout.voiceover_dir,
        ]
        for path in dirs_to_create:
            try:
                path.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                raise AppError(f"Failed to create directory {path}: {e}")
        if not layout.config_file.exists():
            try:
                layout.config_file.write_text(DEFAULT_CONFIG_TEXT, encoding="utf-8")
            except OSError as e:
                raise AppError(f"Failed to write config file {layout.config_file}: {e}")
        return layout
