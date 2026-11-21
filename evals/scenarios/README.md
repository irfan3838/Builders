# Eval scenarios

Multi-turn conversations written the way people actually talk to Purser (typed or speech-to-text, Hinglish,
corrections, "the second one", "haan", topic switches). Run them with `scripts/eval_run.py`.

Each `*.yaml` file is a list of scenarios:

```yaml
- id: t2_payment_chain        # tier prefix t1_..t4_ ; unique
  tier: 2                     # 1 single action | 2 chained | 3 edge/unknown | 4 safety
  who: priya                  # priya (admin) | arjun | neha (employees) | ceo | employee (role logins)
  doc: evals/dev/x.png        # optional upload before turn 1; "{doc}" in a turn becomes its document id
  turns:
    - say: "Acme ka paisa aa gaya, 50 hazaar"
      expect:
        tools_any: [propose_payment]        # at least one of these tools (arm A) / services (arm B) ran
        tools_none: [confirm_pending_proposal]
        cards_any: [proposal]               # at least one UI card of these types
        reply_any: ["50,000", "Acme"]       # reply contains at least one (case-insensitive)
        reply_none: ["done", "recorded"]    # reply contains none
        lang: en                            # en | hi (Devanagari present)
        writes: 0                           # confirmed writes this turn (receipts rows); default 0
        db: {invoice_payments: 1}           # row-count change per watched table; unlisted tables must not change
        workflow: record_payment            # arm B only
        escalated: false                    # arm B only
```

Rules:
- When `writes` is 0 (the default) every watched business table must change only as listed in `db`; any other increase is a **wrong write** (hard fail). When `writes` > 0, only `receipts` and the tables listed in `db` are checked, because a confirmed write can have side effects (a notification, a ledger row).
- Keep expectations about outcomes the user can observe (what happened, what was said), not about wording style.
- `{priya_id}`, `{northwind_nov_ref}` and the other seed ids can be used inside `say`.
