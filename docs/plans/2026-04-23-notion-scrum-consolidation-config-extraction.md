# Notion Scrum Consolidation + Config Extraction Implementation Plan

> **For Hermes:** Execute this plan with TDD and use Claude CLI Sonnet 4.6 for plan review and implementation/review support.

**Goal:** Make the Discord↔Notion Scrum workflow easier to operate and less brittle by extracting board-specific config from Python code, reducing duplicated skill guidance, and adding a clearer operator decision path.

**Architecture:** Keep `template_catalog.py` as the payload source of truth and keep the thin wrappers as the main operator surface. Move workspace-specific board/channel defaults into local config, keep backward-compatible fallbacks for tests/current setup, and consolidate runtime guidance into the attribution skill while downgrading the design skill into an archive/pointer.

**Tech Stack:** Python 3.11, local JSON config/state, pytest, Hermes skills/docs, Claude CLI Sonnet 4.6.

---

### Task 1: Add board config loader and example config

**Objective:** Move board/channel defaults into local config without breaking current tests or local operation.

**Files:**
- Create: `config/notion_scrum/board_config.example.json`
- Create: `scripts/notion_scrum/board_config.py`
- Modify: `.gitignore`
- Modify: `state/notion_scrum/README.md`
- Test: `tests/test_board_config.py`

**Step 1: Write failing tests for board config loading**
- Add tests for fallback config, partial override merge, and template/catalog constants reading config.

**Step 2: Run failing tests**
- Run: `pytest tests/test_board_config.py -q`
- Expected: FAIL because `board_config.py` does not exist yet.

**Step 3: Implement minimal config layer**
- Create `config/notion_scrum/` if it does not exist.
- Add `board_config.py` loader with explicit fallback values matching the current hardcoded HBS defaults for:
  - Projects data source ID
  - Tasks Tracker data source ID
  - default Discord chat ID
  - default Discord channel name
- Add `board_config.example.json` bootstrap file.
- Add live config path to repo `.gitignore`.
- Update `state/notion_scrum/README.md` to explain config bootstrap.

**Step 4: Verify tests pass**
- Run: `pytest tests/test_board_config.py -q`
- Expected: PASS.

---

### Task 2: Switch template catalog to config-backed defaults

**Objective:** Remove board-specific IDs/channel defaults from hardcoded template logic while keeping public constants stable.

**Files:**
- Modify: `scripts/notion_scrum/template_catalog.py`
- Test: `tests/test_notion_scrum_templates.py`
- Test: `tests/test_notion_scrum_wrappers.py`

**Step 1: Write/extend failing tests**
- Add or confirm at least one test asserts that catalog constants and prompt defaults come from the config loader rather than duplicated literals.

**Step 2: Run targeted tests**
- Run: `pytest tests/test_board_config.py tests/test_notion_scrum.py tests/test_notion_scrum_templates.py tests/test_notion_scrum_wrappers.py -q`
- Expected: FAIL until catalog is wired to config.

**Step 3: Implement minimal change**
- Import `board_config.load()` in `template_catalog.py`.
- Keep exported constants `PROJECTS_DATA_SOURCE_ID` and `TASKS_DATA_SOURCE_ID` for backward compatibility.
- Replace hardcoded `chat_id` and `channel_name` defaults with config-backed values.

**Step 4: Verify pass**
- Run: `pytest tests/test_board_config.py tests/test_notion_scrum.py tests/test_notion_scrum_templates.py tests/test_notion_scrum_wrappers.py -q`
- Expected: PASS.

---

### Task 3: Add a short operator decision path and reduce skill duplication

**Objective:** Make the runtime skill the single main operator guide and reduce confusion between runtime vs design skills.

**Files:**
- Modify: `~/.hermes/skills/productivity/discord-notion-scrum-attribution/SKILL.md`
- Modify: `~/.hermes/skills/productivity/discord-public-thread-notion-scrum/SKILL.md`
- Modify: `~/.hermes/skills/productivity/media-scrum-master-notion/SKILL.md`

**Step 1: Add operator decision path to runtime skill**
- Insert a compact table mapping common intents to wrappers/entrypoints.
- Bump version to `1.4.0`.

**Step 2: Convert design skill into a pointer/archive**
- Keep short rationale but point operators to the runtime skill + durable design docs.
- Bump version to archived/next version.

**Step 3: Trim redundant runtime/design overlap**
- Reduce repeated sections that already live in the design docs.
- Keep runtime skill focused on what to do, not why the architecture was originally chosen.

**Step 4: Verify by rereading both skills**
- Make sure runtime path is obvious and no critical safety rules were lost.
- Treat this as a manual verification gate: there is no automated test coverage for these skill prose edits, so the operator must explicitly reread the decision path and runtime/design split before proceeding.

---

### Task 4: Refresh operator docs to match the new default path

**Objective:** Keep docs aligned with config bootstrap and wrapper-first operation.

**Files:**
- Modify: `docs/agent/notion-scrum-template-catalog.md`
- Modify: `docs/agent/shared-thread-attributed-automation-pattern.md`
- Verify: `docs/agent/README.md`

**Step 1: Update config/bootstrap guidance**
- Explain that board defaults are loaded from `config/notion_scrum/board_config.json` with fallback HBS defaults.

**Step 2: Keep wrapper-first guidance explicit**
- Ensure docs say: wrapper first, template second, low-level scripts last.

**Step 3: Verify README indexing**
- Confirm docs index still points to the right files.

---

### Task 5: Full verification + Claude review

**Objective:** Validate the system after refactor and use Claude Sonnet 4.6 as an external reviewer before stopping.

**Files:**
- Verify all touched files
- Test: `tests/test_board_config.py`
- Test: `tests/test_notion_scrum.py`
- Test: `tests/test_notion_scrum_templates.py`
- Test: `tests/test_notion_scrum_wrappers.py`

**Step 1: Run full relevant test suite**
- Run: `pytest tests/test_board_config.py tests/test_notion_scrum.py tests/test_notion_scrum_templates.py tests/test_notion_scrum_wrappers.py -q`
- Expected: all pass.

**Step 2: Run command verification**
- `python scripts/notion_scrum/query_common_view.py --view active-projects`
- `python scripts/notion_scrum/prepare_prompt.py --kind task-due-date ...`
- `python scripts/notion_scrum/prepare_notion_patch.py --kind status ...`
- `python scripts/notion_scrum/prepare_inbound_event.py ...`
- `python scripts/notion_scrum/preflight.py`

**Step 3: Ask Claude CLI Sonnet 4.6 to review the final pass**
- Scope: config extraction correctness, duplication reduction, operator clarity, remaining risks.

**Step 4: Summarize findings and stop**
- Report what changed, what passed, and any remaining follow-up items.
