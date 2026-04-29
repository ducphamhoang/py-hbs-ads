from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts" / "notion_scrum"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import board_cache
import update_by_title

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


def test_parse_free_text_status_update_for_task() -> None:
    parsed = update_by_title.parse_instruction("set task AE polish pass of project Project Alpha to In progress")

    assert parsed == {
        "target_kind": "tasks",
        "title": "AE polish pass",
        "project_title": "Project Alpha",
        "patch_kind": "status",
        "patch_variables": {"status_name": "In progress"},
    }


def test_parse_free_text_due_date_update_for_task() -> None:
    parsed = update_by_title.parse_instruction("set due date of task AE polish pass of project Project Alpha to 2026-04-30")

    assert parsed == {
        "target_kind": "tasks",
        "title": "AE polish pass",
        "project_title": "Project Alpha",
        "patch_kind": "date",
        "patch_variables": {"property_name": "Due date", "date_start": "2026-04-30"},
    }


def test_parse_free_text_note_update_for_task() -> None:
    parsed = update_by_title.parse_instruction("note on task AE polish pass of project Project Alpha: blocked by missing asset")

    assert parsed == {
        "target_kind": "tasks",
        "title": "AE polish pass",
        "project_title": "Project Alpha",
        "patch_kind": "rich-text",
        "patch_variables": {"property_name": "Notes", "text": "blocked by missing asset"},
    }


def test_parse_vietnamese_status_update_for_task() -> None:
    parsed = update_by_title.parse_instruction("đổi status task AE polish pass của project Project Alpha thành In progress")

    assert parsed == {
        "target_kind": "tasks",
        "title": "AE polish pass",
        "project_title": "Project Alpha",
        "patch_kind": "status",
        "patch_variables": {"status_name": "In progress"},
    }


def test_parse_vietnamese_due_date_update_for_task() -> None:
    parsed = update_by_title.parse_instruction("đặt due date task AE polish pass của project Project Alpha là 2026-04-30")

    assert parsed == {
        "target_kind": "tasks",
        "title": "AE polish pass",
        "project_title": "Project Alpha",
        "patch_kind": "date",
        "patch_variables": {"property_name": "Due date", "date_start": "2026-04-30"},
    }


def test_parse_vietnamese_note_update_for_task() -> None:
    parsed = update_by_title.parse_instruction("ghi note cho task AE polish pass của project Project Alpha: blocked by missing asset")

    assert parsed == {
        "target_kind": "tasks",
        "title": "AE polish pass",
        "project_title": "Project Alpha",
        "patch_kind": "rich-text",
        "patch_variables": {"property_name": "Notes", "text": "blocked by missing asset"},
    }


def test_parse_block_task_sets_status_and_blocked_reason() -> None:
    parsed = update_by_title.parse_instruction("block task AE polish pass of project Project Alpha because missing asset")

    assert parsed == {
        "target_kind": "tasks",
        "title": "AE polish pass",
        "project_title": "Project Alpha",
        "patch_kind": "multi",
        "patch_variables": {
            "patches": [
                {"kind": "status", "variables": {"status_name": "Blocked"}},
                {"kind": "rich-text", "variables": {"property_name": "Blocked reason", "text": "missing asset"}},
            ]
        },
    }


def test_parse_vietnamese_block_task_sets_status_and_blocked_reason() -> None:
    parsed = update_by_title.parse_instruction("đánh dấu blocked task AE polish pass của project Project Alpha vì missing asset")

    assert parsed == {
        "target_kind": "tasks",
        "title": "AE polish pass",
        "project_title": "Project Alpha",
        "patch_kind": "multi",
        "patch_variables": {
            "patches": [
                {"kind": "status", "variables": {"status_name": "Blocked"}},
                {"kind": "rich-text", "variables": {"property_name": "Blocked reason", "text": "missing asset"}},
            ]
        },
    }


def test_build_request_normalizes_due_date_formats() -> None:
    request = update_by_title.build_request(
        instruction=None,
        target_kind="tasks",
        title="AE polish pass",
        project_title="Project Alpha",
        status=None,
        due_date="30/04/2026",
        note=None,
        blocked_reason=None,
    )

    assert request["patch_kind"] == "date"
    assert request["patch_variables"] == {"property_name": "Due date", "date_start": "2026-04-30"}


def test_build_request_supports_explicit_blocked_reason() -> None:
    request = update_by_title.build_request(
        instruction=None,
        target_kind="tasks",
        title="AE polish pass",
        project_title="Project Alpha",
        status=None,
        due_date=None,
        note=None,
        blocked_reason="missing asset",
    )

    assert request["patch_kind"] == "multi"
    assert request["patch_variables"]["patches"][0]["variables"] == {"status_name": "Blocked"}


def test_build_request_rejects_invalid_due_date() -> None:
    with pytest.raises(ValueError):
        update_by_title.build_request(
            instruction=None,
            target_kind="tasks",
            title="AE polish pass",
            project_title="Project Alpha",
            status=None,
            due_date="2026-99-99",
            note=None,
            blocked_reason=None,
        )


def test_build_request_from_kwargs_prefers_explicit_fields() -> None:
    request = update_by_title.build_request(
        instruction=None,
        target_kind="tasks",
        title="AE polish pass",
        project_title="Project Alpha",
        status="In progress",
        due_date=None,
        note=None,
    )

    assert request["patch_kind"] == "status"
    assert request["patch_variables"] == {"status_name": "In progress"}


def test_execute_update_by_title_calls_apply_wrapper(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = {}

    def fake_apply(**kwargs):
        captured.update(kwargs)
        return {"ok": True, "action_taken": "patch_applied", "write_applied": True, "data": {"page_id": "task-1"}}

    monkeypatch.setattr(update_by_title, "apply_patch_from_resolved_target", fake_apply)

    result = update_by_title.execute_update_by_title(
        snapshot=_snapshot(),
        instruction="set task AE polish pass of project Project Alpha to In progress",
        target_kind=None,
        title=None,
        project_title=None,
        status=None,
        due_date=None,
        note=None,
        resolve_mode="auto",
        max_cache_age_seconds=900,
        execute=True,
        now_iso="2026-04-23T09:35:00Z",
    )

    assert result["ok"] is True
    assert captured["target_kind"] == "tasks"
    assert captured["title"] == "AE polish pass"
    assert captured["project_title"] == "Project Alpha"
    assert captured["patch_kind"] == "status"
    assert captured["patch_variables"] == {"status_name": "In progress"}


def test_execute_update_by_title_adds_user_hint_for_ambiguity(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_apply(**kwargs):
        return {
            "ok": False,
            "action_taken": "target_ambiguous",
            "write_applied": False,
            "data": {"ambiguity_message": "Task 'AE polish pass' đang match nhiều rows."},
        }

    monkeypatch.setattr(update_by_title, "apply_patch_from_resolved_target", fake_apply)

    result = update_by_title.execute_update_by_title(
        snapshot=_snapshot(),
        instruction="set task AE polish pass of project Project Alpha to In progress",
        target_kind=None,
        title=None,
        project_title=None,
        status=None,
        due_date=None,
        note=None,
        resolve_mode="auto",
        max_cache_age_seconds=900,
        execute=False,
        now_iso="2026-04-23T09:35:00Z",
    )

    assert result["ok"] is False
    assert result["data"]["user_hint"] == "Task 'AE polish pass' đang match nhiều rows."


def test_build_request_rejects_multiple_update_intents() -> None:
    with pytest.raises(ValueError):
        update_by_title.build_request(
            instruction=None,
            target_kind="tasks",
            title="AE polish pass",
            project_title="Project Alpha",
            status="In progress",
            due_date="2026-04-30",
            note=None,
        )
