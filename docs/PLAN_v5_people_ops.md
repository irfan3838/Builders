# Munshi — scope addendum v5: people operations (2026-11-21, ~13:00 IST)

**Decision (user):** Munshi becomes the single copilot for finance *and* HR/admin/employees. The user accepted the risk to the AWS deploy and the evaluation time.
**Channels (user):** built-in team inbox, plus real email through the user's Gmail (SMTP app password). Real email goes only to an allow-list of demo recipients (`EMAIL_ALLOWED_RECIPIENTS`). Other recipients get the inbox copy and an explicit "email skipped (not on demo allow-list)" status.

## Added capabilities (same agent, same propose → confirm → receipt engine)
| Capability | Weekend acceptance |
|---|---|
| Onboard an employee | "Add Neha Kapoor as Sales executive from 1 Dec, reporting to Priya." The preview shows login, department, manager, leave balances and an onboarding checklist. Confirm creates all of it in one transaction and queues a welcome message (inbox and allow-listed email). |
| Leave | An employee asks by voice ("kal aur parson casual leave"). The preview shows days, type and the balance after. Confirm submits it. The manager or admin approves through the same approval flow. Balances come from an append-only leave ledger (granted / reserved / used). Self-approval is barred. |
| Announcements and messages | "Send an announcement to Sales: office closed Friday." The agent drafts. The preview shows the exact text, the recipients and the channels. Confirm queues delivery. Each message has a delivery status (queued / sent / skipped / failed) and a provider id. |
| Inbox | "Koi naya message?" reads unread inbox items. Employees hear their leave decisions and announcements. |
| HR policy answers | Leave, reimbursement and working-hours questions are answered from a seeded synthetic policy document with a citation. The agent never invents policy. |

## Rules
- Every send is an external side effect, so it gets a preview, an explicit confirmation and a receipt. Sends go through a transactional outbox and are delivered after commit. A retried confirmation never re-sends.
- Roles: `admin` (finance + HR; Priya), `employee` (Arjun), and managers via `reports_to`. An employee only sees their own leave, inbox and claims.
- Out of scope this weekend: payroll runs, attendance, performance reviews, document e-signing. These are on the roadmap.
