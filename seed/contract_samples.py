"""Synthetic agreements for the contracts module (seed, file generation, tests). Every one is fictional and labelled.

Our company is the workspace, "Purser Demo Traders Private Limited". Counterparties reuse seeded synthetic parties so
contracts link to their receivables / bills. `NDA_COPILOT_FIXTURE` is the copilot test NDA, word for word.
"""

LABEL = "SYNTHETIC TEST DOCUMENT - fictional parties, not a real agreement."

NDA_COPILOT_FIXTURE = """MUTUAL NON-DISCLOSURE AGREEMENT

This Agreement is made between Dzruptiv AI Private Limited and Acme Corp, effective 1 April 2026.

1. Confidential Information. Each party shall keep the other's Confidential Information secret.

2. Liability. The Supplier's liability shall not be limited in any way for any breach of this Agreement.

3. Indemnity. The Supplier shall indemnify and hold harmless the Client against any and all claims whatsoever.

4. Payment. Invoices are payable Net 30 from the date of invoice.

5. Governing Law. This Agreement is governed by the laws of India.
"""

SEEDED: dict[str, dict] = {
    "nda_acme": {
        "filename": "Acme Traders - Mutual NDA (SYNTHETIC).pdf",
        "text": f"""MUTUAL NON-DISCLOSURE AGREEMENT

{LABEL}

This Agreement is made between Purser Demo Traders Private Limited and Acme Traders Private Limited, effective 1 April 2026.

1. Confidential Information. Each party shall keep the other's Confidential Information secret.

2. Liability. The Supplier's liability shall not be limited in any way for any breach of this Agreement.

3. Indemnity. The Supplier shall indemnify and hold harmless the Client against any and all claims whatsoever.

4. Payment. Invoices are payable Net 30 from the date of invoice.

5. Governing Law. This Agreement is governed by the laws of India.
""",
    },
    "msa_lotus": {
        "filename": "Lotus Hospitality - MSA (SYNTHETIC).pdf",
        "text": f"""MASTER SERVICES AGREEMENT

{LABEL}

This Agreement is entered into on 1 March 2025 between Purser Demo Traders Private Limited (hereinafter referred to as the "Service Provider") and Lotus Hospitality Private Limited, a company incorporated in India (hereinafter referred to as the "Client").

1. Term. This Agreement shall remain in force for a period of twenty-four (24) months from the Effective Date and shall automatically renew for successive one year terms unless either party gives sixty (60) days' prior written notice of non-renewal.

2. Fees. The Client shall pay the fees in each invoice within 30 days of the date of invoice.

3. Limitation of Liability. The aggregate liability of the Service Provider under this Agreement shall not exceed Rs. 10,00,000 (Rupees Ten Lakhs only). The foregoing limitation shall not apply to breach of Clause 4 (Confidentiality) or to the Service Provider's indemnity obligations.

4. Confidentiality. The Service Provider shall keep the Client's Confidential Information secret. This obligation shall survive termination for a period of three (3) years.

5. Indemnity. The Service Provider shall indemnify the Client against all claims arising from loss of client data caused by the Service Provider.

6. Governing Law. This Agreement is governed by the laws of India.
""",
    },
    "nda_nimbus_oneway": {
        "filename": "Nimbus Retail - One-way NDA (SYNTHETIC).pdf",
        "text": f"""ONE-WAY NON-DISCLOSURE AGREEMENT

{LABEL}

This Agreement is made on 10 June 2026 between Nimbus Retail Private Limited (hereinafter referred to as the "Discloser") and Purser Demo Traders Private Limited (hereinafter referred to as the "Recipient").

1. Purpose. The Discloser will share store sales data with the Recipient to evaluate a reporting project.

2. Confidentiality. The Recipient shall hold the Confidential Information in strict confidence and use it only for the Purpose.

3. Indemnity. The Recipient shall hold harmless the Discloser from any loss arising from unauthorised disclosure by the Recipient.

4. Term. This Agreement shall remain in force for a period of one (1) year from the date above.

5. Governing Law. This Agreement is governed by the laws of India.
""",
    },
    "vendor_ganesh": {
        "filename": "Shree Ganesh Printers - Supply Agreement (SYNTHETIC).pdf",
        "text": f"""PRINTING SUPPLY AGREEMENT

{LABEL}

This Agreement is entered into on 20 December 2025 between Shree Ganesh Printers (hereinafter referred to as the "Supplier") and Purser Demo Traders Private Limited (hereinafter referred to as the "Customer").

1. Term. This Agreement shall remain in force for a period of twelve (12) months and shall automatically renew for a further twelve months unless the Customer gives fifteen (15) days' prior written notice.

2. Termination. The Supplier may terminate this Agreement at any time for convenience by giving notice to the Customer.

3. Payment Terms. The Customer shall pay each invoice within 15 days of receipt.

4. Limitation of Liability. The aggregate liability of the Supplier shall not exceed INR 2,00,000.

5. Governing Law. This Agreement is governed by the laws of India.
""",
    },
}

# Not seeded: the fresh file for the live demo (drag it in and ask Purser to review it).
LIVE_DEMO = {
    "filename": "Northwind Labs - MSA (SYNTHETIC).pdf",
    "text": f"""MASTER SERVICES AGREEMENT

{LABEL}

This Agreement is entered into on 1 December 2026 between Purser Demo Traders Private Limited (hereinafter referred to as the "Service Provider") and Northwind Labs Inc, a company incorporated in Delaware (hereinafter referred to as the "Client").

1. Term. This Agreement shall remain in force for a period of thirty-six (36) months from the Effective Date.

2. Fees and Payment Terms. Invoices are payable Net 45 from the date of invoice.

3. Limitation of Liability. The aggregate liability of the Service Provider shall not exceed the fees paid by the Client in the twelve (12) months preceding the claim. This limitation shall not apply to a data breach caused by the Service Provider or to breach of confidentiality.

4. Data Protection. The Service Provider shall be liable for any loss of client data arising from its systems.

5. Intellectual Property. The Service Provider hereby assigns all right, title and interest in the intellectual property in the deliverables to the Client.

6. Indemnity. The Service Provider shall indemnify, defend and hold harmless the Client against any and all claims arising from the services.

7. Termination. The Client may terminate this Agreement at any time without cause on thirty (30) days' notice.

8. Confidentiality. Each party shall keep the other's Confidential Information confidential. These obligations shall survive for a period of two (2) years after termination.

9. Governing Law. This Agreement is governed by the laws of India.
""",
}
