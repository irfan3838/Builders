from app.agent.workflows.spec import Workflow as W

M = "budget"
WORKFLOWS = [
    W("approve_claim_or_bill", M, "Approve or reject a submitted claim or vendor bill: 'approve C4', 'Neha ka claim "
      "approve karo', 'reject the BlueDart bill'. NOT for leave (leave_decision).",
      ("get_record", "get_attention_items", "propose_approval"),
      ("Find the claim/bill reference: from the user's words, else get_attention_items or get_record.",
       "If several fit, ask which one.", "Call propose_approval with the reference and decision.",
       "Read its 'say' text and ask for confirmation. Stop.")),
    W("settle_payment", M, "Record that a claim or vendor bill was paid outside Purser: 'B1 paid', 'Arjun ko "
      "reimburse kar diya', 'settle the claim'. NOT for customer money coming in (record_payment).",
      ("get_record", "get_attention_items", "propose_settlement"),
      ("Find the reference (user's words, get_attention_items or get_record).", "Call propose_settlement.",
       "Read its 'say' text and ask for confirmation. Never say money is being transferred. Stop.")),
    W("budget_status", M, "Budget position or remaining amount for a category or the year: 'travel mein kitna "
      "bacha', 'how much is left in Events', 'budget status'.",
      ("get_budget_month", "get_budget_status", "get_budget_year", "list_budget_categories"),
      ("'This month' or no period: get_budget_month for the category. Annual: get_budget_status. 'Month by month': "
       "get_budget_year.", "Keep remaining (exact rupees), status (underused / on track / overrun) and pacing "
       "apart; say which you mean.", "Speak the key numbers only, then one next-step offer.")),
    W("budget_alerts", M, "Budget warnings: 'koi alert', 'any budget warnings', 'what is over budget'.",
      ("get_budget_alerts",),
      ("Call get_budget_alerts.", "Name category, alert, spent vs budget and how far through the month.",
       "Offer the most useful fix (for example a top-up proposal).")),
    W("explain_budget_change", M, "Why a budget moved: 'kya badla', 'what changed in Travel', 'why is IT lower'.",
      ("explain_budget_change", "get_budget_history"),
      ("Call explain_budget_change for the category.", "Name the movements and receipts it returned.")),
    W("budget_history", M, "Who changed the budget and when: 'who changed the budget', 'budget history'.",
      ("get_budget_history",), ("Call get_budget_history.", "Speak the latest changes with who and when.")),
    W("budget_change", M, "Move, add or reduce budget money: 'Events se 5000 Travel mein daal do', 'top up "
      "Marketing by 20k', 'reduce IT by 10,000'.",
      ("propose_budget_change", "get_budget_month", "list_budget_categories"),
      ("transfer = from one category to another; top_up = new money; reduce = take back.",
       "Resolve months as YYYY-MM from today's date; ask for a reason if none was given. Pass amounts as plain digits "
       "of the number the user said ('5 hazaar' → '5000').",
       "Call propose_budget_change; if the tool refuses (past or closed month), say why.",
       "Read its 'say' text and ask for confirmation. Stop.")),
    W("close_month", M, "Close a budget month: 'close October', 'October band karo'.",
      ("propose_close_month", "get_budget_month"),
      ("Call propose_close_month straight away with any reasons and carry-over choices the user gave; map spoken "
       "reasons to the closest variance reason.", "Do not hold back for missing reasons; the preview lists them.",
       "Read its 'say' text and ask for confirmation. Stop.")),
    W("budget_recommendations", M, "Budget recommendations or applying them: 'recommendations', 'budget kahan "
      "badhana chahiye', 'apply the recommendations'.",
      ("get_budget_recommendations", "propose_apply_recommendations"),
      ("Always call get_budget_recommendations again.", "Explain the trend (which 3 closed months, average %) and "
       "the plan steps.", "Only if the user asks to apply: propose_apply_recommendations, read 'say', ask, stop.")),
    W("budget_forecast", M, "Forecast or what-if: 'kitna kharcha hoga', 'forecast Travel', 'agar marketing 20% "
      "badhe toh'.", ("forecast_budget", "what_if"),
      ("Forecast: forecast_budget. Scenario: what_if.", "Say that a forecast changes nothing; moving money needs a "
       "confirmed change.")),
]
