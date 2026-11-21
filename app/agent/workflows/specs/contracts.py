from app.agent.workflows.spec import Workflow as W

M = "contracts"
_LEGAL = ("Always say this is an automated reading for Legal to confirm. Never give legal advice or call a contract "
          "safe or complete. Say dates the spoken way ('30 December 2026').")
WORKFLOWS = [
    W("contract_review", M, "Review a newly uploaded contract: 'review this contract', 'contract upload kiya', "
      "'what's in this agreement' (for an upload).",
      ("inspect_document", "review_contract", "propose_create_contract"),
      ("Call review_contract right after inspect_document.", "Speak in order: what it is and with whom; the flags "
       "that bind us (clause, risk, cap if stated); carve-outs from the cap; the next deadline. At most three flags; "
       "say how many more.", "We are the service provider: Supplier/Service Provider wording is us. If who bears a "
       "duty is unclear, say so.", "Offer to save it (propose_create_contract); the preview is the question.", _LEGAL),
      required=("review_contract",)),
    W("save_contract", M, "Save the reviewed contract: 'save it', 'haan contract save karo' after a review.",
      ("propose_create_contract",), ("Call propose_create_contract.", "Read its 'say' text and ask. Stop.")),
    W("contract_lookup", M, "Show or find saved contracts or a clause: 'open the Acme contract', 'Acme ke contract "
      "mein kya hai', 'find NDAs', 'show me the liability clause'.",
      ("get_contract", "search_contracts", "show_contract_clause"),
      ("One contract: get_contract (accepts a counterparty or title). Several: search_contracts. A clause: "
       "show_contract_clause.", _LEGAL)),
    W("liabilities", M, "Liabilities and open review flags: 'kaunse liabilities humpe hain', 'what are we liable "
      "for', 'open flags', 'kya review karna baaki hai'.",
      ("list_liabilities",),
      ("'On us / what are we liable for': list_liabilities bearer=us. 'Open flags': undecided_only=true.",
       "A cap is the stated maximum; a carve-out is uncapped. Never add up caps or estimate a loss.", _LEGAL)),
    W("contract_deadlines", M, "Renewals, expiry or notice dates: 'renewal kab hai', 'upcoming deadlines', "
      "'notice dates'.", ("contract_deadlines",),
      ("Call contract_deadlines (default 90 days).", "Say each date back with its contract.", _LEGAL)),
    W("contract_finding_decision", M, "Decide a contract review flag: 'accept that risk', 'reject flag 2, it binds "
      "only them', 'change the risk to low'.",
      ("list_liabilities", "show_contract_clause", "propose_review_contract_finding"),
      ("Accept = the risk stands; reject = false positive (e.g. the duty binds only the other side); modify = new "
       "risk level, corrected bearer or better explanation.", "Call propose_review_contract_finding; read 'say'; "
       "ask; stop.")),
    W("contract_edit", M, "Change a saved contract's details or status, or rescan it: 'expiry is 31 March', 'mark "
      "it terminated', 'rescan the Lotus contract'.",
      ("get_contract", "propose_contract_details", "propose_contract_status", "propose_rescan_contract"),
      ("Pick the matching propose_* tool for details, status or rescan.", "Read its 'say' text and ask. Stop.")),
]
