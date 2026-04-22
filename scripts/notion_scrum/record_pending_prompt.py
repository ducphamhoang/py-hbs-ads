
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from audit import AuditEventType, append_event
from common import DEFAULT_AUDIT_LOG, DEFAULT_PENDING_PROMPTS, stdin_json
from prompt_store import append_prompt


def main() -> None:
    parser = argparse.ArgumentParser(description="Record a pending scrum prompt")
    parser.add_argument("--state", type=Path, default=DEFAULT_PENDING_PROMPTS)
    parser.add_argument("--audit-log", type=Path, default=DEFAULT_AUDIT_LOG)
    args = parser.parse_args()

    incoming = stdin_json()
    prompt = dict(incoming)
    append_prompt(args.state, prompt)

    append_event(
        args.audit_log,
        AuditEventType.PROMPT_RECORDED,
        pending_prompt_id=prompt.get("pending_prompt_id"),
        thread_id=((prompt.get("source") or {}).get("thread_id")),
        task_id=((prompt.get("notion") or {}).get("task_id")),
        target_person=((prompt.get("target") or {}).get("canonical_person_key")),
    )
    print(json.dumps({"success": True, "pending_prompt_id": prompt.get("pending_prompt_id")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
