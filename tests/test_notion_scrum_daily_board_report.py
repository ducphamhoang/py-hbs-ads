from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts" / "notion_scrum"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import daily_board_report


PROJECT_WITH_TEMPLATE_ONLY = {
    "id": "project-1",
    "title": "[CTB] V AI - Demon Awakening",
    "status": "In progress",
    "end_date": "2026-04-23",
    "owner_names": ["HungCT"],
    "owner_person_keys": ["hungct"],
    "task_ids": [],
}

PROJECT_WITH_REAL_CONTENT_AND_DOD = {
    "id": "project-2",
    "title": "[AI] Improve Virtual AI Tester - part 3",
    "status": "In progress",
    "end_date": "2026-04-28",
    "owner_names": ["duc phan"],
    "owner_person_keys": ["ducplc"],
    "task_ids": ["task-1"],
}


def test_analyze_project_hygiene_flags_missing_subtasks_unclear_content_and_missing_dod() -> None:
    blocks = [
        {"type": "heading_3", "text": "About project"},
        {"type": "paragraph", "text": "Provide an overview of the project’s goals and context"},
        {"type": "heading_3", "text": "Action items"},
        {"type": "to_do", "text": ""},
    ]

    result = daily_board_report.analyze_project_hygiene(PROJECT_WITH_TEMPLATE_ONLY, blocks)

    assert result["missing_subtasks"] is True
    assert result["unclear_content"] is True
    assert result["missing_definition_of_done"] is True


def test_analyze_project_hygiene_accepts_real_content_and_definition_of_done() -> None:
    blocks = [
        {"type": "heading_3", "text": "About project"},
        {"type": "paragraph", "text": "Tạo Agentic AI có thể autoplay game trên Unity Editor."},
        {"type": "paragraph", "text": "Definition of Done: autoplay được flow target trong Unity Editor với log rõ ràng."},
        {"type": "bulleted_list_item", "text": "Evidence expectation: repeatable run with observable artifacts."},
    ]

    result = daily_board_report.analyze_project_hygiene(PROJECT_WITH_REAL_CONTENT_AND_DOD, blocks)

    assert result["missing_subtasks"] is False
    assert result["unclear_content"] is False
    assert result["missing_definition_of_done"] is False


def test_format_daily_check_message_includes_new_project_hygiene_sections() -> None:
    report = {
        "generated_at_ict": "2026-04-24 10:04 ICT",
        "counts": {
            "active_projects": 6,
            "active_tasks": 12,
            "overdue_tasks": 1,
            "missing_due_date": 8,
            "missing_owner": 4,
            "projects_missing_subtasks": 1,
            "projects_unclear_content": 2,
            "projects_missing_definition_of_done": 3,
        },
        "action_items": [],
        "ownerless_tasks": [],
        "undated_tasks": [],
        "projects_missing_subtasks": [
            {
                "title": "[CTB] V AI - Demon Awakening",
                "owner_person_keys": ["hungct"],
                "owner_names": ["HungCT"],
            }
        ],
        "projects_unclear_content": [
            {
                "title": "[CTB] V AI - Demon Awakening",
                "owner_person_keys": ["hungct"],
                "owner_names": ["HungCT"],
            },
            {
                "title": "[CTB] V - Market Practice - DDigger",
                "owner_person_keys": [],
                "owner_names": ["Po (myntt7)"],
            },
        ],
        "projects_missing_definition_of_done": [
            {
                "title": "[CTB] V AI - Demon Awakening",
                "owner_person_keys": ["hungct"],
                "owner_names": ["HungCT"],
            }
        ],
    }

    message = daily_board_report.format_daily_check_message(
        report,
        discord_identity_by_person={"hungct": {"mention": "<@779207417295798304>", "user_id": "779207417295798304"}},
    )

    assert "Projects thiếu sub task: 1" in message
    assert "Projects thiếu nội dung rõ ràng: 2" in message
    assert "Projects thiếu DoD: 3" in message
    assert "**Cảnh báo theo project**" in message
    assert message.count("[CTB] V AI - Demon Awakening") == 1
    assert "(HungCT) project **[CTB] V AI - Demon Awakening** thiếu: **sub task; nội dung rõ ràng; Definition of Done**" in message
    assert "Po (myntt7) project **[CTB] V - Market Practice - DDigger** thiếu: **nội dung rõ ràng**" in message


def test_owner_label_can_emit_tokenized_discord_mentions_for_cron_reconstruction() -> None:
    label = daily_board_report._owner_label(
        ["hungct"],
        {"hungct": {"mention": "<@***>", "user_id": "779207417295798304"}},
        ["HungCT"],
        mention_style="token",
    )

    assert label == "@@discord_user_id:779207417295798304@@ (HungCT)"


def test_project_data_warnings_are_grouped_into_single_project_line() -> None:
    report = {
        "generated_at_ict": "2026-04-24 10:04 ICT",
        "counts": {
            "active_projects": 1,
            "active_tasks": 4,
            "overdue_tasks": 0,
            "missing_due_date": 4,
            "missing_owner": 4,
            "projects_missing_subtasks": 1,
            "projects_unclear_content": 0,
            "projects_missing_definition_of_done": 0,
        },
        "action_items": [],
        "projects_missing_subtasks": [
            {
                "title": "[CTB] V - Meme US",
                "owner_person_keys": [],
                "owner_names": [],
            }
        ],
        "projects_unclear_content": [],
        "projects_missing_definition_of_done": [],
        "ownerless_tasks": [
            {
                "title": "AE polish pass",
                "project_titles": ["[CTB] V - Meme US"],
                "owner_person_keys": [],
                "owner_names": [],
            },
            {
                "title": "Unity implementation pass",
                "project_titles": ["[CTB] V - Meme US"],
                "owner_person_keys": [],
                "owner_names": [],
            },
        ],
        "undated_tasks": [
            {
                "title": "AE polish pass",
                "project_titles": ["[CTB] V - Meme US"],
                "owner_person_keys": [],
                "owner_names": [],
            },
            {
                "title": "Unity implementation pass",
                "project_titles": ["[CTB] V - Meme US"],
                "owner_person_keys": [],
                "owner_names": [],
            },
        ],
    }

    message = daily_board_report.format_daily_check_message(report, discord_identity_by_person={})

    assert message.count("[CTB] V - Meme US") == 1
    assert "project **[CTB] V - Meme US** thiếu: **sub task; 2 task thiếu owner (AE polish pass; Unity implementation pass); 2 task thiếu due date (AE polish pass; Unity implementation pass)**" in message


import json

FAKE_RISKS = {
    "schema_version": "1.0",
    "generated_at": "2026-04-24T00:00:00+07:00",
    "thresholds": {"overload_projects": 3, "overload_tasks": 8},
    "risks": {
        "absent_owner_tasks": [
            {"task_id": "t1", "task_title": "Fix bug", "owner_key": "alice", "backup_key": "bob"}
        ],
        "absent_owner_projects": [
            {"project_id": "p1", "project_title": "Proj Alpha", "owner_key": "alice"}
        ],
        "absent_no_backup": [
            {"person_key": "carol", "display_name": "Carol"}
        ],
        "overloaded_owners": [
            {"person_key": "dave", "display_name": "Dave", "active_projects": 4, "active_tasks": 9}
        ],
        "reduced_bandwidth_with_overdue": [
            {"person_key": "eve", "display_name": "Eve", "bandwidth": 0.5, "overdue_tasks": 3}
        ],
    },
}


def _minimal_report_base() -> dict:
    """Return the minimal dict that format_daily_check_message currently requires."""
    return {
        "generated_at_ict": "2026-04-24 10:04 ICT",
        "counts": {
            "active_projects": 0,
            "active_tasks": 0,
            "overdue_tasks": 0,
            "missing_due_date": 0,
            "missing_owner": 0,
            "projects_missing_subtasks": 0,
            "projects_unclear_content": 0,
            "projects_missing_definition_of_done": 0,
        },
        "action_items": [],
        "ownerless_tasks": [],
        "undated_tasks": [],
        "projects_missing_subtasks": [],
        "projects_unclear_content": [],
        "projects_missing_definition_of_done": [],
    }


def test_build_report_returns_none_staffing_risks_when_snapshot_absent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """RED: build_report result dict should have staffing_risks=None when snapshot file is absent."""
    registry = {"people": {}, "identity_index": {}, "pending_people": []}
    monkeypatch.setattr(daily_board_report, "load_api_key", lambda: "fake-key")
    monkeypatch.setattr(daily_board_report, "_read_json", lambda path: registry)
    monkeypatch.setattr(daily_board_report, "_query_all", lambda api_key, view_name: [])
    monkeypatch.setattr(daily_board_report, "_fetch_block_texts", lambda api_key, block_id: [])

    report, _ = daily_board_report.build_report(root=tmp_path)

    assert report["staffing_risks"] is None


def test_build_report_populates_staffing_risks_when_snapshot_present(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """RED: build_report should call staffing_risk.detect_risks and include result when snapshot exists."""
    registry = {"people": {}, "identity_index": {}, "pending_people": []}
    snapshot_path = tmp_path / "state" / "notion_scrum" / "cache" / "staffing_snapshot.json"
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_data = {"people": {}, "schema_version": "1.0"}
    snapshot_path.write_text(json.dumps(snapshot_data))

    def _read_json_side_effect(path):
        if Path(path) == snapshot_path:
            return snapshot_data
        return registry

    class _MockStaffingRisk:
        @staticmethod
        def detect_risks(snapshot):
            return FAKE_RISKS

    monkeypatch.setattr(daily_board_report, "load_api_key", lambda: "fake-key")
    monkeypatch.setattr(daily_board_report, "_read_json", _read_json_side_effect)
    monkeypatch.setattr(daily_board_report, "_query_all", lambda api_key, view_name: [])
    monkeypatch.setattr(daily_board_report, "_fetch_block_texts", lambda api_key, block_id: [])
    monkeypatch.setattr(daily_board_report, "staffing_risk", _MockStaffingRisk)

    report, _ = daily_board_report.build_report(root=tmp_path)

    assert report["staffing_risks"] is not None
    assert isinstance(report["staffing_risks"]["risks"]["absent_owner_tasks"], list)


def test_format_daily_check_message_renders_staffing_sections_when_risks_present() -> None:
    """RED: formatter should render a staffing section header when staffing_risks present."""
    report = _minimal_report_base()
    report["staffing_risks"] = FAKE_RISKS

    message = daily_board_report.format_daily_check_message(
        report,
        discord_identity_by_person={
            "alice": {"mention": "<@ALICE_ID>", "user_id": "ALICE_ID"},
            "bob": {"mention": "<@BOB_ID>", "user_id": "BOB_DISCORD_ID"},
        },
    )

    assert "Nhân sự" in message


def test_format_daily_check_message_with_no_staffing_risks_produces_no_staffing_section() -> None:
    """Should NOT crash and should NOT render staffing header when staffing_risks is None."""
    report = _minimal_report_base()
    report["staffing_risks"] = None

    message = daily_board_report.format_daily_check_message(report, discord_identity_by_person={})

    assert "Nhân sự vắng mặt" not in message
    assert "staffing_risks" in report  # trivially true — confirms test ran


def test_format_daily_check_message_includes_backup_discord_token_for_absent_owner_task() -> None:
    """RED: formatter should include backup owner's discord token for absent_owner_tasks."""
    report = _minimal_report_base()
    report["staffing_risks"] = FAKE_RISKS  # absent_owner_tasks has backup_key="bob"

    message = daily_board_report.format_daily_check_message(
        report,
        discord_identity_by_person={
            "bob": {"mention": "<@BOB_ID>", "user_id": "BOB_DISCORD_ID"},
        },
    )

    assert "@@discord_user_id:BOB_DISCORD_ID@@" in message


def test_build_report_filters_archived_projects_and_their_tasks(monkeypatch: pytest.MonkeyPatch) -> None:
    registry = {"people": {}, "identity_index": {}, "pending_people": []}
    active_project_page = {
        "id": "project-active",
        "url": "https://notion.so/project-active",
        "last_edited_time": "2026-04-24T00:00:00Z",
        "properties": {
            "Project name": {"type": "title", "title": [{"plain_text": "Project Active"}]},
            "Status": {"type": "status", "status": {"name": "In progress"}},
            "Tasks Tracker": {"type": "relation", "relation": [{"id": "task-active"}]},
            "Assignee": {"type": "people", "people": []},
        },
    }
    archived_project_page = {
        "id": "project-archived",
        "url": "https://notion.so/project-archived",
        "last_edited_time": "2026-04-24T00:00:00Z",
        "properties": {
            "Project name": {"type": "title", "title": [{"plain_text": "Project Archived"}]},
            "Status": {"type": "status", "status": {"name": "Archived"}},
            "Tasks Tracker": {"type": "relation", "relation": [{"id": "task-archived"}]},
            "Assignee": {"type": "people", "people": []},
        },
    }
    task_active = {
        "id": "task-active",
        "url": "https://notion.so/task-active",
        "last_edited_time": "2026-04-24T00:00:00Z",
        "properties": {
            "Task name": {"type": "title", "title": [{"plain_text": "Active task"}]},
            "Status": {"type": "status", "status": {"name": "In progress"}},
            "Due date": {"type": "date", "date": {"start": "2026-04-24"}},
            "Assignee": {"type": "people", "people": []},
            "Projects 1": {"type": "relation", "relation": [{"id": "project-active"}]},
        },
    }
    task_archived = {
        "id": "task-archived",
        "url": "https://notion.so/task-archived",
        "last_edited_time": "2026-04-24T00:00:00Z",
        "properties": {
            "Task name": {"type": "title", "title": [{"plain_text": "Archived task"}]},
            "Status": {"type": "status", "status": {"name": "In progress"}},
            "Due date": {"type": "date", "date": {"start": "2026-04-24"}},
            "Assignee": {"type": "people", "people": []},
            "Projects 1": {"type": "relation", "relation": [{"id": "project-archived"}]},
        },
    }

    pages_by_view = {
        "active-projects": [active_project_page, archived_project_page],
        "active-tasks": [task_active, task_archived],
        "ownerless-active-tasks": [task_active, task_archived],
        "undated-active-tasks": [],
    }

    monkeypatch.setattr(daily_board_report, "load_api_key", lambda: "fake-key")
    monkeypatch.setattr(daily_board_report, "_read_json", lambda path: registry)
    monkeypatch.setattr(daily_board_report, "_query_all", lambda api_key, view_name: pages_by_view[view_name])
    monkeypatch.setattr(daily_board_report, "_fetch_block_texts", lambda api_key, block_id: [])

    report, _ = daily_board_report.build_report(root=Path("~/work/py-hbs-ads").expanduser())

    assert report["counts"]["active_projects"] == 1
    assert report["counts"]["active_tasks"] == 1
    assert report["action_items"][0]["project"] == "Project Active"
    assert all(item["project_titles"] == ["Project Active"] for item in report["ownerless_tasks"])
