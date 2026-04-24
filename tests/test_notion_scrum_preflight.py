from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts" / "notion_scrum"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import preflight  # noqa: F401, E402
import result_contracts  # noqa: F401, E402


# ---------------------------------------------------------------------------
# Inline fixture helpers (no @pytest.fixture decorators)
# ---------------------------------------------------------------------------

def _write_registry(tmp_path: Path) -> Path:
    """Write a minimal valid registry with person1 only — no unresolved Notion mappings."""
    reg = {
        "schema_version": "1.0",
        "people": {
            "person1": {
                "canonical_person_key": "person1",
                "display_name": "Person One",
                "notion": {
                    "user_id": "uid-001",
                    "display_name": "Person One",
                },
                "platform_identities": [],
                "status": "active",
            }
        },
        "identity_index": {},
        "pending_people": [],
    }
    path = tmp_path / "team_registry.json"
    path.write_text(json.dumps(reg, indent=2), encoding="utf-8")
    return path


def _write_empty_prompts(tmp_path: Path) -> Path:
    """Write an empty pending_prompts.json in the expected container format."""
    container = {
        "schema_version": "1.0",
        "updated_at": "2026-04-24T00:00:00Z",
        "prompts": [],
    }
    path = tmp_path / "pending_prompts.json"
    path.write_text(json.dumps(container, indent=2), encoding="utf-8")
    return path


def _write_people_state(tmp_path: Path, data: dict) -> Path:
    """Write people_state.json with given data."""
    path = tmp_path / "people_state.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def _valid_people_state_with_person1_active() -> dict:
    """Return a valid people_state with person1 in active status."""
    return {
        "schema_version": "1.0",
        "updated_at": "2026-04-24T00:00:00Z",
        "people": {
            "person1": {
                "availability": {
                    "status": "active",
                    "since": None,
                    "until": None,
                    "backup_person_key": None,
                    "timezone": None,
                    "half_day": None,
                    "note": None,
                    "source": {},
                    "updated_at": "",
                },
                "capacity": {"bandwidth": "normal", "note": None, "updated_at": ""},
                "coordination": {
                    "default_followup_policy": "",
                    "backup_person_key": None,
                    "last_status_check_at": "",
                },
                "metadata": {"tags": [], "last_actor_person_key": None},
            }
        },
    }


# ---------------------------------------------------------------------------
# Tests (7 functions to lock preflight staffing extension contract)
# ---------------------------------------------------------------------------

def test_preflight_missing_people_state_is_warning(tmp_path: Path) -> None:
    """Test that missing people_state.json is a warning, not an error."""
    registry_path = _write_registry(tmp_path)
    prompts_path = _write_empty_prompts(tmp_path)
    missing_people_state_path = tmp_path / "nonexistent" / "people_state.json"

    result = preflight.run_preflight(
        registry_path=registry_path,
        state_path=prompts_path,
        audit_log_path=tmp_path / "audit.jsonl",
        people_state_path=missing_people_state_path,
        require_people_state=False,
    )

    assert result["ok"] is True, "Preflight should succeed when people_state is missing with require_people_state=False"
    # Should have warnings about missing people_state
    warnings = result.get("data", {}).get("warnings", [])
    assert any("people_state" in w.lower() for w in warnings), \
        "Should warn about missing people_state"


def test_preflight_invalid_people_state_version_is_error(tmp_path: Path) -> None:
    """Test that invalid people_state schema version is an error."""
    registry_path = _write_registry(tmp_path)
    prompts_path = _write_empty_prompts(tmp_path)
    invalid_state = {
        "schema_version": "2.0",  # Unsupported version
        "updated_at": "2026-04-24T00:00:00Z",
        "people": {},
    }
    people_state_path = _write_people_state(tmp_path, invalid_state)

    result = preflight.run_preflight(
        registry_path=registry_path,
        state_path=prompts_path,
        audit_log_path=tmp_path / "audit.jsonl",
        people_state_path=people_state_path,
        require_people_state=True,
    )

    assert result["ok"] is False, "Preflight should fail on unsupported schema version"
    errors = result.get("errors", [])
    assert any("schema_version" in e.lower() or "unsupported" in e.lower() for e in errors), \
        "Should error about unsupported schema version"


def test_preflight_malformed_people_state_json_is_error(tmp_path: Path) -> None:
    """Test that malformed JSON in people_state is an error."""
    registry_path = _write_registry(tmp_path)
    prompts_path = _write_empty_prompts(tmp_path)
    people_state_path = tmp_path / "people_state.json"
    people_state_path.write_text("{invalid json}", encoding="utf-8")

    result = preflight.run_preflight(
        registry_path=registry_path,
        state_path=prompts_path,
        audit_log_path=tmp_path / "audit.jsonl",
        people_state_path=people_state_path,
        require_people_state=True,
    )

    assert result["ok"] is False, "Preflight should fail on malformed JSON"
    errors = result.get("errors", [])
    assert len(errors) > 0, "Should have at least one error for malformed JSON"


def test_preflight_unknown_backup_key_is_error(tmp_path: Path) -> None:
    """Test that unknown backup_person_key in people_state is an error."""
    registry_path = _write_registry(tmp_path)
    prompts_path = _write_empty_prompts(tmp_path)
    invalid_state = {
        "schema_version": "1.0",
        "updated_at": "2026-04-24T00:00:00Z",
        "people": {
            "person1": {
                "availability": {
                    "status": "leave",
                    "since": "2026-04-22",
                    "until": "2026-05-01",
                    "backup_person_key": "ghost_person",  # Not in registry
                    "timezone": None,
                    "half_day": None,
                    "note": None,
                    "source": {},
                    "updated_at": "2026-04-24T00:00:00Z",
                },
                "capacity": {"bandwidth": "normal", "note": None, "updated_at": ""},
                "coordination": {
                    "default_followup_policy": "",
                    "backup_person_key": None,
                    "last_status_check_at": "",
                },
                "metadata": {"tags": [], "last_actor_person_key": None},
            }
        },
    }
    people_state_path = _write_people_state(tmp_path, invalid_state)

    result = preflight.run_preflight(
        registry_path=registry_path,
        state_path=prompts_path,
        audit_log_path=tmp_path / "audit.jsonl",
        people_state_path=people_state_path,
        require_people_state=True,
    )

    assert result["ok"] is False, "Preflight should fail on unknown backup key"
    errors = result.get("errors", [])
    assert any("backup" in e.lower() for e in errors), \
        "Should error about unknown backup_person_key"


def test_preflight_invalid_leave_dates_is_error(tmp_path: Path) -> None:
    """Test that invalid leave date window is an error."""
    registry_path = _write_registry(tmp_path)
    prompts_path = _write_empty_prompts(tmp_path)
    invalid_state = {
        "schema_version": "1.0",
        "updated_at": "2026-04-24T00:00:00Z",
        "people": {
            "person1": {
                "availability": {
                    "status": "leave",
                    "since": "2026-05-01",  # After until
                    "until": "2026-04-01",  # Before since (inverted)
                    "backup_person_key": None,
                    "timezone": None,
                    "half_day": None,
                    "note": None,
                    "source": {},
                    "updated_at": "2026-04-24T00:00:00Z",
                },
                "capacity": {"bandwidth": "normal", "note": None, "updated_at": ""},
                "coordination": {
                    "default_followup_policy": "",
                    "backup_person_key": None,
                    "last_status_check_at": "",
                },
                "metadata": {"tags": [], "last_actor_person_key": None},
            }
        },
    }
    people_state_path = _write_people_state(tmp_path, invalid_state)

    result = preflight.run_preflight(
        registry_path=registry_path,
        state_path=prompts_path,
        audit_log_path=tmp_path / "audit.jsonl",
        people_state_path=people_state_path,
        require_people_state=True,
    )

    assert result["ok"] is False, "Preflight should fail on invalid leave dates"
    errors = result.get("errors", [])
    assert any("until" in e.lower() or "since" in e.lower() or "leave" in e.lower() for e in errors), \
        "Should error about invalid leave date window"


def test_preflight_legacy_registry_and_prompt_checks_still_run(tmp_path: Path) -> None:
    """Test that existing registry and prompt validation still runs (no regression)."""
    registry_path = _write_registry(tmp_path)
    prompts_path = _write_empty_prompts(tmp_path)
    people_state_path = _write_people_state(tmp_path, _valid_people_state_with_person1_active())

    result = preflight.run_preflight(
        registry_path=registry_path,
        state_path=prompts_path,
        audit_log_path=tmp_path / "audit.jsonl",
        people_state_path=people_state_path,
        require_people_state=False,
    )

    assert result["ok"] is True, "Preflight should succeed with valid inputs"
    # Check that result has the standard keys
    assert set(result.keys()) == set(result_contracts.RESULT_KEYS), \
        "Result envelope should preserve all RESULT_KEYS"


def test_preflight_success_preserves_stable_envelope_with_staffing(tmp_path: Path) -> None:
    """Test that preflight success with staffing checks preserves stable result envelope."""
    registry_path = _write_registry(tmp_path)
    prompts_path = _write_empty_prompts(tmp_path)
    people_state_path = _write_people_state(tmp_path, _valid_people_state_with_person1_active())

    result = preflight.run_preflight(
        registry_path=registry_path,
        state_path=prompts_path,
        audit_log_path=tmp_path / "audit.jsonl",
        people_state_path=people_state_path,
        require_people_state=False,
    )

    # Check stable envelope is preserved
    assert result["ok"] is True
    assert set(result.keys()) == set(result_contracts.RESULT_KEYS)
    assert result["action_taken"] == "preflight_run"
    assert "warnings" in result["data"]
    assert isinstance(result["audit_events"], list)
