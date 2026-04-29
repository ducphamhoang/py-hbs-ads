# Notion Scrum Staffing-Awareness Implementation Plan

> **For Hermes:** Use subagent-driven-development for execution. Before implementation starts, get an external review from Claude CLI Sonnet 4.6 on the PRD and this plan.

**Goal:** Add a staffing-aware people-state layer to the Discord↔Notion Scrum workflow so Hermes can track leave/availability, derive effective workload and assignment risk, and produce staffing-aware follow-ups and reports without weakening guarded-write safety.

**Architecture:** Keep identity (`team_registry.json`), coordination (`pending_prompts.json`), and staffing (`people_state.json`) as separate sources of truth. Build a derived `staffing_snapshot.json` from registry + board cache + people state. Keep operator entrypoints thin, centralize people-state logic in a shared store module, and extend reporting/routing using the derived snapshot rather than scattering availability logic across every script.

**Tech Stack:** Python 3.11, local JSON state, pytest, existing `scripts/notion_scrum` helpers, Hermes skill/docs, Claude CLI Sonnet 4.6 review.

---

## Delivery outline

### New files
- `scripts/notion_scrum/people_state_store.py`
- `scripts/notion_scrum/update_people_state.py`
- `scripts/notion_scrum/query_people_state.py`
- `scripts/notion_scrum/build_staffing_snapshot.py`
- `scripts/notion_scrum/staffing_risk_report.py`
- `tests/test_notion_scrum_people_state.py`
- `tests/test_notion_scrum_staffing_report.py`
- `docs/agent/hermes-discord-notion-scrum-staffing-state-schema.md`

### Modified files
- `scripts/notion_scrum/preflight.py`
- `scripts/notion_scrum/result_contracts.py`
- `scripts/notion_scrum/daily_board_report.py`
- `docs/agent/hermes-discord-notion-scrum-state-schema.md`
- `docs/agent/hermes-discord-notion-scrum-skill-spec.md`
- `docs/agent/notion-scrum-template-catalog.md`
- `~/.hermes/skills/productivity/discord-notion-scrum-attribution/SKILL.md`

### State files
- `state/notion_scrum/people_state.json`
- `state/notion_scrum/cache/staffing_snapshot.json`

---

### Task 1: Freeze the data model and bootstrap examples

**Objective:** Define the staffing schema and result-envelope additions clearly before adding logic so later scripts share one contract.

**Files:**
- Create: `docs/agent/hermes-discord-notion-scrum-staffing-state-schema.md`
- Modify: `docs/agent/hermes-discord-notion-scrum-state-schema.md`
- Modify: `scripts/notion_scrum/result_contracts.py`
- Create: `state/notion_scrum/people_state.json` (if repo policy allows bootstrap state) or document bootstrap shape
- Test: `tests/test_notion_scrum_people_state.py`

**Step 1: Write failing schema tests**
- Add tests for:
  - valid empty/default people-state container
  - valid leave window record
  - invalid backup person key
  - invalid date window (`until < since`)
  - invalid availability or bandwidth enum
  - staffing result envelope includes `effective_followup_person_key` and `routing_reason`

**Step 2: Run targeted tests to confirm failure**
- Run: `pytest tests/test_notion_scrum_people_state.py -q`
- Expected: FAIL because the people-state module does not exist yet.

**Step 3: Write the schema doc**
- Document the canonical JSON structure for:
  - `availability`
  - `capacity`
  - `coordination`
  - metadata/source blocks
- Keep the initial model small:
  - `active`, `leave`, `ooo`, `partial`, `unknown`
  - `normal`, `reduced`, `limited`, `unknown`
- Explicitly state that assignment is derived from board cache, not manually entered here.

**Step 4: Extend the stable result contract now**
- Add at least:
  - `effective_followup_person_key`
  - `routing_reason`
- Keep the staffing scripts on the same envelope style as the existing workflow.

**Step 5: Create minimal bootstrap state shape**
- Add a default `people_state.json` shape or document the exact bootstrappable container:
  - `schema_version`
  - `updated_at`
  - `people`

**Step 6: Verify test/doc alignment**
- Re-read the schema doc and confirm every tested field is documented.

---

### Task 2: Build the shared people-state store module

**Objective:** Centralize load/save/validate/transition logic so operator scripts stay thin.

**Files:**
- Create: `scripts/notion_scrum/people_state_store.py`
- Test: `tests/test_notion_scrum_people_state.py`

**Step 1: Implement minimal module surface**
Add functions for:
- `load_people_state(path)`
- `save_people_state(path, data)`
- `validate_people_state(data, registry=None)`
- `set_leave(...)`
- `clear_leave(...)`
- `set_bandwidth(...)`
- `set_backup(...)`
- `get_person_state(...)`
- `is_person_absent(...)`
- `effective_followup_target(...)`

**Step 2: Keep writes explicit and deterministic**
- Require canonical person keys internally.
- Do not let this module perform fuzzy person resolution.
- Accept optional registry input for backup-person validation.

**Step 3: Write minimal transition rules**
- `set_leave` sets `availability.status=leave` and dates.
- `clear_leave` resets to `active` or `unknown` by explicit rule.
- `set_bandwidth` changes only capacity fields.
- `set_backup` changes only coordination backup.

**Step 4: Run tests**
- Run: `pytest tests/test_notion_scrum_people_state.py -q`
- Expected: PASS for schema validation + basic transitions.

**Step 5: Commit checkpoint**
- Suggested commit: `feat: add notion scrum people state store`

---

### Task 3: Add guarded operator write path for availability/leave changes

**Objective:** Let operators manage staffing state through a thin, safe structured CLI wrapper.

**Files:**
- Create: `scripts/notion_scrum/update_people_state.py`
- Test: `tests/test_notion_scrum_people_state.py`

**Step 1: Write failing CLI tests**
Add tests for structured commands such as:
- `--person toanvt --action set-leave --until 2026-04-28`
- `--person toanvt --action clear-leave`
- `--person ma --action set-bandwidth --bandwidth reduced --note "off this afternoon"`
- ambiguity when a person alias maps to multiple candidates
- dry-run output vs `--execute`

**Step 2: Implement structured CLI surface**
- Use flags, not free-form natural-language parsing.
- Hermes is responsible for producing the structured command.
- Include resolved canonical person key and action type in result data.

**Step 3: Keep the wrapper thin**
- Resolve person through registry-backed helpers.
- Call `people_state_store.py` directly.
- Default to dry-run.
- Stop on ambiguity.

**Step 4: Verify targeted tests**
- Run: `pytest tests/test_notion_scrum_people_state.py -q`
- Expected: PASS.

**Step 5: Manual smoke commands**
- Run dry-run examples with local fixtures, for example:
  - `python scripts/notion_scrum/update_people_state.py --person toanvt --action set-leave --until 2026-04-28 --backup ducph`
  - `python scripts/notion_scrum/update_people_state.py --person ma --action set-bandwidth --bandwidth reduced --note "off this afternoon"`
- Expected: structured dry-run output, no write unless `--execute`.

---

### Task 4: Add read-only people-state query surface

**Objective:** Make staffing facts easy to inspect without opening JSON files directly.

**Files:**
- Create: `scripts/notion_scrum/query_people_state.py`
- Test: `tests/test_notion_scrum_people_state.py`

**Step 1: Implement query modes**
Support at least:
- `--person <name>`
- `--on-leave-today`
- `--reduced-bandwidth`
- `--backup-for <name>`

**Step 2: Keep query path read-only and lightweight**
- No preflight requirement for read-only use.
- Return compact JSON by default or with `--json`.

**Step 3: Verify query tests**
- Run: `pytest tests/test_notion_scrum_people_state.py -q`
- Expected: PASS.

---

### Task 5: Build derived staffing snapshot

**Objective:** Create one fast read model for reports and routing instead of recomputing people/task/project joins everywhere.

**Files:**
- Create: `scripts/notion_scrum/build_staffing_snapshot.py`
- Create: `state/notion_scrum/cache/staffing_snapshot.json` (generated artifact)
- Test: `tests/test_notion_scrum_staffing_report.py`

**Step 1: Write failing derivation tests**
Cover at least:
- absent person with active tasks
- absent owner with backup
- owner with multiple active projects/tasks
- person with reduced bandwidth and overdue item

**Step 2: Implement derivation logic**
Input sources:
- `team_registry.json`
- `people_state.json`
- `cache/board_snapshot.json`

Output per person should include:
- display name
- availability status / leave window
- backup person key
- active projects/tasks
- counts
- risk flags

**Step 3: Keep assignments derived, not manually overridden**
- Derive projects/tasks from board cache owner ids + registry notion mappings.
- Do not invent assignment overrides in V1.

**Step 4: Verify tests**
- Run: `pytest tests/test_notion_scrum_staffing_report.py -q`
- Expected: PASS.

**Step 5: Add manual smoke command**
- `python scripts/notion_scrum/build_staffing_snapshot.py`
- Expected: writes snapshot JSON and prints summary counts.

---

### Task 6: Add staffing-risk module and optional operator CLI

**Objective:** Separate staffing-specific risk logic from the broader daily board report so it stays testable and reusable.

**Files:**
- Create: `scripts/notion_scrum/staffing_risk_report.py`
- Test: `tests/test_notion_scrum_staffing_report.py`

**Step 1: Decide the file identity and lock it in**
- Treat `staffing_risk_report.py` as a reusable module first.
- It may expose a small standalone CLI too, but the primary contract is importable functions used by `daily_board_report.py`.

**Step 2: Implement minimum risk groups**
- tasks on absent owners
- projects with absent owners
- absent owners without backup
- overloaded people
- reduced-bandwidth people with overdue items

**Step 3: Make thresholds explicit**
- Start with defaults in code or config constants.
- Keep thresholds overridable later.

**Step 4: Emit structured result first**
- JSON output should be stable and machine-usable.
- Human formatting can be handled by `daily_board_report.py`.

**Step 5: Verify tests**
- Run: `pytest tests/test_notion_scrum_staffing_report.py -q`
- Expected: PASS.

---

### Task 7: Extend preflight for people-state integrity

**Objective:** Catch broken staffing configuration before live operations depend on it.

**Files:**
- Modify: `scripts/notion_scrum/preflight.py`
- Test: `tests/test_notion_scrum_people_state.py`

**Step 1: Add people-state validation to preflight**
Preflight should warn or error on:
- invalid schema
- unknown backup person keys
- invalid leave ranges
- unsupported schema version

**Step 2: Decide warning vs error behavior**
Recommended default:
- missing `people_state.json` = warning for read-only workflows
- invalid existing `people_state.json` = error for staffing-aware writes

**Step 3: Verify targeted tests**
- Run: `pytest tests/test_notion_scrum_people_state.py tests/test_notion_scrum.py -q`
- Expected: PASS.

---

### Task 8: Extend daily board report with staffing-aware sections

**Objective:** Upgrade the daily digest from task hygiene only to staffing-aware operational coordination.

**Files:**
- Modify: `scripts/notion_scrum/daily_board_report.py`
- Test: `tests/test_notion_scrum_staffing_report.py`

**Step 1: Load staffing snapshot or build from inputs**
- Prefer a generated `staffing_snapshot.json` when present/fresh.
- Fall back to building or to a board-only mode with warnings if missing.

**Step 2: Add staffing sections to rendered output**
At minimum render:
- people on leave / unusual availability
- tasks sitting with absent owners
- projects with absent owners and no backup
- overloaded owners

**Step 3: Respect mention policy**
- Use registry-backed Discord mention tokens.
- If owner is absent and backup exists, action lines should mention backup or clearly say follow-up should route there.

**Step 4: Keep backward compatibility**
- If people-state is unavailable, current board hygiene output should still work.

**Step 5: Run report tests**
- Run: `pytest tests/test_notion_scrum_staffing_report.py tests/test_notion_scrum.py -q`
- Expected: PASS.

---

### Task 9: Add staffing-aware follow-up/routing helper usage

**Objective:** Make the workflow capable of choosing the right human target without silently mutating Notion ownership.

**Files:**
- Modify: `scripts/notion_scrum/people_state_store.py`
- Optionally modify: `scripts/notion_scrum/daily_board_report.py`
- Test: `tests/test_notion_scrum_people_state.py`

**Step 1: Add effective-followup helper paths**
- Given a canonical owner, return:
  - direct owner if active
  - backup if absent and backup exists
  - escalation-needed if absent and no backup

**Step 2: Keep routing separate from ownership**
- Do not change assignee fields in Notion.
- Only influence prompts/recommendations/reporting.

**Step 3: Add tests**
- verify active owner routes to self
- absent owner routes to backup
- absent owner without backup triggers escalation state

**Step 4: Run tests**
- Run: `pytest tests/test_notion_scrum_people_state.py -q`
- Expected: PASS.

---

### Task 10: Patch skill + docs to explain the new operating model

**Objective:** Keep the runtime guidance aligned with the new three-layer state model.

**Files:**
- Modify: `docs/agent/hermes-discord-notion-scrum-skill-spec.md`
- Modify: `docs/agent/notion-scrum-template-catalog.md`
- Modify: `~/.hermes/skills/productivity/discord-notion-scrum-attribution/SKILL.md`

**Step 1: Add staffing-aware operator decision path**
Cover:
- when to query board cache,
- when to query people state,
- when to update leave/availability,
- how routing changes when owner is absent.

**Step 2: Document safety boundaries**
Explicitly state:
- leave state changes follow-up routing,
- leave state does not auto-reassign Notion ownership,
- ambiguity blocks people-state writes too.

**Step 3: Verify prose manually**
- Re-read the skill and docs end-to-end.
- Confirm the routing rules, reporting expectations, and wrapper-first guidance are obvious.

---

### Task 11: Full verification + Claude review

**Objective:** Validate the proposed design and implementation approach before coding starts or before merge if code is already complete.

**Files:**
- Verify all touched files
- Test: `tests/test_notion_scrum_people_state.py`
- Test: `tests/test_notion_scrum_staffing_report.py`
- Test: `tests/test_notion_scrum.py`

**Step 1: Run full relevant tests**
- Run: `pytest tests/test_notion_scrum_people_state.py tests/test_notion_scrum_staffing_report.py tests/test_notion_scrum.py -q`
- Expected: all pass.

**Step 2: Run manual smoke commands**
- `python scripts/notion_scrum/preflight.py`
- `python scripts/notion_scrum/query_people_state.py --on-leave-today`
- `python scripts/notion_scrum/build_staffing_snapshot.py`
- `python scripts/notion_scrum/staffing_risk_report.py` *(only if a standalone CLI is kept; otherwise verify through an import-level test and `daily_board_report.py` output)*
- `python scripts/notion_scrum/daily_board_report.py --format text` (or current supported CLI shape)

**Step 3: Ask Claude CLI Sonnet 4.6 to review**
Review scope:
- schema split correctness
- script/module boundaries
- whether the design is too fragmented or appropriately layered
- risks around stale people-state and routing semantics
- whether operator surfaces are sensible

**Step 4: Stop with explicit verdict**
Final summary should state:
- what is approved,
- what must change before implementation,
- what can wait for V2.

---

## Recommended implementation defaults

- Keep leave windows date-only in V1.
- Keep assignments derived from board cache, not editable in people-state.
- Make operator-command people-state writes first-class before adding prompt-driven leave workflows.
- Keep `staffing_snapshot.json` as a standalone derived artifact.
- Reuse existing stable result-envelope style for new scripts.

## Main risks to watch during implementation

1. Mixing derived assignment with manually entered staffing facts in one file.
2. Letting staffing state silently mutate Notion ownership.
3. Spreading availability logic across too many scripts instead of using one shared module.
4. Breaking current board-only daily report behavior when staffing state is missing.

## Done definition

The implementation is done when:
- leave/availability state is writable through guarded scripts,
- staffing snapshot derivation works from real board cache + registry,
- daily report shows staffing-aware risks,
- follow-up routing can choose backup/escalation safely,
- tests cover schema, transitions, derivation, and report output,
- Claude Sonnet 4.6 review says the design is broadly reasonable with no major architectural objections.
