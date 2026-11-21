from app.agent.workflows.spec import Workflow as W

M = "documents"
WORKFLOWS = [
    W("document_intake", M, "An uploaded receipt or bill to process: 'I uploaded a bill', 'claim this receipt', "
      "'document 12', 'maine bill upload kiya'. NOT for contracts (contract_review).",
      ("inspect_document", "find_reservations", "resolve_party", "list_budget_categories", "close_intake",
       "propose_submit_claim", "propose_submit_bill", "get_record"),
      ("Call inspect_document for the document id.",
       "If the breakdown does not add up, stop: say so and ask for the correct amount. If total-only, say you could "
       "not verify the breakdown.",
       "If there is a probable duplicate, read it (get_record) and resolve it first.",
       "If inspect_document says it is a contract, say it is a contract and stop (contract_review handles it).",
       "Ask who paid if not clear: an employee (reimbursement claim), the company already (matched payment or "
       "reconciliation via close_intake), or the vendor is still owed (vendor bill).",
       "Employee paid: resolve_party (kind employee); check find_reservations and if one matches ask whether this "
       "receipt is the final charge for it.",
       "Ask for the budget category if not obvious (list_budget_categories).",
       "Then call propose_submit_claim or propose_submit_bill, read its 'say' text and ask for confirmation. Stop."),
      required=("inspect_document",)),
    W("correct_document_field", M, "Correct a value read from the uploaded document: 'the amount is 4,500 not "
      "45,000', 'date is wrong, it is 3rd Nov', 'vendor is Indigo'.",
      ("correct_extracted_field", "inspect_document"),
      ("Call correct_extracted_field with the field and the user's value.", "Say the corrected value back.",
       "Continue the claim/bill steps if one was in progress (ask the next missing detail).")),
    W("reconcile_paid_receipt", M, "A receipt the company already paid: 'company ne pay kar diya', 'already "
      "paid by card', 'just record it, it's paid'.",
      ("inspect_document", "close_intake", "get_record"),
      ("If a company payment matches, say so and close_intake(matched_payment); if none matches say it needs "
       "reconciliation and close_intake(reconciliation).", "Never create a payable or a claim for it.")),
]
