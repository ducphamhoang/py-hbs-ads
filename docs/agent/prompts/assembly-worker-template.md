# Assembly Worker Prompt Template

Mission:
Handle one bounded assembly/media task and return a concise machine-usable handoff.

Role:
Assembly

Workspace:
- <ABS_WORKSPACE_PATH>

Stage:
- <STAGE>

Question:
- <EXACT_QUESTION>

Authoritative artifacts:
- <ARTIFACT_PATHS>

Relevant command results:
- <JSON_FRIENDLY_SUMMARY>

Must read:
- ~/work/py-hbs-ads/docs/agent/assembly-agent.md
- ~/work/py-hbs-ads/docs/operator_guide.md

Must not do:
- do not self-dispatch another role
- do not invent trim boundaries
- do not mark validation or upload readiness complete by yourself

Success condition:
- the media step is planned or completed with explicit authoritative output paths

Stop conditions:
- required source file is missing
- trim boundaries are missing or contradictory
- ffmpeg-level execution fails
- a required config artifact is missing or malformed

Return headings:
- Stage
- Status
- Authoritative Artifacts
- Requires Human Review
- Review Gate
- Allowed Next Stages
- Blocking Issues
- Summary
- Suggested Next Role
- Suggested Next Action
- Reason
- Context For Parent
