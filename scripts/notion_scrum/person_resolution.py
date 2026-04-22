#!/usr/bin/env python3
from __future__ import annotations

from typing import Any

from common import find_person_by_canonical_key, find_person_by_platform_identity


def resolve_platform_identity(
    registry: dict[str, Any],
    platform: str,
    platform_user_id: str,
) -> dict[str, Any] | None:
    """Return the canonical person dict for a platform identity, or None if not found."""
    return find_person_by_platform_identity(
        registry,
        platform=platform,
        platform_user_id=platform_user_id,
    )


def get_canonical_person(
    registry: dict[str, Any],
    canonical_person_key: str | None,
) -> dict[str, Any] | None:
    """Return the person dict for a canonical_person_key, or None."""
    return find_person_by_canonical_key(registry, canonical_person_key)


def get_pending_candidates(registry: dict[str, Any]) -> list[dict[str, Any]]:
    """Return all pending_people entries from the registry."""
    return list(registry.get("pending_people") or [])


def build_actor_label(
    person: dict[str, Any] | None,
    *,
    fallback: dict[str, Any] | None = None,
) -> str:
    """
    Build a human-readable actor label.

    Priority:
    1. "NotionDisplayName (canonical_person_key)" when both are available
    2. notion display_name alone
    3. canonical_person_key
    4. fallback["display_name"]
    5. fallback["platform_user_id"]
    6. "unknown"
    """
    if person is None:
        person = {}
    notion = person.get("notion") or {}
    notion_name = notion.get("display_name")
    canonical = person.get("canonical_person_key")

    if notion_name and canonical:
        return f"{notion_name} ({canonical})"
    if notion_name:
        return notion_name
    if canonical:
        return canonical
    if fallback:
        return fallback.get("display_name") or fallback.get("platform_user_id") or "unknown"
    return "unknown"
