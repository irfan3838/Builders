# Workflows (`PURSER_WORKFLOWS=1`)

One workflow per user action, each with a checklist. A cheap model runs it; code verifies it; a finished workflow is
killed so its tool output never stays in the conversation; anything unknown goes to a stronger model.

## A turn
1. **Continuation, no LLM**: a change waits for confirmation and the user said a clear yes/no
   (`services/affirmation.py`) → the existing confirm/cancel tool runs. "Yes" with nothing pending does the last
   offered next step, or says nothing is pending.
2. **Picker** (`OPENAI_MODEL_WORKFLOW`, default `OPENAI_MODEL_FAST`): one structured-output call over the
   role-filtered menu (`registry.menu`) → a workflow name or `none`.
3. **Workflow run**: the same cheap model with only that workflow's tools (+ `ask_choice`, `suggest_next_actions`),
   its checklist and a compact brief (last 3 exchanges, summaries of finished workflows, the pending change). No chat
   history is replayed.
4. **Verify in code** (`spec.verify`): a proposal was created, the user was asked, the server refused, or a required
   tool returned ok. Otherwise retry once with the reason.
5. **Kill**: a finished workflow leaves one summary line in `Conversation.workflow_state["memo"]`.
6. **Escalate** (`OPENAI_MODEL_ESCALATION`, default `gpt-6-sol`) when: the picker says `none`, the workflow replies
   `ESCALATE:`, verification fails twice, the user corrects the same change more than twice, or a step crashes. The
   strong model gets that module's tools and the brief, not the history. Each one is logged in `escalations`.

Writes always go through propose → preview → confirm; only the engine confirms, and the confirm tool still checks the
user's own words.

## Add or change a workflow
Edit `specs/<module>.py`:
```python
W("record_payment", "revenue",
  "Customer money came in: 'paisa aa gaya', 'payment mila'. NOT for money we pay out (settle_payment).",
  ("list_client_invoices", "propose_payment"),           # the only tools it may call
  ("Find the invoice's S… ref with list_client_invoices …",  # checklist the model follows
   "Call propose_payment …", "Read the 'say' text and ask for confirmation. Stop."))
```
`registry.check()` runs on first load and fails loudly if a spec names an unknown tool, uses confirm/cancel, or if any
real tool is reachable from no workflow. Then re-run the evals: `uv run python -m scripts.eval_run --arm B`.

The escalation log is the backlog: `select trigger, utterance from escalations order by id desc`.

## User routines (custom workflows)

Users describe a routine in plain words (chat/voice: the `manage_my_routines` workflow; or Settings > My routines).
`custom.py` compiles it into the same `Workflow` shape: one structured-output call whose tool field is a `Literal` of
the tools the user's role may use, then a deterministic `validate()` (limits, role allowlist, injection denylist,
no unprompted emails/links, shared routines may not pin recipients/links/amounts, only admins share), one repair, and
a collision check that runs the real picker on the routine's example phrases. Saved rows live in `custom_workflows`.

At run time `engine.run` loads the actor's routines (`custom.for_actor`): "run <title>" matches in code
(`fast_match`, no model call), otherwise they join the picker menu. A routine runs with only its frozen tools, its
steps fenced as `<user_routine>` data under the CORE rules, and every write is still a propose_* the user confirms.
The raw description (`source_prompt`) is audit-only and never sent to the runtime model. Routines never enter
`registry.workflows()`, so the coverage `check()` is unaffected.
