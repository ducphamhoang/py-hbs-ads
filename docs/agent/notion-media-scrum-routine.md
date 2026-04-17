# Notion Media Scrum Routine

This document defines the recurring routine for using the Notion board as a media-team Scrum/Scrumban system.

## Daily or 3x-weekly flow review

Goal:
- understand what needs attention now
- not to re-plan the whole board every day

Inputs:
- active projects
- active tasks
- overdue tasks
- tasks with no owner
- tasks with no due date
- projects with no linked tasks
- project status mismatches

Questions to answer:
- what is due soon?
- what is overdue?
- what is blocked or likely blocked?
- what is active but underspecified?
- which owner has too many live items?
- which project looks active but has no real execution plan yet?

Expected output:
- one short digest
- top risks only
- concrete next actions for owners or PM

## Weekly traffic review

Goal:
- rebalance work
- decide what is actually active
- prevent zombie projects/tasks from polluting the board

Check:
- active projects with no tasks
- active tasks with no project
- active tasks with no owner
- active tasks with no due date
- tasks overdue more than one review cycle
- projects that should be paused, done, or broken down further

Expected decisions:
- assign owner
- assign due date
- link task to project
- split task
- archive task
- update project status

## Weekly risk review

Goal:
- protect delivery quality and predictability

Focus on:
- owner overload
- too many overdue tasks under one owner
- projects with mismatched status signals
- projects that are `In progress` but have zero linked tasks
- tasks old enough that they are probably stale

Expected output:
- risk list by project
- workload imbalance summary
- cleanup list

## Project intake rule

When a new project is created in `Projects`:
- assign owner
- choose operational status
- decide whether it is still intake/research or truly active
- if active, create at least one task in `Tasks Tracker`
- if no executable task exists yet, mark clearly that the project is not execution-ready

## Task intake rule

When a new task is created in `Tasks Tracker`:
- link to one project
- assign one primary owner
- choose a meaningful task name
- set status
- set due date
- ensure it is a reviewable output or bounded execution item

## Suggested digest sections

### Daily digest
- Active projects count
- Active tasks count
- Overdue tasks
- Projects with no linked tasks
- Tasks with no owner
- Tasks with no due date
- Top owner load
- Suggested immediate actions

### Weekly digest
- Workload by owner
- Projects at risk
- Stale tasks to archive or split
- Hygiene trend
- Recommended board cleanup actions

## Success condition

This routine is working when:
- active work is clearly owned
- active work is due-dated
- every active project has real execution detail or an explicit intake note
- review and revision become visible instead of hidden
- daily summaries point to action, not noise
