# Setup Guide: Notion Scrum Configuration

This guide helps you find your Notion workspace IDs and configure `board_config.json` so the Notion Scrum automation tools can read and write to your Notion databases.

## Quick Start

1. **Find your Notion database IDs** (see [Finding Database IDs](#finding-database-ids) below)
2. **Create or edit `config/notion_scrum/board_config.json`**:
   ```json
   {
     "projects_data_source_id": "<your-projects-db-id>",
     "tasks_data_source_id": "<your-tasks-db-id>",
     "default_discord_chat_id": "your-discord-channel",
     "default_discord_channel_name": "#your-channel-name"
   }
   ```
3. **Test the setup** with a template:
   ```bash
   python scripts/notion_scrum/template_catalog.py \
     --template create_project \
     --var project_name="Test Project"
   ```

---

## Finding Database IDs

### What is a Data Source ID?

In Notion's API, a **data source ID** (also called collection ID) is the unique identifier for a specific view or collection within a database. You need this ID to create or query pages.

### Method 1: From Notion URL

When you open a database view in Notion, the URL contains clues:

```
https://www.notion.so/workspace/MyDatabase-abc123def456?v=collection789
```

The ID you need is in the `collection` parameter (not the page ID). However, Notion's web URL often hides the full ID. Use Method 2 instead.

### Method 2: Using Notion API (Recommended)

If you have a valid Notion integration token:

```bash
# List all databases in your workspace
curl -X GET https://api.notion.com/v1/search \
  -H "Authorization: Bearer YOUR_NOTION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "Projects", "filter": {"value": "database", "property": "object"}}'
```

Look for your Projects database in the response. The `id` field is your data source ID.

### Method 3: From Notion Web UI (Easiest)

1. Open your **Projects** database in Notion
2. At the top, ensure you're viewing a **Table view** (not Board, Calendar, etc.)
3. Click **⋯ (More)** → **Copy database link**
4. Paste it somewhere and look for the pattern: `https://www.notion.so/YOUR_WORKSPACE/TABLE_NAME-**[32-CHAR-ID]**`
5. The 32-character string at the end (without dashes) is your data source ID

**Example:**
```
Notion URL: https://www.notion.so/workspace/Projects-abc123def456?v=xyz789
Data Source ID: abc123def456
```

### Method 4: Ask the Database Creator

If you don't have API access, ask whoever created the database to share the data source IDs. They can:
1. Right-click the database in Notion
2. Select **Copy link**
3. Share the link with you

---

## Configuring board_config.json

### Location

```
config/notion_scrum/board_config.json
```

Create this file if it doesn't exist.

### Required Fields

| Field | Example | Notes |
|-------|---------|-------|
| `projects_data_source_id` | `"2e945d07-72af-8117-a240-000bf508da50"` | ID of your Projects database |
| `tasks_data_source_id` | `"2e945d07-72af-81dd-821a-000b082e6e95"` | ID of your Tasks database |
| `default_discord_chat_id` | `"discord-channel-hbs-creative"` | Used for prompts (optional, can be empty) |
| `default_discord_channel_name` | `"#hbs-creative-sml"` | Display name for Discord channel (optional, can be empty) |

### Example Configuration

```json
{
  "projects_data_source_id": "2e945d07-72af-8117-a240-000bf508da50",
  "tasks_data_source_id": "2e945d07-72af-81dd-821a-000b082e6e95",
  "default_discord_chat_id": "discord-channel-hbs-creative",
  "default_discord_channel_name": "#hbs-creative-sml"
}
```

### Defaults (Fallback)

If `board_config.json` doesn't exist or is incomplete, the system uses built-in defaults:

```python
DEFAULT_BOARD_CONFIG = {
    "projects_data_source_id": "2e945d07-72af-8117-a240-000bf508da50",
    "tasks_data_source_id": "2e945d07-72af-81dd-821a-000b082e6e95",
    "default_discord_chat_id": "discord-channel-hbs-creative",
    "default_discord_channel_name": "#hbs-creative-sml",
}
```

To override any field, create `board_config.json` with just that field:

```json
{
  "projects_data_source_id": "your-custom-id"
}
```

---

## Testing Your Setup

### List Available Templates

```bash
python scripts/notion_scrum/template_catalog.py --list
```

Should output all available templates with their required and optional variables.

### Test Creating a Project

```bash
python scripts/notion_scrum/template_catalog.py \
  --template create_project \
  --var project_name="Demo Project"
```

**Output:** JSON representing the project creation request (does not actually create yet).

### Test Creating a Task

```bash
python scripts/notion_scrum/template_catalog.py \
  --template create_task \
  --var task_name="Demo Task" \
  --var project_id="abc-123-def-456"
```

**Note:** `project_id` is the Notion page ID of an existing project (get it from the Projects database).

---

## Template Variables Reference

### create_project

**Required:**
- `project_name` — Name of the project

**Optional:**
- `owner_email` — Notion email of the project owner (e.g., "alice@company.com")
- `end_date` — End date in ISO 8601 format (e.g., "2026-05-31")
- `brief` — Project description (plain text, stored as page content)

**Example:**
```bash
python scripts/notion_scrum/template_catalog.py \
  --template create_project \
  --var project_name="Q2 Redesign" \
  --var owner_email="alice@company.com" \
  --var end_date="2026-06-30" \
  --var brief="Complete UI redesign for dashboard"
```

### create_task

**Required:**
- `task_name` — Name of the task
- `project_id` — Notion page ID of the parent project

**Optional:**
- `assignee_email` — Notion email of the task assignee (e.g., "bob@company.com")
- `due_date` — Due date in ISO 8601 format (e.g., "2026-05-15")
- `brief` — Task description (plain text, stored as page content)

**Example:**
```bash
python scripts/notion_scrum/template_catalog.py \
  --template create_task \
  --var task_name="Design mockups" \
  --var project_id="abc-123-def-456" \
  --var assignee_email="bob@company.com" \
  --var due_date="2026-05-15" \
  --var brief="Create high-fidelity mockups for dashboard"
```

---

## Troubleshooting

### "Unknown template" error

```
KeyError: "Unknown template: create_project"
```

**Fix:** Make sure you're in the right directory and the template name is spelled correctly.

```bash
# List available templates
python scripts/notion_scrum/template_catalog.py --list | grep create
```

### "Missing placeholder variable" error

```
KeyError: "Missing placeholder variable: project_name"
```

**Fix:** Provide the required variable with `--var`:

```bash
python scripts/notion_scrum/template_catalog.py \
  --template create_project \
  --var project_name="My Project"
```

### board_config.json not found

The system will use built-in defaults automatically. To customize:

```bash
mkdir -p config/notion_scrum
cat > config/notion_scrum/board_config.json << 'EOF'
{
  "projects_data_source_id": "your-id-here",
  "tasks_data_source_id": "your-id-here"
}
EOF
```

### Person field shows "None" instead of user ID

**Issue:** When you provide `owner_email` or `assignee_email`, the templates store it as-is. Notion's API requires actual user IDs.

**Resolution:** Use the person field resolution tool (see next session task #2) to convert emails → user IDs at runtime.

For now, you can:
1. Create the project/task without owner/assignee
2. Manually assign in Notion
3. Or get the Notion user ID from your workspace and provide it directly

---

## Next Steps

- **See:** `AGENT_CAPABILITIES.md` for full operation workflows
- **Task 2:** Person field resolution (convert email → Notion user ID automatically)
- **Task 3:** End-to-end test with real project + task creation

