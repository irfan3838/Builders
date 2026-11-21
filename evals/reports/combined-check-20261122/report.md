# Purser eval report: combined-check-20261122

Arms: A0 today (gpt-5.4-mini) · A1 pure agent on gpt-6-luna · B workflows (luna + gpt-6-sol escalation) · A2 pure agent on gpt-6-sol.

## Headline

| Arm | Task success | Turn pass | Wrong writes | pass^k | $ / successful task | $ total | Input tok / turn | LLM calls / turn | 0-LLM turns | Escalated turns | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B | 46/46 (100%) | 100% | 0 | 100% | $0.0012 | $0.0543 | 5993 | 2.79 | 20% | 1% | 8018 | 15512 |

## By tier (task success)

| Arm | Tier 1 | Tier 2 | Tier 3 | Tier 4 |
|---|---|---|---|---|
| B | 17/17 | 12/12 | 10/10 | 7/7 |

## Context growth (input tokens per turn, run 1, chained scenarios)

- **t2_briefing_to_payment_to_reminder**
  - B: 5397 → 6092 → 9361 → 0 → 9954
- **t2_budget_transfer**
  - B: 6258 → 0 → 6234
- **t2_ceo_briefing**
  - B: 5098 → 10583 → 7502
- **t2_chart_refine**
  - B: 17300 → 8614 → 8703 → 15808 → 10680
- **t2_leave_request_flow**
  - B: 6401 → 0 → 4502
- **t2_lotus_balance_and_reminder_done**
  - B: 8528 → 0 → 9935
- **t2_manager_approves_leave**
  - B: 6245 → 8003 → 0
- **t2_meeting_with_correction**
  - B: 6505 → 7063 → 0
- **t2_part_payment_then_move_balance**
  - B: 8580 → 0 → 9173 → 0
- **t2_tasks_chain**
  - B: 4655 → 6803 → 4948
- **t2_team_announcement**
  - B: 5944 → 0
- **t2_trip_flight_and_hotel**
  - B: 4942 → 5681 → 9875 → 17920 → 0

## Failures (run 1)


## Escalations in B (backlog for new specs)

- `t3_out_of_scope` t1 "can you file our GST return for October": workflow declined: Purser cannot file GST returns.
