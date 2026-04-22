# State Schema — Hermes Discord ↔ Notion Scrum Attribution

This document defines the concrete JSON state used by the Discord public-thread Scrum workflow.

The goal is to keep the state:
- deterministic
- auditable
- small enough for local-file operation
- independent from Hermes core internals

---

## 1. Files

Recommended state files:
- `~/work/py-hbs-ads/state/notion_scrum/team_registry.json`
- `~/work/py-hbs-ads/state/notion_scrum/pending_prompts.json`
- `~/work/py-hbs-ads/state/notion_scrum/audit_log.jsonl`

---

## 2. Design principles

### 2.1 Stable keys over display labels
Use platform user ID as the durable external identity key.

Do not use Discord display name as the authoritative key.

### 2.2 Canonical person layer
Every external identity should resolve to one `canonical_person_key`.

This lets the workflow map multiple external identities to one person if needed.

### 2.3 Pending prompts are workflow objects
A pending prompt is not just a message.
It is a coordination object that links:
- a thread
- a question
- a target person
- a target task/project
- allowed update types
- lifecycle state

### 2.4 Append-only audit log
Every attempted or successful write should append a JSON line to the audit log.

---

## 3. `team_registry.json`

## 3.1 Purpose
Maps platform identities to canonical people and Notion targets.

## 3.2 Top-level structure

```json
{
  "schema_version": "1.0",
  "updated_at": "2026-04-20T16:30:00Z",
  "people": {
    "duc": {
      "canonical_person_key": "duc",
      "display_name": "Duc",
      "aliases": ["Đức", "Duc", "duc"],
      "role": "owner",
      "notion": {
        "people_page_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "user_id": null,
        "display_name": "Duc"
      },
      "platform_identities": [
        {
          "platform": "discord",
          "platform_user_id": "400303290174144512",
          "platform_username": "duc",
          "display_names": ["Duc", "Đức"]
        }
      ],
      "status": "active",
      "notes": "Primary project owner"
    }
  },
  "identity_index": {
    "discord:400303290174144512": "duc"
  }
}
```

## 3.3 Field definitions

### Top-level
- `schema_version`: string version for migration
- `updated_at`: ISO timestamp
- `people`: object keyed by `canonical_person_key`
- `identity_index`: map from `<platform>:<platform_user_id>` to canonical key

### Person object
- `canonical_person_key`: stable internal key
- `display_name`: preferred human-readable name
- `aliases`: known nicknames / alternate labels
- `role`: optional workflow role (`owner`, `editor`, `producer`, etc.)
- `notion`: Notion mapping object
- `platform_identities`: list of external identity records
- `status`: `active` / `inactive`
- `notes`: optional free text

### `notion`
- `people_page_id`: preferred if using a People directory database
- `user_id`: native Notion user ID if used
- `display_name`: Notion-side label

### `platform_identities[]`
- `platform`: currently `discord` for this workflow
- `platform_user_id`: authoritative external user ID
- `platform_username`: optional username/handle
- `display_names`: known observed display labels

## 3.4 Resolution rule
When resolving a sender:
1. Build `external_key = "<platform>:<platform_user_id>"`
2. Look up `identity_index[external_key]`
3. Use the resulting `canonical_person_key` to fetch the person record

If not found:
- result is unresolved
- no identity-sensitive Notion write may occur

---

## 4. `pending_prompts.json`

## 4.1 Purpose
Tracks open and resolved follow-up questions issued by Hermes.

## 4.2 Top-level structure

```json
{
  "schema_version": "1.0",
  "updated_at": "2026-04-20T16:30:00Z",
  "prompts": [
    {
      "pending_prompt_id": "pp_20260420_163000_roughcut_due_ma",
      "status": "open",
      "created_at": "2026-04-20T16:30:00Z",
      "updated_at": "2026-04-20T16:30:00Z",
      "closed_at": null,
      "source": {
        "platform": "discord",
        "chat_id": "1491765658759991561",
        "thread_id": "1495697645052887090",
        "channel_name": "#hbs-creative-sml",
        "session_key": "optional-session-key"
      },
      "outbound_message": {
        "assistant_message_id": "1496000000000000000",
        "reply_to_message_id": null,
        "text": "@Ma — task rough cut v1 chưa có due date. Mày muốn để ngày nào?"
      },
      "target": {
        "canonical_person_key": "ma",
        "platform": "discord",
        "platform_user_id": "1489176949271035984"
      },
      "notion": {
        "project_id": "11111111-2222-3333-4444-555555555555",
        "project_title": "Game teaser 03",
        "task_id": "66666666-7777-8888-9999-000000000000",
        "task_title": "rough cut v1"
      },
      "question": {
        "question_type": "due_date_request",
        "question_slot": "due_date",
        "prompt_summary": "Ask Ma for due date for rough cut v1",
        "expected_answer_shapes": ["date", "short_note"],
        "allowed_update_types": ["due_date_proposal", "task_comment"],
        "priority": "normal"
      },
      "resolution": {
        "matched_inbound_message_id": null,
        "matched_by": null,
        "match_confidence": null,
        "resolved_update_type": null,
        "resolved_value": null,
        "resolution_notes": null
      },
      "metadata": {
        "tags": ["scrum", "followup", "due-date"],
        "expires_at": "2026-04-23T16:30:00Z"
      }
    }
  ]
}
```

## 4.3 Field definitions

### Top-level
- `schema_version`: string version
- `updated_at`: ISO timestamp
- `prompts`: list of prompt objects

### Prompt identity and lifecycle
- `pending_prompt_id`: unique durable ID
- `status`: `open`, `answered`, `cancelled`, `expired`
- `created_at`
- `updated_at`
- `closed_at`

### `source`
- `platform`
- `chat_id`
- `thread_id`
- `channel_name`
- `session_key`: optional diagnostic field only

### `outbound_message`
- `assistant_message_id`: Discord message ID of Hermes’s prompt if known
- `reply_to_message_id`: if Hermes asked by replying to another message
- `text`: exact outbound question text

### `target`
- `canonical_person_key`: intended respondent
- `platform`
- `platform_user_id`: intended external user if known

### `notion`
- `project_id`
- `project_title`
- `task_id`
- `task_title`

At least one of `project_id` or `task_id` must exist.

### `question`
- `question_type`: category of coordination question
- `question_slot`: what field or decision the workflow wants
- `prompt_summary`: concise semantic summary
- `expected_answer_shapes`: allowed answer shapes
- `allowed_update_types`: safe write types for this prompt
- `priority`: `low`, `normal`, `high`

### `resolution`
Populated only after a reply is matched or the prompt is closed.

Fields:
- `matched_inbound_message_id`
- `matched_by`: `reply_to`, `single_open_prompt_for_sender`, `explicit_task_reference`, etc.
- `match_confidence`: float `0.0`–`1.0`
- `resolved_update_type`
- `resolved_value`: object/string/primitive depending on type
- `resolution_notes`

### `metadata`
- `tags`
- `expires_at`

---

## 5. `audit_log.jsonl`

## 5.1 Purpose
Append-only write and match audit.

Each line is one JSON object.

Example:
```json
{"timestamp":"2026-04-20T16:45:00Z","event_type":"notion_write","pending_prompt_id":"pp_20260420_163000_roughcut_due_ma","person":"ma","task_id":"66666666-7777-8888-9999-000000000000","update_type":"task_comment","dry_run":false,"success":true,"details":{"summary":"Added due-date note from Ma"}}
```

## 5.2 Recommended event types
- `identity_resolved`
- `identity_unresolved`
- `prompt_recorded`
- `reply_matched`
- `reply_ambiguous`
- `reply_unmatched`
- `update_planned`
- `notion_write`
- `notion_write_blocked`
- `state_doctor_warning`

---

## 6. Enumerations

## 6.1 `question_type`
Recommended initial values:
- `due_date_request`
- `status_check`
- `blocker_check`
- `owner_ack_request`
- `task_breakdown_request`
- `review_state_check`
- `generic_followup`

## 6.2 `allowed_update_types`
Recommended initial values:
- `task_comment`
- `status_note`
- `blocked_note`
- `due_date_proposal`
- `owner_ack`
- `mark_prompt_answered`

## 6.3 prompt `status`
- `open`
- `answered`
- `cancelled`
- `expired`

---

## 7. Matching contract for scripts

The matcher should return a JSON object shaped roughly like this:

```json
{
  "matched": true,
  "confidence": 0.96,
  "method": "reply_to",
  "pending_prompt_id": "pp_20260420_163000_roughcut_due_ma",
  "candidate_count": 1,
  "candidates": [
    {
      "pending_prompt_id": "pp_20260420_163000_roughcut_due_ma",
      "score": 0.96,
      "reasons": ["reply_to_assistant_message", "sender_matches_target"]
    }
  ],
  "requires_clarification": false,
  "clarification_reason": null
}
```

If ambiguous:

```json
{
  "matched": false,
  "confidence": 0.42,
  "method": "ambiguous",
  "pending_prompt_id": null,
  "candidate_count": 2,
  "candidates": [ ... ],
  "requires_clarification": true,
  "clarification_reason": "multiple_open_prompts_for_same_sender"
}
```

---

## 8. Migration rule

If schema changes later:
- bump `schema_version`
- write a one-shot migration script instead of silently mutating formats ad hoc

---

## 9. V1 minimum validation rules

### `team_registry.json`
- must contain `schema_version`
- every person must have `canonical_person_key`
- every indexed identity must map to an existing person
- no duplicate external identity keys

### `pending_prompts.json`
- must contain `schema_version`
- every prompt must have `pending_prompt_id`
- every open prompt must have `source.thread_id`
- every open prompt must have at least one Notion target (`project_id` or `task_id`)
- every open prompt must have `allowed_update_types`

---

## 10. Recommendation

Keep these schemas intentionally boring.

The goal is not elegance — it is reliable attribution, safe matching, and auditable writes in a shared Discord thread.
