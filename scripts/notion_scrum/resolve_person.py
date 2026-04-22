
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from audit import AuditEventType, append_event
from common import DEFAULT_AUDIT_LOG, DEFAULT_TEAM_REGISTRY, external_identity_key, load_registry
from person_resolution import resolve_platform_identity


def main() -> None:
    parser = argparse.ArgumentParser(description="Resolve platform user to canonical person")
    parser.add_argument("--platform", required=True)
    parser.add_argument("--platform-user-id", required=True)
    parser.add_argument("--display-name", default="")
    parser.add_argument("--registry", type=Path, default=DEFAULT_TEAM_REGISTRY)
    parser.add_argument("--audit-log", type=Path, default=DEFAULT_AUDIT_LOG)
    args = parser.parse_args()

    registry = load_registry(args.registry)
    ext_key = external_identity_key(args.platform, args.platform_user_id)
    person = resolve_platform_identity(registry, args.platform, args.platform_user_id)
    canonical = person.get("canonical_person_key") if person else None

    result = {
        "resolved": bool(person),
        "external_identity_key": ext_key,
        "canonical_person_key": canonical,
        "person": person,
    }

    append_event(
        args.audit_log,
        AuditEventType.IDENTITY_RESOLVED if person else AuditEventType.IDENTITY_UNRESOLVED,
        platform=args.platform,
        platform_user_id=args.platform_user_id,
        display_name=args.display_name,
        canonical_person_key=canonical,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
