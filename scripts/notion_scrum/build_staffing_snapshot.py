#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import board_cache
import people_state_store
from common import (
    DEFAULT_ROOT,
    DEFAULT_STATE_DIR,
    DEFAULT_TEAM_REGISTRY,
    load_registry,
    save_json,
    utc_now_iso,
)

# Path defaults
DEFAULT_CACHE_DIR = DEFAULT_ROOT / "state" / "notion_scrum" / "cache"
DEFAULT_BOARD_CACHE = DEFAULT_CACHE_DIR / "board_snapshot.json"
DEFAULT_PEOPLE_STATE = DEFAULT_STATE_DIR / "people_state.json"
DEFAULT_STAFFING_SNAPSHOT = DEFAULT_CACHE_DIR / "staffing_snapshot.json"

# Active-status vocabulary (locked by Plan 01 tests)
# ACTIVE = NOT IN ("Done", "Archived") → includes "Not started", "In progress"
_INACTIVE_STATUSES: frozenset[str] = frozenset({"Done", "Archived"})


def build_staffing_snapshot(
    registry: dict[str, Any],
    people_state: dict[str, Any],
    board_snapshot: dict[str, Any],
    today_iso: str | None = None,
) -> dict[str, Any]:
    """Derive a staffing snapshot from registry, people state, and board snapshot.

    This is a purely local, read-optimized function — no Notion API calls.
    Assignments derive from board cache owner_ids joined through registry Notion mappings.
    people_state is consulted only for availability status and backup key, never for
    project/task lists (D-02).

    Args:
        registry: team_registry.json contents
        people_state: people_state.json contents (empty container OK)
        board_snapshot: board_snapshot.json contents (empty dict OK)
        today_iso: ISO date string for overdue calculation (defaults to utc_now_iso)

    Returns:
        Snapshot dict with schema_version, generated_at, inputs, meta, people,
        project_effective_owners
    """
    today = today_iso or utc_now_iso()[:10]  # Use date portion only

    # Step 1 — Build the Notion-user-ID-to-person-key index
    notion_id_to_person_key: dict[str, str] = {}
    for person_key, person in registry.get("people", {}).items():
        notion = person.get("notion") or {}
        uid = notion.get("user_id")
        if uid:
            notion_id_to_person_key[uid] = person_key

    # Step 2 — Collect unresolved owner IDs while resolving owners in projects and tasks
    unresolved_owner_ids: set[str] = set()

    projects_records: dict[str, Any] = (
        (board_snapshot.get("records") or {}).get("projects") or {}
    )
    tasks_records: dict[str, Any] = (
        (board_snapshot.get("records") or {}).get("tasks") or {}
    )

    # Resolve project owner IDs and collect unresolved ones
    project_resolved_owners: dict[str, list[str]] = {}
    for project_id, project in projects_records.items():
        owner_ids = project.get("owner_ids") or []
        resolved = [notion_id_to_person_key[oid] for oid in owner_ids if oid in notion_id_to_person_key]
        unresolved = [oid for oid in owner_ids if oid not in notion_id_to_person_key]
        unresolved_owner_ids.update(unresolved)
        project_resolved_owners[project_id] = resolved

    # Resolve task owner IDs and collect unresolved ones
    task_resolved_owners: dict[str, list[str]] = {}
    for task_id, task in tasks_records.items():
        owner_ids = task.get("owner_ids") or []
        resolved = [notion_id_to_person_key[oid] for oid in owner_ids if oid in notion_id_to_person_key]
        unresolved = [oid for oid in owner_ids if oid not in notion_id_to_person_key]
        unresolved_owner_ids.update(unresolved)
        task_resolved_owners[task_id] = resolved

    # Step 3 — Initialize per-person accumulators from registry (all registry people appear)
    people_accumulator: dict[str, dict[str, Any]] = {}
    for person_key, person in registry.get("people", {}).items():
        notion = person.get("notion") or {}
        notion_display_name = notion.get("display_name")
        top_level_display_name = person.get("display_name")
        # Prefer registry notion.display_name; fall back to top-level display_name; then canonical key
        display_name = notion_display_name or top_level_display_name or person_key

        # Get availability from people_state (or default to status="unknown", backup=None)
        person_state = people_state_store.get_person_state(people_state, person_key)
        if person_state is not None:
            avail = person_state.get("availability") or {}
            cap = person_state.get("capacity") or {}
            availability_status = avail.get("status", "unknown")
            leave_since = avail.get("since")
            leave_until = avail.get("until")
            bandwidth = cap.get("bandwidth", "unknown")
            backup_person_key = avail.get("backup_person_key")
        else:
            availability_status = "unknown"
            leave_since = None
            leave_until = None
            bandwidth = "unknown"
            backup_person_key = None

        people_accumulator[person_key] = {
            "canonical_person_key": person_key,
            "display_name": display_name,
            "availability_status": availability_status,
            "leave_since": leave_since,
            "leave_until": leave_until,
            "bandwidth": bandwidth,
            "backup_person_key": backup_person_key,
            "active_project_ids": [],
            "active_project_titles": [],
            "active_task_ids": [],
            "active_task_titles": [],
            "active_projects": 0,
            "active_tasks": 0,
            "blocked_tasks": 0,
            "overdue_tasks": 0,
            "undated_tasks": 0,
            "risk_flags": [],
        }

    # Step 4 — Walk board projects to populate per-person assignment data
    active_project_ids: list[str] = []
    for project_id, project in projects_records.items():
        project_status = project.get("status")
        if project_status in _INACTIVE_STATUSES:
            continue
        active_project_ids.append(project_id)
        project_title = project.get("title") or project_id
        resolved_keys = project_resolved_owners.get(project_id, [])
        for owner_key in resolved_keys:
            if owner_key in people_accumulator:
                acc = people_accumulator[owner_key]
                acc["active_project_ids"].append(project_id)
                acc["active_project_titles"].append(project_title)
                acc["active_projects"] += 1

    # Step 5 — Walk board tasks to populate task counts
    for task_id, task in tasks_records.items():
        task_status = task.get("status")
        if task_status in _INACTIVE_STATUSES:
            continue
        task_title = task.get("title") or task_id
        due_date = task.get("due_date")  # ISO date string or None
        blocked_reason = task.get("blocked_reason")
        resolved_keys = task_resolved_owners.get(task_id, [])

        is_blocked = bool(blocked_reason) or task_status == "Blocked"
        is_overdue = due_date is not None and due_date < today
        is_undated = due_date is None

        for owner_key in resolved_keys:
            if owner_key in people_accumulator:
                acc = people_accumulator[owner_key]
                acc["active_task_ids"].append(task_id)
                acc["active_task_titles"].append(task_title)
                acc["active_tasks"] += 1
                if is_overdue:
                    acc["overdue_tasks"] += 1
                if is_blocked:
                    acc["blocked_tasks"] += 1
                if is_undated:
                    acc["undated_tasks"] += 1

    # Step 6 — Derive person risk_flags (low-level facts only, per D-09)
    for person_key, acc in people_accumulator.items():
        risk_flags: list[str] = []
        is_absent = people_state_store.is_person_absent(people_state, person_key)
        if is_absent:
            risk_flags.append("absent_owner")
        if is_absent and acc["backup_person_key"] is None:
            risk_flags.append("absent_no_backup")
        acc["risk_flags"] = risk_flags

    # Step 7 — Build project_effective_owners map (active projects only)
    project_effective_owners: dict[str, Any] = {}
    for project_id in active_project_ids:
        board_owner_keys = sorted(project_resolved_owners.get(project_id, []))
        effective_keys: list[str] = []
        has_absent_owner = False
        has_no_backup = False

        for owner_key in board_owner_keys:
            effective_key, routing_reason = people_state_store.effective_followup_target(
                people_state, owner_key
            )
            if effective_key not in effective_keys:
                effective_keys.append(effective_key)
            if people_state_store.is_person_absent(people_state, owner_key):
                has_absent_owner = True
                if routing_reason == "escalation_needed":
                    has_no_backup = True

        project_effective_owners[project_id] = {
            "board_owner_person_keys": board_owner_keys,
            "effective_owner_person_keys": sorted(effective_keys),
            "has_absent_owner": has_absent_owner,
            "has_no_backup": has_no_backup,
        }

    # Step 8 — Sort list outputs for stable JSON and assemble result
    for acc in people_accumulator.values():
        acc["active_project_ids"] = sorted(acc["active_project_ids"])
        acc["active_project_titles"] = sorted(acc["active_project_titles"])
        acc["active_task_ids"] = sorted(acc["active_task_ids"])
        acc["active_task_titles"] = sorted(acc["active_task_titles"])

    return {
        "schema_version": "1.0",
        "generated_at": today_iso or utc_now_iso(),
        "inputs": {
            "registry_source": str(DEFAULT_TEAM_REGISTRY),
            "people_state_source": str(DEFAULT_PEOPLE_STATE),
            "board_snapshot_source": str(DEFAULT_BOARD_CACHE),
        },
        "meta": {
            "unresolved_owner_ids": sorted(unresolved_owner_ids),
            "person_count": len(people_accumulator),
            "active_project_count": len(active_project_ids),
        },
        "people": {
            person_key: people_accumulator[person_key]
            for person_key in sorted(people_accumulator.keys())
        },
        "project_effective_owners": project_effective_owners,
    }


def write_staffing_snapshot(path: Path, snapshot: dict[str, Any]) -> None:
    """Atomically write staffing snapshot to path via common.save_json."""
    save_json(path, snapshot)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build derived staffing snapshot from local state"
    )
    parser.add_argument("--registry", type=Path, default=DEFAULT_TEAM_REGISTRY)
    parser.add_argument("--people-state", type=Path, default=DEFAULT_PEOPLE_STATE)
    parser.add_argument("--board-cache", type=Path, default=DEFAULT_BOARD_CACHE)
    parser.add_argument("--output", type=Path, default=DEFAULT_STAFFING_SNAPSHOT)
    parser.add_argument(
        "--dry-run", action="store_true", help="Print snapshot without writing file"
    )
    args = parser.parse_args()

    registry = load_registry(args.registry)
    people_state = people_state_store.load_people_state(args.people_state)
    board_snapshot_data = board_cache.load_snapshot(args.board_cache)

    snapshot = build_staffing_snapshot(
        registry=registry,
        people_state=people_state,
        board_snapshot=board_snapshot_data,
    )

    if not args.dry_run:
        write_staffing_snapshot(args.output, snapshot)

    print(
        json.dumps(
            {
                "ok": True,
                "output": str(args.output),
                "person_count": len(snapshot["people"]),
                "unresolved_count": len(snapshot["meta"]["unresolved_owner_ids"]),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
