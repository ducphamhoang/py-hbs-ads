# B1 owner-alignment prompts for Projects with zero linked Tasks

Use this before creating execution tasks for active projects.

Core rule:
- do not invent execution tasks for a project with zero linked tasks until the assigned owner confirms how they want to break the work down
- the goal is to capture the owner's intended reviewable outputs, not to force a fake decomposition

## Short question set

Ask the owner these 5 questions:

1. Is this project still actively moving, or should it be paused/archived?
2. What is the first reviewable output you want tracked on the board?
3. If this project starts now, what are the first 1–3 task titles you would create?
4. What is the first review point or approval gate?
5. Is there a target due date or delivery date we should attach to the first task(s)?

## Project-specific prompts

### 1. `[CTB] V - Meme US`
Current state:
- Status: `Not started`
- Owner: none
- Zero linked tasks

Questions:
- Is this project real active backlog, or should it be paused/archived for now?
- Who should be the owner if it stays active?
- What is the first trackable output: brief, concept shortlist, reference pack, or rough cut direction?
- What would be the first 1–3 task titles if we start tracking it properly?
- Does this have any target release/delivery timing yet?

### 2. `[CTB] V - Market Practice - DDigger`
Current state:
- Status: `Not started`
- Owner: `Po (myntt7)`
- Zero linked tasks

Questions for Po:
- Is this still intake/research only, or should we start execution tracking now?
- What is the first reviewable output: reference set, angle summary, script direction, or first concept draft?
- What are the first 1–3 task titles you would create?
- What is the first review gate for this project?
- Do we already have a target date or only exploratory timing?

### 3. `[CTB] V - Gỗ celshading v2`
Current state:
- Status: `In progress`
- Owner: `Po (myntt7)`
- Zero linked tasks

Questions for Po:
- Since this is already marked `In progress`, what concrete output is currently being worked on?
- What should be the first task on the board right now?
- If the work is still exploratory, should the project status go back to `Not started` until there is a real execution task?
- What is the first reviewable artifact: reference pack, visual test, style frame, or draft asset?
- What due date should be attached to that first task?

### 4. `[AI]Optimize MCP CoPlay Token Usage`
Current state:
- Status: `In progress`
- Owner: `duc phan`
- Zero linked tasks

Questions for duc phan:
- What concrete execution item is currently active in this project?
- What would you call the first task on the board right now?
- Is the first deliverable a measurement baseline, bottleneck analysis, implementation spike, or optimization proposal?
- What review point should we track first?
- What due date should be attached to the first task?

### 5. `[AI] Improve Virtual AI Tester`
Current state:
- Status: `In progress`
- Owner: `duc phan`
- Zero linked tasks

Questions for duc phan:
- What concrete execution item is currently active here?
- What should the first task be called?
- Is the first output an audit, bug list, prototype improvement, or testing report?
- What review/decision point should be tracked first?
- What due date should be attached to the first task?

## What to do with the answers

If the owner says the project is not really active:
- pause/archive the project or keep it explicitly in intake only

If the owner says the project is active:
- create the first 1–3 task titles exactly from the owner's intended breakdown
- add owner + due date
- keep the project status aligned with actual task movement

## Important rule for Scrum Master mode

For media/creative work, the Scrum Master should not fabricate task decomposition just to satisfy board hygiene.
The Scrum Master should first extract the owner's intended reviewable outputs, then structure the board around those outputs.
