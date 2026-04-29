from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts" / "notion_scrum"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import board_cache
import resolve_prepare_apply_patch

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


def test_apply_patch_from_resolved_target_dry_run_skips_write() -> None:
    result = resolve_prepare_apply_patch.apply_patch_from_resolved_target(
        snapshot=_snapshot(),
        target_kind="tasks",
        title="AE polish pass",
        project_title="Project Alpha",
        patch_kind="status",
        patch_variables={"status_name": "In progress"},
        resolve_mode="auto",
        max_cache_age_seconds=900,
        execute=False,
        now_iso="2026-04-23T09:35:00Z",
    )

    assert result["ok"] is True
    assert result["action_taken"] == "patch_dry_run_prepared"
    assert result["write_applied"] is False
    assert result["data"]["patch"]["request"]["page_id"] == "task-1"


def test_apply_patch_from_resolved_target_execute_calls_notion_patch(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, dict]] = []

    monkeypatch.setattr(resolve_prepare_apply_patch, "load_api_key", lambda: "fake-key")

    def fake_patch(api_key: str, page_id: str, properties: dict) -> dict:
        calls.append((page_id, properties))
        assert api_key == "fake-key"
        return {"ok": True, "page_id": page_id}

    monkeypatch.setattr(resolve_prepare_apply_patch, "notion_patch_page", fake_patch)

    result = resolve_prepare_apply_patch.apply_patch_from_resolved_target(
        snapshot=_snapshot(),
        target_kind="tasks",
        title="AE polish pass",
        project_title="Project Alpha",
        patch_kind="status",
        patch_variables={"status_name": "In progress"},
        resolve_mode="auto",
        max_cache_age_seconds=900,
        execute=True,
        now_iso="2026-04-23T09:35:00Z",
    )

    assert result["ok"] is True
    assert result["action_taken"] == "patch_applied"
    assert result["write_applied"] is True
    assert calls == [("task-1", {"Status": {"status": {"name": "In progress"}}})]


def test_apply_patch_from_resolved_target_execute_supports_multi_patch(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, dict]] = []

    monkeypatch.setattr(resolve_prepare_apply_patch, "load_api_key", lambda: "fake-key")

    def fake_patch(api_key: str, page_id: str, properties: dict) -> dict:
        calls.append((page_id, properties))
        return {"ok": True, "page_id": page_id, "properties": properties}

    monkeypatch.setattr(resolve_prepare_apply_patch, "notion_patch_page", fake_patch)

    result = resolve_prepare_apply_patch.apply_patch_from_resolved_target(
        snapshot=_snapshot(),
        target_kind="tasks",
        title="AE polish pass",
        project_title="Project Alpha",
        patch_kind="multi",
        patch_variables={
            "patches": [
                {"kind": "status", "variables": {"status_name": "Blocked"}},
                {"kind": "rich-text", "variables": {"property_name": "Blocked reason", "text": "missing asset"}},
            ]
        },
        resolve_mode="auto",
        max_cache_age_seconds=900,
        execute=True,
        now_iso="2026-04-23T09:35:00Z",
    )

    assert result["ok"] is True
    assert result["write_applied"] is True
    assert len(calls) == 2
    assert calls[0][1] == {"Status": {"status": {"name": "Blocked"}}}
    assert calls[1][1] == {"Blocked reason": {"rich_text": [{"type": "text", "text": {"content": "missing asset"}}]}}


def test_apply_patch_from_resolved_target_multi_patch_returns_structured_partial_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, dict]] = []

    monkeypatch.setattr(resolve_prepare_apply_patch, "load_api_key", lambda: "fake-key")

    def fake_patch(api_key: str, page_id: str, properties: dict) -> dict:
        calls.append((page_id, properties))
        if len(calls) == 2:
            raise RuntimeError("second patch failed")
        return {"ok": True}

    monkeypatch.setattr(resolve_prepare_apply_patch, "notion_patch_page", fake_patch)

    result = resolve_prepare_apply_patch.apply_patch_from_resolved_target(
        snapshot=_snapshot(),
        target_kind="tasks",
        title="AE polish pass",
        project_title="Project Alpha",
        patch_kind="multi",
        patch_variables={
            "patches": [
                {"kind": "status", "variables": {"status_name": "Blocked"}},
                {"kind": "rich-text", "variables": {"property_name": "Blocked reason", "text": "missing asset"}},
            ]
        },
        resolve_mode="auto",
        max_cache_age_seconds=900,
        execute=True,
        now_iso="2026-04-23T09:35:00Z",
    )

    assert result["ok"] is False
    assert result["action_taken"] == "patch_apply_failed"
    assert result["write_applied"] is True
    assert result["data"]["applied_count"] == 1


def test_apply_patch_from_resolved_target_rejects_missing_page_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        resolve_prepare_apply_patch,
        "prepare_patch_from_resolved_target",
        lambda **kwargs: {"ok": True, "data": {"patch": {"kind": "status", "request": {"page_id": None, "properties": {}}}}},
    )

    result = resolve_prepare_apply_patch.apply_patch_from_resolved_target(
        snapshot=_snapshot(),
        target_kind="tasks",
        title="AE polish pass",
        project_title="Project Alpha",
        patch_kind="status",
        patch_variables={"status_name": "In progress"},
        resolve_mode="auto",
        max_cache_age_seconds=900,
        execute=True,
        now_iso="2026-04-23T09:35:00Z",
    )

    assert result["ok"] is False
    assert result["action_taken"] == "patch_prepare_failed"
    assert "missing page_id" in result["errors"][0]


def test_apply_patch_from_resolved_target_propagates_resolution_failure() -> None:
    result = resolve_prepare_apply_patch.apply_patch_from_resolved_target(
        snapshot=_snapshot(),
        target_kind="tasks",
        title="missing",
        project_title="Project Alpha",
        patch_kind="status",
        patch_variables={"status_name": "In progress"},
        resolve_mode="auto",
        max_cache_age_seconds=900,
        execute=True,
        now_iso="2026-04-23T09:35:00Z",
    )

    assert result["ok"] is False
    assert result["action_taken"] == "target_not_found"
    assert result["write_applied"] is False
