from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class WorkspaceSettings:
    root: Path


@dataclass(slots=True)
class LibrarySettings:
    """Shared persistent asset library, separate from job workspaces."""
    root: Path

    @property
    def raw_dir(self) -> Path:
        return self.root / "raw"

    @property
    def trimmed_dir(self) -> Path:
        return self.root / "trimmed"

    @property
    def hooks_dir(self) -> Path:
        return self.root / "hooks"

    @property
    def generated_variants_dir(self) -> Path:
        return self.root / "generated_variants"

    @property
    def sharepoint_downloads_dir(self) -> Path:
        """Where SharePoint downloads land in the shared library."""
        return self.root / "raw"


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
    # Multiple base path variants (e.g. V200+, V300+, V400+)
    # V1-199 live directly under the root video folder (no 100+ folder)
    base_path_v100: str = ""
    base_path_v200: str = ""
    base_path_v300: str = ""
    base_path_v400: str = ""

    def resolve_base_path(self, target: str | None = None) -> str:
        """Resolve the SharePoint base path for a given variant target.

        Args:
            target: Variant identifier like "v204", "v317", "v406", or None.
                   When None, falls back to the default base_path.
                   V1-199 → base_path_v100 (root video folder)
                   V200-299 → base_path_v200
                   V300-399 → base_path_v300
                   V400+ → base_path_v400

        Returns:
            The resolved SharePoint base path string.
        """
        if target is None:
            return self.base_path or self.base_path_v400

        # Extract numeric portion from target (e.g. "v204" → 204)
        import re
        match = re.search(r"(\d+)", target.lower())
        if match:
            version_num = int(match.group(1))
            if version_num < 200:
                if self.base_path_v100:
                    return self.base_path_v100
            elif version_num < 300:
                if self.base_path_v200:
                    return self.base_path_v200
            elif version_num < 400:
                if self.base_path_v300:
                    return self.base_path_v300
            else:
                if self.base_path_v400:
                    return self.base_path_v400

        # Fallback to default
        return self.base_path


@dataclass(slots=True)
class TeamsSettings:
    tenant_id: str = ""
    app_id: str = ""
    auth_type: str = "deviceCode"
    required_scopes: str = "User.Read,Chat.ReadBasic,Chat.Read,ChatMessage.Send"

    def scope_list(self) -> list[str]:
        return [scope.strip() for scope in self.required_scopes.split(",") if scope.strip()]


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
    library: LibrarySettings
    tools: ToolSettings
    database: DatabaseSettings
    notify: NotifySettings
    sharepoint: SharePointSettings
    teams: TeamsSettings
    ai: AISettings
    voiceover: VoiceoverSettings
    output_mode: str = "text"
