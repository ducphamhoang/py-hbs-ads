#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from common import DEFAULT_AUDIT_LOG, DEFAULT_PENDING_PROMPTS, DEFAULT_TEAM_REGISTRY, load_registry
from match_inbound_reply import match_reply
from notion_adapter import apply_actions
from person_resolution import resolve_platform_identity
from plan_notion_update import plan_update
from prompt_store import get_open_prompts
from result_contracts import build_result


def _event_from_payload(payload: dict) -> dict:
    return dict(payload.get("event") or payload)


def _find_prompt(prompts: list[dict], pending_prompt_id: str | None) -> dict | None:
    for prompt in prompts:
        if prompt.get("pending_prompt_id") == pending_prompt_id:
            return prompt
    return None


def process_inbound_reply(
    event: dict,
    *,
    execute: bool = False,
    registry_path: Path = DEFAULT_TEAM_REGISTRY,
    state_path: Path = DEFAULT_PENDING_PROMPTS,
    audit_log_path: Path = DEFAULT_AUDIT_LOG,
) -> dict:
    working_event = dict(event)
    registry = load_registry(registry_path)
    person = resolve_platform_identity(
        registry,
        working_event.get("platform"),
        working_event.get("platform_user_id"),
    )
    canonical_person_key = (person or {}).get("canonical_person_key")
    if canonical_person_key:
        working_event["canonical_person_key"] = canonical_person_key
    else:
        return build_result(
            ok=False,
            action_taken="clarification_needed",
            requires_clarification=True,
            clarification_reason="identity_unresolved",
            canonical_person_key=working_event.get("canonical_person_key"),
            errors=["sender identity could not be resolved from platform user id"],
            data={"event": working_event},
        )

    prompts = get_open_prompts(state_path)
    matched = match_reply(event=working_event, prompts=prompts)
    if not matched.get("matched"):
        return build_result(
            ok=False,
            action_taken="clarification_needed",
            requires_clarification=True,
            clarification_reason=matched.get("clarification_reason"),
            canonical_person_key=canonical_person_key,
            data={"event": working_event, "match": matched},
        )

    prompt = _find_prompt(prompts, matched.get("pending_prompt_id"))
    if prompt is None:
        return build_result(
            ok=False,
            action_taken="clarification_needed",
            requires_clarification=True,
            clarification_reason="matched_prompt_missing",
            canonical_person_key=canonical_person_key,
            matched_prompt_id=matched.get("pending_prompt_id"),
            errors=["matched prompt is no longer open or could not be found"],
            data={"event": working_event, "match": matched},
        )

    plan = plan_update(prompt=prompt, event=working_event, matched=matched)
    if not plan.get("safe_to_apply"):
        return build_result(
            ok=False,
            action_taken="clarification_needed",
            requires_clarification=True,
            clarification_reason=plan.get("reason") or "unsafe_update",
            pending_prompt_id=prompt.get("pending_prompt_id"),
            canonical_person_key=canonical_person_key,
            matched_prompt_id=matched.get("pending_prompt_id"),
            resolved_update_type=plan.get("resolved_update_type"),
            data={"event": working_event, "match": matched, "plan": plan},
        )

    applied = apply_actions(
        plan=plan,
        prompt=prompt,
        event=working_event,
        execute=execute,
        registry_path=registry_path,
        state_path=state_path,
        audit_log_path=audit_log_path,
    )
    write_applied = bool(execute and applied.get("success"))
    return build_result(
        ok=bool(applied.get("success")),
        action_taken="write_applied" if write_applied else "dry_run_planned",
        write_applied=write_applied,
        pending_prompt_id=prompt.get("pending_prompt_id"),
        canonical_person_key=canonical_person_key,
        matched_prompt_id=matched.get("pending_prompt_id"),
        resolved_update_type=plan.get("resolved_update_type"),
        audit_events=["notion_write"],
        data={
            "event": working_event,
            "match": matched,
            "plan": plan,
            "apply": applied,
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Process an inbound Scrum reply")
    parser.add_argument("--execute", action="store_true", help="Actually write to Notion. Default is dry-run.")
    parser.add_argument("--registry", type=Path, default=DEFAULT_TEAM_REGISTRY)
    parser.add_argument("--state", type=Path, default=DEFAULT_PENDING_PROMPTS)
    parser.add_argument("--audit-log", type=Path, default=DEFAULT_AUDIT_LOG)
    args = parser.parse_args()

    raw = sys.stdin.read().strip()
    if not raw:
        raise SystemExit("Expected event JSON on stdin")
    result = process_inbound_reply(
        _event_from_payload(json.loads(raw)),
        execute=args.execute,
        registry_path=args.registry,
        state_path=args.state,
        audit_log_path=args.audit_log,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
