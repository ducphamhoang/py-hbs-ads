# Notion Scrum Template Catalog

This file turns the most common Discord ↔ Notion coordination jobs into reusable templates instead of ad-hoc JSON fragments.

Primary implementation:
- `scripts/notion_scrum/template_catalog.py`

## Why this exists

Common operations repeat in this workflow:
- query `Projects` where `Status != Done`
- query `Tasks Tracker` where `Status != Done`
- query active tasks missing owner / due date
- patch project/task `Status`
- patch a rich-text note on a project/task page
- resolve a Discord user to canonical person + Notion mapping
- create a validated pending prompt for due date / status follow-up
- build an inbound Discord event payload for dry-run or execute

Instead of rebuilding those JSON shapes every time, use the catalog and override only the variables that actually change.

## Board defaults captured here

Board/channel defaults are now loaded at runtime from:
- `config/notion_scrum/board_config.json`

Bootstrap from:
- `config/notion_scrum/board_config.example.json`

The values below are the current HBS fallback defaults used when no local config override exists:
- `Projects` data source: `2e945d07-72af-8117-a240-000bf508da50`
- `Tasks Tracker` data source: `2e945d07-72af-81dd-821a-000b082e6e95`
- default Discord chat ID: `discord-channel-hbs-creative`
- default Discord channel name: `#hbs-creative-sml`

Treat these as local-environment defaults, not universal Notion IDs.

## Available templates

### Query templates
- `query_projects_not_done`
- `query_tasks_not_done`
- `query_tasks_missing_owner`
- `query_tasks_missing_due_date`

### Local cache helpers
- `scripts/notion_scrum/sync_board_cache.py`
- `scripts/notion_scrum/query_board_cache.py`
- `scripts/notion_scrum/resolve_board_target.py`
- `scripts/notion_scrum/resolve_and_prepare_patch.py`
- `scripts/notion_scrum/resolve_prepare_apply_patch.py`
- `scripts/notion_scrum/update_by_title.py`
- cache artifact: `state/notion_scrum/cache/board_snapshot.json`
- use `update_by_title.py` as the preferred direct-operator surface in Discord when the user phrases a safe explicit command like `set task X of project Y to In progress`, `set due date of task X ...`, `note on task X ...`, or `block task X ... because ...`
- `update_by_title.py` also understands Vietnamese operator phrases like `đổi status task ... thành ...`, `đặt due date task ... là ...`, `ghi note cho task ...: ...`, and `đánh dấu blocked task ... vì ...`
- `set due date ...` now patches the real Notion date property (default `Due date`) instead of only writing a note field
- ambiguous cache lookups now return candidate summaries + a user-facing clarification message

### Update templates
- `update_page_status`
- `update_page_rich_text`
- `update_page_date`

### Identity / event templates
- `lookup_notion_person_by_discord`
- `inbound_discord_reply_event`

### Prompt templates
- `prompt_task_due_date_request`
- `prompt_task_status_request`

## Reuse pattern

### 1. List templates

```bash
python ~/work/py-hbs-ads/scripts/notion_scrum/template_catalog.py --list
```

### 2. Render one template

```bash
python ~/work/py-hbs-ads/scripts/notion_scrum/template_catalog.py \
  --template query_tasks_not_done
```

### 3. Render with overrides

```bash
python ~/work/py-hbs-ads/scripts/notion_scrum/template_catalog.py \
  --template update_page_status \
  --var page_id=aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee \
  --var status_name='In progress'
```

## Common task recipes

### A. Query active Projects

```bash
python ~/work/py-hbs-ads/scripts/notion_scrum/template_catalog.py \
  --template query_projects_not_done
```

Use the rendered JSON as the body for:
- `POST /v1/data_sources/{data_source_id}/query`

### B. Query active Tasks Tracker rows

```bash
python ~/work/py-hbs-ads/scripts/notion_scrum/template_catalog.py \
  --template query_tasks_not_done
```

### C. Find active tasks missing owner

```bash
python ~/work/py-hbs-ads/scripts/notion_scrum/template_catalog.py \
  --template query_tasks_missing_owner
```

### D. Find active tasks missing due date

```bash
python ~/work/py-hbs-ads/scripts/notion_scrum/template_catalog.py \
  --template query_tasks_missing_due_date
```

### E. Update a Project or Task status

```bash
python ~/work/py-hbs-ads/scripts/notion_scrum/template_catalog.py \
  --template update_page_status \
  --var page_id=<page-id> \
  --var status_name='Done'
```

### F. Update a rich-text field on a Project or Task page

```bash
python ~/work/py-hbs-ads/scripts/notion_scrum/template_catalog.py \
  --template update_page_rich_text \
  --var page_id=<page-id> \
  --var property_name='Due date note' \
  --var text='Owner confirmed 2026-04-25 in Discord'
```

### G. Resolve the right user before writing

```bash
python ~/work/py-hbs-ads/scripts/notion_scrum/template_catalog.py \
  --template lookup_notion_person_by_discord \
  --var platform_user_id=400303290174144512 \
  --var display_name=Duc
```

Then feed the rendered fields into `lookup_notion_person.py` or `resolve_person.py`.

### H. Create a due-date follow-up prompt

```bash
python ~/work/py-hbs-ads/scripts/notion_scrum/template_catalog.py \
  --template prompt_task_due_date_request \
  --var pending_prompt_id=pp_due_rough_cut_v1 \
  --var thread_id=1496392425214840965 \
  --var assistant_message_id=assistant-msg-1 \
  --var canonical_person_key=ma \
  --var platform_user_id=discord-user-ma \
  --var project_id=project-123 \
  --var project_title='Game teaser 03' \
  --var task_id=task-456 \
  --var task_title='rough cut v1' \
  --var display_name=Ma
```

Then pipe the `prompt` object into `create_pending_prompt.py`.

### I. Build an inbound reply payload for dry-run

```bash
python ~/work/py-hbs-ads/scripts/notion_scrum/template_catalog.py \
  --template inbound_discord_reply_event \
  --var thread_id=1496392425214840965 \
  --var platform_user_id=400303290174144512 \
  --var display_name=Duc \
  --var reply_to_message_id=assistant-msg-1 \
  --var reply_text='2026-04-25'
```

Then feed the `event` object into `process_inbound_reply.py`.

## Wrapper commands built on top of the catalog

To reduce copy/paste and subsection extraction, the common wrapper layer now exists too:
- `scripts/notion_scrum/query_common_view.py`
- `scripts/notion_scrum/prepare_prompt.py`
- `scripts/notion_scrum/prepare_notion_patch.py`
- `scripts/notion_scrum/prepare_inbound_event.py`

These wrappers keep the template catalog as the source of truth, but expose a smaller operator surface.

### Query wrappers

```bash
python ~/work/py-hbs-ads/scripts/notion_scrum/query_common_view.py --view active-projects
python ~/work/py-hbs-ads/scripts/notion_scrum/query_common_view.py --view active-tasks
python ~/work/py-hbs-ads/scripts/notion_scrum/query_common_view.py --view ownerless-active-tasks
python ~/work/py-hbs-ads/scripts/notion_scrum/query_common_view.py --view undated-active-tasks
```

### Local cache wrappers

```bash
python ~/work/py-hbs-ads/scripts/notion_scrum/sync_board_cache.py
python ~/work/py-hbs-ads/scripts/notion_scrum/query_board_cache.py --kind tasks --title 'AE polish pass'
python ~/work/py-hbs-ads/scripts/notion_scrum/query_board_cache.py --kind projects --id <project-id>
python ~/work/py-hbs-ads/scripts/notion_scrum/resolve_board_target.py --kind tasks --title 'AE polish pass' --project-title '[CTB] V - Market Practice - DDigger' --mode auto
python ~/work/py-hbs-ads/scripts/notion_scrum/resolve_and_prepare_patch.py --target-kind tasks --title 'AE polish pass' --project-title '[CTB] V - Market Practice - DDigger' --patch-kind status --var status_name='In progress'
python ~/work/py-hbs-ads/scripts/notion_scrum/resolve_prepare_apply_patch.py --target-kind tasks --title 'AE polish pass' --project-title '[CTB] V - Market Practice - DDigger' --patch-kind status --var status_name='In progress' --execute
python ~/work/py-hbs-ads/scripts/notion_scrum/update_by_title.py --instruction "set task AE polish pass of project [CTB] V - Market Practice - DDigger to In progress"
python ~/work/py-hbs-ads/scripts/notion_scrum/update_by_title.py --instruction "block task AE polish pass of project [CTB] V - Market Practice - DDigger because missing asset"
python ~/work/py-hbs-ads/scripts/notion_scrum/update_by_title.py --instruction "đặt due date task AE polish pass của project [CTB] V - Market Practice - DDigger là 2026-04-30"
```

`resolve_board_target.py` policies:
- `--mode auto`: use cache-only when the snapshot is fresh and uniquely resolves the title; otherwise do one live page revalidation.
- `--mode safe`: always do one live page revalidation after cache lookup.
- `--mode fast`: require a fresh cache snapshot and skip the live revalidation call.

### Prompt wrappers

```bash
python ~/work/py-hbs-ads/scripts/notion_scrum/prepare_prompt.py \
  --kind task-due-date \
  --var pending_prompt_id=pp_due_1 \
  --var thread_id=thread-1 \
  --var assistant_message_id=assistant-1 \
  --var canonical_person_key=ma \
  --var platform_user_id=discord-user-ma \
  --var project_id=project-1 \
  --var project_title='Game teaser 03' \
  --var task_id=task-1 \
  --var task_title='rough cut v1' \
  --var display_name=Ma
```

```bash
python ~/work/py-hbs-ads/scripts/notion_scrum/prepare_prompt.py \
  --kind task-status \
  --var pending_prompt_id=pp_status_1 \
  --var thread_id=thread-1 \
  --var assistant_message_id=assistant-1 \
  --var canonical_person_key=ma \
  --var platform_user_id=discord-user-ma \
  --var project_id=project-1 \
  --var project_title='Game teaser 03' \
  --var task_id=task-1 \
  --var task_title='rough cut v1' \
  --var display_name=Ma
```

### Patch wrappers

```bash
python ~/work/py-hbs-ads/scripts/notion_scrum/prepare_notion_patch.py \
  --kind status \
  --var page_id=<page-id> \
  --var status_name='In progress'
```

```bash
python ~/work/py-hbs-ads/scripts/notion_scrum/prepare_notion_patch.py \
  --kind rich-text \
  --var page_id=<page-id> \
  --var property_name='Due date note' \
  --var text='Owner confirmed 2026-04-25 in Discord'
```

### Inbound event wrapper

```bash
python ~/work/py-hbs-ads/scripts/notion_scrum/prepare_inbound_event.py \
  --var thread_id=1496392425214840965 \
  --var platform_user_id=400303290174144512 \
  --var display_name=Duc \
  --var reply_to_message_id=assistant-msg-1 \
  --var reply_text='2026-04-25'
```

## Reuse guidance

Best default reuse stack is now:
1. use a wrapper command when the operation already has one
2. otherwise render from `template_catalog.py`
3. pass the returned `request`, `prompt`, or `event` into the existing workflow script
4. avoid hand-writing JSON unless neither the wrapper nor the template fits

Before first use in a new local environment:
- copy `config/notion_scrum/board_config.example.json` to `config/notion_scrum/board_config.json`
- replace the fallback HBS board/channel values with the real local workspace values if they differ

If a recurring operation shows up 2-3 times:
- first add a template if the payload shape is repeating
- then add a wrapper if the operator flow is still repetitive or error-prone
