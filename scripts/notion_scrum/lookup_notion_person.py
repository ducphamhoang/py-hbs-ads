#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from audit import AuditEventType, append_event
from common import (
    DEFAULT_AUDIT_LOG,
    DEFAULT_TEAM_REGISTRY,
    load_registry,
)
from person_resolution import get_canonical_person, get_pending_candidates, resolve_platform_identity


def lookup_person(
    *,
    canonical_person_key: str | None = None,
    platform: str | None = None,
    platform_user_id: str | None = None,
    registry_path: Path = DEFAULT_TEAM_REGISTRY,
) -> dict[str, Any]:
    registry = load_registry(registry_path)
    pending_list = get_pending_candidates(registry)

    person = get_canonical_person(registry, canonical_person_key)
    if person is None and platform and platform_user_id:
        person = resolve_platform_identity(registry, platform, platform_user_id)

    resolved_canonical = (person or {}).get("canonical_person_key") or canonical_person_key
    pending_match = next(
        (p for p in pending_list if p.get("canonical_person_key") == resolved_canonical),
        None,
    )

    if person is not None:
        notion = dict((person.get("notion") or {}))
        return {
            "resolved": bool(notion.get("user_id") or notion.get("people_page_id")),
            "mapping_source": "registry",
            "canonical_person_key": person.get("canonical_person_key"),
            "notion": notion,
            "candidates": list((pending_match or {}).get("notion_candidates") or []),
        }

    if pending_match is not None:
        return {
            "resolved": False,
            "mapping_source": "pending_people",
            "canonical_person_key": canonical_person_key,
            "notion": None,
            "candidates": list(pending_match.get("notion_candidates") or []),
        }

    return {
        "resolved": False,
        "mapping_source": "none",
        "canonical_person_key": canonical_person_key,
        "notion": None,
        "candidates": [],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Look up Notion identity mapping for a canonical person")
    parser.add_argument("--canonical-person-key", default=None)
    parser.add_argument("--platform", default=None)
    parser.add_argument("--platform-user-id", default=None)
    parser.add_argument("--registry", type=Path, default=DEFAULT_TEAM_REGISTRY)
    parser.add_argument("--audit-log", type=Path, default=DEFAULT_AUDIT_LOG)
    args = parser.parse_args()

    result = lookup_person(
        canonical_person_key=args.canonical_person_key,
        platform=args.platform,
        platform_user_id=args.platform_user_id,
        registry_path=args.registry,
    )
    append_event(
        args.audit_log,
        AuditEventType.NOTION_PERSON_LOOKUP,
        canonical_person_key=result.get("canonical_person_key"),
        mapping_source=result.get("mapping_source"),
        resolved=result.get("resolved"),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
