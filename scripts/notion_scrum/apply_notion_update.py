
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from audit import AuditEventType, append_event
from common import (
    DEFAULT_AUDIT_LOG,
    DEFAULT_PENDING_PROMPTS,
    DEFAULT_TEAM_REGISTRY,
    load_api_key,
    notion_append_blocks,
    notion_patch_page,
    paragraph_block,
)
from lookup_notion_person import lookup_person
from person_resolution import build_actor_label as format_actor_label
from prompt_store import mark_answered


def build_actor_label(event: dict, registry_path: Path = DEFAULT_TEAM_REGISTRY) -> str:
    person = lookup_person(
        canonical_person_key=event.get("canonical_person_key"),
        platform=event.get("platform"),
        platform_user_id=event.get("platform_user_id"),
        registry_path=registry_path,
    )
    person_dict = None
    if person.get("mapping_source") == "registry":
        person_dict = {
            "canonical_person_key": person.get("canonical_person_key"),
            "notion": person.get("notion") or {},
        }
    elif person.get("canonical_person_key"):
        person_dict = {"canonical_person_key": person.get("canonical_person_key")}
    return format_actor_label(person_dict, fallback=event)


def build_comment_text(plan: dict, event: dict, prompt: dict, registry_path: Path = DEFAULT_TEAM_REGISTRY) -> str:
    actor = build_actor_label(event, registry_path=registry_path)
    notion = prompt.get("notion") or {}
    target_title = notion.get("task_title") or notion.get("project_title") or "task"
    return f"[Hermes Scrum] Reply from {actor} on {target_title}: {event.get('text', '').strip()}"


def build_actions(plan: dict, prompt: dict, event: dict, registry_path: Path = DEFAULT_TEAM_REGISTRY) -> list[dict]:
    update_type = plan.get("resolved_update_type")
    task_id = plan.get("task_id")
    project_id = plan.get("project_id")
    comment_block_id = task_id or project_id
    actions: list[dict] = []
    if update_type in {"task_comment", "status_note", "blocked_note", "owner_ack", "due_date_proposal"} and comment_block_id:
        actions.append({
            "action": "append_block_comment",
            "block_id": comment_block_id,
            "text": build_comment_text(plan, event, prompt, registry_path=registry_path),
        })
    if update_type == "due_date_proposal" and task_id:
        actions.append({
            "action": "patch_page_property",
            "page_id": task_id,
            "properties": {
                "Due date note": {
                    "rich_text": [{"type": "text", "text": {"content": str(plan.get('resolved_value') or '')[:1800]}}]
                }
            },
        })
    return actions


def apply_update(
    *,
    plan: dict,
    prompt: dict,
    event: dict,
    execute: bool,
    registry_path: Path = DEFAULT_TEAM_REGISTRY,
    state_path: Path = DEFAULT_PENDING_PROMPTS,
    audit_log_path: Path = DEFAULT_AUDIT_LOG,
) -> dict:
    if not plan.get("safe_to_apply"):
        result = {"success": False, "dry_run": not execute, "reason": "plan_not_safe"}
        append_event(
            audit_log_path,
            AuditEventType.NOTION_WRITE_BLOCKED,
            pending_prompt_id=prompt.get("pending_prompt_id"),
            task_id=plan.get("task_id"),
            update_type=plan.get("resolved_update_type"),
            dry_run=not execute,
            success=False,
            reason="plan_not_safe",
        )
        return result

    update_type = plan.get("resolved_update_type")
    task_id = plan.get("task_id")
    dry_run = not execute
    actions = build_actions(plan, prompt, event, registry_path=registry_path)

    api_calls = []
    if execute:
        api_key = load_api_key()
        for action in actions:
            if action["action"] == "append_block_comment":
                api_calls.append(notion_append_blocks(api_key, action["block_id"], [paragraph_block(action["text"])]))
            elif action["action"] == "patch_page_property":
                api_calls.append(notion_patch_page(api_key, action["page_id"], action["properties"]))
        pending_prompt_id = prompt.get("pending_prompt_id")
        if pending_prompt_id:
            mark_answered(
                state_path,
                pending_prompt_id,
                resolved_update_type=plan.get("resolved_update_type"),
                resolved_value=plan.get("resolved_value"),
                resolution_notes=event.get("text"),
            )
    result = {
        "success": True,
        "dry_run": dry_run,
        "update_type": update_type,
        "actions": actions,
        "api_call_count": len(api_calls),
    }
    append_event(
        audit_log_path,
        AuditEventType.NOTION_WRITE,
        pending_prompt_id=prompt.get("pending_prompt_id"),
        task_id=task_id,
        update_type=update_type,
        dry_run=dry_run,
        success=True,
        actor_label=build_actor_label(event, registry_path=registry_path),
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply a safe Notion update")
    parser.add_argument("--execute", action="store_true", help="Actually write to Notion. Default is dry-run.")
    parser.add_argument("--audit-log", type=Path, default=DEFAULT_AUDIT_LOG)
    parser.add_argument("--registry", type=Path, default=DEFAULT_TEAM_REGISTRY)
    parser.add_argument("--state", type=Path, default=DEFAULT_PENDING_PROMPTS)
    args = parser.parse_args()

    payload = json.load(sys.stdin)
    result = apply_update(
        plan=payload.get("plan") or {},
        prompt=payload.get("prompt") or {},
        event=payload.get("event") or {},
        execute=args.execute,
        registry_path=args.registry,
        state_path=args.state,
        audit_log_path=args.audit_log,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
