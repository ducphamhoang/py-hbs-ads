
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import DEFAULT_AUDIT_LOG, DEFAULT_PENDING_PROMPTS, DEFAULT_TEAM_REGISTRY, append_jsonl, load_json, utc_now_iso


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate scrum workflow local state")
    parser.add_argument("--registry", type=Path, default=DEFAULT_TEAM_REGISTRY)
    parser.add_argument("--state", type=Path, default=DEFAULT_PENDING_PROMPTS)
    parser.add_argument("--audit-log", type=Path, default=DEFAULT_AUDIT_LOG)
    args = parser.parse_args()

    warnings = []
    registry = load_json(args.registry, default={"people": {}, "identity_index": {}})
    state = load_json(args.state, default={"prompts": []})

    people = registry.get("people", {})
    idx = registry.get("identity_index", {})
    for ext_key, canonical in idx.items():
        if canonical not in people:
            warnings.append(f"identity_index points to missing person: {ext_key} -> {canonical}")

    seen = set()
    for prompt in state.get("prompts", []):
        ppid = prompt.get("pending_prompt_id")
        if not ppid:
            warnings.append("prompt missing pending_prompt_id")
            continue
        if ppid in seen:
            warnings.append(f"duplicate pending_prompt_id: {ppid}")
        seen.add(ppid)
        if prompt.get("status") == "open":
            source = prompt.get("source") or {}
            notion = prompt.get("notion") or {}
            question = prompt.get("question") or {}
            if not source.get("thread_id"):
                warnings.append(f"open prompt missing thread_id: {ppid}")
            if not notion.get("task_id") and not notion.get("project_id"):
                warnings.append(f"open prompt missing notion target: {ppid}")
            if not question.get("allowed_update_types"):
                warnings.append(f"open prompt missing allowed_update_types: {ppid}")

    for warning in warnings:
        append_jsonl(args.audit_log, {
            "timestamp": utc_now_iso(),
            "event_type": "state_doctor_warning",
            "warning": warning,
        })

    print(json.dumps({
        "ok": not warnings,
        "warning_count": len(warnings),
        "warnings": warnings,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
