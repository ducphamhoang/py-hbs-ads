# Notion Media Scrum Policy

This document defines the operating policy for using the Notion board as the source of truth for media-team Scrum/Scrumban coordination.

Scope:
- team work tracked in the `Projects` data source
- execution work tracked in the related `Tasks Tracker` data source
- media production tasks such as video editing, AE/motion, Unity creative work, voice-over, packaging, review, and release prep

## Goal

Keep the board useful for coordination, not just archival logging.

The board must support:
- current workload visibility
- owner clarity
- due-date awareness
- review/revision flow
- project risk reporting
- AI-generated daily and weekly coordination summaries

## The two-level model

### Projects

`Projects` is the deliverable layer.

A project row should represent one of these:
- one deliverable
- one creative initiative
- one campaign unit
- one shippable media package
- one bounded internal initiative that still needs tracking at deliverable level

Examples:
- one game creative video
- one AE enhancement package
- one Unity creative experiment that is still treated as a discrete deliverable

### Tasks Tracker

`Tasks Tracker` is the execution layer.

A task row should represent:
- one reviewable output
- one production step
- one bounded execution item
- one task that can be clearly assigned and tracked

Examples:
- rough cut of sequence A
- style frame set for opener
- voice-over list and handoff
- animation pass for selected shots
- playable prototype build
- internal review fixes batch 1
- final export package

## Source-of-truth rule

Short-term rule for this board:
- `Projects.Status` is the operational source of truth for project state.
- `Projects.Cal. Status` is advisory only.
- If `Status` and `Cal. Status` disagree, treat it as a hygiene alert, not as automatic truth.

Why:
- current formulas/rollups do not yet reflect the real workflow reliably enough
- media work has review and revision loops that are often not captured by simplistic task rollups

Future option:
- after board hygiene improves, `Cal. Status` may become a stronger signal, but not before task/project discipline is stable

## Minimum hygiene rules

### Every active Project must have
- Project name
- Status
- at least one owner/assignee
- either:
  - at least one linked execution task in `Tasks Tracker`, or
  - an explicit note that the project is still only at intake/research/brief stage

### Every active Task must have
- Task name
- linked Project
- owner/assignee
- Status
- Due date

If any of these are missing, the task is not board-ready for active execution.

## What counts as active

### Active Project statuses
- `In progress`
- `Not started`

### Active Task statuses
Until the task status model is expanded, active means:
- `In progress`
- `Not started`

## Recommended media-friendly task statuses

The current board should move toward this execution status set:
- `Not started`
- `In progress`
- `Internal review`
- `Client review`
- `Blocked`
- `Done`

Why this matters:
- media teams live in review and revision loops
- without explicit review/blocking states, active work appears healthier than it really is

## Review and revision policy

Review is first-class workflow, not hidden work.

Guidelines:
- do not leave review items inside generic `In progress`
- if work is waiting for internal review, mark it explicitly
- if work is waiting for stakeholder/client review, mark it explicitly
- if work cannot proceed due to missing direction/assets/approval, mark it blocked

## Task slicing rule for media work

Do not slice like software subtasks unless that genuinely helps.
Slice by reviewable artifact or bounded output.

Good task examples:
- rough cut v1
- style frame options
- animatic pass
- Unity playable build for review
- export package for internal review
- revision pass from consolidated notes

Weak task examples:
- creative
- fix video
- improve quality
- V
- blank-title tasks

## Board-quality alerts

These conditions should be treated as operational issues:
- active project with no linked tasks
- active project with no owner
- `Status` vs `Cal. Status` mismatch on an active project
- active task with no linked project
- active task with no owner
- active task with no due date
- active task flagged past due
- active task with weak/blank name

## Suggested cadences

### Daily or 3x-weekly flow review
Focus on:
- due soon
- overdue
- blocked
- in review too long
- active projects with no executable tasks

### Weekly planning / traffic review
Focus on:
- incoming work
- owner load by discipline
- projects with no task breakdown
- overdue carryover
- whether large projects need task splitting

### Weekly risk review
Focus on:
- projects with active status but no tasks
- projects where formula status disagrees with operational status
- tasks overdue and still not started
- owners with too much active load

## AI Scrum Master responsibilities

An AI Scrum Master for this board should:
- audit board hygiene
- summarize current workload and risks
- highlight overdue/blocked/orphaned work
- suggest task splitting for vague or oversized work
- prepare short daily/weekly digests
- never treat formulas as stronger than real board state without explicit policy change

## Things the AI should not do automatically

Without human approval, do not:
- change project status based only on formula mismatch
- close active work automatically
- reassign owners automatically
- set fake due dates to satisfy hygiene metrics
- infer project readiness from sparse task data

## Immediate cleanup priorities

1. resolve active projects with no linked tasks
2. resolve active tasks with no linked project
3. resolve active tasks with no owner
4. resolve active tasks with no due date
5. rename or archive weak/blank active tasks
6. reduce `Status` vs `Cal. Status` mismatches on active projects
