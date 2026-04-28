#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
import re
from typing import Any

from board_config import DEFAULT_BOARD_CONFIG, load as load_board_config

PROJECTS_DATA_SOURCE_ID = DEFAULT_BOARD_CONFIG["projects_data_source_id"]
TASKS_DATA_SOURCE_ID = DEFAULT_BOARD_CONFIG["tasks_data_source_id"]
DEFAULT_DISCORD_CHAT_ID = DEFAULT_BOARD_CONFIG["default_discord_chat_id"]
DEFAULT_DISCORD_CHANNEL_NAME = DEFAULT_BOARD_CONFIG["default_discord_channel_name"]

_PLACEHOLDER_RE = re.compile(r"{{\s*([a-zA-Z0-9_]+)\s*}}")

TEMPLATES: dict[str, dict[str, Any]] = {
    "query_projects_not_done": {
        "kind": "notion_query",
        "description": "Query the Projects data source for rows whose Status is neither Done nor Archived.",
        "defaults": {
            "data_source_id": PROJECTS_DATA_SOURCE_ID,
            "page_size": 100,
        },
        "required_variables": [],
        "request": {
            "filter": {
                "and": [
                    {"property": "Status", "status": {"does_not_equal": "Done"}},
                    {"property": "Status", "status": {"does_not_equal": "Archived"}},
                ]
            },
            "sorts": [
                {"property": "End date", "direction": "ascending"},
                {"property": "Project name", "direction": "ascending"},
            ],
            "page_size": "{{page_size}}",
        },
    },
    "query_tasks_not_done": {
        "kind": "notion_query",
        "description": "Query the Tasks Tracker data source for rows whose Status is not Done.",
        "defaults": {
            "data_source_id": TASKS_DATA_SOURCE_ID,
            "page_size": 100,
        },
        "required_variables": [],
        "request": {
            "filter": {
                "property": "Status",
                "status": {"does_not_equal": "Done"},
            },
            "sorts": [
                {"property": "Due date", "direction": "ascending"},
                {"property": "Task name", "direction": "ascending"},
            ],
            "page_size": "{{page_size}}",
        },
    },
    "query_tasks_missing_owner": {
        "kind": "notion_query",
        "description": "Query active Tasks Tracker rows missing an Assignee.",
        "defaults": {
            "data_source_id": TASKS_DATA_SOURCE_ID,
            "page_size": 100,
        },
        "required_variables": [],
        "request": {
            "filter": {
                "and": [
                    {"property": "Status", "status": {"does_not_equal": "Done"}},
                    {"property": "Assignee", "people": {"is_empty": True}},
                ]
            },
            "sorts": [
                {"property": "Due date", "direction": "ascending"},
                {"property": "Task name", "direction": "ascending"},
            ],
            "page_size": "{{page_size}}",
        },
    },
    "query_tasks_missing_due_date": {
        "kind": "notion_query",
        "description": "Query active Tasks Tracker rows missing a Due date.",
        "defaults": {
            "data_source_id": TASKS_DATA_SOURCE_ID,
            "page_size": 100,
        },
        "required_variables": [],
        "request": {
            "filter": {
                "and": [
                    {"property": "Status", "status": {"does_not_equal": "Done"}},
                    {"property": "Due date", "date": {"is_empty": True}},
                ]
            },
            "sorts": [
                {"property": "Task name", "direction": "ascending"},
            ],
            "page_size": "{{page_size}}",
        },
    },
    "update_page_status": {
        "kind": "notion_patch_page",
        "description": "Patch the Status property of a project/task page.",
        "defaults": {"status_property": "Status"},
        "required_variables": ["page_id", "status_name"],
        "request": {
            "page_id": "{{page_id}}",
            "properties": {
                "{{status_property}}": {
                    "status": {"name": "{{status_name}}"}
                }
            },
        },
    },
    "update_page_rich_text": {
        "kind": "notion_patch_page",
        "description": "Patch a rich-text property on a project/task page.",
        "defaults": {"property_name": "Notes"},
        "required_variables": ["page_id", "text"],
        "request": {
            "page_id": "{{page_id}}",
            "properties": {
                "{{property_name}}": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": "{{text}}"},
                        }
                    ]
                }
            },
        },
    },
    "update_page_date": {
        "kind": "notion_patch_page",
        "description": "Patch a date property on a project/task page.",
        "defaults": {"property_name": "Due date"},
        "required_variables": ["page_id", "date_start"],
        "request": {
            "page_id": "{{page_id}}",
            "properties": {
                "{{property_name}}": {
                    "date": {"start": "{{date_start}}"}
                }
            },
        },
    },
    "lookup_notion_person_by_discord": {
        "kind": "local_identity_lookup",
        "description": "Resolve a Discord sender to canonical person + Notion mapping via the local registry.",
        "defaults": {"platform": "discord"},
        "required_variables": ["platform_user_id"],
        "request": {
            "platform": "{{platform}}",
            "platform_user_id": "{{platform_user_id}}",
            "display_name": "{{display_name}}",
        },
    },
    "prompt_task_due_date_request": {
        "kind": "pending_prompt",
        "description": "Create a validated outbound prompt asking one owner for a task due date.",
        "defaults": {
            "platform": "discord",
            "chat_id": DEFAULT_DISCORD_CHAT_ID,
            "channel_name": DEFAULT_DISCORD_CHANNEL_NAME,
            "question_type": "due_date_request",
            "question_slot": "due_date",
            "priority": "normal",
        },
        "required_variables": [
            "pending_prompt_id",
            "thread_id",
            "assistant_message_id",
            "canonical_person_key",
            "platform_user_id",
            "project_id",
            "project_title",
            "task_id",
            "task_title",
            "display_name",
        ],
        "prompt": {
            "pending_prompt_id": "{{pending_prompt_id}}",
            "status": "open",
            "source": {
                "platform": "{{platform}}",
                "chat_id": "{{chat_id}}",
                "thread_id": "{{thread_id}}",
                "channel_name": "{{channel_name}}",
            },
            "outbound_message": {
                "assistant_message_id": "{{assistant_message_id}}",
                "reply_to_message_id": None,
                "text": "@{{display_name}} — task {{task_title}} của project {{project_title}} chưa có due date. Trả lời YYYY-MM-DD giúp tao.",
            },
            "target": {
                "canonical_person_key": "{{canonical_person_key}}",
                "platform": "{{platform}}",
                "platform_user_id": "{{platform_user_id}}",
            },
            "notion": {
                "project_id": "{{project_id}}",
                "project_title": "{{project_title}}",
                "task_id": "{{task_id}}",
                "task_title": "{{task_title}}",
            },
            "question": {
                "question_type": "{{question_type}}",
                "question_slot": "{{question_slot}}",
                "prompt_summary": "Ask {{display_name}} for the due date of {{task_title}}",
                "expected_answer_shapes": ["date", "short_note"],
                "allowed_update_types": ["due_date_proposal", "task_comment"],
                "priority": "{{priority}}",
            },
        },
    },
    "prompt_task_status_request": {
        "kind": "pending_prompt",
        "description": "Create a validated outbound prompt asking one owner for the latest task status.",
        "defaults": {
            "platform": "discord",
            "chat_id": DEFAULT_DISCORD_CHAT_ID,
            "channel_name": DEFAULT_DISCORD_CHANNEL_NAME,
            "question_type": "status_request",
            "question_slot": "status",
            "priority": "normal",
            "status_choices": "blocked, in progress, waiting review",
        },
        "required_variables": [
            "pending_prompt_id",
            "thread_id",
            "assistant_message_id",
            "canonical_person_key",
            "platform_user_id",
            "project_id",
            "project_title",
            "task_id",
            "task_title",
            "display_name",
        ],
        "prompt": {
            "pending_prompt_id": "{{pending_prompt_id}}",
            "status": "open",
            "source": {
                "platform": "{{platform}}",
                "chat_id": "{{chat_id}}",
                "thread_id": "{{thread_id}}",
                "channel_name": "{{channel_name}}",
            },
            "outbound_message": {
                "assistant_message_id": "{{assistant_message_id}}",
                "reply_to_message_id": None,
                "text": "@{{display_name}} — task {{task_title}} của project {{project_title}} đang ở trạng thái nào? Trả lời một trong các giá trị: {{status_choices}}.",
            },
            "target": {
                "canonical_person_key": "{{canonical_person_key}}",
                "platform": "{{platform}}",
                "platform_user_id": "{{platform_user_id}}",
            },
            "notion": {
                "project_id": "{{project_id}}",
                "project_title": "{{project_title}}",
                "task_id": "{{task_id}}",
                "task_title": "{{task_title}}",
            },
            "question": {
                "question_type": "{{question_type}}",
                "question_slot": "{{question_slot}}",
                "prompt_summary": "Ask {{display_name}} for the latest status of {{task_title}}",
                "expected_answer_shapes": ["status_choice", "short_note"],
                "allowed_update_types": ["status_note", "blocked_note", "task_comment", "owner_ack"],
                "priority": "{{priority}}",
            },
        },
    },
    "inbound_discord_reply_event": {
        "kind": "inbound_event",
        "description": "Build a dry-run/event payload for process_inbound_reply.py.",
        "defaults": {"platform": "discord"},
        "required_variables": ["thread_id", "platform_user_id", "reply_text"],
        "event": {
            "platform": "{{platform}}",
            "thread_id": "{{thread_id}}",
            "platform_user_id": "{{platform_user_id}}",
            "display_name": "{{display_name}}",
            "reply_to_message_id": "{{reply_to_message_id}}",
            "text": "{{reply_text}}",
        },
    },
    "create_project": {
        "kind": "notion_page_create",
        "description": "Create a new project page in the Projects database",
        "defaults": {
            "data_source_id": PROJECTS_DATA_SOURCE_ID,
            "status": "In progress",
        },
        "required_variables": ["project_name"],
        "request": {
            "parent": {
                "database_id": "{{data_source_id}}",
            },
            "properties": {
                "Project name": {
                    "title": [
                        {
                            "type": "text",
                            "text": {"content": "{{project_name}}"},
                        }
                    ]
                },
                "Status": {
                    "status": {"name": "{{status}}"}
                },
            },
        },
    },
    "create_task": {
        "kind": "notion_page_create",
        "description": "Create a new task page in the Tasks database linked to a project",
        "defaults": {
            "data_source_id": TASKS_DATA_SOURCE_ID,
            "status": "To do",
        },
        "required_variables": ["task_name", "project_id"],
        "request": {
            "parent": {
                "database_id": "{{data_source_id}}",
            },
            "properties": {
                "Task name": {
                    "title": [
                        {
                            "type": "text",
                            "text": {"content": "{{task_name}}"},
                        }
                    ]
                },
                "Status": {
                    "status": {"name": "{{status}}"}
                },
                "Projects": {
                    "relation": [{"id": "{{project_id}}"}]
                },
            },
        },
    },
}


def _replace_placeholders(value: Any, variables: dict[str, Any]) -> Any:
    if isinstance(value, dict):
        return {
            _replace_placeholders(key, variables): _replace_placeholders(subvalue, variables)
            for key, subvalue in value.items()
        }
    if isinstance(value, list):
        return [_replace_placeholders(item, variables) for item in value]
    if isinstance(value, str):
        matches = list(_PLACEHOLDER_RE.finditer(value))
        if not matches:
            return value
        if len(matches) == 1 and matches[0].span() == (0, len(value)):
            key = matches[0].group(1)
            if key not in variables:
                raise KeyError(f"Missing placeholder variable: {key}")
            return variables[key]

        def repl(match: re.Match[str]) -> str:
            key = match.group(1)
            if key not in variables:
                raise KeyError(f"Missing placeholder variable: {key}")
            replacement = variables[key]
            return "" if replacement is None else str(replacement)

        return _PLACEHOLDER_RE.sub(repl, value)
    return value


def _collect_placeholders(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, subvalue in value.items():
            found.update(_collect_placeholders(key))
            found.update(_collect_placeholders(subvalue))
    elif isinstance(value, list):
        for item in value:
            found.update(_collect_placeholders(item))
    elif isinstance(value, str):
        found.update(match.group(1) for match in _PLACEHOLDER_RE.finditer(value))
    return found


def list_templates() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for name in sorted(TEMPLATES):
        spec = TEMPLATES[name]
        items.append(
            {
                "name": name,
                "kind": spec["kind"],
                "description": spec["description"],
                "required_variables": list(spec.get("required_variables") or []),
                "defaults": copy.deepcopy(spec.get("defaults") or {}),
            }
        )
    return items


def _apply_runtime_board_defaults(name: str, variables: dict[str, Any]) -> None:
    board_config = load_board_config()
    if name == "query_projects_not_done":
        variables["data_source_id"] = board_config["projects_data_source_id"]
    elif name in {"query_tasks_not_done", "query_tasks_missing_owner", "query_tasks_missing_due_date"}:
        variables["data_source_id"] = board_config["tasks_data_source_id"]
    elif name in {"prompt_task_due_date_request", "prompt_task_status_request"}:
        variables["chat_id"] = board_config["default_discord_chat_id"]
        variables["channel_name"] = board_config["default_discord_channel_name"]
    elif name == "create_project":
        variables["data_source_id"] = board_config["projects_data_source_id"]
    elif name == "create_task":
        variables["data_source_id"] = board_config["tasks_data_source_id"]


def _renderable_sections(spec: dict[str, Any]) -> list[str]:
    return [section for section in ("request", "prompt", "event") if section in spec]


def render_template(name: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
    if name not in TEMPLATES:
        raise KeyError(f"Unknown template: {name}")
    spec = TEMPLATES[name]
    merged_variables = dict(spec.get("defaults") or {})
    _apply_runtime_board_defaults(name, merged_variables)
    if variables:
        merged_variables.update(variables)

    needed: set[str] = set()
    for section in _renderable_sections(spec):
        needed.update(_collect_placeholders(spec[section]))
    missing = sorted(key for key in needed if key not in merged_variables)
    if missing:
        raise KeyError(
            f"Template {name!r} missing required variables: {', '.join(missing)}"
        )

    rendered = copy.deepcopy(spec)
    for section in _renderable_sections(spec):
        rendered[section] = _replace_placeholders(rendered[section], merged_variables)
    rendered["name"] = name
    rendered["profile"] = {
        key: merged_variables[key]
        for key in sorted(rendered.get("defaults") or {})
        if key in merged_variables and (key.endswith("_id") or key in {"platform", "chat_id", "channel_name", "page_size"})
    }
    return rendered


def _parse_vars(items: list[str]) -> dict[str, str | None]:
    parsed: dict[str, str | None] = {}
    for item in items:
        if "=" in item:
            key, value = item.split("=", 1)
            parsed[key] = value
        else:
            parsed[item] = None
    return parsed


def main() -> None:
    parser = argparse.ArgumentParser(description="List and render reusable Notion Scrum templates")
    parser.add_argument("--list", action="store_true", help="List available templates")
    parser.add_argument("--template", help="Template name to render")
    parser.add_argument(
        "--var",
        action="append",
        default=[],
        help="Template variable in key=value form. Repeat as needed.",
    )
    args = parser.parse_args()

    if args.list:
        print(json.dumps({"templates": list_templates()}, ensure_ascii=False, indent=2))
        return
    if not args.template:
        raise SystemExit("Use --list or provide --template <name>")

    rendered = render_template(args.template, variables=_parse_vars(args.var))
    print(json.dumps(rendered, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
