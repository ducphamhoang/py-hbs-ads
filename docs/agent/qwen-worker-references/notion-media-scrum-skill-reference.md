Workspace-local reference for Qwen workers
Source of truth: Hermes skill `media-scrum-master-notion`
Last synced by Hermes: 2026-04-09

Use this reference when a standalone Qwen worker needs Notion scrum/traffic-manager guidance from inside the py-hbs-ads workspace.

Summary
- Use a Scrumban/Kanban mindset for media teams, not rigid software Scrum.
- Treat Projects as deliverables/initiatives and Tasks as reviewable outputs.
- Audit both project and task layers before trusting progress.
- Prefer cleanup and schema hardening before heavy automation.

Known board facts for this environment
- Primary data source: Projects
- Related execution data source: Tasks Tracker
- Notion integration can patch page properties and data-source schema
- Project-level normalization using Cal. Status as agreed truth has already been used successfully
- Current pause point: owner alignment for zero-task active B1 projects

High-value checks
- active projects with zero tasks
- tasks with no linked project
- tasks with no owner
- tasks with no due date
- overdue tasks
- vague/blank task names
- status mismatch between manual status and formulas/rollups

Owner-alignment rule
- Do not invent execution tasks for an active project just because it has zero linked tasks.
- Not started + zero tasks can be acceptable during intake/research.
- In progress + zero tasks is usually not acceptable; ask owner how they want to break the work down.
- For B1 cleanup conversations, use: ~/work/py-hbs-ads/docs/agent/notion_b1_owner_alignment_prompts_2026-04-09.md

Useful local artifacts
- ~/work/py-hbs-ads/docs/agent/notion-media-scrum-policy.md
- ~/work/py-hbs-ads/docs/agent/notion-media-scrum-routine.md
- ~/work/py-hbs-ads/docs/agent/notion_projects_audit_latest.md
- ~/work/py-hbs-ads/docs/agent/notion_tasks_cleanup_report_latest.md
- ~/work/py-hbs-ads/docs/agent/notion_tasks_manual_review_latest.md
- ~/work/py-hbs-ads/scripts/notion_media_scrum_audit.py

Bounded worker guidance
- Do not browse unrelated Notion content.
- Do not update records outside explicitly named objects/fields.
- For real updates, require exact page/database IDs, exact property names, allowed mutation scope, and a verification plan.
- If IDs/auth/mappings are unclear, return a blocker handoff so the parent can fall back to the main model.
