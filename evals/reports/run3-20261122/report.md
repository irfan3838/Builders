# Purser eval report: run3-20261122

Arms: A0 today (gpt-5.4-mini) · A1 pure agent on gpt-6-luna · B workflows (luna + gpt-6-sol escalation) · A2 pure agent on gpt-6-sol.

## Headline

| Arm | Task success | Turn pass | Wrong writes | pass^k | $ / successful task | $ total | Input tok / turn | LLM calls / turn | 0-LLM turns | Escalated turns | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A0 | 40/45 (89%) | 94% | 0 | 89% | $0.0104 | $0.4147 | 36195 | 2.35 | 0% | 0% | 7654 | 14361 |
| A1 | 42/45 (93%) | 95% | 0 | 93% | $0.0025 | $0.1044 | 39709 | 2.51 | 0% | 0% | 9451 | 15104 |
| B | 44/45 (98%) | 99% | 0 | 98% | $0.0017 | $0.0762 | 6875 | 2.97 | 20% | 1% | 8738 | 19843 |

## By tier (task success)

| Arm | Tier 1 | Tier 2 | Tier 3 | Tier 4 |
|---|---|---|---|---|
| A0 | 17/17 | 9/12 | 8/10 | 6/6 |
| A1 | 17/17 | 11/12 | 8/10 | 6/6 |
| B | 16/17 | 12/12 | 10/10 | 6/6 |

## Context growth (input tokens per turn, run 1, chained scenarios)

- **t2_briefing_to_payment_to_reminder**
  - A0: 50035 → 51775 → 53700 → 55090 → 18589
  - A1: 33241 → 51768 → 53975 → 36935 → 57066
  - B: 5225 → 8360 → 9181 → 0 → 7140
- **t2_budget_transfer**
  - A0: 33408 → 33963 → 34593
  - A1: 33367 → 33975 → 51902
  - B: 6108 → 0 → 6073
- **t2_ceo_briefing**
  - A0: 36278 → 56099 → 47673
  - A1: 36319 → 37953 → 43232
  - B: 5060 → 17631 → 7459
- **t2_chart_refine**
  - A0: 33305 → 33806 → 34925 → 35859 → 36979
  - A1: 55874 → 60236 → 83612 → 65554 → 139443
  - B: 17107 → 8778 → 26579 → 15201 → 67713
- **t2_leave_request_flow**
  - A0: 24279 → 24593 → 24879
  - A1: 24266 → 24753 → 25037
  - B: 4548 → 0 → 4507
- **t2_lotus_balance_and_reminder_done**
  - A0: 50728 → 34571 → 35445
  - A1: 50524 → 34608 → 54172
  - B: 8327 → 0 → 9740
- **t2_manager_approves_leave**
  - A0: 69068 → 35977 → 36338
  - A1: 50551 → 34387 → 34768
  - B: 6084 → 7802 → 0
- **t2_meeting_with_correction**
  - A0: 36534 → 37720 → 25645
  - A1: 36424 → 37634 → 25671
  - B: 6376 → 6909 → 0
- **t2_part_payment_then_move_balance**
  - A0: 50832 → 34711 → 35511 → 36486
  - A1: 67365 → 34869 → 35644 → 36620
  - B: 8382 → 0 → 8985 → 0
- **t2_tasks_chain**
  - A0: 36519 → 24856 → 25159
  - A1: 36598 → 25071 → 25427
  - B: 6457 → 6694 → 4871
- **t2_team_announcement**
  - A0: 33426 → 33975
  - A1: 33364 → 33848
  - B: 5771 → 0
- **t2_trip_flight_and_hotel**
  - A0: 24263 → 38412 → 40734 → 28115 → 28984
  - A1: 24239 → 25392 → 27178 → 28558 → 29528
  - B: 4823 → 5465 → 9719 → 14626 → 0

## Failures (run 1)

- A0 `t2_briefing_to_payment_to_reminder` t5 "aur October wale ke liye Friday ko reminder daal do": tools_any ['add_reminder'] (called []); reply_any ['Friday', '27']; db reminders +0 (want +1)
- A0 `t2_lotus_balance_and_reminder_done` t3 "Lotus wala reminder bhi complete kar do": tools_any ['complete_reminder'] (called ['get_attention_items'])
- A0 `t2_chart_refine` t4 "sirf Marketing aur Travel dikhao": cards_any ['chart'] (got [])
- A0 `t3_split_payment_two_invoices` t1 "Acme Traders ne 1,63,000 bheja hai, October aur November don": reply_any ['1,25,000', '38,000', 'October', 'November']
- A0 `t3_hotel_receipt_claim` t3 "Travel category, submit it": tools_any ['propose_submit_claim'] (called ['confirm_pending_proposal'])
- A1 `t2_team_announcement` t1 "Sales team ko message bhejo ki offsite 5 December ko hai, Lo": reply_any ['Lonavala']
- A1 `t3_ambiguous_client` t2 "Tradelinks wala": tools_any ['propose_payment'] (called ['ask_choice', 'list_client_invoices'])
- A1 `t3_ambiguous_client` t3 "haan": tools_any ['confirm_pending_proposal'] (called ['propose_payment']); db receipts +0 (want +1); db invoice_payments +0 (want +1)
- A1 `t3_hotel_receipt_claim` t3 "Travel category, submit it": tools_any ['propose_submit_claim'] (called ['confirm_pending_proposal'])
- B `t1_whats_pending` t1 "kya pending hai aaj": reply_any ['Lotus', 'invoice', 'reminder', 'leave', 'claim', 'approv']

## Escalations in B (backlog for new specs)

- `t2_chart_refine` t5 "compare with last quarter": checklist failed: no required tool succeeded (outcomes: ['VALIDATION'])
