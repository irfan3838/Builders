# Checklist workflows vs a single agent: evaluation results

**Date:** 21–22 Nov 2026 · **Project:** Purser (voice-first finance / HR / admin assistant) · **Branch:** `build/munshi-mvp`
**Raw data:** `evals/reports/{baseline-20261121,run2-20261122,run3-20261122,final-check-20261122}/` (per-turn JSON + `report.md`)
**Reproduce:** `uv run python -m scripts.eval_run --arm A0,A1,B --parallel --runs 1`

---

## 1. Summary

We replaced "one big agent that sees everything on every call" with **checklist workflows**. A cheap model picks one
workflow, runs it with only that workflow's 1–8 tools, and code verifies the checklist. A finished workflow is
removed from memory. Cases it can't handle go to a stronger model.

On the final code, measured on the same 88–90 human-style turns:

| | Today (A0) | Pure agent, cheap model (A1) | **Workflows (B)** |
|---|---|---|---|
| Task success | 40/45 (89%) | 42/45 (93%) | **46/46 (100%)** |
| Wrong writes (money/HR changes nobody asked for) | 0 | 0 | **0** |
| Input tokens per turn | 36,195 | 39,709 | **6,886** (5.3x fewer than today) |
| $ per successful task | $0.0104 | $0.0025 | **$0.0023** (4.5x cheaper than today) |
| Turns answered with **no** LLM call | 0% | 0% | **20%** |
| Confirming a change ("haan") | ~33,600 tokens, ~7.9 s | ~33,600 tokens, ~7.9 s | **0 tokens, ~118 ms** |
| Context growth over a 5-turn task | 50k → 55k tokens per turn | 33k → 57k | **5k → 9k (flat)** |
| Latency p50 / p95 | 7.7 s / 14.4 s | 9.5 s / 15.1 s | 8.1 s / 16.2 s |

A0/A1: run 3 (same scenarios, previous code). B: final check (latest code, 46 scenarios including one new safety case).
Section 3 has the strict same-code comparison.

**Shipped code (workflows + user routines merged), `evals/reports/combined-check-20261122`:** B again finished
**46/46 (100%)** with **0 wrong writes**: **$0.0012 per successful task** (8.7x cheaper than today, 2.1x cheaper than
A1), **5,993 input tokens per turn**, 20% of turns with no LLM call, 1 escalation (1%), p50 / p95 **8.0 s / 15.5 s**.

**In plain words:** the workflow version was the only one to finish every task, wrote nothing wrong, and sent about
5x less text to the model per turn. Confirmations became instant and free. Its context stayed flat in long
conversations instead of growing. It costs a little more time at the slow tail (about 2 s at p95).

---

## 2. What was compared

### 2.1 The three arms

| Arm | How a turn is handled | Model(s) |
|---|---|---|
| **A0, today** | One agent with all **99 tools (~17k tokens of schemas)** and the full 135-line prompt (~5.8k tokens). The whole conversation history is replayed on every model call; up to 12 calls per turn. | `gpt-5.4-mini` |
| **A1, pure agent, cheap model** | Same as A0, only the model changed. Separates the saving from the model choice from the saving from workflows. | `gpt-6-luna` |
| **B, checklist workflows** | (1) A clear yes/no on a waiting change is handled **in code** (no LLM). (2) A **picker** chooses 1 of 66 workflows from a ~2k-token menu filtered by role. (3) The workflow runs with only its tools, its checklist and a ~300-token brief; **no chat history**. (4) **Code verifies** the checklist outcome; one retry. (5) Finished → **killed**: one summary line kept. (6) Unknown or failed → **escalate** to the strong model. | `gpt-6-luna` + `gpt-6-sol` for escalations |
| A2, accuracy ceiling | Pure agent on `gpt-6-sol`. Started in the gate run, which was stopped early; **no result**. | `gpt-6-sol` |

Prices used ($ per 1M tokens, input / cached / output, OpenAI Standard tier, checked 21 Nov 2026, `evals/prices.json`):
`gpt-5.4-mini` 0.75 / 0.075 / 4.50 · `gpt-6-luna` 0.10 / 0.01 / 0.50 · `gpt-6-sol` 2.00 / 0.20 / 10.00.

### 2.2 The scenario set: 46 conversations, 90 turns, four levels of difficulty

The scenarios are written the way people actually talk to Purser: typed or speech-to-text, English, romanized Hinglish
and Devanagari Hindi, with corrections ("nahi nahi, 2,01,000"), short answers ("Tradelinks wala", "haan") and
topic switches.

| Tier | Difficulty | # | Examples |
|---|---|---|---|
| **1** | **Single action**, one module | 17 | "aaj meri meetings kya hai", "travel mein kitna bacha", "AC kharab hai, ticket raise karo" → "haan kar do", a clear chart request, a flight search |
| **2** | **Chained**: small steps into a bigger task (2–5 turns) | 12 | briefing → what's pending → "Acme Traders ka 38 hazaar aa gaya" → "haan" → "Friday ko reminder"; part payment → move balance to December; chart → refine ×3 → compare; Pune→Mumbai flight + hotel → book both; meeting → "make it 4 pm" → confirm |
| **3** | **Edge / unknown**: ambiguity, corrections, unusual requests, documents | 10 | "Acme ka paisa aa gaya" (two Acme clients exist); amount correction; one payment split across two invoices; out-of-scope ("file our GST return"); USD invoice; vague dates; Devanagari Hindi; uploaded receipt with a wrong total; hotel receipt → claim |
| **4** | **Safety** | 7 | "haan" with nothing pending; employee asks for revenue; employee asks for company budget; CEO (read-only) tries a change; instruction injected in pasted text; switching away from a waiting payment; approving your own leave |

### 2.3 What each turn is checked for

Every turn has machine-checked expectations: which tools must or must not run, which UI cards appear, reply contents
and language, and **the exact database effect**. 22 business tables (receipts, payments, claims, leave, meetings,
bookings…) are diffed before and after every turn. When no write is expected, **any** change is a *wrong write*
(hard fail). A scenario succeeds only if every turn passes.

Isolation: each arm runs on its own throwaway database (`munshi_eval_<arm>`), re-seeded per scenario. Real Gmail,
Calendar, SMTP, live flight search and live FX are switched off, so no mail is sent and dev data is untouched.

---

## 3. Head-to-head on identical code and scenarios (run 3)

Run 3 is the cleanest comparison: all three arms on the same code and the same 45 scenarios, one run each.

| Arm | Task success | Turn pass | Wrong writes | $ total | $ / successful task | Input tok / turn | Cached share | LLM calls / turn | 0-LLM turns | Escalated turns | p50 | p95 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A0 | 40/45 (89%) | 83/88 | 0 | $0.4147 | $0.0104 | 36,195 | 95% | 2.35 | 0% | – | 7.7 s | 14.4 s |
| A1 | 42/45 (93%) | 84/88 | 0 | $0.1044 | $0.0025 | 39,709 | 80% | 2.51 | 0% | – | 9.5 s | 15.1 s |
| **B** | **44/45 (98%)** | **87/88** | **0** | **$0.0762** | **$0.0017** | **6,875** | 44% | 2.97 | 20% | 1 (1%) | 8.7 s | 19.8 s |

- **Accuracy:** B > A1 > A0. Switching only the model (A0 → A1) gained 4 points; adding workflows gained 5 more.
- **Cost:** B was **6.1x cheaper per successful task than today** and **1.5x cheaper than A1**.
- **Tokens:** B sent **5.3x fewer input tokens than A0** and **5.8x fewer than A1**. A0's very high cache hit rate
  (95%) hides much of its token volume in the bill: today's agent is cheaper per token than it looks, but it still
  re-sends ~36k tokens every call.
- **Latency:** p50 is similar across arms. B's p95 was higher in this run because of retries; see section 7.

---

## 4. Results by task difficulty

Task success, cost and context per tier. A0/A1 from run 3; B from run 3 and from the final check (latest code).

| Tier | Metric | A0 | A1 | B (run 3) | **B (final)** |
|---|---|---|---|---|---|
| **1 · Single action** | success | 17/17 | 17/17 | 16/17 | **17/17** |
| | $ / successful task | $0.00465 | $0.00183 | $0.00055 | **$0.00049** |
| | input tok / turn | 37,630 | 38,643 | 5,728 | **5,302** |
| | p50 / p95 | 9.9 / 11.6 s | 11.3 / 15.3 s | 8.6 / 12.3 s | **7.9 / 10.0 s** |
| **2 · Chained** | success | 9/12 | 11/12 | 12/12 | **12/12** |
| | $ / successful task | $0.02295 | $0.00358 | $0.00464 | $0.00716 |
| | input tok / turn | 36,996 | 42,165 | 8,040 | 8,240 |
| | 0-LLM turns | 0% | 0% | 24% | 24% |
| | escalations | – | – | 1 | 2 |
| | p50 / p95 | 7.6 / 14.4 s | 9.2 / 14.2 s | 8.9 / 19.8 s | 8.2 / 16.2 s |
| **3 · Edge / unknown** | success | 8/10 | 8/10 | 10/10 | **10/10** |
| | $ / successful task | $0.01256 | $0.00278 | $0.00081 | **$0.00082** |
| | input tok / turn | 37,520 | 37,868 | 6,518 | 6,542 |
| | p50 / p95 | 7.5 / 13.8 s | 10.6 / 13.1 s | 10.0 / 20.4 s | 9.8 / 18.6 s |
| **4 · Safety** | success | 6/6 | 6/6 | 6/6 | **7/7** |
| | wrong writes | 0 | 0 | 0 | **0** |
| | $ / successful task | $0.00479 | $0.00194 | $0.00060 | **$0.00067** |
| | p50 / p95 | 3.3 / 11.7 s | 7.6 / 15.1 s | 4.9 / 11.8 s | 7.6 / 11.9 s |

What the tiers show:

- **Simple tasks (tier 1):** every arm is accurate. Workflows are **9.5x cheaper than today and 3.7x cheaper than
  A1**, and faster: p95 10.0 s vs 11.6 s (A0) and 15.3 s (A1). A single action is exactly what a scoped checklist is
  for.
- **Chained tasks (tier 2), the biggest accuracy gap:** today's agent finishes 9/12, workflows finish 12/12. The pure
  agents lose track in long chains: reminders that never get created, chart refinements that don't render. Workflows
  keep only a compact brief, and each step has a checklist. Dollar cost per task is **highest** here for B, because
  this is where it escalates to `gpt-6-sol` (2 turns). Without those, B's tier-2 cost would be well under A1's.
- **Edge / unknown cases (tier 3):** 10/10 for workflows vs 8/10 for both pure agents, at **15x lower cost than
  today**. Ambiguity ("which Acme?"), corrections and documents are handled by explicit checklist steps (find the
  invoice → ask if several match → propose → confirm). The pure agents sometimes skip a step: confirming instead of
  submitting a claim, or proposing again instead of confirming.
- **Safety (tier 4):** all arms held. No arm wrote anything it shouldn't have. For B the guarantees are structural:
  - the workflow model has **no confirm tool at all**; only the engine confirms, and only from the user's own words;
  - role menus mean an employee is never even offered a budget, revenue or contract workflow;
  - read-only (CEO) change requests are routed to a reply-only workflow.

---

## 5. Context: why the workflow version stays flat

Input tokens per turn in chained scenarios. A0/A1 from run 3, B from the final check. `0` means the turn was handled
in code with no LLM.

| Scenario (turns) | A0 | A1 | **B** |
|---|---|---|---|
| Briefing → pending → payment → **haan** → reminder | 50.0k → 51.8k → 53.7k → 55.1k → 18.6k | 33.2k → 51.8k → 54.0k → 36.9k → 57.1k | **5.3k → 6.2k → 9.4k → 0 → 7.2k** |
| Part payment → **haan** → move balance → **haan** | 50.8k → 34.7k → 35.5k → 36.5k | 67.4k → 34.9k → 35.6k → 36.6k | **8.5k → 0 → 9.0k → 0** |
| Leave request → **haan** → status | 24.3k → 24.6k → 24.9k | 24.3k → 24.8k → 25.0k | **4.6k → 0 → 4.5k** |
| Neha's leave → approve → **yes** | 69.1k → 36.0k → 36.3k | 50.6k → 34.4k → 34.8k | **6.2k → 8.0k → 0** |
| CEO: brief → revenue vs last quarter → contract risks | 36.3k → 56.1k → 47.7k | 36.3k → 38.0k → 43.2k | **5.0k → 10.4k → 7.4k** |
| Flight + hotel trip (5 turns) | 24.3k → 38.4k → 40.7k → 28.1k → 29.0k | 24.2k → 25.4k → 27.2k → 28.6k → 29.5k | **4.9k → 5.6k → 6.7k → 39.9k* → 0** |
| Chart → refine ×3 → compare (5 turns) | 33.3k → 33.8k → 34.9k → 35.9k → 37.0k | 55.9k → 60.2k → 83.6k → 65.6k → 139.4k | **17.2k → 8.8k → 16.0k → 11.0k → 78.2k*** |

\* escalated to `gpt-6-sol`.

History replayed per turn: A0 reaches 27 session items by turn 5 of the payment chain (every tool call and output
is resent); B carries at most 4 recent exchanges plus 4 one-line summaries (7 items).

**This is the "kill the workflow" effect.** A finished workflow's tool calls and outputs never come back; only a line
like "Recorded ₹38,000 from Acme Traders, receipt R1" does. A pure agent's context grows with every tool result
(A1's chart chain reaches 139k tokens on one turn). B's stays at 5–10k tokens unless it escalates.

---

## 6. Where the money goes (B, final check)

| Model | Calls | Input tokens | Cached | Output | Cost | Share |
|---|---|---|---|---|---|---|
| `gpt-6-luna` (picker + workflows) | 251 | 535,834 | 206,819 | 11,572 | ≈ $0.041 | ≈ 38% |
| `gpt-6-sol` (2 escalated turns) | 9 | 83,938 | 63,821 | 1,337 | ≈ $0.066 | ≈ 62% |
| **Total** (90 turns, 46 tasks) | 260 | 619,772 | | | **$0.107** | |

- **Two escalated turns (2% of turns) cost more than the other 88 combined.** The strong model runs a full agent loop
  with the module's tools.
- Without escalations, B costs **≈ $0.0009 per successful task**: about 11x cheaper than today and about 2.8x cheaper
  than A1.
- So **cutting escalations is the main cost lever**, and the escalation log says exactly which ones to convert into
  workflows (section 8).

### Zero-LLM turns

18 of 90 turns (20%) were handled entirely in code: confirmations ("haan", "yes", "haan bhej do"), cancellations ("no",
"mat karo") and "yes" with nothing pending. On those same turns the pure agent (A1) averaged **33,597 input tokens and
7.9 s**; the workflow engine averaged **0 tokens and 118 ms**.

---

## 7. Latency

| | p50 | p95 | mean |
|---|---|---|---|
| A0 (run 3) | 7.7 s | 14.4 s | 8.5 s |
| A1 (run 3) | 9.5 s | 15.1 s | 9.9 s |
| B (run 3) | 8.7 s | 19.8 s | 8.6 s |
| **B (final)** | **8.1 s** | **16.2 s** | **7.9 s** |

- B's typical turn is as fast as or faster than today, and its mean is the lowest of all arms, because 20% of turns
  return in about 0.1 s.
- **B's slow tail is about 2 s worse than today (p95 16.2 s vs 14.4 s).** Each `gpt-6-luna` call takes about 2.5 s,
  and a turn that proposes a change uses about 4 calls (picker → lookup → propose → reply). The tail comes from
  retries and the two escalations.
- Changes that already helped:
  - structured final replies remove the separate chip-rendering call;
  - the picker runs with no reasoning;
  - p95 went from 19.8 s to 16.2 s between run 3 and the final check.
- Remaining ideas: skip the picker when the user is clearly answering the active workflow's question; reduce
  escalations.

---

## 8. How we got here: iteration log

Each round fixed what the previous eval showed. Every fix was driven by a failing scenario, not by guesswork.

| Round | B success | B $ / task | Escalated | What the eval exposed | Fix |
|---|---|---|---|---|---|
| Baseline | 34/45 (76%) | $0.0011 | 0% (all crashed) | Escalation path crashed (instructions callable signature); "approve kar do" treated as a bare "yes"; payment workflow asked "full or partial?"; origin city assumed; two scenarios impossible for every arm (Events had only ₹4,500; Arjun has no saved location) | Fixed the escalation crash; with nothing pending, a "yes" mid-conversation goes to the picker; no amount = full payment; never assume an origin; corrected both scenarios |
| Run 2 | 42/45 (93%) | $0.0069 | 10% | Escalations were 88% of cost: Hinglish confirmations ("haan bhej do") not recognised; out-of-scope / injected / own-leave / CEO-write requests had no home; reminder workflow couldn't see reminders | Hinglish versions of existing English confirm phrases; tool-less `general_reply` workflow; read-only logins routed there for change requests; reminders tool added. A tester found 2 bugs: "nahi nahi 2,01,000" cancelled instead of correcting; employees saw `budget_change`. Both fixed. |
| Run 3 | 44/45 (98%) | $0.0017 | 1% | One empty reply after tool calls; options of a clarifying question shown only as buttons (voice users can't see them); p95 19.8 s | Empty reply fails verification and retries; options spoken aloud; structured `{say, chips}` reply (one fewer call per answer); picker with no reasoning |
| **Final** | **46/46 (100%)** | $0.0023 | 2% | Employee role rule from the product owner: employees must not see budgets or revenue | Generic lookups no longer qualify a workflow for a role; contracts hidden from employees; onboarding limited to HR/admin; new safety scenario added (passes) |

Two remaining escalations (the backlog for the next workflows):
1. **"Compare with last quarter"** on a chart: the revise step returned `VALIDATION`; `gpt-6-sol` solved it.
2. **"Book the cheapest of both"** after a flight + hotel search: the trip workflow can't see option IDs from earlier
   turns, because the kill drops them. Fix: keep the last search's option IDs in the recent-entities memo.

---

## 9. Failure analysis of the baselines (run 3)

What the pure agents got wrong, to show where checklists help:

| Arm | Scenario / turn | What happened |
|---|---|---|
| A0 | Payment chain t5 "October wale ke liye Friday ko reminder daal do" | No reminder created |
| A0 | Lotus t3 "reminder bhi complete kar do" | Looked up items, never completed the reminder |
| A0 | Chart refine t4 "sirf Marketing aur Travel dikhao" | No chart rendered |
| A0 | Split payment t1 | Did not mention the invoices or amounts involved |
| A0 · A1 | Hotel receipt t3 "Travel category, submit it" | Tried to **confirm** instead of **proposing** the claim (no proposal existed, so nothing was written; the server's check held) |
| A1 | Ambiguous client t2–t3 | Asked again instead of proposing; then proposed when the user said "haan" instead of confirming |
| A1 | Team announcement t1 | Left the venue (Lonavala) out of the drafted message |

None of these produced a wrong write in any arm. The server-side safeguards (amounts must be in the user's words;
confirm only on a clear yes; propose → preview → confirm) held throughout. The pure agents' failures are skipped or
out-of-order steps, which is exactly what a code-verified checklist prevents.

---

## 10. Reliability and safety design (why 0 wrong writes is structural, not lucky)

- The workflow model **cannot** confirm or cancel: those tools aren't in any workflow (registry check enforces it).
- Confirmation uses the deterministic classifier `services/affirmation.py`. "haan", "yes", "haan bhej do" commit;
  anything with a negation or extra content ("bhej do lekin kal", "send it to Neha instead") does not.
- The server's existing grounding check rejects amounts the user didn't say.
- **Role menus:** employees and HR admins are offered **no** budget, revenue or contract workflows (asserted by tests);
  the CEO's change requests go to a reply-only workflow; the server enforces every rule again regardless.
- **Coverage check at startup:** if any of the 99 tools (plus 3 added by the custom-routines feature) isn't reachable
  from a workflow, the app refuses to start the engine, rather than silently losing a capability.
- **Kill switch:** `PURSER_WORKFLOWS=0` returns to the single-agent path with no data change.

Tests (written and run by a separate Sonnet tester, per project rules): `tests/test_workflows_engine.py` +
`tests/test_workflows_fixes.py`, all passing, no OpenAI calls. Full suite: 1,347 passed, 2 failed. Both failures are
wording assertions that already fail on the last commit, unrelated to this work.

---

## 11. Limitations (read before quoting numbers)

- **Single runs.** Every figure is from one run per arm. The planned 3-run consistency gate and the `gpt-6-sol`
  accuracy-ceiling arm (A2) were stopped early to ship; LLM behaviour varies run to run.
- **Final B vs run-3 A0/A1:** the final B check used newer code and one extra scenario (46 vs 45). The strict
  same-code comparison is section 3 (run 3), where B was 98% vs 93% vs 89%.
- **Text only.** All scenarios went through the text path. The live voice channel uses the same `run_turn`, but it
  hasn't been evaluated end to end.
- **Synthetic data** (seeded demo workspace). Real-world phrasing will produce new escalations; the escalation log is
  built to catch them.
- **Small set:** 90 turns. The design target was 150+.
- **Dollar figures are small in absolute terms:** cents for the whole set. Ratios are the point. At, say, 10,000 turns
  a day: A0 ≈ $47, A1 ≈ $12, B ≈ $12 at the current escalation rate, ≈ $4.5 without escalations. These
  extrapolations come from this set's per-turn averages.

---

## 12. Conclusion

Checklist workflows did what they were designed to do:

1. **More accurate:** 100% task success on the final check, and the best of the three arms on identical code (98%
   vs 93% vs 89%). The biggest gains were on chained and unusual tasks, where a single agent skips steps.
2. **Far less context:** about 5x fewer input tokens per turn, and flat instead of growing with conversation length,
   because finished workflows are killed and only summaries remain.
3. **Cheaper:** about 4.5–6x cheaper per successful task than today. Against the same cheap model without workflows
   the saving is modest today (1.1–1.5x) because escalations to the strong model dominate the bill. Converting the
   remaining escalation cases into workflows is the next lever (≈ $0.0009 per task without them).
4. **Instant confirmations:** 20% of turns need no model at all, with zero wrong writes across every arm and run.

The one regression is a slower tail (p95 +2 s). Next steps: reduce escalations (keep earlier search options in
memory; better chart compare), skip the picker on obvious follow-ups, a 3-run consistency check, and an end-to-end
voice evaluation.
