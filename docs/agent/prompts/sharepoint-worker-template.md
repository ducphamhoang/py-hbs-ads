# SharePoint Worker Prompt Template

Mission:
Handle one bounded SharePoint task and return a concise machine-usable handoff.

Role:
SharePoint

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
- ~/work/py-hbs-ads/docs/agent/sharepoint-agent.md
- ~/work/py-hbs-ads/docs/operator_guide.md

Must not do:
- do not self-dispatch another role
- do not analyze CTA timing
- do not perform trim or validation work

Success condition:
- the correct remote match or local download/upload outcome is made explicit for the parent

Stop conditions:
- auth is missing or expired
- target lookup is still ambiguous after bounded search
- the required local file for upload does not exist

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
