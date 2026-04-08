# Python Development Guide - hbs-ads

## Purpose

This guide defines the engineering rules for the Python rewrite of `hbs-ads`.

It is intended for:

- developers implementing the rewrite;
- reviewers checking maintainability and correctness;
- AI coding agents contributing code.

The goal is a Python codebase that stays operationally reliable without turning into a pile of scripts.

## Development Priorities

Optimize for:

- clarity over cleverness;
- explicit behavior over hidden magic;
- feature ownership over framework sprawl;
- safe integration with external tools;
- small-team maintainability;
- testability before convenience.

## Tech Direction

Recommended baseline:

- Python 3.12+
- `src/` layout
- `pyproject.toml`
- `typer` or `click` for CLI
- `pydantic` for config and IO models where it adds value
- `pytest` for tests
- SQLite for local operational storage
- `ffmpeg` and `ffprobe` as external executables

The project should stay conservative about dependencies. Add libraries only when they remove meaningful maintenance burden.

## Core Rules

### 1. Keep CLI Code Thin

CLI modules may:

- parse flags and arguments;
- construct typed request objects;
- call one service or orchestrator;
- render output;
- map exceptions to exit codes.

CLI modules must not:

- implement workflow logic;
- build SQL;
- call `subprocess` directly;
- call provider SDKs directly;
- coordinate multi-step business rules outside `pipeline`.

### 2. Put Logic In Features

Feature behavior belongs in feature packages.

Examples:

- trim logic goes in `features.trim`
- variant generation rules go in `features.variants`
- SharePoint behavior goes in `features.sharepoint`
- performance attribution goes in `features.perf`

Do not bury feature logic in generic infrastructure modules.

### 3. Avoid Dumping Grounds

Do not create:

- `utils.py`
- `helpers.py`
- `common.py`
- `misc.py`

If code is shared, give it a precise name and a precise reason to exist.

### 4. Use Typed Inputs And Outputs

Service APIs should use typed request and result models.

Preferred options:

- `dataclass(slots=True)` for internal service models;
- `pydantic` models for config, external payload validation, and structured IO boundaries.

Do not pass loose dicts between major layers.

### 5. Make Side Effects Obvious

Any workflow that writes files, updates the DB, sends notifications, uploads assets, invokes AI, or runs subprocesses must expose that clearly in the service API and command help.

Hidden side effects are not acceptable.

## Python Best Practices

### Style

- follow PEP 8 and format with `ruff format` or `black`
- lint with `ruff`
- use one import style consistently
- keep functions short enough to read without scrolling through unrelated concerns
- prefer explicit names over short clever ones

### Typing

- type all public functions and methods
- type service inputs and outputs
- type repository interfaces and adapter boundaries
- run `mypy` or `pyright` in CI

Typing is required because this project coordinates files, DB state, subprocesses, and external APIs. Untyped code will drift too fast.

### Dataclasses And Pydantic

Use `dataclass` for internal behavior models that do not need validation magic.

Use `pydantic` for:

- config loading;
- environment-driven settings;
- request/response payload validation;
- parsing external AI or webhook data.

Do not turn every internal model into a Pydantic model by default.

### Exceptions

Use explicit exception types for meaningful failure categories.

Recommended categories:

- `UserInputError`
- `ConfigError`
- `WorkspaceError`
- `DependencyError`
- `ExternalServiceError`
- `DomainError`

Rules:

- raise specific exceptions near the failing boundary;
- add context when re-raising;
- do not swallow exceptions silently;
- do not return mixed `None` or `False` sentinel values instead of errors for real failures.

### Logging

Use the standard `logging` module unless there is a strong reason not to.

Rules:

- keep user-facing output separate from logs;
- never log raw secrets;
- log intent and identifiers, not sensitive payloads;
- prefer structured context in logs over long prose.

### Paths And Filesystem

Rules:

- use `pathlib.Path`;
- resolve workspace-relative paths explicitly;
- do not hardcode user-specific absolute paths;
- validate file existence before destructive actions;
- document overwrite behavior.

Do not scatter filesystem conventions throughout the codebase. Centralize workspace path rules.

### Subprocesses

All subprocess execution must go through one adapter layer.

Rules:

- use argument lists, not shell strings;
- set explicit timeouts where appropriate;
- capture stdout and stderr separately;
- support dry-run mode;
- sanitize logged commands;
- return structured results.

Never call `subprocess.run(..., shell=True)` for normal workflow code.

### SQLite And Persistence

Rules:

- migrations are mandatory for schema changes;
- DB writes that belong together should use one transaction;
- repositories should stay close to the owning feature;
- DB code should not leak SQL details into CLI modules.

If using SQLAlchemy, prefer SQLAlchemy 2.x patterns and keep the ORM surface small. Heavy ORM indirection is not the goal.

### Concurrency

Use concurrency only when it produces real operational value.

Good candidates:

- scanning independent files;
- batch metadata extraction;
- uploads with bounded workers;
- AI requests on independent items.

Rules:

- keep concurrency bounded;
- preserve deterministic summaries;
- prefer simple executors or task groups over clever scheduling abstractions.

For most features, correctness and observability matter more than squeezing out parallel speed.

## Code Organization Rules

### File Size

Guideline:

- split files before they become hard to scan
- avoid thousand-line modules unless there is a very strong reason

### Function Design

Prefer functions that do one of these clearly:

- parse input;
- validate data;
- plan side effects;
- execute side effects;
- render output.

Mixed-purpose functions are harder to test and maintain.

### Service Design

A service should expose one clear workflow operation.

Good examples:

- `TrimService.trim_clip(...)`
- `VariantService.generate(...)`
- `SharePointService.upload_variant(...)`

Bad examples:

- giant god services with unrelated responsibilities
- generic `run()` methods with opaque dict inputs

### Interface Use

Use protocols or abstract base classes only at meaningful seams.

Good seams:

- subprocess runner
- repository contract
- AI provider client
- notification sender

Bad seams:

- every service by default
- internal pure functions with one obvious implementation

## Config Rules

Configuration precedence should be predictable:

1. code defaults
2. config file
3. environment variables
4. CLI flags

Rules:

- centralize config loading;
- do not call `os.getenv()` randomly across features;
- keep secrets in env vars;
- validate config once at startup when possible;
- inject resolved settings into services.

## Testing Rules

Testing is required for production-facing logic.

### Required Coverage Areas

- config parsing and validation
- workspace path resolution
- trim request parsing and plan building
- variant generation and validation rules
- platform export validation
- SharePoint path logic
- performance matching and attribution
- markdown and JSON report generation

### Test Layers

1. Unit tests
   - pure logic and validation

2. Integration tests
   - DB behavior
   - migrations
   - subprocess adapters with fixtures
   - workspace initialization

3. Golden tests
   - command output
   - markdown reports
   - JSON payloads

4. End-to-end tests
   - selected CLI flows against `testdata/`

### Test Style

- prefer `pytest`
- use factories and fixtures for workspace state
- mock at external boundaries, not internal implementation details
- assert behavior, not private implementation trivia

If a test breaks because of harmless refactoring, the test is probably written at the wrong level.

## CLI Standards

Commands should follow:

- `hbs-ads <feature> <action>`
- `--dry-run` for mutating operations where practical
- `--workspace` override where needed
- consistent non-zero exit codes on failure
- concise default output
- optional JSON output for automation

Help text must describe purpose and side effects, not only flags.

## Review Standards

Code review should reject changes that:

- move business logic into CLI files;
- introduce vague shared modules;
- add hidden side effects;
- couple features tightly without a real need;
- skip typing at important boundaries;
- omit tests for non-trivial workflow behavior;
- shell out unsafely;
- read secrets directly from scattered env access.

## Recommended Tooling

Recommended commands:

```bash
python -m pip install -e .[dev]
ruff check .
ruff format .
pytest
mypy src
```

If the team prefers `pyright` over `mypy`, pick one and enforce it consistently.

## Definition Of Done

A change is not done unless:

- the architecture rules are still respected;
- typing is present at the main boundaries;
- tests cover the changed behavior;
- logs and errors remain actionable;
- docs are updated when the public workflow or structure changes.

## Final Rule

This rewrite should feel like one coherent Python application, not a new pile of scripts under `src/`. If a change makes the code faster to write today but harder to reason about next month, it is usually the wrong trade.
