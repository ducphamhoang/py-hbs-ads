from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path


INITIAL_MIGRATIONS: list[tuple[str, str]] = [
    (
        "0001_initial",
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS operation_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            command TEXT NOT NULL,
            status TEXT NOT NULL,
            started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            ended_at TEXT,
            summary TEXT NOT NULL DEFAULT ''
        );
        """,
    ),
    (
        "0002_clips",
        """
        CREATE TABLE IF NOT EXISTS clips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT NOT NULL UNIQUE,
            kind TEXT NOT NULL,
            source_path TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'new',
            tags_json TEXT NOT NULL DEFAULT '[]',
            approved INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """,
    ),
    (
        "0003_variants",
        """
        CREATE TABLE IF NOT EXISTS variants (
            name TEXT PRIMARY KEY,
            config_path TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'generated',
            render_path TEXT NOT NULL DEFAULT '',
            export_paths_json TEXT NOT NULL DEFAULT '[]',
            archive_path TEXT NOT NULL DEFAULT '',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """,
    ),
    (
        "0004_clip_analysis",
        """
        ALTER TABLE clips ADD COLUMN confidence TEXT NOT NULL DEFAULT 'low';
        ALTER TABLE clips ADD COLUMN gemini_tagged INTEGER NOT NULL DEFAULT 0;
        ALTER TABLE clips ADD COLUMN analysis_json TEXT NOT NULL DEFAULT '{}';
        """,
    ),
]


@dataclass(slots=True)
class BootstrapResult:
    path: Path
    applied_migrations: list[str]


@dataclass(slots=True)
class ClipRecord:
    path: str
    kind: str
    source_path: str
    status: str = "new"
    tags: list[str] | None = None
    approved: bool = False
    confidence: str = "low"
    gemini_tagged: bool = False
    analysis: dict[str, object] | None = None


@dataclass(slots=True)
class VariantRecord:
    name: str
    config_path: str = ""
    status: str = "generated"
    render_path: str = ""
    export_paths: list[str] | None = None
    archive_path: str = ""
    metadata: dict[str, object] | None = None


class SQLiteDatabase:
    def __init__(self, path: Path) -> None:
        self.path = path

    def bootstrap(self) -> BootstrapResult:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        applied: list[str] = []
        with sqlite3.connect(self.path) as conn:
            conn.execute("PRAGMA busy_timeout = 30000")
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            existing = {
                row[0]
                for row in conn.execute("SELECT version FROM schema_migrations").fetchall()
            }
            for version, sql in INITIAL_MIGRATIONS:
                if version in existing:
                    continue
                conn.executescript(sql)
                conn.execute(
                    "INSERT INTO schema_migrations(version) VALUES (?)",
                    (version,),
                )
                applied.append(version)
            conn.commit()
        return BootstrapResult(path=self.path, applied_migrations=applied)

    def upsert_clip(self, clip: ClipRecord) -> None:
        self.bootstrap()
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                """
                INSERT INTO clips(path, kind, source_path, status, tags_json, approved)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                    kind = excluded.kind,
                    source_path = excluded.source_path,
                    status = excluded.status,
                    tags_json = excluded.tags_json,
                    approved = excluded.approved,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    clip.path,
                    clip.kind,
                    clip.source_path,
                    clip.status,
                    json.dumps(clip.tags or []),
                    int(clip.approved),
                ),
            )
            conn.commit()

    def list_clips(self, *, pending_only: bool = False) -> list[ClipRecord]:
        self.bootstrap()
        query = (
            "SELECT path, kind, source_path, status, tags_json, approved, confidence, gemini_tagged, analysis_json "
            "FROM clips"
        )
        if pending_only:
            query += " WHERE approved = 0"
        query += " ORDER BY path"
        with sqlite3.connect(self.path) as conn:
            rows = conn.execute(query).fetchall()
        def _parse_tags(raw: str) -> list[str]:
            try:
                return json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                return []

        def _parse_analysis(raw: str) -> dict[str, object]:
            try:
                return json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                return {}

        return [
            ClipRecord(
                path=row[0],
                kind=row[1],
                source_path=row[2],
                status=row[3],
                tags=_parse_tags(row[4]),
                approved=bool(row[5]),
                confidence=row[6],
                gemini_tagged=bool(row[7]),
                analysis=_parse_analysis(row[8]),
            )
            for row in rows
        ]

    def upsert_variant(self, variant: VariantRecord) -> None:
        self.bootstrap()
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                """
                INSERT INTO variants(
                    name,
                    config_path,
                    status,
                    render_path,
                    export_paths_json,
                    archive_path,
                    metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    config_path = excluded.config_path,
                    status = excluded.status,
                    render_path = excluded.render_path,
                    export_paths_json = excluded.export_paths_json,
                    archive_path = excluded.archive_path,
                    metadata_json = excluded.metadata_json,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    variant.name,
                    variant.config_path,
                    variant.status,
                    variant.render_path,
                    json.dumps(variant.export_paths or []),
                    variant.archive_path,
                    json.dumps(variant.metadata or {}),
                ),
            )
            conn.commit()

    def get_variant(self, name: str) -> VariantRecord | None:
        self.bootstrap()
        with sqlite3.connect(self.path) as conn:
            row = conn.execute(
                """
                SELECT name, config_path, status, render_path, export_paths_json, archive_path, metadata_json
                FROM variants
                WHERE name = ?
                """,
                (name,),
            ).fetchone()
        if row is None:
            return None
        def _parse_export_paths(raw: str) -> list[str]:
            try:
                return json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                return []

        def _parse_metadata(raw: str) -> dict[str, object]:
            try:
                return json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                return {}

        return VariantRecord(
            name=row[0],
            config_path=row[1],
            status=row[2],
            render_path=row[3],
            export_paths=_parse_export_paths(row[4]),
            archive_path=row[5],
            metadata=_parse_metadata(row[6]),
        )

    def list_variants(self) -> list[VariantRecord]:
        self.bootstrap()
        with sqlite3.connect(self.path) as conn:
            rows = conn.execute(
                """
                SELECT name, config_path, status, render_path, export_paths_json, archive_path, metadata_json
                FROM variants
                ORDER BY name
                """
            ).fetchall()

        def _parse_export_paths(raw: str) -> list[str]:
            try:
                return json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                return []

        def _parse_metadata(raw: str) -> dict[str, object]:
            try:
                return json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                return {}

        return [
            VariantRecord(
                name=row[0],
                config_path=row[1],
                status=row[2],
                render_path=row[3],
                export_paths=_parse_export_paths(row[4]),
                archive_path=row[5],
                metadata=_parse_metadata(row[6]),
            )
            for row in rows
        ]

    def set_tags(self, path: str, tags: list[str], status: str, approved: bool = False) -> None:
        self.bootstrap()
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                """
                UPDATE clips
                SET tags_json = ?, status = ?, approved = ?, updated_at = CURRENT_TIMESTAMP
                WHERE path = ?
                """,
                (json.dumps(tags), status, int(approved), path),
            )
            conn.commit()

    def update_clip_analysis(
        self,
        *,
        path: str,
        tags: list[str],
        status: str,
        confidence: str,
        gemini_tagged: bool,
        analysis: dict[str, object],
        approved: bool = False,
    ) -> None:
        self.bootstrap()
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                """
                UPDATE clips
                SET
                    tags_json = ?,
                    status = ?,
                    approved = ?,
                    confidence = ?,
                    gemini_tagged = ?,
                    analysis_json = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE path = ?
                """,
                (
                    json.dumps(tags),
                    status,
                    int(approved),
                    confidence,
                    int(gemini_tagged),
                    json.dumps(analysis),
                    path,
                ),
            )
            conn.commit()

    def approve_all(self) -> int:
        self.bootstrap()
        with sqlite3.connect(self.path) as conn:
            cursor = conn.execute(
                """
                UPDATE clips
                SET approved = 1, status = 'approved', updated_at = CURRENT_TIMESTAMP
                WHERE approved = 0
                """
            )
            conn.commit()
            return cursor.rowcount
