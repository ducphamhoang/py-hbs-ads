# Operator Guide

## Purpose

`hbs-ads` is the Python CLI for the ad-production workflow rewrite. This guide covers installation, workspace bootstrap, representative workflows, and how to verify that a workspace is healthy before cutover.

## Install

Recommended local setup:

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -e .[dev]
```

Module-style invocation also works during development:

```bash
PYTHONPATH=src python3 -m hbs_ads.cli.main --help
```

## Core Conventions

- Run commands as `hbs-ads <area> <action>`.
- Use `--workspace PATH` to point at a job workspace.
- Use `--dry-run` before the first live run of any mutating command.
- Use `--json` or `--output json` for automation-safe output.
- Use `--output quiet` when the caller only needs the exit code.

## Bootstrap

Create a workspace and database first:

```bash
hbs-ads --workspace /path/to/job init workspace
hbs-ads --workspace /path/to/job init db
```

Expected directories include:

- `_ASSETS/raw`
- `_ASSETS/trimmed`
- `_HOOKS`
- `VARIANTS`
- `generated_variants`
- `inbox`
- `archive`
- `logs`
- `reports`
- `sharepoint`
- `voiceover`

## Verification Commands

Run these after bootstrap or before switching an operator workflow to the Python CLI:

```bash
hbs-ads --workspace /path/to/job assets list --raw
hbs-ads --workspace /path/to/job ingest run --dry-run
hbs-ads --workspace /path/to/job notify progress --message smoke-test --dry-run
hbs-ads --workspace /path/to/job --json init workspace
```

Healthy signs:

- the workspace initializes without errors
- dry-run commands return planned work without mutating files
- JSON mode returns a single machine-readable payload

## Common Workflow Areas

### Ingest and trim

```bash
hbs-ads --workspace /path/to/job ingest run
hbs-ads --workspace /path/to/job trim run --config cuts.json --dry-run
hbs-ads --workspace /path/to/job trim clip --input raw.mp4 --from 1s --to 2s --name hero-win --dry-run
```

### Tagging and variants

```bash
hbs-ads --workspace /path/to/job tag auto
hbs-ads --workspace /path/to/job tag ai
hbs-ads --workspace /path/to/job tag pending
hbs-ads --workspace /path/to/job tag approve --all
hbs-ads --workspace /path/to/job variants generate --max-body 2
hbs-ads --workspace /path/to/job variants assemble --config generated_variants/sample.json
hbs-ads --workspace /path/to/job variants export --variant sample-cut
hbs-ads --workspace /path/to/job variants validate --platform tiktok
```

### Pipeline

```bash
hbs-ads --workspace /path/to/job pipeline run
```

If review is still required, the pipeline returns a blocked status rather than silently continuing.

### Reporting and integrations

```bash
hbs-ads --workspace /path/to/job competitor analyze
hbs-ads --workspace /path/to/job perf ingest
hbs-ads --workspace /path/to/job sharepoint setup
hbs-ads --workspace /path/to/job sharepoint upload --file VARIANTS/sample/export/sample.mp4 --variant sample
hbs-ads --workspace /path/to/job notify render-done --variant sample
hbs-ads --workspace /path/to/job voiceover generate --script "Buy now and save."
```

## Shared Library

The shared library (`~/work/video-library` by default) stores persistent assets across all jobs:

```
~/work/video-library/
├── raw/                 ← SharePoint downloads, source footage
├── trimmed/             ← Trimmed clips
├── hooks/               ← Hook templates
└── generated_variants/  ← Reusable variant JSON configs
```

Configure via `.env` (`VIDEO_LIBRARY_ROOT`) or `hbs-ads.yaml` (`library.root`). The workspace (`--workspace PATH`) is for **ephemeral job state** — raw assets and downloads belong in the library.

## JSON Output Contract

Success payloads include:

- `ok`
- `status`
- `command`
- `workspace`
- `message`
- `dry_run`
- `data`

Error payloads include:

- `ok`
- `status`
- `command`
- `workspace`
- `error.message`
- `error.exit_code`

## SharePoint Integration

### One-Time Setup

SharePoint authentication uses the **device code flow** via the `m365` CLI tool.

**Prerequisites:**
- `.env` file configured with SharePoint credentials (see `.env.example` or copy from legacy workspace)
- Required variables: `SP_SITE_URL`, `SP_TENANT_ID`, `SP_BASE_PATH`

**Initial authentication:**

```bash
hbs-ads --workspace /path/to/job sharepoint setup
```

This will:
1. Display a device code and URL (`https://login.microsoft.com/device`)
2. You open the URL in your browser and enter the code
3. Sign in with your Microsoft account
4. The CLI verifies the connection and saves setup to `sharepoint/setup.json`

**Re-authenticating:**

If your token expires or you switch accounts:

```bash
hbs-ads --workspace /path/to/job sharepoint setup
```

Just run the same command again - it will generate a new device code for you.

### SharePoint Commands

```bash
# Setup and authenticate
hbs-ads --workspace /path/to/job sharepoint setup

# Upload a variant to SharePoint
hbs-ads --workspace /path/to/job sharepoint upload --file VARIANTS/sample/export/sample.mp4 --variant sample

# List files on SharePoint
hbs-ads --workspace /path/to/job sharepoint list --query v10

# Download files from SharePoint
hbs-ads --workspace /path/to/job sharepoint download --variant v10
hbs-ads --workspace /path/to/job sharepoint download --file-url "/path/to/file.mp4"

# Dry-run (preview without changes)
hbs-ads --workspace /path/to/job sharepoint upload --file ... --variant sample --dry-run
```

## Microsoft Teams Integration

Teams chat support uses CLI for Microsoft 365 (`m365`) as a Graph wrapper.

Required delegated Graph permissions on the Entra app used by `m365`:

- `User.Read`
- `Chat.ReadBasic` for listing chats
- `Chat.Read` for reading chat messages
- `ChatMessage.Send` for sending chat messages

Configure a tenant/app when the default `m365` app does not have those scopes:

```bash
M365_TENANT_ID=your-tenant.onmicrosoft.com
M365_TEAMS_APP_ID=00000000-0000-0000-0000-000000000000
```

Then run:

```bash
hbs-ads --workspace /path/to/job teams setup
hbs-ads --workspace /path/to/job teams auth-check
hbs-ads --workspace /path/to/job teams chats --top 10
hbs-ads --workspace /path/to/job teams messages --chat-id <chat-id> --top 20
hbs-ads --workspace /path/to/job teams send --chat-id <chat-id> --message "Can you review this cut?" --dry-run
hbs-ads --workspace /path/to/job teams send --chat-id <chat-id> --message "Can you review this cut?"
```

Important: `m365 login` cannot add Teams scopes dynamically. The scopes must already be granted and consented on the Entra app registration used for login.

For a temporary Graph Explorer proof of concept, export a short-lived Graph access token instead of using `m365`:

```bash
export HBS_ADS_GRAPH_ACCESS_TOKEN=<graph-explorer-access-token>
hbs-ads --workspace /path/to/job --json teams chats --top 10
hbs-ads --workspace /path/to/job --json teams messages --chat-id <chat-id> --top 10
```

The token is read from the environment only, is not written to `teams/setup.json`, and should not be committed or pasted into logs.

### Troubleshooting

**`clip.exe` error:**
If you see `Command failed with ENOENT: clip.exe`, ensure `~/.local/bin/clip.exe` exists (created during initial setup). This is a workaround for Linux/WSL where the `m365` CLI tries to copy the device code to clipboard.

**Token expired:**
Run `sharepoint setup` again to re-authenticate.

**Missing .env variables:**
Check that `.env` contains `SP_SITE_URL` and `SP_TENANT_ID`. Run `hbs-ads --json sharepoint setup` to see what configuration is being used.

## Known Limits

- SharePoint integration uses **live Microsoft 365 API calls** via the `m365` CLI for authentication and REST API for file operations.
- Voiceover generation is deterministic local artifact creation, not a real TTS provider call.
- Media execution still assumes external tools such as `ffmpeg` and `ffprobe` when the workflow moves beyond fixture-driven validation.
