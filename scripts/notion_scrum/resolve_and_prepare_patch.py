#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from board_cache import DEFAULT_BOARD_CACHE, load_snapshot, resolve_target
from prepare_notion_patch import prepare_patch
from result_contracts import build_result


def _prepare_patch_bundle(patch_kind: str, patch_variables: dict[str, Any], *, page_id: str) -> dict[str, Any]:
    if patch_kind == "multi":
        patches = []
        for item in patch_variables.get("patches") or []:
            variables = dict(item.get("variables") or {})
            variables["page_id"] = page_id
            patches.append(prepare_patch(item["kind"], variables=variables))
        return {"kind": "multi", "patches": patches}
    variables = dict(patch_variables)
    variables["page_id"] = page_id
    return prepare_patch(patch_kind, variables=variables)


def prepare_patch_from_resolved_target(
    *,
    snapshot: dict[str, Any],
    target_kind: str,
    title: str,
    project_title: str | None,
    patch_kind: str,
    patch_variables: dict[str, str | None],
    resolve_mode: str,
    max_cache_age_seconds: int,
    now_iso: str | None = None,
) -> dict[str, Any]:
    resolved = resolve_target(
        snapshot=snapshot,
        kind=target_kind,
        title=title,
        project_title=project_title,
        mode=resolve_mode,
        max_cache_age_seconds=max_cache_age_seconds,
        now_iso=now_iso,
    )
    if not resolved.get("ok"):
        return build_result(
            ok=False,
            action_taken=resolved.get("action_taken") or "target_resolution_failed",
            errors=list(resolved.get("errors") or []),
            data={
                **(resolved.get("data") or {}),
                "patch_kind": patch_kind,
                "patch_variables": patch_variables,
            },
        )

    resolved_id = ((resolved.get("data") or {}).get("resolved_id"))
    try:
        patch = _prepare_patch_bundle(patch_kind, patch_variables, page_id=resolved_id)
    except Exception as exc:
        return build_result(
            ok=False,
            action_taken="patch_prepare_failed",
            errors=[str(exc)],
            data={
                "resolved_target": resolved.get("data") or {},
                "patch_kind": patch_kind,
                "patch_variables": patch_variables,
            },
        )
    return build_result(
        ok=True,
        action_taken="patch_prepared_from_resolved_target",
        data={
            "resolved_target": resolved.get("data") or {},
            "patch": patch,
        },
    )


def _parse_vars(items: list[str]) -> dict[str, str | None]:
    result: dict[str, str | None] = {}
    for item in items:
        if "=" in item:
            key, value = item.split("=", 1)
            result[key] = value
        else:
            result[item] = None
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Resolve a project/task target from cache, then build a Notion patch payload")
    parser.add_argument("--cache", type=Path, default=DEFAULT_BOARD_CACHE)
    parser.add_argument("--target-kind", choices=["projects", "tasks"], required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--project-title")
    parser.add_argument("--patch-kind", choices=["status", "rich-text", "date", "multi"], required=True)
    parser.add_argument("--resolve-mode", choices=["auto", "safe", "fast"], default="auto")
    parser.add_argument("--max-cache-age-seconds", type=int, default=900)
    parser.add_argument("--var", action="append", default=[], help="patch variable key=value")
    args = parser.parse_args()

    snapshot = load_snapshot(args.cache)
    result = prepare_patch_from_resolved_target(
        snapshot=snapshot,
        target_kind=args.target_kind,
        title=args.title,
        project_title=args.project_title,
        patch_kind=args.patch_kind,
        patch_variables=_parse_vars(args.var),
        resolve_mode=args.resolve_mode,
        max_cache_age_seconds=args.max_cache_age_seconds,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
