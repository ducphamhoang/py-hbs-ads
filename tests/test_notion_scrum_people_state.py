from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts" / "notion_scrum"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import people_state_store  # noqa: E402
import result_contracts     # noqa: E402


# ---------------------------------------------------------------------------
# Inline helpers (no @pytest.fixture decorators — inline pattern per project)
# ---------------------------------------------------------------------------

def _sample_registry(tmp_path: Path) -> Path:
    """Write a minimal team_registry.json with ducph and toanvt as valid people."""
    path = tmp_path / "team_registry.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "updated_at": "2026-04-24T00:00:00Z",
                "people": {
                    "ducph": {
                        "canonical_person_key": "ducph",
                        "display_name": "ducph",
                        "aliases": ["ducph", "DucPH"],
                        "role": "owner",
                        "notion": {
                            "people_page_id": None,
                            "user_id": "00000000-0000-4000-8000-000000000001",
                            "display_name": "DucPH",
                            "email": "ducph@example.invalid",
                            "mapping_confidence": "high",
                            "mapping_source": "test fixture",
                        },
                        "platform_identities": [
                            {
                                "platform": "discord",
                                "platform_user_id": "discord-user-ducph",
                                "platform_username": "ducph",
                                "display_names": ["ducph"],
                            }
                        ],
                        "status": "active",
                        "notes": "fixture",
                    },
                    "toanvt": {
                        "canonical_person_key": "toanvt",
                        "display_name": "toanvt",
                        "aliases": ["toanvt", "ToanVT"],
                        "role": "member",
                        "notion": {
                            "people_page_id": None,
                            "user_id": "00000000-0000-4000-8000-000000000002",
                            "display_name": "ToanVT",
                            "email": "toanvt@example.invalid",
                            "mapping_confidence": "high",
                            "mapping_source": "test fixture",
                        },
                        "platform_identities": [
                            {
                                "platform": "discord",
                                "platform_user_id": "discord-user-toanvt",
                                "platform_username": "toanvt",
                                "display_names": ["toanvt"],
                            }
                        ],
                        "status": "active",
                        "notes": "fixture",
                    },
                },
                "identity_index": {
                    "discord:discord-user-ducph": "ducph",
                    "discord:discord-user-toanvt": "toanvt",
                },
                "pending_people": [],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _empty_container() -> dict:
    """Return a valid empty people_state container."""
    return {
        "schema_version": "1.0",
        "updated_at": "2026-04-24T00:00:00Z",
        "people": {},
    }


def _sample_source() -> dict:
    """Return a valid source attribution object."""
    return {
        "kind": "manual_command",
        "platform": "discord",
        "platform_user_id": "discord-user-ducph",
        "message_id": None,
        "confirmed_by": "ducph",
    }


def _make_person(
    status: str = "active",
    bandwidth: str = "normal",
    backup_key: str | None = None,
    since: str | None = None,
    until: str | None = None,
) -> dict:
    """Return a fully-structured person record dict matching PRD §10.1 shape."""
    return {
        "availability": {
            "status": status,
            "since": since,
            "until": until,
            "timezone": "Asia/Ho_Chi_Minh",
            "half_day": None,
            "note": None,
            "backup_person_key": backup_key,
            "source": _sample_source(),
            "updated_at": "2026-04-24T00:00:00Z",
        },
        "capacity": {
            "bandwidth": bandwidth,
            "note": None,
            "updated_at": "2026-04-24T00:00:00Z",
        },
        "coordination": {
            "default_followup_policy": "route_to_backup",
            "backup_person_key": backup_key,
            "last_status_check_at": "2026-04-24T00:00:00Z",
        },
        "metadata": {
            "tags": [],
            "last_actor_person_key": "ducph",
        },
    }


# ---------------------------------------------------------------------------
# STATE-01: load and save a valid container
# ---------------------------------------------------------------------------

def test_load_save_valid_container(tmp_path: Path) -> None:
    """STATE-01: load_people_state returns valid container; save_people_state persists it."""
    state_path = tmp_path / "people_state.json"
    container = _empty_container()
    state_path.write_text(json.dumps(container, indent=2) + "\n", encoding="utf-8")

    result = people_state_store.load_people_state(state_path)
    assert result["schema_version"] == "1.0"
    assert "updated_at" in result
    assert "people" in result

    people_state_store.save_people_state(state_path, result)
    reloaded = json.loads(state_path.read_text(encoding="utf-8"))
    assert reloaded["schema_version"] == "1.0"
    assert "people" in reloaded


# ---------------------------------------------------------------------------
# COMPAT-02: missing file returns graceful empty container (not raise)
# ---------------------------------------------------------------------------

def test_load_missing_file_returns_empty_container(tmp_path: Path) -> None:
    """COMPAT-02: load_people_state returns empty container when file does not exist."""
    result = people_state_store.load_people_state(tmp_path / "nonexistent.json")
    assert isinstance(result, dict)
    assert "schema_version" in result
    assert "updated_at" in result
    assert "people" in result
    assert result["people"] == {}


# ---------------------------------------------------------------------------
# STATE-02: validate rejects invalid availability.status
# ---------------------------------------------------------------------------

def test_validate_rejects_invalid_status(tmp_path: Path) -> None:
    """STATE-02: validate_people_state rejects a person with availability.status='vacation'."""
    container = _empty_container()
    person = _make_person(status="vacation")  # invalid — allowed: active/leave/ooo/partial/unknown
    container["people"]["toanvt"] = person

    errors = people_state_store.validate_people_state(container)
    assert len(errors) > 0
    assert any("status" in e for e in errors)


# ---------------------------------------------------------------------------
# STATE-03: validate rejects invalid capacity.bandwidth
# ---------------------------------------------------------------------------

def test_validate_rejects_invalid_bandwidth(tmp_path: Path) -> None:
    """STATE-03: validate_people_state rejects a person with capacity.bandwidth='full'."""
    container = _empty_container()
    person = _make_person(bandwidth="full")  # invalid — allowed: normal/reduced/limited/unknown
    container["people"]["ducph"] = person

    errors = people_state_store.validate_people_state(container)
    assert len(errors) > 0
    assert any("bandwidth" in e for e in errors)


# ---------------------------------------------------------------------------
# STATE-04: validate rejects date window where until < since
# ---------------------------------------------------------------------------

def test_validate_rejects_invalid_date_window(tmp_path: Path) -> None:
    """STATE-04: validate_people_state rejects leave window where until < since."""
    container = _empty_container()
    person = _make_person(status="leave", since="2026-04-28", until="2026-04-24")
    container["people"]["toanvt"] = person

    errors = people_state_store.validate_people_state(container)
    assert len(errors) > 0
    assert any("until" in e or "date" in e for e in errors)


# ---------------------------------------------------------------------------
# STATE-05: validate rejects backup_person_key unknown in registry
# ---------------------------------------------------------------------------

def test_validate_rejects_unknown_backup_key(tmp_path: Path) -> None:
    """STATE-05: validate_people_state rejects backup_person_key not in registry."""
    reg_path = _sample_registry(tmp_path)
    registry = json.loads(reg_path.read_text(encoding="utf-8"))

    container = _empty_container()
    person = _make_person(status="leave", backup_key="unknownperson")
    container["people"]["ducph"] = person

    errors = people_state_store.validate_people_state(container, registry=registry)
    assert len(errors) > 0
    assert any("backup" in e or "unknown" in e for e in errors)


# ---------------------------------------------------------------------------
# STATE-06: set_leave transition
# ---------------------------------------------------------------------------

def test_set_leave_transition() -> None:
    """STATE-06: set_leave sets person to leave status with correct fields."""
    data = _empty_container()
    source = _sample_source()

    data = people_state_store.set_leave(
        data,
        "toanvt",
        since="2026-04-24",
        until="2026-04-28",
        backup_key="ducph",
        note="nghỉ phép",
        source=source,
    )

    person = data["people"]["toanvt"]
    assert person["availability"]["status"] == "leave"
    assert person["availability"]["since"] == "2026-04-24"
    assert person["availability"]["until"] == "2026-04-28"
    assert person["availability"]["backup_person_key"] == "ducph"


# ---------------------------------------------------------------------------
# STATE-07: clear_leave transition
# ---------------------------------------------------------------------------

def test_clear_leave_transition() -> None:
    """STATE-07: clear_leave resets person back to active and clears leave fields."""
    data = _empty_container()
    source = _sample_source()

    # First put toanvt on leave
    data = people_state_store.set_leave(
        data,
        "toanvt",
        since="2026-04-24",
        until="2026-04-28",
        backup_key="ducph",
        note="nghỉ phép",
        source=source,
    )

    # Now clear the leave
    data = people_state_store.clear_leave(data, "toanvt", source=source)

    person = data["people"]["toanvt"]
    assert person["availability"]["status"] == "active"
    assert person["availability"].get("since") is None or "since" not in person["availability"] or person["availability"]["since"] is None
    assert person["availability"].get("until") is None or "until" not in person["availability"] or person["availability"]["until"] is None


# ---------------------------------------------------------------------------
# STATE-08a: set_bandwidth transition
# ---------------------------------------------------------------------------

def test_set_bandwidth_transition() -> None:
    """STATE-08a: set_bandwidth sets capacity.bandwidth and note on a person."""
    data = _empty_container()
    source = _sample_source()

    data = people_state_store.set_bandwidth(
        data,
        "ducph",
        bandwidth="reduced",
        note="half day",
        source=source,
    )

    person = data["people"]["ducph"]
    assert person["capacity"]["bandwidth"] == "reduced"
    assert person["capacity"]["note"] == "half day"


# ---------------------------------------------------------------------------
# STATE-08b: set_backup transition
# ---------------------------------------------------------------------------

def test_set_backup_transition() -> None:
    """STATE-08b: set_backup updates both coordination and availability backup_person_key."""
    data = _empty_container()
    source = _sample_source()

    data = people_state_store.set_backup(data, "ducph", backup_key="toanvt", source=source)

    person = data["people"]["ducph"]
    assert person["coordination"]["backup_person_key"] == "toanvt"
    assert person["availability"]["backup_person_key"] == "toanvt"


# ---------------------------------------------------------------------------
# STATE-09a: is_person_absent covers all statuses
# ---------------------------------------------------------------------------

def test_is_person_absent() -> None:
    """STATE-09a: is_person_absent returns True for leave/ooo; False for active/partial/missing."""
    data = _empty_container()
    data["people"]["toanvt"] = _make_person(status="leave")
    data["people"]["ducph"] = _make_person(status="active")
    data["people"]["ooouser"] = _make_person(status="ooo")
    data["people"]["partialuser"] = _make_person(status="partial")

    assert people_state_store.is_person_absent(data, "toanvt") is True
    assert people_state_store.is_person_absent(data, "ducph") is False
    assert people_state_store.is_person_absent(data, "ooouser") is True
    assert people_state_store.is_person_absent(data, "partialuser") is False
    assert people_state_store.is_person_absent(data, "nobodyhere") is False


# ---------------------------------------------------------------------------
# STATE-09b: effective_followup_target — active owner
# ---------------------------------------------------------------------------

def test_effective_followup_target_active() -> None:
    """STATE-09b: effective_followup_target returns (owner, 'owner_active') for active person."""
    data = _empty_container()
    data["people"]["ducph"] = _make_person(status="active")

    target, reason = people_state_store.effective_followup_target(data, "ducph")
    assert target == "ducph"
    assert reason == "owner_active"


# ---------------------------------------------------------------------------
# STATE-09c: effective_followup_target — leave with backup
# ---------------------------------------------------------------------------

def test_effective_followup_target_leave_with_backup() -> None:
    """STATE-09c: effective_followup_target routes to backup when owner is on leave with backup."""
    data = _empty_container()
    data["people"]["toanvt"] = _make_person(status="leave", backup_key="ducph")

    target, reason = people_state_store.effective_followup_target(data, "toanvt")
    assert target == "ducph"
    assert reason == "owner_absent_backup_used"


# ---------------------------------------------------------------------------
# STATE-09d: effective_followup_target — leave with no backup
# ---------------------------------------------------------------------------

def test_effective_followup_target_leave_no_backup() -> None:
    """STATE-09d: effective_followup_target returns escalation_needed when on leave with no backup."""
    data = _empty_container()
    data["people"]["toanvt"] = _make_person(status="leave", backup_key=None)

    target, reason = people_state_store.effective_followup_target(data, "toanvt")
    assert target == "toanvt"
    assert reason == "escalation_needed"


# ---------------------------------------------------------------------------
# STATE-09e: effective_followup_target — missing person returns unknown
# ---------------------------------------------------------------------------

def test_effective_followup_target_missing_person() -> None:
    """STATE-09e: effective_followup_target returns (key, 'unknown') for missing person."""
    data = _empty_container()

    target, reason = people_state_store.effective_followup_target(data, "nobody")
    assert target == "nobody"
    assert reason == "unknown"


# ---------------------------------------------------------------------------
# STATE-10: result envelope includes staffing fields
# ---------------------------------------------------------------------------

def test_result_envelope_includes_staffing_fields() -> None:
    """STATE-10: result_contracts.RESULT_KEYS includes effective_followup_person_key and routing_reason."""
    assert "effective_followup_person_key" in result_contracts.RESULT_KEYS
    assert "routing_reason" in result_contracts.RESULT_KEYS

    result = result_contracts.build_result()
    assert "effective_followup_person_key" in result
    assert result["routing_reason"] == "unknown"


# RED PHASE: All tests above fail until people_state_store.py is created (Wave 2 Plan 02)
# and result_contracts.py is extended with staffing fields (Wave 2 Plan 03).
