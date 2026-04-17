Qwen worker workspace-local references

Purpose
- Keep the minimum worker-facing references inside the workspace so standalone Qwen workers can read them without depending on ~/.hermes paths.
- These files are mirrors or distilled references for worker delegation, not the canonical source of truth.

Canonical sources
- Hermes skill: qwen-code-standalone-headless
- Hermes skill: media-scrum-master-notion
- py-hbs-ads agent docs under /home/brewuser/work/py-hbs-ads/docs/agent/

Sync rule
- When the relevant Hermes skills change, sync the worker-facing parts needed by Qwen into this workspace-local directory.
- Prefer small focused mirrors/summaries over dumping every skill file into the repo.
- If a Qwen worker needs a doc and cannot access ~/.hermes, add or refresh a workspace-local mirror here first.

Current local references
- notion-media-scrum-skill-reference.md
- qwen-worker-orchestration-reference.md
- video-analysis-mapping.md
