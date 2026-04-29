#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from common import load_api_key, notion_patch_page
from resolve_and_prepare_patch import prepare_patch_from_resolved_target
from board_cache import DEFAULT_BOARD_CACHE, load_snapshot
from result_contracts import build_result


def apply_patch_from_resolved_target(
    *,
    snapshot: dict[str, Any],
    target_kind: str,
    title: str,
    project_title: str | None,
    patch_kind: str,
    patch_variables: dict[str, str | None],
    resolve_mode: str,
    max_cache_age_seconds: int,
    execute: bool,
    now_iso: str | None = None,
) -> dict[str, Any]:
    prepared = prepare_patch_from_resolved_target(
        snapshot=snapshot,
        target_kind=target_kind,
        title=title,
        project_title=project_title,
        patch_kind=patch_kind,
        patch_variables=patch_variables,
        resolve_mode=resolve_mode,
        max_cache_age_seconds=max_cache_age_seconds,
        now_iso=now_iso,
    )
    if not prepared.get("ok"):
        return build_result(
            ok=False,
            action_taken=prepared.get("action_taken") or "patch_prepare_failed",
            write_applied=False,
            errors=list(prepared.get("errors") or []),
            data=prepared.get("data") or {},
        )

    patch = ((prepared.get("data") or {}).get("patch") or {})
    if not execute:
        return build_result(
            ok=True,
            action_taken="patch_dry_run_prepared",
            write_applied=False,
            data=prepared.get("data") or {},
        )

    api_key = load_api_key()
    if patch.get("kind") == "multi":
        apply_responses = []
        applied_count = 0
        try:
            for subpatch in patch.get("patches") or []:
                request = subpatch.get("request") or {}
                page_id = request.get("page_id")
                properties = request.get("properties") or {}
                if not page_id:
                    return build_result(
                        ok=False,
                        action_taken="patch_prepare_failed",
                        write_applied=False,
                        errors=["prepared patch is missing page_id"],
                        data=prepared.get("data") or {},
                    )
                apply_responses.append(notion_patch_page(api_key, page_id, properties))
                applied_count += 1
        except Exception as exc:
            return build_result(
                ok=False,
                action_taken="patch_apply_failed",
                write_applied=applied_count > 0,
                errors=[f"multi-patch apply failed: {exc}"],
                data={
                    **(prepared.get("data") or {}),
                    "apply_response": apply_responses,
                    "applied_count": applied_count,
                },
            )
        response_data: Any = apply_responses
    else:
        request = patch.get("request") or {}
        page_id = request.get("page_id")
        properties = request.get("properties") or {}
        if not page_id:
            return build_result(
                ok=False,
                action_taken="patch_prepare_failed",
                write_applied=False,
                errors=["prepared patch is missing page_id"],
                data=prepared.get("data") or {},
            )
        response_data = notion_patch_page(api_key, page_id, properties)
    return build_result(
        ok=True,
        action_taken="patch_applied",
        write_applied=True,
        data={
            **(prepared.get("data") or {}),
            "apply_response": response_data,
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
    parser = argparse.ArgumentParser(description="Resolve from cache, prepare a Notion patch, and optionally execute it")
    parser.add_argument("--cache", type=Path, default=DEFAULT_BOARD_CACHE)
    parser.add_argument("--target-kind", choices=["projects", "tasks"], required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--project-title")
    parser.add_argument("--patch-kind", choices=["status", "rich-text", "date", "multi"], required=True)
    parser.add_argument("--resolve-mode", choices=["auto", "safe", "fast"], default="auto")
    parser.add_argument("--max-cache-age-seconds", type=int, default=900)
    parser.add_argument("--var", action="append", default=[], help="patch variable key=value")
    parser.add_argument("--execute", action="store_true", help="Actually write the patch to Notion")
    args = parser.parse_args()

    snapshot = load_snapshot(args.cache)
    result = apply_patch_from_resolved_target(
        snapshot=snapshot,
        target_kind=args.target_kind,
        title=args.title,
        project_title=args.project_title,
        patch_kind=args.patch_kind,
        patch_variables=_parse_vars(args.var),
        resolve_mode=args.resolve_mode,
        max_cache_age_seconds=args.max_cache_age_seconds,
        execute=args.execute,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
