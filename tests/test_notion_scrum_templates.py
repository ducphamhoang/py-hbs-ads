from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts" / "notion_scrum"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import prompt_store
import template_catalog


REQUIRED_TEMPLATE_NAMES = {
    "query_projects_not_done",
    "query_tasks_not_done",
    "query_tasks_missing_owner",
    "query_tasks_missing_due_date",
    "update_page_status",
    "update_page_rich_text",
    "lookup_notion_person_by_discord",
    "prompt_task_due_date_request",
    "prompt_task_status_request",
    "inbound_discord_reply_event",
}


def test_list_templates_exposes_common_catalog_names() -> None:
    names = {item["name"] for item in template_catalog.list_templates()}

    assert REQUIRED_TEMPLATE_NAMES <= names


def test_render_query_projects_not_done_uses_projects_defaults() -> None:
    rendered = template_catalog.render_template("query_projects_not_done")

    assert rendered["kind"] == "notion_query"
    assert rendered["profile"]["data_source_id"] == template_catalog.PROJECTS_DATA_SOURCE_ID
    assert rendered["request"]["filter"] == {
        "and": [
            {"property": "Status", "status": {"does_not_equal": "Done"}},
            {"property": "Status", "status": {"does_not_equal": "Archived"}},
        ]
    }


def test_render_prompt_task_due_date_request_substitutes_fields_and_stays_valid() -> None:
    rendered = template_catalog.render_template(
        "prompt_task_due_date_request",
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

    prompt = rendered["prompt"]
    assert prompt_store.validate_prompt_schema(prompt) == []
    assert prompt["target"]["platform_user_id"] == "discord-user-ma"
    assert "Game teaser 03" in prompt["outbound_message"]["text"]
    assert "rough cut v1" in prompt["outbound_message"]["text"]
    assert "YYYY-MM-DD" in prompt["outbound_message"]["text"]


def test_render_update_page_status_substitutes_page_id_and_status() -> None:
    rendered = template_catalog.render_template(
        "update_page_status",
        variables={
            "page_id": "page-123",
            "status_name": "In progress",
        },
    )

    assert rendered["kind"] == "notion_patch_page"
    assert rendered["request"]["page_id"] == "page-123"
    assert rendered["request"]["properties"] == {
        "Status": {"status": {"name": "In progress"}},
    }


def test_render_template_raises_for_missing_required_variables() -> None:
    with pytest.raises(KeyError):
        template_catalog.render_template("update_page_status")
