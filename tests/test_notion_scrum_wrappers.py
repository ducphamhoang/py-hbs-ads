from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts" / "notion_scrum"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import prepare_inbound_event
import prepare_notion_patch
import prepare_prompt
import prompt_store
import query_common_view
import template_catalog


def test_query_common_view_active_projects_uses_projects_template() -> None:
    result = query_common_view.prepare_view("active-projects")

    assert result["view"] == "active-projects"
    assert result["template_name"] == "query_projects_not_done"
    assert result["request"]["filter"] == {
        "and": [
            {"property": "Status", "status": {"does_not_equal": "Done"}},
            {"property": "Status", "status": {"does_not_equal": "Archived"}},
        ]
    }
    assert result["data_source_id"] == template_catalog.PROJECTS_DATA_SOURCE_ID


def test_query_common_view_rejects_unknown_view() -> None:
    with pytest.raises(KeyError):
        query_common_view.prepare_view("does-not-exist")


def test_prepare_prompt_due_date_request_returns_valid_prompt_payload() -> None:
    result = prepare_prompt.prepare_prompt(
        "task-due-date",
        variables={
            "pending_prompt_id": "pp_due_1",
            "thread_id": "thread-1",
            "assistant_message_id": "assistant-1",
            "canonical_person_key": "ma",
            "platform_user_id": "discord-user-ma",
            "project_id": "project-1",
            "project_title": "Game teaser 03",
            "task_id": "task-1",
            "task_title": "rough cut v1",
            "display_name": "Ma",
        },
    )

    assert result["kind"] == "task-due-date"
    assert result["template_name"] == "prompt_task_due_date_request"
    assert prompt_store.validate_prompt_schema(result["prompt"]) == []


def test_prepare_notion_patch_status_maps_to_status_template() -> None:
    result = prepare_notion_patch.prepare_patch(
        "status",
        variables={
            "page_id": "page-123",
            "status_name": "Done",
        },
    )

    assert result["kind"] == "status"
    assert result["template_name"] == "update_page_status"
    assert result["request"]["properties"]["Status"]["status"]["name"] == "Done"


def test_prepare_inbound_event_builds_event_payload() -> None:
    result = prepare_inbound_event.prepare_event(
        variables={
            "thread_id": "thread-1",
            "platform_user_id": "discord-user-ducph",
            "display_name": "Duc",
            "reply_to_message_id": "assistant-1",
            "reply_text": "2026-04-25",
        }
    )

    assert result["template_name"] == "inbound_discord_reply_event"
    assert result["event"]["platform"] == "discord"
    assert result["event"]["text"] == "2026-04-25"
