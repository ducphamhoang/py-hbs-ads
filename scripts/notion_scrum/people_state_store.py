#!/usr/bin/env python3
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from common import load_json, save_json, utc_now_iso

VALID_STATUSES: frozenset[str] = frozenset({"active", "leave", "ooo", "partial", "unknown"})
VALID_BANDWIDTHS: frozenset[str] = frozenset({"normal", "reduced", "limited", "unknown"})


def _ensure_person(data: dict[str, Any], person_key: str) -> dict[str, Any]:
    """Ensure person_key exists in data["people"]; insert blank record if absent.

    Returns the person dict (data["people"][person_key]).
    """
    if person_key not in data["people"]:
        data["people"][person_key] = {
            "availability": {
                "status": "unknown",
                "since": None,
                "until": None,
                "timezone": None,
                "half_day": None,
                "note": None,
                "backup_person_key": None,
                "source": {},
                "updated_at": "",
            },
            "capacity": {
                "bandwidth": "unknown",
                "note": None,
                "updated_at": "",
            },
            "coordination": {
                "default_followup_policy": "",
                "backup_person_key": None,
                "last_status_check_at": "",
            },
            "metadata": {
                "tags": [],
                "last_actor_person_key": None,
            },
        }
    return data["people"][person_key]


def load_people_state(path: str | Path) -> dict[str, Any]:
    """Load people state container from path.

    Returns an empty container dict if the file is absent — never raises FileNotFoundError.
    """
    return load_json(
        Path(path),
        default={"schema_version": "1.0", "updated_at": utc_now_iso(), "people": {}},
    )


def save_people_state(path: str | Path, data: dict[str, Any]) -> None:
    """Atomically write people state container to path via common.save_json."""
    save_json(Path(path), data)


def validate_people_state(
    data: dict[str, Any],
    registry: dict[str, Any] | None = None,
) -> list[str]:
    """Validate a people state container.

    Returns a list of human-readable error strings. Empty list means valid.
    """
    errors: list[str] = []
    for person_key, person in data.get("people", {}).items():
        avail = person.get("availability", {})
        cap = person.get("capacity", {})
        status = avail.get("status", "unknown")
        bandwidth = cap.get("bandwidth", "unknown")
        since_str = avail.get("since")
        until_str = avail.get("until")
        backup_key = avail.get("backup_person_key")

        if status not in VALID_STATUSES:
            errors.append(f"{person_key}: invalid availability.status {status!r}")

        if bandwidth not in VALID_BANDWIDTHS:
            errors.append(f"{person_key}: invalid capacity.bandwidth {bandwidth!r}")

        if since_str and until_str:
            since_date = date.fromisoformat(since_str)
            until_date = date.fromisoformat(until_str)
            if until_date < since_date:
                errors.append(
                    f"{person_key}: availability.until {until_str!r} is before since {since_str!r}"
                )

        if backup_key and registry:
            if backup_key not in registry.get("people", {}):
                errors.append(
                    f"{person_key}: backup_person_key {backup_key!r} not found in registry"
                )

    return errors


def set_leave(
    data: dict[str, Any],
    person_key: str,
    since: str,
    until: str,
    backup_key: str | None,
    note: str | None,
    source: dict[str, Any],
) -> dict[str, Any]:
    """Transition person to leave status with leave window, backup, note, and source.

    Pure: modifies data in-place and returns data. Caller must call save_people_state.
    """
    now = utc_now_iso()
    person = _ensure_person(data, person_key)
    person["availability"].update(
        {
            "status": "leave",
            "since": since,
            "until": until,
            "backup_person_key": backup_key,
            "note": note,
            "source": source,
            "updated_at": now,
        }
    )
    data["updated_at"] = now
    return data


def clear_leave(
    data: dict[str, Any],
    person_key: str,
    source: dict[str, Any],
) -> dict[str, Any]:
    """Transition person back to active, clearing leave fields.

    Pure: modifies data in-place and returns data. Caller must call save_people_state.
    """
    now = utc_now_iso()
    person = _ensure_person(data, person_key)
    person["availability"].update(
        {
            "status": "active",
            "since": None,
            "until": None,
            "note": None,
            "source": source,
            "updated_at": now,
        }
    )
    data["updated_at"] = now
    return data


def set_bandwidth(
    data: dict[str, Any],
    person_key: str,
    bandwidth: str,
    note: str | None,
    source: dict[str, Any],
) -> dict[str, Any]:
    """Update capacity.bandwidth and note for a person.

    Pure: modifies data in-place and returns data. Caller must call save_people_state.
    """
    now = utc_now_iso()
    person = _ensure_person(data, person_key)
    person["capacity"].update(
        {
            "bandwidth": bandwidth,
            "note": note,
            "updated_at": now,
        }
    )
    data["updated_at"] = now
    return data


def set_backup(
    data: dict[str, Any],
    person_key: str,
    backup_key: str,
    source: dict[str, Any],
) -> dict[str, Any]:
    """Set backup_person_key in both availability and coordination for a person.

    Pure: modifies data in-place and returns data. Caller must call save_people_state.
    """
    now = utc_now_iso()
    person = _ensure_person(data, person_key)
    person["availability"]["backup_person_key"] = backup_key
    person["coordination"]["backup_person_key"] = backup_key
    data["updated_at"] = now
    return data


def get_person_state(data: dict[str, Any], person_key: str) -> dict[str, Any] | None:
    """Return the person dict for person_key, or None if not present."""
    return data.get("people", {}).get(person_key)


def is_person_absent(data: dict[str, Any], person_key: str) -> bool:
    """Return True if person's availability.status is 'leave' or 'ooo'; False otherwise."""
    person = get_person_state(data, person_key)
    if person is None:
        return False
    status = person.get("availability", {}).get("status", "unknown")
    return status in {"leave", "ooo"}


def effective_followup_target(data: dict[str, Any], person_key: str) -> tuple[str, str]:
    """Return (target_person_key, routing_reason) for follow-up routing.

    Routing rules:
    - Person not in data          → (person_key, "unknown")
    - status == "active"          → (person_key, "owner_active")
    - status in {leave, ooo}:
        backup exists             → (backup_key, "owner_absent_backup_used")
        no backup                 → (person_key, "escalation_needed")
    - partial / unknown / other   → (person_key, "unknown")
    """
    person = get_person_state(data, person_key)
    if person is None:
        return (person_key, "unknown")

    status = person.get("availability", {}).get("status", "unknown")

    if status == "active":
        return (person_key, "owner_active")

    if status in {"leave", "ooo"}:
        backup_key = person.get("availability", {}).get("backup_person_key") or person.get(
            "coordination", {}
        ).get("backup_person_key")
        if backup_key:
            return (backup_key, "owner_absent_backup_used")
        return (person_key, "escalation_needed")

    # partial, unknown, or any other status
    return (person_key, "unknown")
