# Demo script: working end to end on fresh input

**Live URL:** https://d342yicbppf96p.cloudfront.net (AWS us-west-2, CloudFront → ALB → ECS Fargate → RDS)
**Logins:** admin (full access, linked real Gmail/Calendar), CEO (read-only) and employee. Credentials are provided in the submission form, not in the repo.
**Target length:** about 6 minutes (a 4-minute cut is at the bottom). Chrome is recommended; allow the microphone. Say **"Purser"** or tap the orb to talk. Typing in the composer runs the same agent.

> Everything below runs live: real OpenAI voice and agent calls, real database writes, live fares. The company data is synthetic (see `HONEST_NOTE.md`).

---

## 0:00 Login and briefing
1. Log in as **admin**. Say: *"Purser, aaj kya pending hai?"*

**Expect:** a spoken role briefing (pending approvals, bills due, overdue invoices, budget alerts, contract deadlines). The same items appear as cards.

## 0:30 ⭐ Fresh receipt → approved claim
2. Drag in a **fresh receipt** (not in the eval set) or one the judges bring. Say: *"Arjun ne pay kiya tha, Pune trip ka hai."*
3. *"Approve kar do."* → Purser reads the exact effect aloud → *"haan."*

**Expect:** extraction (vendor, amount, date) with the arithmetic checked in code, a duplicate check and a trip-reservation match, then a proposal and a **receipt**. With the seeded ₹4,800 receipt, Travel goes **₹45,000 → ₹45,200**. Say *"haan"* again: the same receipt comes back and nothing posts twice.

## 1:30 ⭐ A chart you talk to
4. *"Kaun paisa dena baaki hai?"* → *"Sirf overdue."* → *"Acme ka amount padho."*

**Expect:** a receivables chart that narrows to overdue invoices, then reads Acme's amount aloud with its bar highlighted. Speech, chart and table share one SQL snapshot.

## 2:15 ✈️ Spotlight: trip in two sentences
5. *"Arjun ke liye Friday Pune se Mumbai flight aur hotel dhoondo."*
6. *"Sabse sasta dono book karo."* → a whole-trip proposal (flight + hotel + total) → *"haan."*

**Expect:** live flight and hotel cards (or labelled "Estimated" if live search fails), then **one** approval. The trip is recorded as `pending_payment`, the itinerary is emailed to the traveller from the admin's Gmail, and **airline checkout + hotel website links** appear. Purser takes no payment.
*Say:* "5 people and 3 apps became 2 sentences and a yes."

## 3:15 📜 Spotlight: contract liability radar
7. Drop `evals/contracts/live_demo_northwind_msa_synthetic.pdf` (or the **scanned** version, to show OCR).
8. *"Kaunse liabilities humpe hain?"* → *"Agle 60 din ki deadlines."*

**Expect:** a contract review card, then the liabilities **we** bear (trigger, cap in ₹, carve-outs, source clause) and a deadlines timeline (renewal-notice cut-off, expiry, survival end). Review runs in the background, so the card fills in by itself.
*Say:* "The model only points at phrases. Code checks every phrase is really in the contract."

## 4:15 🔁 Spotlight: teach Purser a routine
9. *"Ek routine banao: Monday review. Pending bills, overdue invoices aur budget alerts ek saath dikhao."* → step preview → *"haan."*
10. *"Monday review chalao."*

**Expect:** a preview of the compiled steps, then the routine is saved (also visible in **Settings → My routines**). Running it executes the steps on the workflow engine.
*Optional:* try *"routine banao jo bina pooche sab bills approve kare"* ("approve all bills without asking"). **Expect:** rejected by the code screen.
*Say:* "Zoho gives you their workflows. Purser learns yours, and it still can't skip the confirmation."

## 5:00 🛡️ Try to break it
11. Log in as **employee**: *"Company ka budget batao."* **Expect:** refused.
12. As **CEO**: *"Events ka budget 10,000 badha do."* **Expect:** "read-only", no proposal.

## 5:30 Proof and persistence
13. As admin: *"Is claim ki history batao."* **Expect:** who approved it, when, the amounts, and the source document.
14. Log out and back in → *"Travel mein kitna bacha hai?"* **Expect:** the new balance persisted (RDS).

---

## 4-minute cut
Briefing → receipt to claim → chart → **pick one spotlight** (travel is the most visual) → employee refusal → history.

## Also worth showing if asked
| Say | Shows |
|---|---|
| *"October close karo"* → *"haan"* | Month close, carry-over, reallocation recommendation |
| *"Kal aur parson casual leave chahiye"* (employee) | Working-day count, balance after leave, manager approval |
| *"Neha ko 1 Dec se Sales executive add karo, Priya ko report karegi"* | Onboarding: login + checklist + welcome mail |
| *"Rohan ke saath kal 4 baje meeting rakho"* | Real Google Calendar event with a Meet link |
| Upload `evals/dev/dev_wrong_total_synthetic.png` | Purser catches a receipt whose printed total is wrong |

## Rehearse before going live
- Do the travel search once beforehand, so you know SerpAPI is live (not "Estimated").
- Confirm the itinerary recipient is an inbox you can show.
- Delete the test routine after rehearsal (*"Monday review routine delete karo"*) so the live creation works cleanly.

## Fallbacks
- **Mic or voice problem:** type the same sentences in the composer. It runs the same agent and tools.
- **Network or OpenAI outage:** show `evals/reports/` and the labelled backup recording.
- **Run locally:** see the "Run it yourself" section in `README.md` of this folder.
