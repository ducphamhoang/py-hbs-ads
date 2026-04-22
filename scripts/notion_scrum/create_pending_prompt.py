#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from audit import AuditEventType, append_event
from common import DEFAULT_AUDIT_LOG, DEFAULT_PENDING_PROMPTS
from prompt_store import append_prompt, validate_prompt_schema
from result_contracts import build_result


def create_prompt(
    prompt: dict,
    *,
    state_path: Path = DEFAULT_PENDING_PROMPTS,
    audit_log_path: Path = DEFAULT_AUDIT_LOG,
) -> dict:
    entry = dict(prompt)
    entry.setdefault("status", "open")
    errors = validate_prompt_schema(entry)
    pending_prompt_id = entry.get("pending_prompt_id")
    if errors:
        return build_result(
            ok=False,
            action_taken="validation_failed",
            pending_prompt_id=pending_prompt_id,
            errors=errors,
            data={"prompt": entry},
        )

    append_prompt(state_path, entry)
    append_event(
        audit_log_path,
        AuditEventType.PROMPT_RECORDED,
        pending_prompt_id=pending_prompt_id,
        thread_id=((entry.get("source") or {}).get("thread_id")),
        task_id=((entry.get("notion") or {}).get("task_id")),
        target_person=((entry.get("target") or {}).get("canonical_person_key")),
    )
    return build_result(
        ok=True,
        action_taken="prompt_recorded",
        pending_prompt_id=pending_prompt_id,
        audit_events=[AuditEventType.PROMPT_RECORDED.value],
        data={"prompt": entry},
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a validated pending scrum prompt")
    parser.add_argument("--state", type=Path, default=DEFAULT_PENDING_PROMPTS)
    parser.add_argument("--audit-log", type=Path, default=DEFAULT_AUDIT_LOG)
    args = parser.parse_args()

    raw = sys.stdin.read().strip()
    if not raw:
        raise SystemExit("Expected prompt JSON on stdin")
    result = create_prompt(
        json.loads(raw),
        state_path=args.state,
        audit_log_path=args.audit_log,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
