from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts" / "notion_scrum"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import board_cache


PROJECT_PAGE = {
    "id": "project-1",
    "url": "https://notion.so/project-1",
    "last_edited_time": "2026-04-23T09:00:00Z",
    "properties": {
        "Project name": {"type": "title", "title": [{"plain_text": "Project Alpha"}]},
        "Status": {"type": "status", "status": {"name": "In progress"}},
        "End date": {"type": "date", "date": {"start": "2026-04-25"}},
        "Project lead": {
            "type": "people",
            "people": [{"id": "notion-user-1", "name": "Po (myntt7)"}],
        },
    },
}

TASK_PAGE_A = {
    "id": "task-1",
    "url": "https://notion.so/task-1",
    "last_edited_time": "2026-04-23T09:10:00Z",
    "properties": {
        "Task name": {"type": "title", "title": [{"plain_text": "AE polish pass"}]},
        "Status": {"type": "status", "status": {"name": "Not started"}},
        "Due date": {"type": "date", "date": None},
        "Assignee": {
            "type": "people",
            "people": [{"id": "notion-user-1", "name": "Po (myntt7)"}],
        },
        "Projects 1": {"type": "relation", "relation": [{"id": "project-1"}]},
    },
}

TASK_PAGE_B = {
    "id": "task-2",
    "url": "https://notion.so/task-2",
    "last_edited_time": "2026-04-23T09:20:00Z",
    "properties": {
        "Task name": {"type": "title", "title": [{"plain_text": "AE polish pass"}]},
        "Status": {"type": "status", "status": {"name": "Not started"}},
        "Due date": {"type": "date", "date": {"start": "2026-04-26"}},
        "Assignee": {"type": "people", "people": []},
        "Projects 1": {"type": "relation", "relation": [{"id": "project-1"}]},
    },
}


def test_build_snapshot_creates_exact_title_indexes_and_record_maps() -> None:
    snapshot = board_cache.build_snapshot(
        project_pages=[PROJECT_PAGE],
        task_pages=[TASK_PAGE_A, TASK_PAGE_B],
        fetched_at="2026-04-23T09:30:00Z",
        projects_data_source_id="projects-ds",
        tasks_data_source_id="tasks-ds",
    )

    assert snapshot["meta"]["project_count"] == 1
    assert snapshot["meta"]["task_count"] == 2
    assert snapshot["indexes"]["projects_by_title"]["Project Alpha"] == ["project-1"]
    assert snapshot["indexes"]["tasks_by_title"]["AE polish pass"] == ["task-1", "task-2"]
    assert snapshot["records"]["projects"]["project-1"]["owner_ids"] == ["notion-user-1"]
    assert snapshot["records"]["tasks"]["task-1"]["project_ids"] == ["project-1"]
    assert snapshot["records"]["tasks"]["task-2"]["project_titles"] == ["Project Alpha"]


def test_lookup_exact_title_returns_all_matching_ids() -> None:
    snapshot = board_cache.build_snapshot(
        project_pages=[PROJECT_PAGE],
        task_pages=[TASK_PAGE_A, TASK_PAGE_B],
        fetched_at="2026-04-23T09:30:00Z",
        projects_data_source_id="projects-ds",
        tasks_data_source_id="tasks-ds",
    )

    assert board_cache.lookup_exact_title(snapshot, kind="tasks", title="AE polish pass") == ["task-1", "task-2"]
    assert board_cache.lookup_exact_title(snapshot, kind="projects", title="Project Alpha") == ["project-1"]
    assert board_cache.lookup_exact_title(snapshot, kind="tasks", title="missing") == []


def test_sync_cache_paginates_queries_and_writes_snapshot(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    responses = {
        "projects-ds": [
            {"results": [PROJECT_PAGE], "has_more": False, "next_cursor": None},
        ],
        "tasks-ds": [
            {"results": [TASK_PAGE_A], "has_more": True, "next_cursor": "cursor-1"},
            {"results": [TASK_PAGE_B], "has_more": False, "next_cursor": None},
        ],
    }
    calls: list[tuple[str, dict]] = []

    def fake_notion_request(api_key: str, method: str, url: str, data: dict | None = None) -> dict:
        assert api_key == "fake-key"
        assert method == "POST"
        ds_id = url.rstrip("/").split("/")[-2]
        calls.append((ds_id, dict(data or {})))
        payload = responses[ds_id].pop(0)
        return json.loads(json.dumps(payload))

    monkeypatch.setattr(board_cache, "load_api_key", lambda: "fake-key")
    monkeypatch.setattr(board_cache, "notion_request", fake_notion_request)

    cache_path = tmp_path / "board_snapshot.json"
    result = board_cache.sync_cache(
        cache_path=cache_path,
        projects_data_source_id="projects-ds",
        tasks_data_source_id="tasks-ds",
        fetched_at="2026-04-23T09:30:00Z",
    )

    assert result["ok"] is True
    assert result["action_taken"] == "cache_synced"
    assert result["data"]["project_count"] == 1
    assert result["data"]["task_count"] == 2
    assert len(calls) == 3
    assert calls[1][1].get("start_cursor") is None
    assert calls[2][1]["start_cursor"] == "cursor-1"

    snapshot = json.loads(cache_path.read_text(encoding="utf-8"))
    assert snapshot["meta"]["generated_at"] == "2026-04-23T09:30:00Z"
    assert snapshot["records"]["tasks"]["task-2"]["due_date"] == "2026-04-26"


def test_sync_cache_reports_incomplete_pagination_when_cursor_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def fake_notion_request(api_key: str, method: str, url: str, data: dict | None = None) -> dict:
        return {"results": [PROJECT_PAGE], "has_more": True, "next_cursor": ""}

    monkeypatch.setattr(board_cache, "load_api_key", lambda: "fake-key")
    monkeypatch.setattr(board_cache, "notion_request", fake_notion_request)

    result = board_cache.sync_cache(
        cache_path=tmp_path / "board_snapshot.json",
        projects_data_source_id="projects-ds",
        tasks_data_source_id="tasks-ds",
        fetched_at="2026-04-23T09:30:00Z",
    )

    assert result["ok"] is False
    assert result["action_taken"] == "cache_sync_failed"
    assert "incomplete pagination" in result["errors"][0]


def test_resolve_target_auto_uses_cache_fast_path_when_snapshot_is_fresh(monkeypatch: pytest.MonkeyPatch) -> None:
    snapshot = board_cache.build_snapshot(
        project_pages=[PROJECT_PAGE],
        task_pages=[TASK_PAGE_A],
        fetched_at="2026-04-23T09:30:00Z",
        projects_data_source_id="projects-ds",
        tasks_data_source_id="tasks-ds",
    )

    def fail_live_fetch(*args, **kwargs):
        raise AssertionError("live revalidation should not run on fresh auto fast-path")

    monkeypatch.setattr(board_cache, "load_api_key", lambda: "fake-key")
    monkeypatch.setattr(board_cache, "notion_request", fail_live_fetch)

    result = board_cache.resolve_target(
        snapshot=snapshot,
        kind="tasks",
        title="AE polish pass",
        project_title="Project Alpha",
        mode="auto",
        now_iso="2026-04-23T09:35:00Z",
        max_cache_age_seconds=900,
    )

    assert result["ok"] is True
    assert result["action_taken"] == "target_resolved_from_cache"
    assert result["data"]["resolved_id"] == "task-1"
    assert result["data"]["used_live_revalidation"] is False


def test_resolve_target_safe_revalidates_live_page_when_snapshot_is_stale(monkeypatch: pytest.MonkeyPatch) -> None:
    snapshot = board_cache.build_snapshot(
        project_pages=[PROJECT_PAGE],
        task_pages=[TASK_PAGE_A],
        fetched_at="2026-04-23T09:30:00Z",
        projects_data_source_id="projects-ds",
        tasks_data_source_id="tasks-ds",
    )
    calls: list[tuple[str, str]] = []

    def fake_notion_request(api_key: str, method: str, url: str, data: dict | None = None) -> dict:
        calls.append((method, url))
        assert api_key == "fake-key"
        assert method == "GET"
        assert url.endswith("/task-1")
        return json.loads(json.dumps(TASK_PAGE_A))

    monkeypatch.setattr(board_cache, "load_api_key", lambda: "fake-key")
    monkeypatch.setattr(board_cache, "notion_request", fake_notion_request)

    result = board_cache.resolve_target(
        snapshot=snapshot,
        kind="tasks",
        title="AE polish pass",
        project_title="Project Alpha",
        mode="safe",
        now_iso="2026-04-23T10:30:00Z",
        max_cache_age_seconds=900,
    )

    assert result["ok"] is True
    assert result["action_taken"] == "target_resolved_after_live_check"
    assert result["data"]["resolved_id"] == "task-1"
    assert result["data"]["used_live_revalidation"] is True
    assert calls == [("GET", "https://api.notion.com/v1/pages/task-1")]


def test_resolve_target_safe_revalidates_even_when_snapshot_is_fresh(monkeypatch: pytest.MonkeyPatch) -> None:
    snapshot = board_cache.build_snapshot(
        project_pages=[PROJECT_PAGE],
        task_pages=[TASK_PAGE_A],
        fetched_at="2026-04-23T09:30:00Z",
        projects_data_source_id="projects-ds",
        tasks_data_source_id="tasks-ds",
    )
    calls: list[tuple[str, str]] = []

    def fake_notion_request(api_key: str, method: str, url: str, data: dict | None = None) -> dict:
        calls.append((method, url))
        return json.loads(json.dumps(TASK_PAGE_A))

    monkeypatch.setattr(board_cache, "load_api_key", lambda: "fake-key")
    monkeypatch.setattr(board_cache, "notion_request", fake_notion_request)

    result = board_cache.resolve_target(
        snapshot=snapshot,
        kind="tasks",
        title="AE polish pass",
        project_title="Project Alpha",
        mode="safe",
        now_iso="2026-04-23T09:35:00Z",
        max_cache_age_seconds=900,
    )

    assert result["ok"] is True
    assert result["data"]["used_live_revalidation"] is True
    assert calls == [("GET", "https://api.notion.com/v1/pages/task-1")]


def test_resolve_target_live_revalidation_fails_on_title_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    snapshot = board_cache.build_snapshot(
        project_pages=[PROJECT_PAGE],
        task_pages=[TASK_PAGE_A],
        fetched_at="2026-04-23T09:30:00Z",
        projects_data_source_id="projects-ds",
        tasks_data_source_id="tasks-ds",
    )
    mismatched_page = json.loads(json.dumps(TASK_PAGE_A))
    mismatched_page["properties"]["Task name"]["title"][0]["plain_text"] = "Different task"

    monkeypatch.setattr(board_cache, "load_api_key", lambda: "fake-key")
    monkeypatch.setattr(board_cache, "notion_request", lambda *args, **kwargs: mismatched_page)

    result = board_cache.resolve_target(
        snapshot=snapshot,
        kind="tasks",
        title="AE polish pass",
        project_title="Project Alpha",
        mode="safe",
        now_iso="2026-04-23T09:35:00Z",
        max_cache_age_seconds=900,
    )

    assert result["ok"] is False
    assert result["action_taken"] == "live_revalidation_failed"
    assert "title mismatch" in result["errors"][0]


def test_resolve_target_fast_mode_rejects_stale_snapshot_without_live_call(monkeypatch: pytest.MonkeyPatch) -> None:
    snapshot = board_cache.build_snapshot(
        project_pages=[PROJECT_PAGE],
        task_pages=[TASK_PAGE_A],
        fetched_at="2026-04-23T09:30:00Z",
        projects_data_source_id="projects-ds",
        tasks_data_source_id="tasks-ds",
    )

    def fail_live_fetch(*args, **kwargs):
        raise AssertionError("fast mode should never live revalidate")

    monkeypatch.setattr(board_cache, "load_api_key", lambda: "fake-key")
    monkeypatch.setattr(board_cache, "notion_request", fail_live_fetch)

    result = board_cache.resolve_target(
        snapshot=snapshot,
        kind="tasks",
        title="AE polish pass",
        project_title="Project Alpha",
        mode="fast",
        now_iso="2026-04-23T10:30:00Z",
        max_cache_age_seconds=900,
    )

    assert result["ok"] is False
    assert result["action_taken"] == "cache_stale"
    assert "stale" in result["errors"][0]


def test_resolve_target_ambiguous_includes_candidate_record_summaries() -> None:
    snapshot = board_cache.build_snapshot(
        project_pages=[PROJECT_PAGE],
        task_pages=[TASK_PAGE_A, TASK_PAGE_B],
        fetched_at="2026-04-23T09:30:00Z",
        projects_data_source_id="projects-ds",
        tasks_data_source_id="tasks-ds",
    )

    result = board_cache.resolve_target(
        snapshot=snapshot,
        kind="tasks",
        title="AE polish pass",
        mode="auto",
        now_iso="2026-04-23T09:35:00Z",
        max_cache_age_seconds=900,
    )

    assert result["ok"] is False
    assert result["action_taken"] == "target_ambiguous"
    summaries = result["data"]["candidate_records"]
    assert len(summaries) == 2
    assert summaries[0]["id"] == "task-1"
    assert summaries[0]["title"] == "AE polish pass"
    assert "Project Alpha" in result["data"]["ambiguity_message"]
