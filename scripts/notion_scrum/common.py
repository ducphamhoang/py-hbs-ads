
#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

NOTION_VERSION = "2025-09-03"
DEFAULT_ROOT = Path("~/work/py-hbs-ads").expanduser()
DEFAULT_STATE_DIR = DEFAULT_ROOT / "state" / "notion_scrum"
DEFAULT_SCRIPTS_DIR = DEFAULT_ROOT / "scripts" / "notion_scrum"
DEFAULT_TEAM_REGISTRY = DEFAULT_STATE_DIR / "team_registry.json"
DEFAULT_PENDING_PROMPTS = DEFAULT_STATE_DIR / "pending_prompts.json"
DEFAULT_AUDIT_LOG = DEFAULT_STATE_DIR / "audit_log.jsonl"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        if default is not None:
            return default
        raise FileNotFoundError(path)
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        if default is not None:
            return default
        raise ValueError(f"JSON file is empty: {path}")
    return json.loads(text)


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def stdin_json() -> dict[str, Any]:
    import sys
    raw = sys.stdin.read().strip()
    if not raw:
        raise SystemExit("Expected JSON on stdin")
    return json.loads(raw)


def load_api_key() -> str:
    key = os.getenv("NOTION_API_KEY", "").strip()
    if key:
        return key
    env_path = Path.home() / ".hermes" / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("NOTION_API_KEY="):
                return line.split("=", 1)[1].strip()
    raise SystemExit("NOTION_API_KEY not found in environment or ~/.hermes/.env")


def notion_request(api_key: str, method: str, url: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }
    body = None if data is None else json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        text = exc.read().decode(errors="replace")
        raise RuntimeError(f"Notion API error {exc.code}: {text}") from exc


def notion_patch_page(api_key: str, page_id: str, properties: dict[str, Any]) -> dict[str, Any]:
    return notion_request(api_key, "PATCH", f"https://api.notion.com/v1/pages/{page_id}", {"properties": properties})


def notion_append_blocks(api_key: str, block_id: str, children: list[dict[str, Any]]) -> dict[str, Any]:
    return notion_request(api_key, "PATCH", f"https://api.notion.com/v1/blocks/{block_id}/children", {"children": children})


def paragraph_block(text: str) -> dict[str, Any]:
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [
                {
                    "type": "text",
                    "text": {"content": text[:1900]},
                }
            ]
        },
    }


def external_identity_key(platform: str, platform_user_id: str) -> str:
    return f"{platform}:{platform_user_id}"


def normalize_text(s: str) -> str:
    return " ".join((s or "").strip().lower().split())


def ensure_prompt_container(data: dict[str, Any]) -> dict[str, Any]:
    data.setdefault("schema_version", "1.0")
    data.setdefault("updated_at", utc_now_iso())
    data.setdefault("prompts", [])
    return data


def load_registry(path: Path = DEFAULT_TEAM_REGISTRY) -> dict[str, Any]:
    return load_json(path, default={"people": {}, "identity_index": {}, "pending_people": []})


def find_person_by_canonical_key(registry: dict[str, Any], canonical_person_key: str | None) -> dict[str, Any] | None:
    if not canonical_person_key:
        return None
    return (registry.get("people") or {}).get(canonical_person_key)


def find_person_by_platform_identity(
    registry: dict[str, Any],
    *,
    platform: str | None,
    platform_user_id: str | None,
) -> dict[str, Any] | None:
    if not platform or not platform_user_id:
        return None
    canonical = (registry.get("identity_index") or {}).get(external_identity_key(platform, platform_user_id))
    return find_person_by_canonical_key(registry, canonical)
