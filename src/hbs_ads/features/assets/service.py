from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from hbs_ads.app.settings import ResolvedSettings
from hbs_ads.core.outputs import CommandResult
from hbs_ads.core.workspace import WorkspaceManager


@dataclass(slots=True)
class ListAssetsRequest:
    workspace_root: Path
    raw: bool = False
    trimmed: bool = False
    hooks: bool = False
    variants: bool = False


class AssetsService:
    def __init__(self, workspace: WorkspaceManager, settings: ResolvedSettings) -> None:
        self.workspace = workspace
        self.settings = settings

    def list_assets(self, request: ListAssetsRequest) -> CommandResult:
        layout = self.workspace.from_settings(self.settings)
        scopes = [
            name
            for name, enabled in {
                "raw": request.raw,
                "trimmed": request.trimmed,
                "hooks": request.hooks,
                "variants": request.variants,
            }.items()
            if enabled
        ]
        scope_label = ", ".join(scopes) if scopes else "all"
        return CommandResult(
            status="planned",
            message=f"assets list scaffold ready for workspace {layout.root} (scope: {scope_label})",
            data={"workspace_root": str(layout.root), "scope": scope_label},
        )
