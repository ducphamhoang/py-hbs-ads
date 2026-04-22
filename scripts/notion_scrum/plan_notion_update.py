
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from common import DEFAULT_AUDIT_LOG, append_jsonl, normalize_text, utc_now_iso

ALLOWED_TYPES = {"task_comment", "status_note", "blocked_note", "due_date_proposal", "owner_ack", "mark_prompt_answered"}
DATE_PATTERN = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")


def infer_update_type(text: str) -> tuple[str, str | None]:
    norm = normalize_text(text)
    if not norm:
        return "mark_prompt_answered", None
    if "blocked" in norm or "kẹt" in norm or "vướng" in norm:
        return "blocked_note", text
    if DATE_PATTERN.search(text or ""):
        return "due_date_proposal", text
    if any(token in norm for token in ["ok", "đã nhận", "received", "noted"]):
        return "owner_ack", text
    return "task_comment", text


def plan_update(*, prompt: dict, event: dict, matched: dict) -> dict:
    allowed = set(((prompt.get("question") or {}).get("allowed_update_types")) or [])
    inferred_type, inferred_value = infer_update_type(event.get("text", ""))
    safe = bool(matched.get("matched")) and inferred_type in ALLOWED_TYPES and (not allowed or inferred_type in allowed)
    return {
        "safe_to_apply": safe,
        "pending_prompt_id": prompt.get("pending_prompt_id"),
        "confidence": matched.get("confidence", 0.0),
        "resolved_update_type": inferred_type,
        "resolved_value": inferred_value,
        "task_id": ((prompt.get("notion") or {}).get("task_id")),
        "project_id": ((prompt.get("notion") or {}).get("project_id")),
        "reason": None if safe else "unsafe_or_disallowed_update_type",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Plan a safe Notion update from matched reply")
    parser.add_argument("--audit-log", type=Path, default=DEFAULT_AUDIT_LOG)
    args = parser.parse_args()

    payload = json.load(sys.stdin)
    plan = plan_update(
        prompt=payload.get("prompt") or {},
        event=payload.get("event") or {},
        matched=payload.get("match") or {},
    )

    append_jsonl(args.audit_log, {
        "timestamp": utc_now_iso(),
        "event_type": "update_planned",
        "pending_prompt_id": plan["pending_prompt_id"],
        "update_type": plan["resolved_update_type"],
        "safe_to_apply": plan["safe_to_apply"],
        "confidence": plan["confidence"],
    })
    print(json.dumps(plan, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
