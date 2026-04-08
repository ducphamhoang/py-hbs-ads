from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from hbs_ads.app.settings import ResolvedSettings
from hbs_ads.core.outputs import CommandResult
from hbs_ads.core.workspace import WorkspaceManager
from hbs_ads.infra.db.sqlite import SQLiteDatabase


@dataclass(slots=True)
class InitWorkspaceRequest:
    workspace_root: Path


@dataclass(slots=True)
class InitDBRequest:
    workspace_root: Path
    migrate: bool = False


@dataclass(slots=True)
class BootstrapArtifacts:
    created_paths: list[str]
    config_file: str
    database_file: str


class BootstrapService:
    def __init__(
        self,
        settings: ResolvedSettings,
        workspace: WorkspaceManager,
        database: SQLiteDatabase,
    ) -> None:
        self.settings = settings
        self.workspace = workspace
        self.database = database

    def init_workspace(self, request: InitWorkspaceRequest) -> CommandResult:
        layout = self.workspace.initialize(self.settings)
        created_paths = [
            str(layout.root / name)
            for name in [
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
                "voiceover",
            ]
        ]
        return CommandResult(
            status="ok",
            message=f"workspace initialized at {layout.root}",
            data={
                "created_paths": created_paths,
                "config_file": str(layout.config_file),
                "database_file": str(layout.database_file),
            },
        )

    def init_db(self, request: InitDBRequest) -> CommandResult:
        result = self.database.bootstrap()
        return CommandResult(
            status="ok",
            message=f"database initialized at {result.path}",
            data={
                "database_file": str(result.path),
                "applied_migrations": result.applied_migrations,
                "migrate": request.migrate,
            },
        )
