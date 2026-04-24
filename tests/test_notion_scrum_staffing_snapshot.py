from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts" / "notion_scrum"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_staffing_snapshot  # noqa: F401, E402


# ---------------------------------------------------------------------------
# Active-status vocabulary (locked as comments per plan)
# ---------------------------------------------------------------------------
# ACTIVE_PROJECT_STATUSES = {"Not started", "In progress"} — statuses NOT in ("Done", "Archived")
# ACTIVE_TASK_STATUSES = {"Not started", "In progress"} — statuses NOT in ("Done", "Archived")
# Blocked tasks: blocked_reason is non-empty string OR status == "Blocked"
# Overdue tasks: active task with due_date < today_iso
# Undated tasks: active task with due_date is None


# ---------------------------------------------------------------------------
# Inline helpers (no @pytest.fixture decorators — inline pattern per project)
# ---------------------------------------------------------------------------

def _sample_registry() -> dict:
    """Return a minimal valid registry with person1 and person2."""
    return {
        "schema_version": "1.0",
        "people": {
            "person1": {
                "canonical_person_key": "person1",
                "display_name": "Person One",
                "notion": {
                    "user_id": "00000000-0000-4000-8000-000000000001",
                    "display_name": "Person One (P1)",
                },
                "platform_identities": [],
            },
            "person2": {
                "canonical_person_key": "person2",
                "display_name": "Person Two",
                "notion": {
                    "user_id": "00000000-0000-4000-8000-000000000002",
                    "display_name": None,
                },
                "platform_identities": [],
            },
        },
        "identity_index": {},
        "pending_people": [],
    }


def _sample_board_snapshot_mixed() -> dict:
    """Return a mixed board snapshot with projects and tasks of various statuses."""
    return {
        "meta": {"project_count": 2, "task_count": 4},
        "records": {
            "projects": {
                "project-1": {
                    "id": "project-1",
                    "title": "Alpha",
                    "status": "In progress",
                    "owner_ids": ["00000000-0000-4000-8000-000000000001"],
                },
                "project-2": {
                    "id": "project-2",
                    "title": "Beta",
                    "status": "Done",
                    "owner_ids": ["notion-user-unresolved-xyz"],
                },
            },
            "tasks": {
                "task-1": {
                    "id": "task-1",
                    "title": "Task 1 Undated",
                    "status": "Not started",
                    "owner_ids": ["00000000-0000-4000-8000-000000000001"],
                    "project_ids": ["project-1"],
                    "project_titles": ["Alpha"],
                    "due_date": None,
                    "blocked_reason": None,
                },
                "task-2": {
                    "id": "task-2",
                    "title": "Task 2 Overdue",
                    "status": "In progress",
                    "owner_ids": ["00000000-0000-4000-8000-000000000001"],
                    "project_ids": ["project-1"],
                    "project_titles": ["Alpha"],
                    "due_date": "2026-04-20",
                    "blocked_reason": None,
                },
                "task-3": {
                    "id": "task-3",
                    "title": "Task 3 Blocked",
                    "status": "In progress",
                    "owner_ids": ["00000000-0000-4000-8000-000000000002"],
                    "project_ids": ["project-1"],
                    "project_titles": ["Alpha"],
                    "due_date": "2026-04-30",
                    "blocked_reason": "Waiting on feedback",
                },
                "task-4": {
                    "id": "task-4",
                    "title": "Task 4 Unresolved Owner",
                    "status": "Not started",
                    "owner_ids": ["notion-user-unresolved-999"],
                    "project_ids": ["project-2"],
                    "project_titles": ["Beta"],
                    "due_date": None,
                    "blocked_reason": None,
                },
            },
        },
    }


def _empty_people_state() -> dict:
    """Return an empty but valid people_state container."""
    return {
        "schema_version": "1.0",
        "updated_at": "2026-04-24T00:00:00Z",
        "people": {},
    }


def _people_state_with_leave() -> dict:
    """Return people_state with person1 on leave, backup=person2."""
    return {
        "schema_version": "1.0",
        "updated_at": "2026-04-24T00:00:00Z",
        "people": {
            "person1": {
                "availability": {
                    "status": "leave",
                    "since": "2026-04-22",
                    "until": "2026-05-01",
                    "backup_person_key": "person2",
                    "timezone": None,
                    "half_day": None,
                    "note": None,
                    "source": {},
                    "updated_at": "2026-04-24T00:00:00Z",
                },
                "capacity": {"bandwidth": "unknown", "note": None, "updated_at": ""},
                "coordination": {
                    "default_followup_policy": "",
                    "backup_person_key": None,
                    "last_status_check_at": "",
                },
                "metadata": {"tags": [], "last_actor_person_key": None},
            }
        },
    }


# ---------------------------------------------------------------------------
# Tests (11 functions to lock snapshot derivation contract)
# ---------------------------------------------------------------------------

def test_build_snapshot_from_registry_people_board() -> None:
    """Test that build_staffing_snapshot can generate snapshot from registry + people + board."""
    registry = _sample_registry()
    people_state = _empty_people_state()
    board_snapshot = _sample_board_snapshot_mixed()

    result = build_staffing_snapshot.build_staffing_snapshot(
        registry=registry,
        people_state=people_state,
        board_snapshot=board_snapshot,
        today_iso="2026-04-24",
    )

    assert result is not None
    assert isinstance(result, dict)
    assert "schema_version" in result
    assert "generated_at" in result
    assert "inputs" in result
    assert "people" in result
    assert "project_effective_owners" in result


def test_snapshot_person_record_shape() -> None:
    """Test that each person record in snapshot has required fields."""
    registry = _sample_registry()
    people_state = _empty_people_state()
    board_snapshot = _sample_board_snapshot_mixed()

    result = build_staffing_snapshot.build_staffing_snapshot(
        registry=registry,
        people_state=people_state,
        board_snapshot=board_snapshot,
        today_iso="2026-04-24",
    )

    assert "person1" in result["people"]
    person1 = result["people"]["person1"]

    # Check required fields per PRD
    assert "canonical_person_key" in person1
    assert "display_name" in person1
    assert "availability_status" in person1
    assert "leave_since" in person1
    assert "leave_until" in person1
    assert "bandwidth" in person1
    assert "backup_person_key" in person1
    assert "active_project_ids" in person1
    assert "active_project_titles" in person1
    assert "active_task_ids" in person1
    assert "active_task_titles" in person1
    assert "active_projects" in person1
    assert "active_tasks" in person1
    assert "blocked_tasks" in person1
    assert "overdue_tasks" in person1
    assert "undated_tasks" in person1
    assert "risk_flags" in person1


def test_assignments_from_board_cache_and_registry_only() -> None:
    """Test that assignments derive from board cache + registry only, not people_state."""
    registry = _sample_registry()
    people_state = _empty_people_state()  # No manual assignments in people_state
    board_snapshot = _sample_board_snapshot_mixed()

    result = build_staffing_snapshot.build_staffing_snapshot(
        registry=registry,
        people_state=people_state,
        board_snapshot=board_snapshot,
        today_iso="2026-04-24",
    )

    person1 = result["people"]["person1"]
    # person1 owns task-1 and task-2 in board snapshot
    assert "task-1" in person1["active_task_ids"]
    assert "task-2" in person1["active_task_ids"]
    # person1 owns project-1 in board snapshot
    assert "project-1" in person1["active_project_ids"]


def test_project_effective_owners_with_leave_backup() -> None:
    """Test that project_effective_owners reflects leave + backup substitution."""
    registry = _sample_registry()
    people_state = _people_state_with_leave()  # person1 on leave, backup=person2
    board_snapshot = _sample_board_snapshot_mixed()

    result = build_staffing_snapshot.build_staffing_snapshot(
        registry=registry,
        people_state=people_state,
        board_snapshot=board_snapshot,
        today_iso="2026-04-24",
    )

    assert "project-1" in result["project_effective_owners"]
    project1 = result["project_effective_owners"]["project-1"]

    # Board owner is person1
    assert "board_owner_person_keys" in project1
    assert "person1" in project1["board_owner_person_keys"]

    # Effective owner should substitute person2 (leave + backup)
    assert "effective_owner_person_keys" in project1
    assert "person2" in project1["effective_owner_person_keys"]


def test_missing_people_state_builds_unknown_availability() -> None:
    """Test that snapshot builds from board cache alone when people_state is empty."""
    registry = _sample_registry()
    people_state = _empty_people_state()  # Empty container
    board_snapshot = _sample_board_snapshot_mixed()

    result = build_staffing_snapshot.build_staffing_snapshot(
        registry=registry,
        people_state=people_state,
        board_snapshot=board_snapshot,
        today_iso="2026-04-24",
    )

    # Both registry people should appear
    assert "person1" in result["people"]
    assert "person2" in result["people"]

    # With empty people_state, availability should be unknown
    assert result["people"]["person1"]["availability_status"] == "unknown"
    assert result["people"]["person2"]["availability_status"] == "unknown"

    # Backup should be absent
    assert result["people"]["person1"]["backup_person_key"] is None
    assert result["people"]["person2"]["backup_person_key"] is None


def test_absent_owner_with_backup_yields_effective_owner() -> None:
    """Test absence-with-backup yields correct effective owner substitution."""
    registry = _sample_registry()
    people_state = _people_state_with_leave()
    board_snapshot = _sample_board_snapshot_mixed()

    result = build_staffing_snapshot.build_staffing_snapshot(
        registry=registry,
        people_state=people_state,
        board_snapshot=board_snapshot,
        today_iso="2026-04-24",
    )

    # This test covers SNAP-04: project_effective_owners with substitution
    project1 = result["project_effective_owners"]["project-1"]
    assert "person2" in project1["effective_owner_person_keys"]


def test_unresolved_owner_ids_preserved_in_snapshot() -> None:
    """Test that unresolved board owner IDs are preserved explicitly."""
    registry = _sample_registry()
    people_state = _empty_people_state()
    board_snapshot = _sample_board_snapshot_mixed()

    result = build_staffing_snapshot.build_staffing_snapshot(
        registry=registry,
        people_state=people_state,
        board_snapshot=board_snapshot,
        today_iso="2026-04-24",
    )

    # Unresolved owner IDs should be preserved somewhere in the snapshot
    # (either at top level or in metadata)
    unresolved_found = False
    if "unresolved_owner_ids" in result:
        # Top-level location
        assert "notion-user-unresolved-xyz" in result["unresolved_owner_ids"]
        assert "notion-user-unresolved-999" in result["unresolved_owner_ids"]
        unresolved_found = True
    elif "meta" in result and "unresolved_owner_ids" in result["meta"]:
        # Meta location
        assert "notion-user-unresolved-xyz" in result["meta"]["unresolved_owner_ids"]
        assert "notion-user-unresolved-999" in result["meta"]["unresolved_owner_ids"]
        unresolved_found = True

    assert unresolved_found, "Unresolved owner IDs must be preserved in snapshot"


def test_overdue_blocked_undated_counts_from_board_cache() -> None:
    """Test that overdue, blocked, and undated task counts derive from board cache."""
    registry = _sample_registry()
    people_state = _empty_people_state()
    board_snapshot = _sample_board_snapshot_mixed()

    result = build_staffing_snapshot.build_staffing_snapshot(
        registry=registry,
        people_state=people_state,
        board_snapshot=board_snapshot,
        today_iso="2026-04-24",
    )

    person1 = result["people"]["person1"]
    person2 = result["people"]["person2"]

    # person1 owns task-1 (undated) and task-2 (overdue due 2026-04-20 < 2026-04-24)
    assert person1["undated_tasks"] == 1  # task-1
    assert person1["overdue_tasks"] == 1  # task-2
    assert person1["blocked_tasks"] == 0  # task-1 and task-2 not blocked

    # person2 owns task-3 (blocked by "Waiting on feedback")
    assert person2["blocked_tasks"] == 1  # task-3
    assert person2["overdue_tasks"] == 0  # task-3 due 2026-04-30 is not overdue
    assert person2["undated_tasks"] == 0  # task-3 has a due date


def test_snapshot_has_required_top_level_schema() -> None:
    """Test that snapshot has required top-level schema and structure."""
    registry = _sample_registry()
    people_state = _empty_people_state()
    board_snapshot = _sample_board_snapshot_mixed()

    result = build_staffing_snapshot.build_staffing_snapshot(
        registry=registry,
        people_state=people_state,
        board_snapshot=board_snapshot,
        today_iso="2026-04-24",
    )

    # Top-level schema checks
    assert result["schema_version"] == "1.0"
    assert isinstance(result["generated_at"], str)
    assert result["generated_at"].startswith("20")  # ISO timestamp

    # Inputs section
    assert isinstance(result["inputs"], dict)
    assert "registry_source" in result["inputs"]
    assert "people_state_source" in result["inputs"]
    assert "board_snapshot_source" in result["inputs"]

    # People and projects
    assert isinstance(result["people"], dict)
    assert isinstance(result["project_effective_owners"], dict)


def test_display_name_prefers_registry_notion_name() -> None:
    """Test that display_name prefers registry notion.display_name when present."""
    registry = _sample_registry()
    people_state = _empty_people_state()
    board_snapshot = _sample_board_snapshot_mixed()

    result = build_staffing_snapshot.build_staffing_snapshot(
        registry=registry,
        people_state=people_state,
        board_snapshot=board_snapshot,
        today_iso="2026-04-24",
    )

    person1 = result["people"]["person1"]
    # Registry has notion.display_name="Person One (P1)"
    assert person1["display_name"] == "Person One (P1)"


def test_empty_board_snapshot_lists_all_registry_people_with_zero_assignments() -> None:
    """Test that empty board snapshot still lists all registry people with zero counts."""
    registry = _sample_registry()
    people_state = _empty_people_state()
    empty_board_snapshot = {"records": {"projects": {}, "tasks": {}}}

    result = build_staffing_snapshot.build_staffing_snapshot(
        registry=registry,
        people_state=people_state,
        board_snapshot=empty_board_snapshot,
        today_iso="2026-04-24",
    )

    # All registry people should appear
    assert "person1" in result["people"]
    assert "person2" in result["people"]

    # With no board assignments, counts should be zero
    assert result["people"]["person1"]["active_projects"] == 0
    assert result["people"]["person1"]["active_tasks"] == 0
    assert result["people"]["person2"]["active_projects"] == 0
    assert result["people"]["person2"]["active_tasks"] == 0
