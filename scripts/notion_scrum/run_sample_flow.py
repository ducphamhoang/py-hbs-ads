
#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = ROOT / "scripts" / "notion_scrum"
SAMPLES = SCRIPT_DIR / "samples"


def run_json(cmd: list[str], stdin_obj: dict | None = None) -> dict:
    payload = None if stdin_obj is None else json.dumps(stdin_obj, ensure_ascii=False)
    proc = subprocess.run(
        cmd,
        input=payload,
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(proc.stdout)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="notion_scrum_sample_") as tmp:
        tmpdir = Path(tmp)
        registry = tmpdir / "team_registry.json"
        prompts = tmpdir / "pending_prompts.json"
        audit = tmpdir / "audit_log.jsonl"
        shutil.copyfile(SAMPLES / "sample_team_registry.json", registry)
        prompts.write_text(json.dumps({"schema_version": "1.0", "updated_at": "1970-01-01T00:00:00Z", "prompts": []}, indent=2) + "\n", encoding="utf-8")
        audit.write_text("", encoding="utf-8")

        prompt_obj = json.loads((SAMPLES / "sample_prompt_due_date.json").read_text(encoding="utf-8"))
        event_payload = json.loads((SAMPLES / "sample_event_due_date_reply.json").read_text(encoding="utf-8"))

        recorded = run_json([
            "python", str(SCRIPT_DIR / "record_pending_prompt.py"),
            "--state", str(prompts),
            "--audit-log", str(audit),
        ], prompt_obj)

        resolved = run_json([
            "python", str(SCRIPT_DIR / "resolve_person.py"),
            "--platform", "discord",
            "--platform-user-id", event_payload["event"]["platform_user_id"],
            "--display-name", event_payload["event"].get("display_name", ""),
            "--registry", str(registry),
            "--audit-log", str(audit),
        ])
        event_payload["event"]["canonical_person_key"] = resolved.get("canonical_person_key")

        matched = run_json([
            "python", str(SCRIPT_DIR / "match_inbound_reply.py"),
            "--state", str(prompts),
            "--audit-log", str(audit),
        ], event_payload)

        state = json.loads(prompts.read_text(encoding="utf-8"))
        prompt = next(p for p in state["prompts"] if p["pending_prompt_id"] == matched["pending_prompt_id"])

        planned = run_json([
            "python", str(SCRIPT_DIR / "plan_notion_update.py"),
            "--audit-log", str(audit),
        ], {
            "prompt": prompt,
            "event": event_payload["event"],
            "match": matched,
        })

        applied = run_json([
            "python", str(SCRIPT_DIR / "apply_notion_update.py"),
            "--audit-log", str(audit),
        ], {
            "prompt": prompt,
            "event": event_payload["event"],
            "plan": planned,
        })

        print(json.dumps({
            "recorded": recorded,
            "resolved": resolved,
            "matched": matched,
            "planned": planned,
            "applied": applied,
            "audit_log_path": str(audit),
        }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
