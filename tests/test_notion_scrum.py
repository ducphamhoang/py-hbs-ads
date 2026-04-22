from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts" / "notion_scrum"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import apply_notion_update
import create_pending_prompt
import lookup_notion_person
import match_inbound_reply
import audit
import models
import notion_adapter
import person_resolution
import plan_notion_update
import preflight
import process_inbound_reply
import prompt_store
import result_contracts


def _sample_registry(tmp_path: Path) -> Path:
    path = tmp_path / "team_registry.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "updated_at": "2026-04-20T16:00:00Z",
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
                    }
                },
                "identity_index": {"discord:discord-user-ducph": "ducph"},
                "pending_people": [
                    {
                        "canonical_person_key": "po",
                        "status": "awaiting_discord_identity",
                        "notion_candidates": [
                            {
                                "user_id": "00000000-0000-4000-8000-000000000002",
                                "display_name": "Po (myntt7)",
                                "email": "po@example.invalid",
                            }
                        ],
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def test_build_comment_text_uses_registry_backed_notion_identity(tmp_path: Path) -> None:
    registry = _sample_registry(tmp_path)
    prompt = {"notion": {"task_title": "rough cut v1"}}
    event = {
        "platform": "discord",
        "platform_user_id": "discord-user-ducph",
        "canonical_person_key": "ducph",
        "display_name": "ducph",
        "text": "2026-04-22",
    }

    text = apply_notion_update.build_comment_text(
        plan={"resolved_update_type": "due_date_proposal"},
        event=event,
        prompt=prompt,
        registry_path=registry,
    )

    assert "DucPH" in text
    assert "ducph" in text
    assert "2026-04-22" in text
    assert "rough cut v1" in text


def test_prompt_record_extracts_allowed_update_types_from_question() -> None:
    record = models.PromptRecord(
        pending_prompt_id="pp_1",
        status="open",
        source={"thread_id": "thread-1"},
        target={"canonical_person_key": "ducph"},
        notion={"task_id": "task-1"},
        question={"allowed_update_types": ["task_comment", "due_date_proposal"]},
        created_at="2026-04-20T16:00:00Z",
        updated_at="2026-04-20T16:00:00Z",
    )

    assert record.allowed_update_types == ["task_comment", "due_date_proposal"]


def test_prompt_store_filters_open_prompts_and_marks_terminal_states(tmp_path: Path) -> None:
    state_path = tmp_path / "pending_prompts.json"
    prompt_a = _sample_prompt()
    prompt_b = dict(_sample_prompt())
    prompt_b["pending_prompt_id"] = "pp_2"
    prompt_b["source"] = {"thread_id": "thread-2"}
    prompt_store.append_prompt(state_path, prompt_a)
    prompt_store.append_prompt(state_path, prompt_b)

    assert [p["pending_prompt_id"] for p in prompt_store.get_open_prompts(state_path, thread_id="thread-1")] == ["pp_1"]
    assert prompt_store.mark_cancelled(state_path, "pp_1", at="2026-04-22T08:00:00Z") is True
    assert prompt_store.mark_expired(state_path, "pp_2", at="2026-04-22T08:01:00Z") is True
    assert prompt_store.mark_expired(state_path, "missing") is False

    prompts = prompt_store.load_prompts(state_path)
    assert {p["pending_prompt_id"]: p["status"] for p in prompts} == {"pp_1": "cancelled", "pp_2": "expired"}
    assert prompt_store.get_open_prompts(state_path) == []


def test_prompt_store_schema_validation_and_typed_conversion() -> None:
    invalid = {"pending_prompt_id": "bad", "status": "open", "source": {}, "notion": {}, "question": {}}
    errors = prompt_store.validate_prompt_schema(invalid)

    assert any("source.thread_id" in err for err in errors)
    assert any("notion.task_id and notion.project_id" in err for err in errors)
    assert any("question.allowed_update_types" in err for err in errors)

    record = prompt_store.to_prompt_record(_sample_prompt())
    assert isinstance(record, models.PromptRecord)
    assert record.pending_prompt_id == "pp_1"
    assert record.status == "open"


def test_person_resolution_fallback_order_and_pending_candidates(tmp_path: Path) -> None:
    registry_path = _sample_registry(tmp_path)
    registry = json.loads(registry_path.read_text(encoding="utf-8"))

    person = person_resolution.resolve_platform_identity(registry, "discord", "discord-user-ducph")
    assert person["canonical_person_key"] == "ducph"
    assert person_resolution.get_canonical_person(registry, "missing") is None
    assert person_resolution.get_pending_candidates(registry)[0]["canonical_person_key"] == "po"
    assert person_resolution.build_actor_label(None, fallback={"display_name": "Fallback"}) == "Fallback"
    assert person_resolution.build_actor_label(None, fallback={"platform_user_id": "123"}) == "123"
    assert person_resolution.build_actor_label(None) == "unknown"


def test_audit_event_build_and_append(tmp_path: Path) -> None:
    event = audit.build_event(audit.AuditEventType.PREFLIGHT_RUN, ok=True, warning_count=0)
    assert event["event_type"] == "preflight_run"
    assert event["ok"] is True
    assert "timestamp" in event

    log_path = tmp_path / "audit.jsonl"
    audit.append_event(log_path, audit.AuditEventType.PROMPT_CANCELLED, pending_prompt_id="pp_1")
    record = json.loads(log_path.read_text(encoding="utf-8").strip())
    assert record["event_type"] == "prompt_cancelled"
    assert record["pending_prompt_id"] == "pp_1"


def test_build_actions_includes_registry_identity_metadata(tmp_path: Path) -> None:
    registry = _sample_registry(tmp_path)
    prompt = {
        "pending_prompt_id": "pp_1",
        "notion": {"task_id": "task-123", "task_title": "rough cut v1"},
    }
    event = {
        "platform": "discord",
        "platform_user_id": "discord-user-ducph",
        "canonical_person_key": "ducph",
        "display_name": "ducph",
        "text": "2026-04-22",
    }
    plan = {
        "safe_to_apply": True,
        "resolved_update_type": "due_date_proposal",
        "resolved_value": "2026-04-22",
        "task_id": "task-123",
    }

    actions = apply_notion_update.build_actions(plan, prompt, event, registry_path=registry)

    assert actions[0]["action"] == "append_block_comment"
    assert "DucPH" in actions[0]["text"]
    assert actions[1]["action"] == "patch_page_property"
    assert actions[1]["properties"]["Due date note"]["rich_text"][0]["text"]["content"] == "2026-04-22"


def test_build_actions_uses_project_id_when_task_id_missing(tmp_path: Path) -> None:
    registry = _sample_registry(tmp_path)
    prompt = {
        "pending_prompt_id": "pp_project_1",
        "notion": {"project_id": "project-123", "project_title": "[AI] Improve Virtual AI Tester - part 3"},
    }
    event = {
        "platform": "discord",
        "platform_user_id": "discord-user-ducph",
        "canonical_person_key": "ducph",
        "display_name": "ducph",
        "text": "confirm_dod | notion_email=ducplc@example.invalid | write=yes",
    }
    plan = {
        "safe_to_apply": True,
        "resolved_update_type": "task_comment",
        "resolved_value": "confirm_dod | notion_email=ducplc@example.invalid | write=yes",
        "task_id": None,
        "project_id": "project-123",
    }

    actions = apply_notion_update.build_actions(plan, prompt, event, registry_path=registry)

    assert actions == [
        {
            "action": "append_block_comment",
            "block_id": "project-123",
            "text": "[Hermes Scrum] Reply from DucPH (ducph) on [AI] Improve Virtual AI Tester - part 3: confirm_dod | notion_email=ducplc@example.invalid | write=yes",
        }
    ]


def test_lookup_notion_person_returns_registry_mapping(tmp_path: Path) -> None:
    registry = _sample_registry(tmp_path)

    result = lookup_notion_person.lookup_person(
        canonical_person_key="ducph",
        registry_path=registry,
    )

    assert result["resolved"] is True
    assert result["mapping_source"] == "registry"
    assert result["notion"]["display_name"] == "DucPH"
    assert result["notion"]["user_id"] == "00000000-0000-4000-8000-000000000001"


def test_lookup_notion_person_returns_pending_candidates_when_not_mapped(tmp_path: Path) -> None:
    registry = _sample_registry(tmp_path)

    result = lookup_notion_person.lookup_person(
        canonical_person_key="po",
        registry_path=registry,
    )

    assert result["resolved"] is False
    assert result["mapping_source"] == "pending_people"
    assert result["candidates"][0]["display_name"] == "Po (myntt7)"


def test_lookup_notion_person_preserves_pending_candidates_for_identity_linked_but_unresolved_person(tmp_path: Path) -> None:
    registry = _sample_registry(tmp_path)
    data = json.loads(registry.read_text(encoding="utf-8"))
    data["people"]["ducplc"] = {
        "canonical_person_key": "ducplc",
        "display_name": "duc phan",
        "aliases": ["ducplc", "duc phan"],
        "role": "owner",
        "notion": {
            "people_page_id": None,
            "user_id": None,
            "display_name": None,
            "email": None,
            "mapping_confidence": "unresolved",
            "mapping_source": "fixture pending disambiguation",
        },
        "platform_identities": [
            {
                "platform": "discord",
                "platform_user_id": "discord-user-ducplc",
                "platform_username": "ducplc",
                "display_names": ["duc phan", "ducplc"],
            }
        ],
        "status": "active",
        "notes": "fixture",
    }
    data["identity_index"]["discord:discord-user-ducplc"] = "ducplc"
    data["pending_people"].append(
        {
            "canonical_person_key": "ducplc",
            "status": "awaiting_notion_disambiguation",
            "notion_candidates": [
                {
                    "user_id": "00000000-0000-4000-8000-000000000003",
                    "display_name": "duc phan",
                    "email": "ducplc@example.invalid",
                }
            ],
            "notes": "fixture",
        }
    )
    registry.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    result = lookup_notion_person.lookup_person(
        platform="discord",
        platform_user_id="discord-user-ducplc",
        registry_path=registry,
    )

    assert result["resolved"] is False
    assert result["mapping_source"] == "registry"
    assert result["canonical_person_key"] == "ducplc"
    assert result["candidates"][0]["email"] == "ducplc@example.invalid"


def _sample_prompt() -> dict:
    return {
        "pending_prompt_id": "pp_1",
        "status": "open",
        "source": {"thread_id": "thread-1"},
        "target": {"canonical_person_key": "ducph"},
        "outbound_message": {"assistant_message_id": "assistant-1"},
        "notion": {"task_id": "task-123", "task_title": "rough cut v1", "project_title": "Game teaser 03"},
        "question": {"allowed_update_types": ["due_date_proposal", "task_comment"]},
    }



def _sample_event() -> dict:
    return {
        "platform": "discord",
        "thread_id": "thread-1",
        "platform_user_id": "discord-user-ducph",
        "canonical_person_key": "ducph",
        "display_name": "ducph",
        "reply_to_message_id": "assistant-1",
        "text": "2026-04-22",
    }



def test_infer_update_type_does_not_treat_generic_hyphen_text_as_due_date() -> None:
    update_type, value = plan_notion_update.infer_update_type("task-1 is still open")

    assert update_type == "task_comment"
    assert value == "task-1 is still open"



def test_infer_update_type_prioritizes_explicit_date_over_ack_language() -> None:
    update_type, value = plan_notion_update.infer_update_type("ok, 2026-04-25")

    assert update_type == "due_date_proposal"
    assert value == "ok, 2026-04-25"



def test_score_candidate_rewards_reply_to_same_sender_same_thread() -> None:
    score, reasons = match_inbound_reply.score_candidate(_sample_prompt(), _sample_event())

    assert score >= 0.90
    assert "reply_to_assistant_message" in reasons
    assert "same_thread" in reasons
    assert "sender_matches_target" in reasons



def test_apply_update_dry_run_does_not_mark_prompt_answered(tmp_path: Path) -> None:
    registry = _sample_registry(tmp_path)
    state_path = tmp_path / "pending_prompts.json"
    state_path.write_text(
        json.dumps({"schema_version": "1.0", "updated_at": "2026-04-20T16:00:00Z", "prompts": [_sample_prompt()]}, indent=2) + "\n",
        encoding="utf-8",
    )

    result = apply_notion_update.apply_update(
        plan={
            "safe_to_apply": True,
            "resolved_update_type": "due_date_proposal",
            "resolved_value": "2026-04-22",
            "task_id": "task-123",
        },
        prompt=_sample_prompt(),
        event=_sample_event(),
        execute=False,
        registry_path=registry,
        state_path=state_path,
        audit_log_path=tmp_path / "audit.jsonl",
    )

    assert result["success"] is True
    updated_state = json.loads(state_path.read_text(encoding="utf-8"))
    assert updated_state["prompts"][0]["status"] == "open"



def test_apply_update_execute_marks_prompt_answered_after_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    registry = _sample_registry(tmp_path)
    state_path = tmp_path / "pending_prompts.json"
    state_path.write_text(
        json.dumps({"schema_version": "1.0", "updated_at": "2026-04-20T16:00:00Z", "prompts": [_sample_prompt()]}, indent=2) + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(apply_notion_update, "load_api_key", lambda: "fake-key")
    monkeypatch.setattr(apply_notion_update, "notion_append_blocks", lambda *args, **kwargs: {"ok": True, "type": "append"})
    monkeypatch.setattr(apply_notion_update, "notion_patch_page", lambda *args, **kwargs: {"ok": True, "type": "patch"})

    result = apply_notion_update.apply_update(
        plan={
            "safe_to_apply": True,
            "resolved_update_type": "due_date_proposal",
            "resolved_value": "2026-04-22",
            "task_id": "task-123",
        },
        prompt=_sample_prompt(),
        event=_sample_event(),
        execute=True,
        registry_path=registry,
        state_path=state_path,
        audit_log_path=tmp_path / "audit.jsonl",
    )

    assert result["success"] is True
    updated_state = json.loads(state_path.read_text(encoding="utf-8"))
    assert updated_state["prompts"][0]["status"] == "answered"
    assert updated_state["prompts"][0]["resolution"]["resolved_update_type"] == "due_date_proposal"



def test_plan_update_respects_allowed_update_types_for_generic_task_comment() -> None:
    prompt = _sample_prompt()
    prompt["question"]["allowed_update_types"] = ["due_date_proposal"]
    event = dict(_sample_event())
    event["text"] = "ok noted"
    match = {"matched": True, "confidence": 0.9}

    plan = plan_notion_update.plan_update(prompt=prompt, event=event, matched=match)

    assert plan["resolved_update_type"] == "owner_ack"
    assert plan["safe_to_apply"] is False



def test_match_reply_does_not_auto_match_on_sender_plus_thread_only() -> None:
    prompt = _sample_prompt()
    event = dict(_sample_event())
    event.pop("reply_to_message_id", None)

    result = match_inbound_reply.match_reply(event=event, prompts=[prompt])

    assert result["matched"] is False
    assert result["requires_clarification"] is True



def test_match_reply_matches_listed_choice_from_prompt_text() -> None:
    prompt = {
        "pending_prompt_id": "pp_email_1",
        "source": {"thread_id": "thread-1"},
        "target": {"canonical_person_key": "ducplc"},
        "outbound_message": {
            "assistant_message_id": None,
            "text": "@DucPLC — project [AI] Improve Virtual AI Tester - part 3: trả lời đúng 1 dòng theo format: confirm_dod | notion_email=<ducplc@example.invalid hoặc alternate.ducplc@example.invalid> | write=yes",
        },
        "notion": {"project_title": "[AI] Improve Virtual AI Tester - part 3"},
        "question": {"allowed_update_types": ["task_comment"]},
    }
    event = {
        "platform": "discord",
        "thread_id": "thread-1",
        "platform_user_id": "discord-user-ducplc",
        "canonical_person_key": "ducplc",
        "display_name": "DucPLC",
        "text": "ducplc@example.invalid",
    }

    result = match_inbound_reply.match_reply(event=event, prompts=[prompt])

    assert result["matched"] is True
    assert result["pending_prompt_id"] == "pp_email_1"
    assert result["confidence"] >= 0.45



def test_apply_update_blocked_write_logs_and_keeps_prompt_open(tmp_path: Path) -> None:
    registry = _sample_registry(tmp_path)
    state_path = tmp_path / "pending_prompts.json"
    audit_path = tmp_path / "audit.jsonl"
    state_path.write_text(
        json.dumps({"schema_version": "1.0", "updated_at": "2026-04-20T16:00:00Z", "prompts": [_sample_prompt()]}, indent=2) + "\n",
        encoding="utf-8",
    )

    result = apply_notion_update.apply_update(
        plan={"safe_to_apply": False, "resolved_update_type": "task_comment", "task_id": "task-123"},
        prompt=_sample_prompt(),
        event=_sample_event(),
        execute=False,
        registry_path=registry,
        state_path=state_path,
        audit_log_path=audit_path,
    )

    assert result["success"] is False
    updated_state = json.loads(state_path.read_text(encoding="utf-8"))
    assert updated_state["prompts"][0]["status"] == "open"
    audit_lines = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert audit_lines[-1]["event_type"] == "notion_write_blocked"


def test_result_contract_keys_stable_between_dry_run_and_execute_shapes() -> None:
    dry_run = result_contracts.build_result(
        ok=True,
        action_taken="dry_run_planned",
        write_applied=False,
        pending_prompt_id="pp_1",
    )
    execute = result_contracts.build_result(
        ok=True,
        action_taken="write_applied",
        write_applied=True,
        pending_prompt_id="pp_1",
        audit_events=["notion_write"],
    )

    assert set(dry_run) == set(execute) == set(result_contracts.RESULT_KEYS)


def test_notion_adapter_plans_existing_action_shape(tmp_path: Path) -> None:
    registry = _sample_registry(tmp_path)
    prompt = {
        "pending_prompt_id": "pp_1",
        "notion": {"task_id": "task-123", "task_title": "rough cut v1"},
    }
    event = _sample_event()
    plan = {
        "safe_to_apply": True,
        "resolved_update_type": "due_date_proposal",
        "resolved_value": "2026-04-22",
        "task_id": "task-123",
    }

    assert notion_adapter.plan_actions(plan, prompt, event, registry_path=registry) == apply_notion_update.build_actions(
        plan,
        prompt,
        event,
        registry_path=registry,
    )


def test_create_pending_prompt_records_valid_prompt_with_stable_envelope(tmp_path: Path) -> None:
    state_path = tmp_path / "pending_prompts.json"
    audit_path = tmp_path / "audit.jsonl"

    result = create_pending_prompt.create_prompt(
        _sample_prompt(),
        state_path=state_path,
        audit_log_path=audit_path,
    )

    assert set(result) == set(result_contracts.RESULT_KEYS)
    assert result["ok"] is True
    assert result["action_taken"] == "prompt_recorded"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["prompts"][0]["pending_prompt_id"] == "pp_1"
    audit_lines = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert audit_lines[-1]["event_type"] == "prompt_recorded"


def test_create_pending_prompt_rejects_invalid_prompt_without_mutation(tmp_path: Path) -> None:
    state_path = tmp_path / "pending_prompts.json"
    audit_path = tmp_path / "audit.jsonl"

    result = create_pending_prompt.create_prompt(
        {"pending_prompt_id": "bad", "source": {}, "notion": {}, "question": {}},
        state_path=state_path,
        audit_log_path=audit_path,
    )

    assert result["ok"] is False
    assert result["action_taken"] == "validation_failed"
    assert result["errors"]
    assert not state_path.exists()
    assert not audit_path.exists()


def test_process_inbound_reply_dry_run_keeps_prompt_open(tmp_path: Path) -> None:
    registry = _sample_registry(tmp_path)
    state_path = tmp_path / "pending_prompts.json"
    audit_path = tmp_path / "audit.jsonl"
    state_path.write_text(
        json.dumps({"schema_version": "1.0", "updated_at": "2026-04-20T16:00:00Z", "prompts": [_sample_prompt()]}, indent=2) + "\n",
        encoding="utf-8",
    )

    result = process_inbound_reply.process_inbound_reply(
        _sample_event(),
        execute=False,
        registry_path=registry,
        state_path=state_path,
        audit_log_path=audit_path,
    )

    assert set(result) == set(result_contracts.RESULT_KEYS)
    assert result["ok"] is True
    assert result["action_taken"] == "dry_run_planned"
    assert result["write_applied"] is False
    updated_state = json.loads(state_path.read_text(encoding="utf-8"))
    assert updated_state["prompts"][0]["status"] == "open"


def test_process_inbound_reply_execute_marks_prompt_answered(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    registry = _sample_registry(tmp_path)
    state_path = tmp_path / "pending_prompts.json"
    audit_path = tmp_path / "audit.jsonl"
    state_path.write_text(
        json.dumps({"schema_version": "1.0", "updated_at": "2026-04-20T16:00:00Z", "prompts": [_sample_prompt()]}, indent=2) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(apply_notion_update, "load_api_key", lambda: "fake-key")
    monkeypatch.setattr(apply_notion_update, "notion_append_blocks", lambda *args, **kwargs: {"ok": True, "type": "append"})
    monkeypatch.setattr(apply_notion_update, "notion_patch_page", lambda *args, **kwargs: {"ok": True, "type": "patch"})

    result = process_inbound_reply.process_inbound_reply(
        _sample_event(),
        execute=True,
        registry_path=registry,
        state_path=state_path,
        audit_log_path=audit_path,
    )

    assert result["ok"] is True
    assert result["action_taken"] == "write_applied"
    assert result["write_applied"] is True
    updated_state = json.loads(state_path.read_text(encoding="utf-8"))
    assert updated_state["prompts"][0]["status"] == "answered"


def test_process_inbound_reply_dry_run_and_execute_share_envelope_keys(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    registry = _sample_registry(tmp_path)
    dry_state = tmp_path / "dry_prompts.json"
    execute_state = tmp_path / "execute_prompts.json"
    initial = {"schema_version": "1.0", "updated_at": "2026-04-20T16:00:00Z", "prompts": [_sample_prompt()]}
    dry_state.write_text(json.dumps(initial, indent=2) + "\n", encoding="utf-8")
    execute_state.write_text(json.dumps(initial, indent=2) + "\n", encoding="utf-8")
    monkeypatch.setattr(apply_notion_update, "load_api_key", lambda: "fake-key")
    monkeypatch.setattr(apply_notion_update, "notion_append_blocks", lambda *args, **kwargs: {"ok": True, "type": "append"})
    monkeypatch.setattr(apply_notion_update, "notion_patch_page", lambda *args, **kwargs: {"ok": True, "type": "patch"})

    dry_run = process_inbound_reply.process_inbound_reply(
        _sample_event(),
        execute=False,
        registry_path=registry,
        state_path=dry_state,
        audit_log_path=tmp_path / "dry_audit.jsonl",
    )
    executed = process_inbound_reply.process_inbound_reply(
        _sample_event(),
        execute=True,
        registry_path=registry,
        state_path=execute_state,
        audit_log_path=tmp_path / "execute_audit.jsonl",
    )

    assert set(dry_run) == set(executed) == set(result_contracts.RESULT_KEYS)
    assert dry_run["write_applied"] is False
    assert executed["write_applied"] is True


def test_process_inbound_reply_unmatched_requires_clarification(tmp_path: Path) -> None:
    registry = _sample_registry(tmp_path)
    state_path = tmp_path / "pending_prompts.json"
    state_path.write_text(
        json.dumps({"schema_version": "1.0", "updated_at": "2026-04-20T16:00:00Z", "prompts": []}, indent=2) + "\n",
        encoding="utf-8",
    )

    result = process_inbound_reply.process_inbound_reply(
        _sample_event(),
        execute=False,
        registry_path=registry,
        state_path=state_path,
        audit_log_path=tmp_path / "audit.jsonl",
    )

    assert result["ok"] is False
    assert result["requires_clarification"] is True
    assert result["clarification_reason"] == "no_candidate"


def test_preflight_reports_duplicate_prompts_and_unresolved_people(tmp_path: Path) -> None:
    registry = _sample_registry(tmp_path)
    data = json.loads(registry.read_text(encoding="utf-8"))
    data["people"]["unmapped"] = {
        "canonical_person_key": "unmapped",
        "status": "active",
        "notion": {},
    }
    registry.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    state_path = tmp_path / "pending_prompts.json"
    prompt = _sample_prompt()
    state_path.write_text(
        json.dumps({"schema_version": "1.0", "updated_at": "2026-04-20T16:00:00Z", "prompts": [prompt, dict(prompt)]}, indent=2) + "\n",
        encoding="utf-8",
    )

    result = preflight.run_preflight(
        registry_path=registry,
        state_path=state_path,
        audit_log_path=tmp_path / "audit.jsonl",
    )

    assert result["ok"] is False
    assert any("duplicate pending_prompt_id" in err for err in result["errors"])
    assert any("unresolved Notion mapping: unmapped" in warning for warning in result["data"]["warnings"])


def test_preflight_success_uses_stable_envelope(tmp_path: Path) -> None:
    registry = _sample_registry(tmp_path)
    state_path = tmp_path / "pending_prompts.json"
    state_path.write_text(
        json.dumps({"schema_version": "1.0", "updated_at": "2026-04-20T16:00:00Z", "prompts": [_sample_prompt()]}, indent=2) + "\n",
        encoding="utf-8",
    )

    result = preflight.run_preflight(
        registry_path=registry,
        state_path=state_path,
        audit_log_path=tmp_path / "audit.jsonl",
    )

    assert set(result) == set(result_contracts.RESULT_KEYS)
    assert result["action_taken"] == "preflight_run"
    assert result["errors"] == []
