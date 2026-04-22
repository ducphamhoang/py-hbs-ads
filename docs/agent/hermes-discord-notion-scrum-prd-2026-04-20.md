# PRD — Hermes Discord ↔ Notion Scrum Attribution Pattern (Level 3 Rewrite)

> **Goal:** Turn the current Discord public-thread Scrum workflow into a clear, reusable **shared-thread attributed automation pattern** — not just a one-off Notion hack — and define the architecture, maturity model, and deliverables through **Level 3**.

---

## 1. Executive summary

We already proved the core idea works:
- Hermes can operate in a shared Discord thread.
- Hermes can inspect Notion, ask task-anchored follow-up questions, and use local scripts/state to guard writes.
- The workflow is useful.

What we also learned from recent sessions:
- the pattern is real,
- but the implementation is still too fragmented,
- and similar sessions still require too many repeated tool calls, repeated reads, and incremental script patches.

So this PRD reframes the work.

This is **not** just a PRD for “Hermes updates a Notion task from Discord replies.”
This is a PRD for a reusable outer-layer Hermes pattern:

> **shared-thread attributed automation**

That pattern means:
1. humans talk in one shared thread,
2. the model reasons conversationally,
3. structured local state carries identity + pending-action context,
4. deterministic scripts decide whether a side effect is safe,
5. the assistant either applies a small trusted update or asks a clarifying question.

The Discord ↔ Notion Scrum use case is the first strong instance of that pattern.

---

## 2. Problem statement

Hermes is already good at participating in shared-thread conversations.
That is not the hard part.

The hard part is making shared-thread conversation **safe for automation**.

In this workflow, four things must be true before Hermes can write back to Notion safely:
- the sender must be resolved reliably,
- the reply must be correlated to the right pending question,
- the intended update must be inferred within a narrow allowed surface,
- the write path must be auditable and reversible enough for operations.

Without that layer, Hermes can still sound convincing, but it cannot be trusted to update task state in a public thread.

Recent sessions also exposed a second problem:
- similar tasks still trigger repeated `search_files`, `read_file`, `execute_code`, and validation loops,
- identity logic and prompt-state logic are split across too many scripts,
- fixing one edge case often means patching another script rather than extending a shared abstraction.

So the product problem is now two-part:

### 2.1 Product problem
How do we make shared-thread Discord coordination safe enough for Notion automation?

### 2.2 Systems problem
How do we encode that workflow once as a reusable pattern so future sessions do not keep rebuilding or re-gluing the same logic?

---

## 3. Product thesis

The correct design is still an **outer-layer protocol**, not a Hermes core feature.

But by now the protocol should be treated as a productized pattern with maturity levels:

- **Level 0** — conversational discipline only
- **Level 1** — skill + scripts + local state
- **Level 2** — shared workflow modules, fewer duplicated scripts
- **Level 3** — productized pattern with operator entrypoints and reusable architecture for similar workflows

This PRD targets **Level 3**.

---

## 4. Product objective

Build a Level-3 Discord ↔ Notion Scrum attribution system that:

1. works in shared/public Discord threads,
2. resolves sender identity by platform user ID, not display name,
3. records outbound coordination prompts as durable workflow objects,
4. matches inbound replies deterministically before any write,
5. restricts write actions to a narrow safe surface,
6. exposes an operator-friendly end-to-end entrypoint instead of requiring multi-step manual orchestration,
7. reduces repeated tool-call overhead in similar sessions,
8. establishes a reusable Hermes pattern for future domains beyond Notion scrum.

---

## 5. Non-goals

This PRD does **not** aim to:
- redesign Hermes shared-session behavior,
- add a new Hermes core transport/session primitive,
- make free-form chat fully self-routing without explicit prompt/state anchors,
- auto-resolve all ambiguous human language,
- replace a real project management system,
- generalize immediately to every SaaS integration.

Level 3 still stays outside Hermes core.

---

## 6. Why this is a pattern, not a one-off integration

The repeated structure is now clear.

### 6.1 Shared-thread attributed automation pattern
Any workflow of this class has the same shape:

1. **shared conversation surface**
   - e.g. Discord public thread
2. **runtime sender metadata**
   - e.g. Discord user ID, thread ID, reply target
3. **durable external registry/state**
   - identity registry, pending-action ledger, audit log
4. **deterministic gating scripts**
   - resolve, match, plan, apply
5. **narrow side-effect surface**
   - comment, note, acknowledgment, due-date proposal
6. **clarification fallback**
   - ambiguity blocks writes

This same pattern could later support:
- Discord ↔ Linear triage
- Discord ↔ Notion approvals
- Teams ↔ task follow-up
- shared-thread intake routing with guarded downstream writes

So the Scrum case should be treated as the reference implementation of a broader Hermes operating pattern.

---

## 7. Current evidence from implementation

The pattern is already partially implemented and validated.

### 7.1 What already exists
Under `~/work/py-hbs-ads/` we already have:

#### State
- `state/notion_scrum/team_registry.json`
- `state/notion_scrum/pending_prompts.json`
- `state/notion_scrum/audit_log.jsonl`

#### Scripts
- `scripts/notion_scrum/resolve_person.py`
- `scripts/notion_scrum/record_pending_prompt.py`
- `scripts/notion_scrum/match_inbound_reply.py`
- `scripts/notion_scrum/plan_notion_update.py`
- `scripts/notion_scrum/apply_notion_update.py`
- `scripts/notion_scrum/lookup_notion_person.py`
- `scripts/notion_scrum/scrum_state_doctor.py`
- `scripts/notion_scrum/common.py`

#### Skill layer
- `discord-notion-scrum-attribution`

#### Test layer
- `tests/test_notion_scrum.py`

### 7.2 What recent sessions proved
We already learned these operational truths:
- Discord `platform_user_id` must be authoritative.
- Pending prompts must be durable objects, not just remembered conversation turns.
- Matching should strongly prefer `reply_to` and avoid weak same-thread inference.
- Dry-run and execute paths must differ clearly.
- Project-scoped updates and task-scoped updates both matter.
- Registry-backed identity labels matter for comments/logging.
- `pending_people` must preserve unresolved Notion candidate lists.

### 7.3 What recent sessions also exposed
The implementation is useful but still inefficient:
- too many repeated discovery calls,
- too much schema knowledge spread across scripts,
- orchestration still happens manually step-by-step,
- similar questions still require similar glue work.

That is exactly the gap between Level 1 and Level 3.

---

## 8. Maturity model

## Level 0 — Conversational protocol only

### Definition
The assistant follows behavioral rules in-thread but does not have reliable external state or deterministic gating.

### Characteristics
- task-anchored questions,
- cautious tone,
- explicit clarification when unsure,
- no durable prompt ledger,
- no trusted sender resolution layer.

### Usefulness
Good for human coordination.
Not safe for automated writes.

### Status
Already surpassed.

---

## Level 1 — Skill + scripts + local state

### Definition
The workflow is implemented as a skill-guided protocol plus external JSON state plus helper scripts.

### Characteristics
- team registry,
- pending prompt ledger,
- audit log,
- explicit script chain:
  1. `resolve_person.py`
  2. `match_inbound_reply.py`
  3. `plan_notion_update.py`
  4. `apply_notion_update.py`
- narrow V1 write surface,
- ambiguity stops writes.

### Strength
Safe enough for controlled real usage.

### Weakness
Still too fragmented.
A lot of operational overhead remains in session-level orchestration.

### Status
Mostly achieved.

---

## Level 2 — Shared workflow modules

### Definition
The system stops behaving like a pile of adjacent scripts and starts behaving like one coherent local workflow package.

### Required shift
Move shared logic out of individual scripts into common modules.

### Level-2 capabilities

#### A. Shared person resolution layer
One internal module should own:
- platform identity resolution,
- canonical-person lookup,
- pending-person candidate surfacing,
- actor label generation.

Suggested module:
- `scripts/notion_scrum/person_resolution.py`

Thin wrappers would remain for:
- `resolve_person.py`
- `lookup_notion_person.py`

#### B. Shared prompt store
One internal module should own:
- loading/saving prompt state,
- appending prompts,
- retrieving open prompts,
- marking answered/cancelled/expired,
- validating prompt schema.

Suggested module:
- `scripts/notion_scrum/prompt_store.py`

#### C. Shared audit helper
One internal module should own:
- audit event formatting,
- append-only audit writes,
- event-type conventions.

Suggested module:
- `scripts/notion_scrum/audit.py`

#### D. Shared typed workflow objects
The system should stop spelunking raw dicts everywhere.
Use internal typed models for:
- inbound event,
- prompt record,
- match result,
- update plan.

Suggested module:
- `scripts/notion_scrum/models.py`

### Value of Level 2
- less duplicated schema logic,
- fewer one-off patches,
- easier tests,
- fewer repeated reads during debugging.

### Status
Not complete yet.
This is the immediate refactor layer.

---

## Level 3 — Productized pattern

### Definition
The workflow becomes an operator-friendly productized pattern rather than a set of low-level pieces that Hermes must manually chain together every time.

### Level-3 requirements

#### A. Single workflow entrypoints
The main repeated flows should have direct operator-facing commands.

Required entrypoints:

1. **Inbound reply pipeline**
   - suggested file: `scripts/notion_scrum/process_inbound_reply.py`
   - wraps:
     - resolve sender
     - match reply
     - plan update
     - apply update or emit clarification-needed result

2. **Prompt recording flow**
   - suggested file: `scripts/notion_scrum/create_pending_prompt.py`
   - wraps prompt creation + validation + audit write

3. **Operational preflight**
   - suggested file: `scripts/notion_scrum/preflight.py`
   - validates registry, pending prompt state, unresolved mappings, config assumptions, and doctor checks in one pass

#### B. Stable result contracts
Every Level-3 entrypoint should return a stable JSON result envelope with fields like:
- `ok`
- `action_taken`
- `write_applied`
- `requires_clarification`
- `clarification_reason`
- `pending_prompt_id`
- `canonical_person_key`
- `matched_prompt_id`
- `resolved_update_type`
- `audit_events`

This matters because it turns the workflow into a composable subsystem.

#### C. Explicit dry-run and execute modes
Every write-capable flow must support:
- dry-run as default or clearly available mode,
- execute mode for live write,
- identical output shape in both modes,
- prompt closure only after successful live write.

#### D. Pattern-level docs
The documentation should stop reading like a one-off scrum trick.
It should describe:
- the general attributed-automation pattern,
- why it works in shared threads,
- what parts are reusable,
- what parts are Notion-scrum-specific.

#### E. Reuse boundary
Level 3 must make it easy to adapt the same pattern to another side-effect system later without rewriting the identity/prompt/matching foundation.

### Value of Level 3
- lower session overhead,
- fewer repeated tool calls,
- clearer operator commands,
- easier reuse in future workflows,
- this becomes a genuine Hermes skill pattern.

### Status
This is the target state of this PRD.

---

## 9. User stories

### 9.1 As Hermes, I want to ask a specific owner for a specific missing task field in a shared thread
So the human can answer in context without private DM or manual Notion navigation.

### 9.2 As the system, I want to know exactly who replied
So a nickname change or casual display label does not create a wrong write.

### 9.3 As the system, I want each outbound question to become a durable pending object
So later replies can be matched to a known coordination target.

### 9.4 As the system, I want to run one end-to-end inbound pipeline
So similar sessions do not keep manually redoing the same orchestration steps.

### 9.5 As an operator, I want a preflight command that tells me whether the workflow state is healthy
So I do not have to inspect multiple files and scripts manually.

### 9.6 As a future workflow designer, I want this documented as a pattern
So I can reuse it for another attributed side-effect workflow.

---

## 10. Constraints

### 10.1 Avoid Hermes core changes
We still prefer:
- skills,
- local scripts,
- local state,
- Notion-side schema support,
- operator conventions.

We still avoid changing:
- gateway runtime model,
- transcript format,
- session internals,
- core tool registry.

### 10.2 Shared-thread reality is acceptable
One thread is still one shared conversation.
The system must tolerate that and rely on external structured state for write safety.

### 10.3 Safety beats convenience
If sender, target, or intended write is ambiguous:
- no write,
- ask a task-anchored clarification,
- keep the workflow state coherent.

---

## 11. Functional requirements

## 11.1 Identity requirements
The workflow must:
- resolve sender by `platform + platform_user_id`,
- support canonical-person mapping,
- preserve unresolved Notion candidates when identity is only partially resolved,
- generate consistent actor labels for comments and audit logs.

## 11.2 Prompt-state requirements
The workflow must:
- record outbound prompts as durable objects,
- keep lifecycle states (`open`, `answered`, `cancelled`, `expired`),
- retain thread and Notion target anchors,
- keep allowed update types with each prompt.

## 11.3 Matching requirements
The workflow must:
- prefer explicit `reply_to`,
- support explicit task/project mentions,
- avoid weak auto-match heuristics,
- return structured confidence and reasons.

## 11.4 Planning requirements
The workflow must:
- infer only a narrow set of allowed update types,
- distinguish safe-to-apply from clarification-needed,
- separate planning from live mutation.

## 11.5 Apply requirements
The workflow must:
- support dry-run and execute modes,
- update Notion only through narrow approved actions,
- mark prompts answered only after successful live write,
- write audit events for attempts and outcomes.

## 11.6 Operator requirements
The workflow must provide:
- one-command preflight,
- one-command inbound processing,
- clear result JSON for automation and debugging.

---

## 12. Reference architecture at Level 3

### 12.1 Skill layer
The skill remains responsible for:
- behavioral policy,
- safety stance,
- prompting style,
- deciding when to ask versus when to invoke the workflow.

The skill is **not** the storage or deterministic execution layer.

### 12.2 Shared workflow package
Suggested local package shape:

```text
scripts/notion_scrum/
  common.py
  models.py
  audit.py
  prompt_store.py
  person_resolution.py
  workflow.py
  resolve_person.py
  lookup_notion_person.py
  record_pending_prompt.py
  match_inbound_reply.py
  plan_notion_update.py
  apply_notion_update.py
  process_inbound_reply.py
  create_pending_prompt.py
  preflight.py
  scrum_state_doctor.py
```

### 12.3 State layer
Still under:
- `state/notion_scrum/team_registry.json`
- `state/notion_scrum/pending_prompts.json`
- `state/notion_scrum/audit_log.jsonl`

### 12.4 Domain adapter boundary
The Notion-specific parts should be isolated enough that future adapters could swap in another backend later.

Examples of domain-specific behavior:
- mapping to Notion people/user IDs,
- Notion comment/page patch calls,
- Notion page/project/task semantics.

Examples of pattern-generic behavior:
- sender resolution,
- pending prompt lifecycle,
- reply matching,
- audit discipline,
- dry-run vs execute semantics.

---

## 13. Workflow design

## 13.1 Outbound question flow
1. Hermes inspects task/project state.
2. Hermes identifies a missing field or blocked decision.
3. Hermes resolves the intended human target if possible.
4. Hermes asks a concise task-anchored question in-thread.
5. Hermes records the prompt as a pending workflow object.

Preferred output shape:
- who
- which task/project
- what is missing
- preferred answer format

## 13.2 Inbound reply flow at Level 3
1. Receive inbound event.
2. Run `process_inbound_reply.py` in dry-run or execute mode.
3. Internally:
   - resolve sender
   - locate candidate prompts
   - score match
   - plan update
   - apply update if safe and execute=true
4. Return stable JSON result.
5. Hermes reports either:
   - what was updated, or
   - what clarification is needed.

## 13.3 Preflight flow
1. Run `preflight.py`.
2. Validate:
   - registry integrity,
   - prompt integrity,
   - unresolved people,
   - duplicate prompt IDs,
   - missing allowed update types,
   - state consistency,
   - optionally config assumptions.
3. Return a single operator summary.

---

## 14. Matching and confidence policy

### 14.1 Priority order
Use this order strictly:
1. explicit reply-to a known Hermes message,
2. same thread + same sender + exactly one open prompt,
3. explicit task/project mention in reply text,
4. one open prompt total in thread,
5. otherwise ambiguous.

### 14.2 Conservative default
The system should prefer false negatives over false positive writes.

### 14.3 Clarification policy
If below threshold or multiple candidates remain plausible:
- no write,
- ask a task-anchored clarifying question,
- keep the original prompt open unless explicitly resolved.

---

## 15. Allowed write surface

Level-3 productization does **not** mean broader autonomous mutation.
The safe write surface remains intentionally narrow.

Allow:
- task comment,
- status note,
- blocked note,
- owner acknowledgment,
- due-date proposal/note,
- mark prompt answered,
- safe project-scoped comment where the supported path is explicit.

Do not auto-write:
- reassignment without explicit confirmation,
- inferred completion from casual chat,
- project completion/status flips from one reply,
- vague project-scope requirements as structured facts,
- task creation from ambiguous discussion,
- schema edits.

---

## 16. Deliverables by level

## Level 1 deliverables
- skill spec,
- state schema,
- team registry,
- pending prompt ledger,
- audit log,
- per-step scripts,
- initial tests.

## Level 2 deliverables
- shared person resolution module,
- shared prompt store,
- shared audit helper,
- shared workflow models,
- reduced duplication across scripts,
- expanded tests around shared modules.

## Level 3 deliverables
- `process_inbound_reply.py`,
- `create_pending_prompt.py`,
- `preflight.py`,
- stable JSON result envelopes,
- explicit dry-run/execute contract,
- pattern-level docs,
- clear split between generic attributed-automation logic and Notion-specific adapter logic.

---

## 17. Success criteria

The Level-3 rewrite is successful if:

1. the docs clearly describe a reusable pattern rather than a one-off workflow,
2. a future operator can understand the whole system without reconstructing it from multiple sessions,
3. similar inbound-reply tasks can be run through one workflow entrypoint,
4. repeated session overhead drops because the orchestration is encoded in the tooling,
5. identity/prompt/matching logic is shared rather than copy-patched across scripts,
6. the Notion Scrum use case remains safe in shared threads,
7. the same architecture is obviously adaptable to a future non-Notion attributed workflow.

---

## 18. Risks

### 18.1 Over-generalizing too early
If we abstract too far, we may slow down the current Scrum workflow.

**Mitigation:**
Keep Notion Scrum as the reference implementation and only extract logic that is already clearly shared.

### 18.2 Hiding too much behind one entrypoint
A monolithic wrapper can make debugging harder.

**Mitigation:**
Keep low-level scripts/modules usable and testable; add entrypoints as orchestration wrappers, not opaque replacements.

### 18.3 Pattern drift between docs and code
The docs may say “pattern,” while the code remains ad hoc.

**Mitigation:**
Level-3 deliverables must include shared modules and entrypoints, not just wording changes.

### 18.4 Unsafe convenience pressure
As the workflow becomes easier to run, people may want broader auto-write behavior.

**Mitigation:**
Keep the narrow write allowlist and explicit clarification fallback.

---

## 19. Recommendation

Proceed as follows:

1. treat the current system as a validated **Level-1 reference implementation**,
2. refactor toward **Level 2 shared modules**,
3. add **Level 3 operator entrypoints**,
4. keep the workflow outside Hermes core,
5. document it explicitly as a reusable **Hermes skill pattern for shared-thread attributed automation**.

That is the right level of ambition now.

We already know the workflow is useful.
The next step is to make it coherent, cheaper to operate, and reusable.