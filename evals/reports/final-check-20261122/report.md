# Purser eval report: final-check-20261122

Arms: A0 today (gpt-5.4-mini) · A1 pure agent on gpt-6-luna · B workflows (luna + gpt-6-sol escalation) · A2 pure agent on gpt-6-sol.

## Headline

| Arm | Task success | Turn pass | Wrong writes | pass^k | $ / successful task | $ total | Input tok / turn | LLM calls / turn | 0-LLM turns | Escalated turns | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B | 46/46 (100%) | 100% | 0 | 100% | $0.0023 | $0.1071 | 6886 | 2.89 | 20% | 2% | 8127 | 16246 |

## By tier (task success)

| Arm | Tier 1 | Tier 2 | Tier 3 | Tier 4 |
|---|---|---|---|---|
| B | 17/17 | 12/12 | 10/10 | 7/7 |

## Context growth (input tokens per turn, run 1, chained scenarios)

- **t2_briefing_to_payment_to_reminder**
  - B: 5302 → 6181 → 9361 → 0 → 7210
- **t2_budget_transfer**
  - B: 6174 → 0 → 6290
- **t2_ceo_briefing**
  - B: 5013 → 10394 → 7370
- **t2_chart_refine**
  - B: 17215 → 8800 → 16025 → 10972 → 78222
- **t2_leave_request_flow**
  - B: 4550 → 0 → 4528
- **t2_lotus_balance_and_reminder_done**
  - B: 8440 → 0 → 9862
- **t2_manager_approves_leave**
  - B: 6160 → 7975 → 0
- **t2_meeting_with_correction**
  - B: 6426 → 6989 → 0
- **t2_part_payment_then_move_balance**
  - B: 8497 → 0 → 9031 → 0
- **t2_tasks_chain**
  - B: 4570 → 6730 → 4962
- **t2_team_announcement**
  - B: 5870 → 0
- **t2_trip_flight_and_hotel**
  - B: 4862 → 5556 → 6675 → 39866 → 0

## Failures (run 1)


## Escalations in B (backlog for new specs)

- `t2_chart_refine` t5 "compare with last quarter": checklist failed: no required tool succeeded (outcomes: ['VALIDATION'])
- `t2_trip_flight_and_hotel` t4 "dono mein sabse sasta wala book karo": workflow declined: I can’t access the earlier flight and hotel option IDs needed to propose the cheapest booking.
