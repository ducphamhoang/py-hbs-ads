# Notion Scrum Agent Capabilities

This is the master reference for agents (Hermes, Nemo, etc.) to understand what operations are available, how to use them, and how they connect.

**Key principle:** Before trying anything, read this file. It tells you what you can do and when to use each tool.

---

## Quick Tool Reference

| Tool | Purpose | Input | Output | Use When |
|------|---------|-------|--------|----------|
| `sync_board_cache.py` | Update local board snapshot from Notion | — | `{snapshot_ts, projects_count, tasks_count, ...}` | Cache is stale (age check below) |
| `query_common_view.py` | Query projects/tasks without cache | `--view active-projects\|active-tasks\|ownerless\|undated` | `{request, data_source_id, template_name}` | Need live Notion data |
| `query_board_cache.py` | Inspect cached board snapshot | `--kind projects\|tasks --title/--id` | `{record}` or `{ids}` | Need to find IDs before update |
| `update_by_title.py` | **Main operator surface** — natural language updates | `--instruction "set task X to Y"` | `{ok, action_taken, data}` | User issues natural language command |
| `resolve_prepare_apply_patch.py` | Find, preview, and apply updates | `--target-kind tasks\|projects --title X --patch-kind status --var status_name=Y` | `{ok, data, patch}` | Multi-step update with validation |
| `template_catalog.py` | Render template JSON for custom use | `--template query_tasks_not_done --var page_id=X` | Rendered template JSON | Need to build custom requests |

---

## Common Operations & Their Workflows

### 1. Find and Complete All Tasks for a Project

**User request:** "Set project X and all its tasks to Complete"

```
Step 1: Find the project
  → query_board_cache.py --kind projects --title "Project X"
  → Extract: project_id, linked_task_ids

Step 2: Get task details
  → query_board_cache.py --kind tasks --id <task_id> (for each task)
  → Extract: title, current_status

Step 3: Update all (choose ONE):
  OPTION A (Recommended for 1-2 updates):
    → update_by_title.py --instruction "set task Y to Complete"
    → update_by_title.py --instruction "set project X to Complete"
  
  OPTION B (For bulk updates):
    → resolve_prepare_apply_patch.py --target-kind tasks --title Y 
      --project-title "Project X" --patch-kind status --var status_name=Complete
    
Step 4: Verify
  → query_board_cache.py --kind tasks --title Y (check updated status)
```

**Exit condition:** All tasks + project show `Status: Complete`

---

### 2. Query Active (Non-Done) Items

**User request:** "Show active projects" / "Show tasks without owners"

```
Step 1: Choose view
  → query_common_view.py --view active-projects
  → query_common_view.py --view active-tasks
  → query_common_view.py --view ownerless-active-tasks
  → query_common_view.py --view undated-active-tasks

Step 2: Parse results
  → Extract: count, items[], data_source_id
```

**Use case:** Quick overview without needing cache updates

---

### 3. Blocking a Task (with reason)

**User request:** "Block task X because Y"

```
Step 1: Parse instruction
  → update_by_title.py --instruction "block task X because missing asset"
  
  (Internally does:
    - Set Status → "Blocked"
    - Update "Blocked reason" field → "missing asset"
  )

Step 2: Confirm
  → query_board_cache.py --kind tasks --title X
  → Check: Status = "Blocked", "Blocked reason" = "missing asset"
```

**Supported formats (English):**
```
block task X of project Y because Z
```

**Supported formats (Vietnamese):**
```
đánh dấu blocked task X của project Y vì Z
```

---

### 4. Setting Due Dates

**User request:** "Set due date of task X to 2026-05-15"

```
Step 1: Parse and validate date
  → update_by_title.py --instruction "set due date of task X to 2026-05-15"
  
  Supported formats: YYYY-MM-DD, DD/MM/YYYY, YYYY/MM/DD

Step 2: Confirm
  → query_board_cache.py --kind tasks --title X
  → Check: "Due date" property = 2026-05-15
```

---

### 5. Adding Notes to Tasks

**User request:** "Add note on task X: 'Owner confirmed in Discord'"

```
Step 1: Parse instruction
  → update_by_title.py --instruction "note on task X: Owner confirmed in Discord"

Step 2: Confirm
  → query_board_cache.py --kind tasks --title X
  → Check: notes include new entry
```

---

## Patch Types (update-by_title.py)

When you call `update_by_title.py --instruction "..."`, it parses into a patch type:

### Patch Type: `status`
```python
{
  "patch_kind": "status",
  "patch_variables": {"status_name": "In progress"}
}
```
**Pattern (English):** `set (task|project) TITLE [of project P] to STATUS`
**Pattern (Vietnamese):** `đổi status (task|project) TITLE [của project P] thành STATUS`

### Patch Type: `rich-text` (for notes)
```python
{
  "patch_kind": "rich-text",
  "patch_variables": {
    "property_name": "Due date note",
    "text": "Owner confirmed 2026-04-25"
  }
}
```
**Pattern (English):** `note on (task|project) TITLE [of project P]: TEXT`
**Pattern (Vietnamese):** `ghi note cho (task|project) TITLE [của project P]: TEXT`

### Patch Type: `date`
```python
{
  "patch_kind": "date",
  "patch_variables": {"date_value": "2026-05-15"}
}
```
**Pattern (English):** `set due date of (task|project) TITLE [of project P] to DATE`
**Pattern (Vietnamese):** `đặt due date (task|project) TITLE [của project P] là DATE`

### Patch Type: `multi` (status + reason for blocking)
```python
{
  "patch_kind": "multi",
  "patch_variables": {
    "patches": [
      {"kind": "status", "variables": {"status_name": "Blocked"}},
      {"kind": "rich-text", "variables": {"property_name": "Blocked reason", "text": "missing asset"}}
    ]
  }
}
```
**Pattern (English):** `block (task|project) TITLE [of project P] because REASON`
**Pattern (Vietnamese):** `đánh dấu blocked (task|project) TITLE [của project P] vì REASON`

---

## Resolution Modes

When using `resolve_prepare_apply_patch.py`, specify `--mode`:

| Mode | Behavior | Use Case |
|------|----------|----------|
| `auto` | Cache-first: use snapshot if fresh + unique match; otherwise live revalidation | Default, balanced |
| `safe` | Always do one live Notion revalidation after cache lookup | When accuracy > speed |
| `fast` | Require fresh cache snapshot; fail if not found | When cache is guaranteed fresh |

**Cache freshness check:**
- Snapshot age ≤ 300 seconds (5 min) = fresh
- Snapshot age > 300 seconds = stale, trigger `sync_board_cache.py`

---

## Cache Structure Reference

Local cache file: `state/notion_scrum/cache/board_snapshot.json`

```json
{
  "snapshot_ts": "2026-04-28T14:30:00Z",
  "snapshot_age_seconds": 45,
  "projects": {
    "by_id": {
      "proj-123": { "id": "proj-123", "title": "Project X", "status": "In progress", ... }
    },
    "by_title": {
      "Project X": ["proj-123"]
    }
  },
  "tasks": {
    "by_id": {
      "task-456": { "id": "task-456", "title": "Task Y", "status": "Done", "project_id": "proj-123", ... }
    },
    "by_title": {
      "Task Y": ["task-456"]
    },
    "by_project_id": {
      "proj-123": ["task-456", "task-789"]
    }
  },
  "people": {
    "by_canonical_key": {
      "duc": { "canonical_key": "duc", "discord_id": "400303...", "notion_user_id": "...", ... }
    }
  }
}
```

**Key indexes:**
- `projects.by_id` → Find project by UUID
- `projects.by_title` → Find project IDs by name
- `tasks.by_project_id` → Find all task IDs for a project
- `tasks.by_title` → Find task IDs by name
- `people.by_canonical_key` → Find person by Discord/Notion mapping

---

## Common Errors & Recovery

| Error | Root Cause | Recovery | Prevention |
|-------|-----------|----------|-----------|
| `"No tasks found"` | Cache is stale or tasks aren't linked to project | `sync_board_cache.py` → retry `query_board_cache.py` | Check snapshot age before querying |
| `"Ambiguous title match"` | Multiple projects/tasks with same name | Return candidates + ask user for clarification | Require `--project-title` when ambiguous |
| `"Cache file not found"` | First run or cache was deleted | `sync_board_cache.py` (creates fresh snapshot) | Create on first run |
| `"Notion API 429 (rate limit)"` | Too many API calls in short time | Wait 60s, retry | Batch updates into multi-patch, use cache |
| `"Date format invalid"` | User provided unsupported date format | Reject + show supported: `YYYY-MM-DD, DD/MM/YYYY, YYYY/MM/DD` | Validate before parsing |
| `"Task not linked to project"` | User specified project, but task doesn't belong there | Check cache or ask if project is correct | Verify project_id before update |
| `"Property not found on page"` | Trying to update a field that doesn't exist | Check board schema; use available fields only | Know board schema before patching |

**Age check function:**
```python
age_seconds = (now - snapshot_ts)
if age_seconds > 300:  # 5 minutes
    sync_board_cache()
```

---

## Board Configuration

File: `config/notion_scrum/board_config.json`

```json
{
  "projects_data_source_id": "2e945d07-72af-8117-a240-000bf508da50",
  "tasks_data_source_id": "2e945d07-72af-81dd-821a-000b082e6e95",
  "default_discord_chat_id": "discord-channel-hbs-creative",
  "default_discord_channel_name": "#hbs-creative-sml"
}
```

**These values are:**
- Loaded once per script run
- Used as defaults when no explicit data source is passed
- **NOT** universal Notion IDs — they are specific to HBS workspace
- Can be overridden per environment

---

## Agent Startup Checklist

When Hermes/Nemo starts, verify:

- [ ] `config/notion_scrum/board_config.json` exists and is readable
- [ ] `state/notion_scrum/cache/` directory exists
- [ ] API key is available (from `common.py::load_api_key()`)
- [ ] If cache age > 300s, call `sync_board_cache.py` first
- [ ] User request is parseable by `update_by_title.py` pattern matching

---

## Script Dependencies (Calling Order)

```
User Request
    ↓
update_by_title.py
    ├─→ (if ambiguous title) query_board_cache.py
    ├─→ resolve_prepare_apply_patch.py
    │   ├─→ board_cache.py (load & lookup)
    │   └─→ (if needs live check) query_common_view.py
    └─→ (if --execute) common.py::notion_patch_page() [Notion API call]

Query Request
    ↓
query_common_view.py or query_board_cache.py
    ├─→ template_catalog.py (render request shape)
    └─→ (live) Notion API OR (cached) board_cache.py

Cache Sync
    ↓
sync_board_cache.py
    └─→ board_cache.py::sync_cache()
        └─→ Notion API
```

---

## Template Catalog (Advanced)

If you need to build custom requests outside the above tools, use the template catalog:

```bash
python ~/work/py-hbs-ads/scripts/notion_scrum/template_catalog.py \
  --template query_tasks_not_done \
  --var page_size=50

python ~/work/py-hbs-ads/scripts/notion_scrum/template_catalog.py \
  --template update_page_status \
  --var page_id=<uuid> \
  --var status_name='Done'
```

Available templates:
- **Create:** `create_project`, `create_task`
  - `create_project`: Creates project pages in Projects database with optional owner, end date, and brief. Variables: `project_name` (required), `owner_email` (optional), `end_date` (optional, YYYY-MM-DD), `brief` (optional, rich-text content). Auto-loads `projects_data_source_id` from board_config.
  - `create_task`: Creates task pages in Tasks database, auto-linked to parent project, with optional assignee and due date. Variables: `task_name` (required), `project_id` (required), `assignee_email` (optional), `due_date` (optional, YYYY-MM-DD), `brief` (optional, rich-text content). Auto-loads `tasks_data_source_id` from board_config.
- **Queries:** `query_projects_not_done`, `query_tasks_not_done`, `query_tasks_missing_owner`, `query_tasks_missing_due_date`
- **Updates:** `update_page_status`, `update_page_rich_text`, `update_page_date`
- **Identity:** `lookup_notion_person_by_discord`, `inbound_discord_reply_event`
- **Prompts:** `prompt_task_due_date_request`, `prompt_task_status_request`

**Usage examples:**
```bash
# List all templates
python scripts/notion_scrum/template_catalog.py --list

# Create a project
python scripts/notion_scrum/template_catalog.py \
  --template create_project \
  --var project_name="Game teaser 03" \
  --var brief="30-sec video concept"

# Create a project with owner and end date
python scripts/notion_scrum/template_catalog.py \
  --template create_project \
  --var project_name="Q2 Campaign" \
  --var owner_email="duc@example.com" \
  --var end_date="2026-06-30" \
  --var brief="Creative campaign assets"

# Create a task linked to that project
python scripts/notion_scrum/template_catalog.py \
  --template create_task \
  --var task_name="rough cut v1" \
  --var project_id=<project-uuid>

# Create a task with assignee and due date
python scripts/notion_scrum/template_catalog.py \
  --template create_task \
  --var task_name="Design mockups" \
  --var project_id=<project-uuid> \
  --var assignee_email="ma@example.com" \
  --var due_date="2026-05-15" \
  --var brief="High-fidelity mockups for review"
```

### Field Reference for create_project and create_task

#### Project Creation Fields

| Field | Type | Required | Format | Purpose |
|-------|------|----------|--------|---------|
| `project_name` | text | Yes | Plain text | Title of the project |
| `owner_email` | person | No | Notion email address (e.g., `duc@example.com`) | Person responsible for the project; resolved to Notion user ID at runtime |
| `end_date` | date | No | ISO 8601: `YYYY-MM-DD` | Target completion date for the project |
| `brief` | rich-text | No | Plain text or markdown | Project description/context, stored as page block content |
| `status` | status | No (default: "In progress") | Text matching Notion status option | Current project status |

#### Task Creation Fields

| Field | Type | Required | Format | Purpose |
|-------|------|----------|--------|---------|
| `task_name` | text | Yes | Plain text | Title of the task |
| `project_id` | relation | Yes | Notion page UUID | Parent project this task belongs to |
| `assignee_email` | person | No | Notion email address (e.g., `ma@example.com`) | Person responsible for the task; resolved to Notion user ID at runtime |
| `due_date` | date | No | ISO 8601: `YYYY-MM-DD` | Target completion date for the task |
| `brief` | rich-text | No | Plain text or markdown | Task description/context, stored as page block content |
| `status` | status | No (default: "To do") | Text matching Notion status option | Current task status |

#### Notes on Optional Fields

- **Email fields** (`owner_email`, `assignee_email`): Provide the person's Notion workspace email. The system resolves this to their Notion user ID when creating the page.
- **Date fields** (`end_date`, `due_date`): Must be valid ISO 8601 date format (`YYYY-MM-DD`). Invalid dates will cause the API call to fail.
- **Brief content**: Stored as a rich-text paragraph block under the page. If not provided, no content block is added.
- **Optional fields with empty values**: Simply omit them from the `--var` arguments; they default to empty and are skipped.

---

## Example: Complete Workflow (Project + All Tasks)

**User:** "Complete project 'Game teaser 03' and all its tasks"

**Agent workflow:**

```python
# Step 1: Sync cache if needed
cache_age = check_cache_age()
if cache_age > 300:
    sync_board_cache()
    
# Step 2: Find project
project_ids = query_board_cache(kind='projects', title='Game teaser 03')
if len(project_ids) != 1:
    return f"Found {len(project_ids)} projects; please clarify"
project_id = project_ids[0]

# Step 3: Get linked tasks
project = query_board_cache(kind='projects', id=project_id)
linked_task_ids = project.get('linked_task_ids', [])

# Step 4: Build updates
updates = []
for task_id in linked_task_ids:
    task = query_board_cache(kind='tasks', id=task_id)
    if task['status'] != 'Complete':
        updates.append({
            'title': task['title'],
            'project_title': 'Game teaser 03',
            'target_kind': 'tasks',
            'patch_kind': 'status',
            'patch_variables': {'status_name': 'Complete'}
        })

updates.append({
    'title': 'Game teaser 03',
    'target_kind': 'projects',
    'patch_kind': 'status',
    'patch_variables': {'status_name': 'Complete'}
})

# Step 5: Apply updates
results = []
for update in updates:
    result = resolve_prepare_apply_patch(
        **update,
        resolve_mode='auto',
        max_cache_age_seconds=300,
        execute=True
    )
    results.append(result)
    if not result['ok']:
        return f"Failed at {update['title']}: {result['errors']}"

return f"✓ Updated {len(results)} items to Complete"
```

---

## Quick Decision Tree

**I need to...**

**← Query projects/tasks?**
→ Use `query_common_view.py` (live) or `query_board_cache.py` (cached)

**← Find a specific task by title?**
→ Use `query_board_cache.py --kind tasks --title X` (requires fresh cache)

**← Update status/date/notes on one item?**
→ Use `update_by_title.py --instruction "set task X to Y"`

**← Update many items (bulk)?**
→ Use `resolve_prepare_apply_patch.py --target-kind tasks` in a loop

**← Cache is slow or stale?**
→ Call `sync_board_cache.py` first

**← Not sure if cache is fresh?**
→ Check snapshot age; sync if > 300s

**← Need to preview changes before applying?**
→ Use `resolve_prepare_apply_patch.py` with `--execute false` (dry-run)

---

## Glossary

| Term | Meaning |
|------|---------|
| **Patch** | A change to be applied (status update, note, date, etc.) |
| **Resolve** | Find the real Notion page ID for a user-supplied title |
| **Cache snapshot** | Local JSON copy of Notion board state |
| **Data source ID** | UUID of a Notion database/collection |
| **Target kind** | Either `projects` or `tasks` |
| **Canonical key** | Person's normalized identifier (e.g., `duc`, `ma`) |
| **Dry-run** | Preview changes without applying |
| **Multi-patch** | Multiple changes applied in sequence (e.g., set status + set reason) |

---

**Last updated:** 2026-04-28  
**Maintained by:** Hermes / Agent System  
**Contact for updates:** See `.planning/PROJECT.md`
