#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from audit import AuditEventType, append_event
from common import DEFAULT_AUDIT_LOG, DEFAULT_PENDING_PROMPTS, DEFAULT_TEAM_REGISTRY, load_registry
from prompt_store import load_prompts, validate_prompt_schema
from result_contracts import build_result


def run_preflight(
    *,
    registry_path: Path = DEFAULT_TEAM_REGISTRY,
    state_path: Path = DEFAULT_PENDING_PROMPTS,
    audit_log_path: Path = DEFAULT_AUDIT_LOG,
) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    registry = load_registry(registry_path)
    prompts = load_prompts(state_path)

    people = registry.get("people") or {}
    identity_index = registry.get("identity_index") or {}
    for external_key, canonical_key in identity_index.items():
        if canonical_key not in people:
            errors.append(f"identity_index points to missing person: {external_key} -> {canonical_key}")

    for canonical_key, person in people.items():
        if person.get("status") == "inactive":
            continue
        notion = person.get("notion") or {}
        if not notion.get("user_id") and not notion.get("people_page_id"):
            warnings.append(f"unresolved Notion mapping: {canonical_key}")

    seen_prompt_ids: set[str] = set()
    for prompt in prompts:
        pending_prompt_id = prompt.get("pending_prompt_id")
        if pending_prompt_id in seen_prompt_ids:
            errors.append(f"duplicate pending_prompt_id: {pending_prompt_id}")
        elif pending_prompt_id:
            seen_prompt_ids.add(pending_prompt_id)

        for schema_error in validate_prompt_schema(prompt):
            errors.append(schema_error)

    append_event(
        audit_log_path,
        AuditEventType.PREFLIGHT_RUN,
        ok=not errors,
        error_count=len(errors),
        warning_count=len(warnings),
        prompt_count=len(prompts),
        registry_people_count=len(people),
    )

    return build_result(
        ok=not errors,
        action_taken="preflight_run",
        audit_events=[AuditEventType.PREFLIGHT_RUN.value],
        errors=errors,
        data={
            "warnings": warnings,
            "error_count": len(errors),
            "warning_count": len(warnings),
            "prompt_count": len(prompts),
            "registry_people_count": len(people),
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate Notion Scrum workflow state")
    parser.add_argument("--registry", type=Path, default=DEFAULT_TEAM_REGISTRY)
    parser.add_argument("--state", type=Path, default=DEFAULT_PENDING_PROMPTS)
    parser.add_argument("--audit-log", type=Path, default=DEFAULT_AUDIT_LOG)
    args = parser.parse_args()

    result = run_preflight(
        registry_path=args.registry,
        state_path=args.state,
        audit_log_path=args.audit_log,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
