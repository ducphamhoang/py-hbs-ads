from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_filename(path: Path, index: int) -> str:
    suffix = path.suffix or ".bin"
    stem = path.stem or f"asset-{index:03d}"
    slug = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in stem).strip("-") or f"asset-{index:03d}"
    digest = hashlib.sha256(str(path).encode()).hexdigest()[:8]
    return f"{index:03d}-{slug}-{digest}{suffix}"


def _copy_sidecars(source_path: Path, staged_path: Path) -> None:
    for suffix in (".market-analysis.json", ".mr-analysis.json"):
        sidecar = source_path.with_name(f"{source_path.name}{suffix}")
        if sidecar.exists():
            try:
                shutil.copy2(sidecar, staged_path.with_name(f"{staged_path.name}{suffix}"))
            except OSError:
                pass


def intake_asset_files(
    *,
    workspace_path: Path,
    run_id: str,
    asset_paths: list[Path],
    source: str,
    collector: str,
    query_context: dict[str, Any] | None = None,
    candidate_defaults: dict[str, Any] | None = None,
) -> dict[str, Any]:
    query_context = query_context or {}
    candidate_defaults = candidate_defaults or {}

    collect_root = workspace_path / "logs" / "market-research" / "collect"
    assets_root = collect_root / "assets"
    assets_root.mkdir(parents=True, exist_ok=True)

    staged_assets: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for index, raw_path in enumerate(asset_paths):
        source_path = raw_path.expanduser().resolve()
        if not source_path.exists():
            errors.append({"asset_path": str(source_path), "error": "missing_source_asset"})
            continue

        staged_path = assets_root / _safe_filename(source_path, index)
        try:
            shutil.copy2(source_path, staged_path)
        except OSError as exc:
            errors.append({"asset_path": str(source_path), "error": str(exc)})
            continue
        _copy_sidecars(source_path, staged_path)

        source_record_id = candidate_defaults.get("source_record_id") or source_path.stem or f"upload_{index:03d}"
        candidate = {
            "source": source,
            "source_record_id": str(source_record_id),
            "source_url": str(candidate_defaults.get("source_url", "") or ""),
            "app_name": str(candidate_defaults.get("app_name", "") or ""),
            "publisher_name": str(candidate_defaults.get("publisher_name", "") or ""),
            "geo": str(candidate_defaults.get("geo", "") or ""),
            "platform": str(candidate_defaults.get("platform", "") or source),
            "first_seen_at": str(candidate_defaults.get("first_seen_at", "") or _now_iso()),
            "last_seen_at": str(candidate_defaults.get("last_seen_at", "") or _now_iso()),
            "asset_url": str(staged_path),
            "thumbnail_url": str(candidate_defaults.get("thumbnail_url", "") or ""),
            "landing_url": str(candidate_defaults.get("landing_url", "") or ""),
            "raw_payload": {
                "ingest_mode": "asset_file_intake",
                "original_path": str(source_path),
                "staged_path": str(staged_path),
                "collector": collector,
                "query_context": query_context,
                "file_name": source_path.name,
            },
        }
        candidates.append(candidate)
        staged_assets.append(
            {
                "original_path": str(source_path),
                "staged_path": str(staged_path),
                "size_bytes": staged_path.stat().st_size,
            }
        )

    manifest = {
        "schema_version": "market-collection-handoff/v1",
        "run_context": {
            "run_id": run_id,
            "brief_id": str(candidate_defaults.get("brief_id", "") or ""),
            "collected_at": _now_iso(),
            "collector": collector,
            "source": source,
            "query_context": query_context,
        },
        "candidates": candidates,
        "asset_manifest": {
            "downloaded": staged_assets,
            "missing": errors,
        },
        "collection_report": {
            "candidate_count": len(candidates),
            "errors": errors,
            "notes": [f"intake_source={source}", f"collector={collector}"],
        },
    }

    manifest_path = collect_root / "intake-manifest.json"
    assets_manifest_path = collect_root / "assets-manifest.json"
    collection_report_path = collect_root / "collection-report.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    assets_manifest_path.write_text(json.dumps(manifest["asset_manifest"], indent=2), encoding="utf-8")
    collection_report_path.write_text(json.dumps(manifest["collection_report"], indent=2), encoding="utf-8")

    return {
        "manifest_path": str(manifest_path),
        "assets_manifest_path": str(assets_manifest_path),
        "collection_report_path": str(collection_report_path),
        "candidate_count": len(candidates),
        "error_count": len(errors),
        "staged_assets": staged_assets,
    }
