# SharePoint Agent Guide

This guide teaches an AI agent how to use `hbs-ads sharepoint` commands effectively. Read this before performing any SharePoint search, download, or upload on behalf of a user.

---

## 1. Folder Structure Rule

SharePoint organizes variant videos into **numbered sub-folders by version range**:

```
02.1 - Video/
├── V001–V199  → direct children, no numbered subfolder
│   ├── 001 - V01/
│   ├── 020 - V20/
│   └── 099 - V99/
├── 2 - V200+/ → all V200–V299 variants
├── 3 - V300+/ → all V300–V399 variants
└── 4 - V400+/ → all V400+ variants
```

**Key takeaway**: The V-number alone does not tell you the physical folder. You need the **range mapping**:

| Version Range | Env Variable | Target Flag |
|---|---|---|
| V1–V199 | `SP_BASE_PATH_V100` | `--target v100` |
| V200–V299 | `SP_BASE_PATH_V200` | `--target v200` |
| V300–V399 | `SP_BASE_PATH_V300` | `--target v300` |
| V400+ | `SP_BASE_PATH_V400` | `--target v400` |

---

## 2. Auto-Detection vs Explicit `--target`

### Auto-detection (default)
When you pass `--query v204` or `--variant v204`, the tool extracts the number (`204`) and automatically selects the correct base path (`V200+`).

| Query | Auto-detected target |
|---|---|
| `v150` | `v100` |
| `v204` | `v200` |
| `v317` | `v300` |
| `v406` | `v400` |

### When to use explicit `--target`
- **Broad search**: User says "search everything for v204" → try each target sequentially
- **Cross-version search**: A file might be named `MixV204-V317` and live in V300+ or V400+
- **Unknown version**: User mentions a name that doesn't follow the `V###` pattern
- **Debugging**: Auto-detection returned 0 results but you suspect the file exists elsewhere

### Recommended search strategy
```bash
# Step 1: Try auto-detection first
hbs-ads --workspace . sharepoint list --query <name>

# Step 2: If 0 results, try the "home" target
hbs-ads --workspace . sharepoint list --query <name> --target v<NXX>

# Step 3: If still 0, check parent folders (mix variants may live in higher V ranges)
hbs-ads --workspace . sharepoint list --query <name> --target v400
hbs-ads --workspace . sharepoint list --query <name> --target v100
```

---

## 3. Common Scenarios

### Scenario A: "Find variant v204 for me"
```bash
hbs-ads --workspace . sharepoint list --query v204
# Auto-detects V200+, finds mix variants like V204 (Mix V46-V12.1)
```

### Scenario B: "Download v317 to my workspace"
```bash
hbs-ads --workspace . sharepoint download --variant v317
# Auto-detects V300+, downloads all matching MP4s to ~/work/video-library/raw/v317/
```

### Scenario C: "Upload this file as variant v406"
```bash
hbs-ads --workspace . sharepoint upload --file VARIANTS/v406/export/output.mp4 --variant v406
# Auto-detects V400+ for upload destination
```

### Scenario D: "Find ALL files matching 'v204' across all folders"
```bash
# Search each target individually
hbs-ads --workspace . sharepoint list --query v204 --target v100
hbs-ads --workspace . sharepoint list --query v204 --target v200
hbs-ads --workspace . sharepoint list --query v204 --target v300
hbs-ads --workspace . sharepoint list --query v204 --target v400
```

### Scenario E: "List everything in the root video folder"
```bash
hbs-ads --workspace . sharepoint list --query "" --target v100
# Returns many files/subfolders — use with JSON output for parsing
```

---

## 4. Download Destination

Files download to **`~/work/video-library/raw/<variant>/`** by default (shared library, persistent across all jobs).

The workspace is for **execution state only** — SharePoint downloads go to the library, not the workspace.

Override with `--dest`:
```bash
# Absolute path
hbs-ads --workspace . sharepoint download --variant v204 --dest /tmp/assets

# Relative to workspace (not recommended for raw footage)
hbs-ads --workspace . sharepoint download --variant v204 --dest inbox
```

The CLI creates the directory if it doesn't exist. A manifest file (`sharepoint/download-<variant>.json`) records what was downloaded and includes the `library_root` path.

**Library structure:**
```
~/work/video-library/
├── raw/                 ← SharePoint downloads land here
│   └── v204/
│       └── CTB_V204-*.mp4
├── trimmed/
├── hooks/
└── generated_variants/
```

---

## 5. Important Gotchas

### No "original" variant may exist
Some variants (like V204) were born as **mix variants** and only exist under a mix folder name (e.g., `05 - V204 (Mix V46-V12.1)`). They never had a standalone `V204/` folder. Don't assume every variant has an "original" version.

### Variant naming is inconsistent
- `V204` may appear in filenames as `V204`, `MixV204`, `V204-NewEF02`, etc.
- The `--query` filter matches against **folder names** and **file stems** (case-insensitive)
- Use broad enough queries: `v204` matches `CTB_V204`, `MixV204`, `V281 (V204 New EF01)`, etc.

### Shared-library-first rule
For the Python rewrite, treat SharePoint as a source integration feeding the shared library.
Do not force raw downloads into job workspaces unless the task is intentionally one-off and explicitly scoped that way.

### Upload uses variant name to pick target
When uploading, the tool extracts the version number from `--variant` to determine the correct V folder. `--variant v204` → V200+, `--variant v406` → V400+.

---

## 6. Authentication

```bash
hbs-ads --workspace . sharepoint setup
```

- Generates a device code + URL (`https://login.microsoft.com/device`)
- User opens browser, enters code, signs in
- Token is cached by `m365` CLI — no re-auth needed until it expires
- Re-run the same command to re-authenticate

**Prerequisite**: `.env` file with `SP_SITE_URL` and `SP_TENANT_ID`.

---

## 7. Agent Role Boundaries

This agent may:

- search SharePoint
- list likely matches
- download source footage into the shared library
- upload validated local artifacts
- recommend the next role once the correct local file exists

This agent must not:

- analyze CTA timing itself
- perform trim/assembly work
- mark a variant as validated without QA evidence

Typical recommendation pattern after download:

- Suggested Next Role: Analysis or Assembly
- Suggested Next Action: inspect or trim the local file now that the source is present

---

## 8. Quick Reference

| Command | Description |
|---|---|
| `sharepoint setup` | Authenticate via device code |
| `sharepoint list --query <name>` | Search files (auto-detects target) |
| `sharepoint list --query <name> --target v200` | Search specific V range |
| `sharepoint download --variant <name>` | Download matching files |
| `sharepoint download --file-url "/path/to/file.mp4"` | Download single file by URL |
| `sharepoint upload --file <path> --variant <name>` | Upload to correct V folder |
| Add `--dry-run` to any command | Preview without changes |
| Add `--json` or `--output json` | Machine-readable output |
