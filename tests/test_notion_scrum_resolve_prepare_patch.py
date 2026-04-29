from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts" / "notion_scrum"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import board_cache
import resolve_and_prepare_patch

PROJECT_PAGE = {
    "id": "project-1",
    "url": "https://notion.so/project-1",
    "last_edited_time": "2026-04-23T09:00:00Z",
    "properties": {
        "Project name": {"type": "title", "title": [{"plain_text": "Project Alpha"}]},
        "Status": {"type": "status", "status": {"name": "In progress"}},
    },
}

TASK_PAGE = {
    "id": "task-1",
    "url": "https://notion.so/task-1",
    "last_edited_time": "2026-04-23T09:10:00Z",
    "properties": {
        "Task name": {"type": "title", "title": [{"plain_text": "AE polish pass"}]},
        "Status": {"type": "status", "status": {"name": "Not started"}},
        "Due date": {"type": "date", "date": None},
        "Assignee": {"type": "people", "people": []},
        "Projects 1": {"type": "relation", "relation": [{"id": "project-1"}]},
    },
}


def _snapshot() -> dict:
    return board_cache.build_snapshot(
        project_pages=[PROJECT_PAGE],
        task_pages=[TASK_PAGE],
        fetched_at="2026-04-23T09:30:00Z",
        projects_data_source_id="projects-ds",
        tasks_data_source_id="tasks-ds",
    )


def test_prepare_patch_from_resolved_target_builds_patch_payload() -> None:
    result = resolve_and_prepare_patch.prepare_patch_from_resolved_target(
        snapshot=_snapshot(),
        target_kind="tasks",
        title="AE polish pass",
        project_title="Project Alpha",
        patch_kind="status",
        patch_variables={"status_name": "In progress"},
        resolve_mode="auto",
        now_iso="2026-04-23T09:35:00Z",
        max_cache_age_seconds=900,
    )

    assert result["ok"] is True
    assert result["action_taken"] == "patch_prepared_from_resolved_target"
    assert result["data"]["resolved_target"]["resolved_id"] == "task-1"
    assert result["data"]["patch"]["request"]["page_id"] == "task-1"
    assert result["data"]["patch"]["request"]["properties"]["Status"]["status"]["name"] == "In progress"


def test_prepare_patch_from_resolved_target_propagates_resolution_failure() -> None:
    result = resolve_and_prepare_patch.prepare_patch_from_resolved_target(
        snapshot=_snapshot(),
        target_kind="tasks",
        title="missing",
        project_title="Project Alpha",
        patch_kind="status",
        patch_variables={"status_name": "In progress"},
        resolve_mode="auto",
        now_iso="2026-04-23T09:35:00Z",
        max_cache_age_seconds=900,
    )

    assert result["ok"] is False
    assert result["action_taken"] == "target_not_found"
    assert result["data"]["patch_kind"] == "status"


def test_prepare_patch_from_resolved_target_builds_due_date_property_patch() -> None:
    result = resolve_and_prepare_patch.prepare_patch_from_resolved_target(
        snapshot=_snapshot(),
        target_kind="tasks",
        title="AE polish pass",
        project_title="Project Alpha",
        patch_kind="date",
        patch_variables={"property_name": "Due date", "date_start": "2026-04-30"},
        resolve_mode="auto",
        now_iso="2026-04-23T09:35:00Z",
        max_cache_age_seconds=900,
    )

    assert result["ok"] is True
    assert result["data"]["patch"]["request"]["page_id"] == "task-1"
    assert result["data"]["patch"]["request"]["properties"]["Due date"]["date"]["start"] == "2026-04-30"


def test_prepare_patch_from_resolved_target_handles_unknown_patch_kind_gracefully() -> None:
    result = resolve_and_prepare_patch.prepare_patch_from_resolved_target(
        snapshot=_snapshot(),
        target_kind="tasks",
        title="AE polish pass",
        project_title="Project Alpha",
        patch_kind="unknown-kind",
        patch_variables={},
        resolve_mode="auto",
        now_iso="2026-04-23T09:35:00Z",
        max_cache_age_seconds=900,
    )

    assert result["ok"] is False
    assert result["action_taken"] == "patch_prepare_failed"
    assert "Unknown patch kind" in result["errors"][0]


def test_prepare_patch_from_resolved_target_requires_patch_variables() -> None:
    result = resolve_and_prepare_patch.prepare_patch_from_resolved_target(
        snapshot=_snapshot(),
        target_kind="tasks",
        title="AE polish pass",
        project_title="Project Alpha",
        patch_kind="status",
        patch_variables={},
        resolve_mode="auto",
        now_iso="2026-04-23T09:35:00Z",
        max_cache_age_seconds=900,
    )

    assert result["ok"] is False
    assert result["action_taken"] == "patch_prepare_failed"
    assert "status_name" in result["errors"][0]
