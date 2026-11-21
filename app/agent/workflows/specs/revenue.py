from app.agent.workflows.spec import Workflow as W

M = "revenue"
_FIND = ("Find the invoice's S… reference yourself with list_client_invoices (client + month). Never ask the user "
         "for an S… reference and never guess one; if the client name matches several clients or two invoices fit, "
         "ask which one (name them by client or month).")
_PROPOSE = ("Amounts and rates go to tools as plain digits of the number the user said ('50 hazaar' → '50000'). "
            "Read the proposal's 'say' text and ask for confirmation. Stop.")
WORKFLOWS = [
    W("revenue_overview", M, "How revenue is doing as a figure: 'revenue kaisa hai', 'kitna aaya', 'kitna baaki "
      "hai', 'how much is unpaid'. NOT for a chart or list.",
      ("get_revenue_overview",),
      ("Call get_revenue_overview (period or client if said).", "Five figures, never mixed: projected, received, "
       "outstanding, overdue, to raise. Say which you mean.")),
    W("list_invoices", M, "List or show client invoices: 'kis ka overdue hai', 'Acme ke invoices', 'show invoice "
      "S5', 'Northwind client details'.",
      ("list_client_invoices", "get_invoice", "get_client"),
      ("Lists: list_client_invoices (client / status if said). One invoice: get_invoice. A client: get_client.",
       "Speak at most three rows plus the total.")),
    W("revenue_todo", M, "What to do in revenue: 'revenue mein kya pending hai', 'what should I chase', 'invoices "
      "to raise'.", ("get_revenue_suggestions",),
      ("Call get_revenue_suggestions.", "Speak at most three, then offer the first one as the next action.")),
    W("record_payment", M, "Customer money came in for an invoice: 'paisa aa gaya', 'payment mila', '₹50,000 "
      "aaye', 'Acme ne bheja'. NOT for money we pay out (settle_payment).",
      ("list_client_invoices", "propose_payment"),
      (_FIND, "Call propose_payment with the S… ref. Pass the amount the user said as plain digits ('38 hazaar' → "
       "'38000', '2,01,000' → '201000'); omit it for 'pura aa gaya' and whenever the user gave no amount (that means paid in full: do not ask 'full or partial?'). If the user says it is partial ('baaki baad mein'), settled=false.",
       "If the money covers several invoices, propose them together (several refs) when the tool allows, else "
       "propose the first and say the next one follows after confirmation.", _PROPOSE)),
    W("move_balance", M, "What to do with an invoice balance after a part payment: 'baaki December mein daal do', "
      "'raise a new invoice for the balance', 'carry it to next month'.",
      ("list_client_invoices", "propose_balance_move"),
      (_FIND, "Leave it outstanding (nothing to do), new balance invoice (to=new with a date), or carry onto another "
       "month's invoice (to=month).", "Call propose_balance_move.", _PROPOSE)),
    W("new_invoices", M, "Create client invoices: 'Acme ka November ₹38,000', 'December se March tak ₹50,000 har "
      "mahine', 'new client invoice'.",
      ("propose_invoices", "get_client", "list_client_invoices"),
      ("Ask for the amount if not said. 'December se March' = months=[December], until=March.",
       "If the client is unknown, ask whether it is a new client before new_client=true.",
       "Call propose_invoices.", _PROPOSE)),
    W("invoice_status", M, "Mark an invoice sent or back to to-raise: 'bhej diya', 'invoice sent', 'raise kar "
      "diya', 'galti se sent kiya'.",
      ("list_client_invoices", "propose_invoice_status"),
      (_FIND, "'Sent / bhej diya / raise kar do' = sent; 'galti se sent' = to_raise.", "Call propose_invoice_status.",
       _PROPOSE)),
    W("invoice_change", M, "Change an invoice amount/date/notes or refresh its FX rate: 'November invoice 45k kar "
      "do', 'rate refresh karo', 'due date change'.",
      ("list_client_invoices", "propose_invoice_change"),
      (_FIND, "Call propose_invoice_change (refresh_rate for 'rate refresh').", _PROPOSE)),
    W("fx_rates", M, "Currency rates: 'dollar rate kya hai', 'show FX rates', 'November ka dollar rate 84.20 "
      "rakho'.", ("get_fx_rates", "propose_fx_month_rate"),
      ("Reading: get_fx_rates; say rates as '₹84.20 per dollar'.", "Setting a month's rate: propose_fx_month_rate "
       "with the user's exact number, then read 'say' and ask. If a rate is unavailable, ask the user for it.")),
    W("billing_cycle", M, "Recurring billing or planning next year: '₹30,000 quarterly in advance from December', "
      "'monthly retainer', 'plan next FY'.",
      ("propose_billing_cycle", "get_client"),
      ("'₹30,000 quarterly in advance from December' = amount 30000, amount_is_per_period=true, period_months=3, "
       "timing advance. Planning next year: action plan_fy.", "Call propose_billing_cycle.", _PROPOSE)),
    W("client_change", M, "Pause, resume, rename or delete a client: 'pause Orbit', 'resume Kaveri', 'rename the "
      "client'.", ("propose_client_change", "get_client"),
      ("Call propose_client_change.", _PROPOSE)),
    W("end_project", M, "A client project is over: 'Helix ka project khatam', 'end the Zenith project'.",
      ("propose_end_project", "list_client_invoices"),
      ("Ask how to handle pending invoices if not said: raise each, combine into one, write off from a month, or "
       "just end.", "Call propose_end_project.", _PROPOSE)),
    W("reminders", M, "Revenue reminders and check-ins: 'Friday ko reminder daal do', 'remind me to chase Acme', "
      "'reminder done', 'not paid yet'.",
      ("add_reminder", "complete_reminder", "mark_not_yet", "list_client_invoices", "get_attention_items",
       "get_revenue_suggestions"),
      ("New: add_reminder; it resolves 'Friday / kal / 5 tareekh' from today; say the date back.",
       "Done: complete_reminder; find the reminder id with get_revenue_suggestions (reminders are listed there) or "
       "get_attention_items.",
       "'Not yet / abhi nahi aaya' check-in: mark_not_yet.", "These are saved directly, no confirmation.")),
]
