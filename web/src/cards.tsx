// Generic card canvas. The agent chooses which cards appear; every card loads its facts from the server
// by reference (proposal id, receipt id, document id, budget line, record ref), never from model text.
import { useEffect, useState } from "react";
import { api, Card } from "./api";
import { ChartCard, ViewCard } from "./ChartCard";
import { ContractCard, ContractClauseCard, ContractDeadlinesCard, ContractReviewCard, LiabilitiesCard } from "./ContractCard";
import { FxRatesCard, InvoiceCard, RevenueCard } from "./RevenueCard";
import { MailListCard, MailThreadCard, MeetingsCard, TasksCard, TicketsCard } from "./MailCards";
import { FlightOptionsCard, HotelOptionsCard, PaymentCard } from "./FlightCard";

function useLoad<T>(path: string | null, bump = 0) {
  const [data, setData] = useState<T | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    if (!path) return;
    let live = true;
    api.get<T>(path).then((d) => live && setData(d)).catch((e) => live && setErr(e.message));
    return () => { live = false; };
  }, [path, bump]);
  return { data, err };
}

const Failed = ({ what, err }: { what: string; err: string }) => (
  <section className="card"><p className="error">Could not load {what}: {err}</p></section>
);
const Loading = ({ what }: { what: string }) => <section className="card" aria-busy="true"><p className="hint">Loading {what}…</p></section>;

const STATE_LABEL: Record<string, string> = {
  open: "Awaiting your confirmation", executed: "Done", stale: "Out of date", superseded: "Replaced", expired: "Expired", cancelled: "Cancelled",
};

function ProposalCard({ id, bump, onChanged }: { id: string; bump: number; onChanged: () => void }) {
  const { data, err } = useLoad<any>(`/api/proposals/${id}`, bump);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  if (err) return <Failed what="proposal" err={err} />;
  if (!data) return <Loading what="proposal" />;
  const open = data.status === "open";
  const act = async (verb: "confirm" | "cancel") => {
    setBusy(true); setMsg(null);
    try {
      const r = await api.post<any>(`/api/proposals/${id}/${verb}`);
      if (r.status === "stale" || r.status === "expired") setMsg("Records changed since this preview. Nothing was executed; a fresh preview was prepared.");
      else if (r.receipt) setMsg(`${r.receipt.ref}: ${r.receipt.summary}`);
      onChanged();
    } catch (e: any) { setMsg(e.message); } finally { setBusy(false); }
  };
  const cls = data.status === "executed" ? "done" : open ? "" : "closed";
  return (
    <section className={`card proposal ${cls}`} aria-labelledby={`p-${id}`}>
      <div className="card-head">
        <span className="kind">Proposal</span>
        <h2 id={`p-${id}`}>{data.preview.title}</h2>
        <span className={`state state-${data.status}`}>{STATE_LABEL[data.status] ?? data.status}</span>
      </div>
      <ul className="effects">{data.preview.lines.map((l: string, i: number) => <li key={i} className="num">{l}</li>)}</ul>
      {open && (
        <div className="actions">
          <button className="btn btn-ok" disabled={busy} onClick={() => act("confirm")}>Confirm</button>
          <button className="btn" disabled={busy} onClick={() => act("cancel")}>Cancel</button>
          <span className="hint">or say “yes” / “approve” after Purser reads it out</span>
        </div>
      )}
      {msg && <p className="hint" role="status">{msg}</p>}
    </section>
  );
}

const VIA: Record<string, string> = {
  "voice:live_sideband": "Confirmed by voice (heard by the server)", "voice:realtime_sideband": "Confirmed by voice (heard by the server)",
  "voice:ptt_server": "Confirmed by push-to-talk", "voice:text": "Confirmed by typed reply", button: "Confirmed with the Confirm button",
};

function ReceiptCard({ id, bump }: { id: number; bump: number }) {
  const { data, err } = useLoad<any>(`/api/receipts/${id}`, bump);
  if (err) return <Failed what="receipt" err={err} />;
  if (!data) return <Loading what="receipt" />;
  const budget = (data.effects || []).find((e: any) => e.type === "budget");
  return (
    <section className="card receipt">
      <div className="card-head"><span className="kind">Receipt</span><h2>{data.preview?.title ?? "Executed"}</h2><span className="ref">{data.ref}</span></div>
      <p className="receipt-summary num">{data.summary}</p>
      {budget && <p className="num">{budget.category} available: {fmt(budget.before.available_paise)} → <strong>{fmt(budget.after.available_paise)}</strong></p>}
      <Deliveries receiptId={id} bump={bump} />
      <p className="hint">{VIA[data.confirmed_via] ?? data.confirmed_via} · {new Date(data.created_at).toLocaleTimeString("en-IN")}</p>
    </section>
  );
}

function SourceCard({ id, highlight, bump }: { id: number; highlight: string[]; bump: number }) {
  const { data, err } = useLoad<any>(`/api/documents/${id}`, bump);
  if (err) return <Failed what="document" err={err} />;
  if (!data) return <Loading what="document" />;
  const ex = data.extraction;
  const hl = (k: string) => highlight.includes(k === "total" ? "total_paise" : k);
  const row = (label: string, key: string) => ex?.fields?.[key] ? (
    <><dt>{label}</dt><dd className={`num ${hl(key) ? "field-hl" : ""}`}>{ex.fields[key]}</dd></>
  ) : null;
  const corrected = (ex?.corrections || []).map((c: any) => c.field);
  return (
    <section className="card">
      <div className="card-head"><span className="kind">Source</span><h2>{data.filename}</h2><span className="ref">D{data.id}</span></div>
      <div className="source">
        <img src={`/api/documents/${id}/pages/1`} alt={`Page 1 of ${data.filename}`} loading="lazy" />
        <div>
          {ex ? (
            <>
              <dl className="kv">
                <dt>Type</dt><dd>{ex.doc_type.replace("_", " ")}</dd>
                {row("Vendor", "vendor")}{row("Date", "date")}{row("Total", "total")}{row("Invoice", "invoice_no")}
                {row("Guest / customer", "customer_or_guest")}{row("Due", "due_date")}{row("Payment", "payment_status")}
              </dl>
              {ex.arithmetic === "mismatch" && <p className="flag flag-danger num">Breakdown adds to {ex.fields.breakdown_sum}, not the printed total.</p>}
              {ex.arithmetic === "unverifiable" && <p className="flag flag-warn">Could not verify the breakdown (total only).</p>}
              {ex.arithmetic === "ok" && <p className="flag flag-ok">Breakdown adds up to the total.</p>}
              {corrected.length > 0 && <p className="hint">Corrected by you: {corrected.join(", ")}</p>}
            </>
          ) : <p className="hint">Not read yet.</p>}
          {data.outcome && <p className="hint">Intake outcome: <strong>{data.outcome.replaceAll("_", " ")}</strong>{data.record?.record_ref ? ` · ${data.record.record_ref}` : ""}</p>}
        </div>
      </div>
    </section>
  );
}

const fmt = (paise: number) => "₹" + new Intl.NumberFormat("en-IN").format(Math.round(paise / 100));

function BudgetCard({ lineId, showLedger, bump }: { lineId: number; showLedger: boolean; bump: number }) {
  const { data, err } = useLoad<any>(`/api/budget/lines/${lineId}`, bump);
  if (err) return <Failed what="budget" err={err} />;
  if (!data) return <Loading what="budget" />;
  const p = data.position;
  const b = (k: string, label: string, extra = "") => (
    <div className={`bucket ${extra}`}><div className="label">{label}</div><div className="amount num">{p[k].inr}</div></div>
  );
  return (
    <section className="card">
      <div className="card-head"><span className="kind">Budget</span><h2>{data.category}</h2><span className="ref">{data.department} · {data.fy}</span></div>
      <div className="buckets">
        {b("allocated_paise", "Allocated")}{b("reserved_paise", "Reserved")}{b("committed_paise", "Committed")}{b("spent_paise", "Spent")}{b("available_paise", "Available", "available")}
      </div>
      {p.pending_claims_paise.paise > 0 && <p className="hint num">Pending claims not yet in budget: {p.pending_claims_paise.inr}</p>}
      <MonthStrip lineId={lineId} bump={bump} />
      {showLedger && (
        <table className="ledger" aria-label={`${data.category} ledger movements`}>
          <thead><tr><th>Movement</th><th>Bucket</th><th>Receipt</th><th style={{ textAlign: "right" }}>Amount</th></tr></thead>
          <tbody>
            {data.movements.map((m: any) => (
              <tr key={m.id}><td>{m.memo || m.kind.replaceAll("_", " ")}</td><td>{m.bucket}</td><td className="ref">{m.receipt || "—"}</td>
                <td className={`amount num ${m.amount_paise < 0 ? "neg" : ""}`}>{m.amount}</td></tr>
            ))}
          </tbody>
        </table>
      )}
      <p className="hint">Available = allocated − reserved − committed − spent</p>
    </section>
  );
}

const STATUS_WORD: Record<string, string> = { OVERRUN: "Over", ON_TRACK: "On track", UNDERUSED: "Under", OPEN: "No budget" };

/** The FY month by month: budget vs actual bars, a status word under each month (never colour alone). */
function MonthStrip({ lineId, bump }: { lineId: number; bump: number }) {
  const { data } = useLoad<any>(`/api/budget/lines/${lineId}/months`, bump);
  if (!data) return null;
  const months = data.months.filter((m: any) => m.budget_paise || m.actual_paise);
  if (!months.length) return null;
  const top = Math.max(...months.map((m: any) => Math.max(m.budget_paise, m.actual_paise)), 1);
  const cur = months.find((m: any) => m.when === "current");
  return (
    <div className="months" aria-label={`${data.category} by month`}>
      <div className="months-grid" style={{ gridTemplateColumns: `repeat(${months.length}, 1fr)` }}>
        {months.map((m: any) => (
          <div key={m.month} className={`mcell ${m.when} st-${m.status}`}
               title={`${m.label}: budget ${m.budget}, spent ${m.actual}, remaining ${m.remaining}${m.closed ? " (closed)" : ""}${m.snapshot ? " · imported snapshot" : ""}`}>
            <div className="mbars">
              <span className="mbar budget" style={{ height: `${(m.budget_paise / top) * 100}%` }} />
              <span className="mbar actual" style={{ height: `${(m.actual_paise / top) * 100}%` }} />
            </div>
            <div className="mlabel">{m.label}{m.closed ? " ✓" : ""}</div>
            <div className="mstatus">{m.when === "future" ? "" : STATUS_WORD[m.status] ?? m.status}</div>
          </div>
        ))}
      </div>
      <p className="hint"><span className="key budget" /> budget <span className="key actual" /> spent · ✓ closed
        {cur?.pacing ? ` · this month ${cur.pacing.actual_pct}% used, ${cur.pacing.expected_pct}% of the month gone` : ""}</p>
    </div>
  );
}

function RecordCard({ refId, bump }: { refId: string; bump: number }) {
  const { data, err } = useLoad<any>(`/api/records/${encodeURIComponent(refId)}`, bump);
  if (err) return <Failed what="record" err={err} />;
  if (!data) return <Loading what="record" />;
  return (
    <section className="card">
      <div className="card-head"><span className="kind">{data.type}</span><h2>{data.party}</h2><span className="ref">{data.ref}</span></div>
      <dl className="kv">
        <dt>Amount</dt><dd className="num">{data.amount}</dd><dt>Date</dt><dd>{data.business_date}</dd><dt>Budget</dt><dd>{data.category}</dd>
        <dt>Status</dt><dd>{data.state} · {data.settlement_state}</dd>{data.detail && <><dt>Detail</dt><dd>{data.detail}</dd></>}
      </dl>
    </section>
  );
}

const LIST_KIND: Record<string, string> = { attention: "Needs attention", contracts: "Contracts", revenue: "Revenue" };

function ListCard({ items, hint }: { items: any[]; hint?: string }) {
  return (
    <section className="card">
      <div className="card-head"><span className="kind">{LIST_KIND[hint ?? "attention"] ?? "Records"}</span><h2>{items.length} item{items.length === 1 ? "" : "s"}</h2></div>
      <ol className="list">
        {items.map((i) => (
          <li key={i.ref}><span><strong>{i.who}</strong> <span className="ref">{i.ref}</span><div className="sub">{i.kind.replaceAll("_", " ")}{i.detail ? ` · ${i.detail}` : ""}</div></span>
            <span className="num amount">{i.amount ?? ""}</span></li>
        ))}
      </ol>
    </section>
  );
}

function AuditCard({ refId, bump }: { refId?: string; bump: number }) {
  const { data, err } = useLoad<any>(`/api/audit${refId ? `?ref=${encodeURIComponent(refId)}` : ""}`, bump);
  if (err) return <Failed what="decision history" err={err} />;
  if (!data) return <Loading what="decision history" />;
  return (
    <section className="card">
      <div className="card-head"><span className="kind">Decision history</span><h2>{refId || "Recent"}</h2></div>
      <table className="ledger">
        <thead><tr><th>When</th><th>Who</th><th>What</th><th>Record</th><th>Receipt</th></tr></thead>
        <tbody>{data.events.map((e: any) => (
          <tr key={e.id}><td className="num">{new Date(e.at).toLocaleString("en-IN", { dateStyle: "short", timeStyle: "short" })}</td><td>{e.by || "system"}</td>
            <td>{e.action.replace(".", " ")}</td><td className="ref">{e.record || "—"}</td><td className="ref">{e.receipt || "—"}</td></tr>
        ))}</tbody>
      </table>
    </section>
  );
}

function InboxCard({ bump }: { bump: number }) {
  const { data, err } = useLoad<any>("/api/inbox", bump);
  if (err) return <Failed what="inbox" err={err} />;
  if (!data) return <Loading what="inbox" />;
  return (
    <section className="card">
      <div className="card-head"><span className="kind">Inbox</span><h2>{data.messages.filter((m: any) => m.unread).length || "No"} new</h2></div>
      <ul className="list">
        {data.messages.slice(0, 6).map((m: any) => (
          <li key={m.ref}><span><strong>{m.subject}</strong><div className="sub">{m.from} · {m.body.slice(0, 110)}{m.body.length > 110 ? "…" : ""}</div></span>
            <span className="ref">{m.ref}</span></li>
        ))}
      </ul>
    </section>
  );
}

const LEAVE_NAME: Record<string, string> = { CL: "Casual", SL: "Sick", EL: "Earned" };

function LeaveCard({ userId, bump }: { userId: number; bump: number }) {
  const { data, err } = useLoad<any>(`/api/people/${userId}/leave`, bump);
  if (err) return <Failed what="leave balance" err={err} />;
  if (!data) return <Loading what="leave balance" />;
  return (
    <section className="card">
      <div className="card-head"><span className="kind">Leave balance</span><h2>{data.name}</h2></div>
      <div className="buckets">
        {Object.entries<any>(data.balances).map(([k, v]) => (
          <div key={k} className="bucket available"><div className="label">{LEAVE_NAME[k] ?? k}</div>
            <div className="amount num">{v.available}<span className="hint"> / {v.granted}</span></div>
            {v.reserved > 0 && <div className="hint">{v.reserved} pending</div>}</div>
        ))}
      </div>
    </section>
  );
}

function LeaveRequestsCard({ scope, bump }: { scope: string; bump: number }) {
  const { data, err } = useLoad<any>(`/api/leave-requests?scope=${scope}`, bump);
  if (err) return <Failed what="leave requests" err={err} />;
  if (!data) return <Loading what="leave requests" />;
  const title = scope === "awaiting_my_decision" ? "Awaiting your decision" : scope === "team" ? "Team leave" : "Your leave";
  return (
    <section className="card">
      <div className="card-head"><span className="kind">Leave</span><h2>{title}</h2></div>
      {data.requests.length === 0 ? <p className="hint">None.</p> : (
        <ul className="list">{data.requests.map((r: any) => (
          <li key={r.ref}><span><strong>{r.person}</strong> <span className="ref">{r.ref}</span>
            <div className="sub">{LEAVE_NAME[r.type] ?? r.type} · {r.from}{r.to !== r.from ? ` → ${r.to}` : ""} · {r.days} day(s)</div></span>
            <span className={`state state-${r.state === "approved" ? "executed" : r.state === "submitted" ? "open" : "closed"}`}>{r.state}</span></li>
        ))}</ul>
      )}
    </section>
  );
}

function PersonCard({ userId, bump }: { userId: number; bump: number }) {
  const { data, err } = useLoad<any>(`/api/people/${userId}`, bump);
  if (err) return <Failed what="person" err={err} />;
  if (!data) return <Loading what="person" />;
  return (
    <section className="card">
      <div className="card-head"><span className="kind">{data.status === "invited" ? "New joiner" : "Person"}</span><h2>{data.name}</h2></div>
      <dl className="kv">
        <dt>Role</dt><dd>{data.designation || "—"}</dd><dt>Department</dt><dd>{data.department || "—"}</dd>
        <dt>Manager</dt><dd>{data.manager || "—"}</dd>{data.start_date && <><dt>Starts</dt><dd>{data.start_date}</dd></>}
      </dl>
      {data.tasks.length > 0 && (
        <ul className="list" style={{ marginTop: 10 }}>{data.tasks.map((t: any, i: number) => (
          <li key={i}><span>{t.title}<div className="sub">{t.owner} · due {t.due}</div></span>
            <span className={`state ${t.status === "done" ? "state-executed" : ""}`}>{t.status}</span></li>
        ))}</ul>
      )}
    </section>
  );
}

function Deliveries({ receiptId, bump }: { receiptId: number; bump: number }) {
  const { data } = useLoad<any>(`/api/receipts/${receiptId}/deliveries`, bump);
  if (!data || data.deliveries.length === 0) return null;
  const by = (st: string) => data.deliveries.filter((d: any) => d.status === st).length;
  return <p className="hint">Delivered to {by("delivered") + by("read")} inbox(es){by("sent") ? ` · ${by("sent")} email sent` : ""}
    {by("queued") ? ` · ${by("queued")} email sending` : ""}{by("skipped") ? ` · ${by("skipped")} email skipped (not allow-listed)` : ""}
    {by("failed") ? ` · ${by("failed")} email failed` : ""}</p>;
}

export function CardView({ card, bump, onChanged, onOpen }: { card: Card; bump: number; onChanged: () => void; onOpen?: (c: Card) => void }) {
  switch (card.card) {
    case "proposal": return <ProposalCard id={card.proposal_id} bump={bump} onChanged={onChanged} />;
    case "receipt": return <ReceiptCard id={card.receipt_id} bump={bump} />;
    case "source": return <SourceCard id={card.document_id} highlight={card.highlight || []} bump={bump} />;
    case "budget": return <BudgetCard lineId={card.line_id} showLedger={false} bump={bump} />;
    case "ledger": return <BudgetCard lineId={card.line_id} showLedger bump={bump} />;
    case "record": return <RecordCard refId={card.ref} bump={bump} />;
    case "record_list": return <ListCard items={card.items || []} hint={card.title_hint} />;
    case "audit_trail": return <AuditCard refId={card.ref || undefined} bump={bump} />;
    case "inbox": return <InboxCard bump={bump} />;
    case "leave": return <LeaveCard userId={card.user_id} bump={bump} />;
    case "leave_requests": return <LeaveRequestsCard scope={card.scope || "mine"} bump={bump} />;
    case "person": return <PersonCard userId={card.user_id} bump={bump} />;
    case "chart": return <ChartCard id={card.snapshot_id} highlight={card.highlight} bump={bump} />;
    case "view": return <ViewCard title={card.title} items={card.items || []} bump={bump} />;
    case "revenue": return <RevenueCard fy={card.fy} period={card.period} clientId={card.client_id} bump={bump}
      onOpen={(ref) => onOpen?.({ card: "invoice", ref })} />;
    case "invoice": return <InvoiceCard refId={card.ref} bump={bump} />;
    case "fx_rates": return <FxRatesCard fy={card.fy} bump={bump} />;
    case "contract_review": return <ContractReviewCard documentId={card.document_id} bump={bump} />;
    case "contract": return <ContractCard refId={card.ref} bump={bump} />;
    case "contract_liabilities": return <LiabilitiesCard bump={bump} filters={{ bearer: card.bearer, risk: card.risk,
      counterparty: card.counterparty, contract: card.contract, undecided_only: card.undecided_only }} />;
    case "contract_deadlines": return <ContractDeadlinesCard days={card.days} bump={bump} />;
    case "contract_clause": return <ContractClauseCard findingId={card.finding_id} bump={bump} />;
    case "meetings": return <MeetingsCard title={card.title} source={card.source} items={card.items || []} />;
    case "mail_list": return <MailListCard title={card.title} items={card.items || []} />;
    case "mail_thread": return <MailThreadCard messages={card.messages || []} />;
    case "flight_options": return <FlightOptionsCard card={card} />;
    case "hotel_options": return <HotelOptionsCard card={card} />;
    case "payment": return <PaymentCard card={card} />;
    case "tasks": return <TasksCard items={card.items || []} />;
    case "tickets": return <TicketsCard items={card.items || []} />;
    default: return null;
  }
}

/** Collapse repeats: the newest card for the same object replaces the older one. */
export function cardKey(c: Card): string {
  // A revised chart (same lineage) replaces the earlier version of itself.
  if (c.card === "chart") return "chart:" + (c.lineage ?? c.snapshot_id);
  if (c.card === "view") return "view:" + c.title;
  if (c.card === "revenue") return "revenue";  // one revenue board; a new period/client replaces it
  if (c.card === "fx_rates") return "fx_rates";
  if (c.card === "claim_review") return "claim_review";  // one claim under review; the newest replaces it
  if (c.card === "contract_liabilities") return "contract_liabilities";  // one list; new filters replace it
  if (c.card === "contract_deadlines") return "contract_deadlines";
  if (["meetings", "mail_list", "tasks", "tickets"].includes(c.card)) return c.card;  // the newest list replaces the older one
  if (c.card === "mail_thread") return "mail_thread:" + c.thread_id;
  if (c.card === "flight_options" || c.card === "hotel_options") return c.card;  // the newest search replaces the older list
  if (c.card === "payment") return "payment:" + c.receipt;
  if (c.card === "contract_clause") return "contract_clause:" + c.finding_id;
  return c.card + ":" + (c.proposal_id ?? c.receipt_id ?? c.document_id ?? c.line_id ?? c.user_id ?? c.scope ?? c.ref ?? JSON.stringify(c.items?.map((i: any) => i.ref) ?? ""));
}
