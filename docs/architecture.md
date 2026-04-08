# Architecture - hbs-ads Python Rewrite

## Purpose

This document defines the target architecture for rewriting `hbs-ads` from the current Go-oriented design into a Python codebase that is easier to maintain, test, and extend.

The rewrite keeps the product contract from the PRDs:

- one CLI named `hbs-ads`;
- one consistent command tree;
- compatibility with the existing workspace model where practical;
- explicit support for operator workflows and agent workflows.

The rewrite changes the implementation strategy:

- Python instead of Go;
- feature-first package layout instead of layer sprawl;
- clear boundaries between CLI, application services, domain logic, and infrastructure adapters;
- a codebase optimized for maintainability by a small internal team.

## Architectural Goals

The Python rewrite should optimize for:

- feature ownership over technical layering;
- thin CLI commands;
- explicit side effects;
- typed service inputs and outputs;
- safe subprocess orchestration around `ffmpeg`, `ffprobe`, and external CLIs;
- testability without depending on production services;
- incremental migration from `~/work/hbs-ads`.

## Product Surface To Preserve

The CLI contract remains the public surface of the system:

```text
hbs-ads
├── init
│   ├── workspace
│   └── db
├── assets
│   └── list
├── ingest
│   ├── run
│   ├── watch
│   └── cron
│       ├── install
│       └── remove
├── trim
│   ├── run
│   └── clip
├── tag
│   ├── auto
│   ├── ai
│   ├── approve
│   └── pending
├── variants
│   ├── generate
│   ├── assemble
│   ├── export
│   ├── validate
│   └── archive
├── hooks
│   └── assemble
├── pipeline
│   └── run
├── sharepoint
│   ├── setup
│   ├── upload
│   └── download
├── competitor
│   ├── analyze
│   └── report
├── perf
│   ├── ingest
│   └── report
├── notify
│   ├── render-done
│   └── progress
└── voiceover
    └── generate
```

The rewrite may improve internals aggressively, but it should not casually change command meaning.

## Why Feature-First In Python

Python codebases get messy quickly when teams default to folders like `utils`, `services`, or `helpers`.

This project should instead organize by workflow capability:

- `trim`
- `tagging`
- `variants`
- `sharepoint`
- `competitor`
- `perf`
- `voiceover`
- `pipeline`

This fits the product because the CLI itself is feature-oriented. Each workflow area has distinct rules, external dependencies, storage behavior, and tests. Keeping that logic together reduces cross-package coupling and makes future changes local.

## Top-Level Layout

Recommended repository structure:

```text
py-hbs-ads/
├── docs/
├── scripts/
├── migrations/
├── testdata/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── src/
│   └── hbs_ads/
│       ├── __init__.py
│       ├── cli/
│       ├── app/
│       ├── core/
│       ├── features/
│       └── infra/
├── pyproject.toml
└── README.md
```

## Package Responsibilities

### `src/hbs_ads/cli`

Responsibility:

- command tree definition;
- flag parsing;
- mapping command inputs into typed requests;
- rendering text or JSON output.

Rules:

- no business logic;
- no SQL;
- no direct API calls;
- no ad hoc subprocess invocations.

### `src/hbs_ads/app`

Responsibility:

- dependency wiring;
- settings bootstrap;
- service/container assembly;
- app-level entrypoints used by the CLI.

This is the composition root. It wires features to shared infrastructure.

### `src/hbs_ads/core`

Responsibility:

- stable, cross-cutting primitives used by many features.

Allowed examples:

- config models and loading;
- logging setup;
- output envelopes;
- error types;
- time and path abstractions when needed;
- shared domain enums or value objects;
- execution context and dry-run policy.

This package must remain small and stable.

### `src/hbs_ads/infra`

Responsibility:

- technical adapters for external systems.

Examples:

- SQLite connection/session management;
- repository implementations;
- subprocess runner for `ffmpeg`, `ffprobe`, `m365`, and other CLIs;
- AI provider clients;
- webhook clients;
- filesystem and watcher adapters.

`infra` provides implementations. Features own workflow rules.

### `src/hbs_ads/features`

Responsibility:

- product behavior grouped by business capability.

Each feature owns:

- request/result models;
- service layer;
- validation rules;
- workflow orchestration;
- feature-specific repositories or interfaces;
- tests for feature behavior.

## Feature Package Shape

Small feature:

```text
src/hbs_ads/features/assets/
├── service.py
├── models.py
└── tests or external tests/
```

Medium feature:

```text
src/hbs_ads/features/trim/
├── service.py
├── models.py
├── validators.py
├── ffmpeg_plan.py
└── repository.py
```

Larger feature:

```text
src/hbs_ads/features/variants/
├── service.py
├── models.py
├── generate.py
├── assemble.py
├── export.py
├── archive.py
├── validators.py
└── repository.py
```

Do not force every feature into the same template. Keep the module shape proportional to the actual complexity.

## Recommended Python Module Layout

Recommended internal layout:

```text
src/hbs_ads/
├── cli/
│   ├── main.py
│   ├── root.py
│   ├── renderers.py
│   └── commands/
│       ├── init.py
│       ├── assets.py
│       ├── ingest.py
│       ├── trim.py
│       ├── tag.py
│       ├── variants.py
│       ├── hooks.py
│       ├── pipeline.py
│       ├── sharepoint.py
│       ├── competitor.py
│       ├── perf.py
│       ├── notify.py
│       └── voiceover.py
├── app/
│   ├── bootstrap.py
│   ├── container.py
│   └── settings.py
├── core/
│   ├── config.py
│   ├── errors.py
│   ├── logging.py
│   ├── outputs.py
│   ├── paths.py
│   └── types.py
├── infra/
│   ├── db/
│   ├── exec/
│   ├── ai/
│   ├── notify/
│   ├── sharepoint/
│   └── filesystem/
└── features/
    ├── init/
    ├── assets/
    ├── ingest/
    ├── trim/
    ├── tagging/
    ├── variants/
    ├── hooks/
    ├── pipeline/
    ├── sharepoint/
    ├── competitor/
    ├── perf/
    ├── notify/
    └── voiceover/
```

## Dependency Rules

Allowed dependency direction:

```text
cli -> app -> features -> core / infra
infra -> core
```

Rules:

- `cli` may depend on `app`, feature request models, and renderers.
- `features` may depend on `core` and on infrastructure interfaces or adapters.
- `infra` must not depend on feature packages.
- one feature must not directly reach into another feature's internals.
- cross-feature orchestration belongs in `features/pipeline` or `app`.

## Service Boundary Pattern

Each command should map to a typed service call.

Example shape:

```python
@dataclass(slots=True)
class TrimClipRequest:
    input_path: Path
    start: str
    end: str
    name: str
    workspace_root: Path
    dry_run: bool = False


@dataclass(slots=True)
class TrimClipResult:
    output_path: Path
    duration_seconds: float
    skipped: bool = False
```

Command handlers should:

1. parse flags;
2. construct request objects;
3. call one feature service;
4. render a result.

## Shared vs Feature-Specific Code

Extract shared code only when the sharing is real and stable.

Good shared code:

- config loading;
- subprocess execution;
- DB session handling;
- logging bootstrap;
- path normalization;
- common output formatting.

Bad shared code:

- `utils.py`
- `helpers.py`
- `common.py`
- giant service containers passed everywhere
- generic repository base classes with no real value

If a name is vague, the module is probably wrong.

## Data and Persistence Direction

The Python rewrite should keep SQLite as the default local operational database.

Core entity direction remains aligned with the PRDs:

- `Clip`
- `Variant`
- `CompetitorVideo`
- `PerfRecord`
- `OperationLog`

Recommended rule:

- feature modules define the behavior they need;
- persistence implementations live in `infra/db`;
- schema changes go through migrations;
- no feature should mutate schema implicitly at runtime.

For maintainability, prefer SQLAlchemy 2.x or direct `sqlite3` with a thin repository layer. If the team wants stronger typing and less hidden magic, SQLAlchemy Core or explicit SQL is preferable to a heavy ORM pattern.

## Config Model

Configuration precedence:

1. defaults in code;
2. workspace config file such as `hbs-ads.yaml`;
3. environment variables;
4. command-line flags.

Rules:

- secrets live in env vars, not committed config;
- feature code should not call `os.getenv()` directly;
- config loading happens centrally in `app` and `core`;
- resolved settings are injected into services.

## Workspace Compatibility

The first Python version should preserve the current workspace layout where practical:

```text
workspace/
├── _ASSETS/
├── _HOOKS/
├── _SEQUENCES/
├── VARIANTS/
├── generated_variants/
├── inbox/
├── archive/
├── logs/
├── docs/
├── hbs-ads.yaml
└── clips.db
```

Migration should prefer adapters and explicit normalization over destructive layout changes.

## Subprocess Architecture

Media and integration work remain external-process heavy. That is acceptable if the boundaries are clean.

All subprocess execution should go through one shared adapter in `infra/exec`.

Responsibilities:

- build explicit argument lists;
- support timeouts and cancellation;
- capture stdout and stderr separately;
- redact secrets from logs;
- support dry-run previews;
- return structured execution results.

No feature should build shell strings inline.

## Output and Error Model

The CLI should support three output modes:

- `text` for operators;
- `json` for agents and automation;
- `quiet` for scripting.

Feature services should return typed results, not preformatted strings.

Error classes should distinguish:

- user input errors;
- workspace/config errors;
- external dependency errors;
- external API or network errors;
- internal logic errors.

This keeps CLI rendering simple and predictable.

## Observability

The rewrite should separate user output from logs.

Recommended approach:

- concise CLI output to stdout;
- actionable failures to stderr;
- structured logs written to `logs/`;
- operation summaries recorded in SQLite when useful.

Long-running commands should emit progress events through a shared reporting interface so `pipeline`, `notify`, and future dashboard integrations can consume the same signals.

## Testing Strategy

Required test layers:

1. Unit tests
   - config parsing
   - request validation
   - naming and matching logic
   - platform validation rules

2. Integration tests
   - SQLite migrations
   - workspace initialization
   - repository behavior
   - subprocess integration with fixtures

3. Golden tests
   - markdown reports
   - JSON output
   - stable text summaries

4. End-to-end smoke tests
   - run selected commands against `testdata/`

Python-specific guidance:

- keep unit tests fast and isolated;
- use `pytest`;
- use fixtures for workspace trees and fake subprocess runners;
- mock external APIs at adapter boundaries, not deep inside business logic.

## Migration Plan

### Phase 1 - Skeleton

- create `pyproject.toml`;
- create `src/hbs_ads` package;
- stand up CLI shell and app bootstrap;
- implement config, logging, workspace resolution, and result rendering;
- add `init` and `assets list`.

### Phase 2 - Core Production Path

- implement `ingest`, `trim`, and `variants`;
- add shared subprocess runner;
- support existing workspace conventions and JSON configs;
- add integration tests around fixtures.

### Phase 3 - Metadata and Integrations

- implement `tag`, `notify`, `sharepoint`, and `voiceover`;
- stabilize DB schema and migrations;
- add dry-run coverage for all mutating commands.

### Phase 4 - Intelligence Features

- implement `competitor` and `perf`;
- isolate provider clients behind adapter interfaces;
- add report golden tests.

### Phase 5 - Cutover

- run parity checks against `~/work/hbs-ads`;
- shadow-run critical operator workflows;
- retire legacy entrypoints only after parity is proven.

## Non-Negotiable Rules

- keep the CLI thin;
- keep business logic inside features;
- avoid generic dumping-ground modules;
- prefer typed request and result objects;
- make side effects explicit;
- centralize subprocess and config handling;
- do not let one feature casually reach into another;
- preserve workspace compatibility unless there is a documented reason to break it.

## Final Recommendation

Build the Python rewrite as a feature-first CLI application with a small stable core and explicit infrastructure adapters. The maintainability win comes from keeping each workflow area cohesive, resisting generic abstractions, and treating the CLI contract as a stable product surface while the internals evolve.
