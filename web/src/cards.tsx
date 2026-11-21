// Generic card canvas. The agent chooses which cards appear; every card loads its facts from the server
// by reference (proposal id, receipt id, document id, budget line, record ref), never from model text.
import { useEffect, useState } from "react";
import { api, Card } from "./api";

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
          <span className="hint">or say “haan” / “yes” after Munshi reads it out</span>
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

function ListCard({ items }: { items: any[] }) {
  return (
    <section className="card">
      <div className="card-head"><span className="kind">Needs attention</span><h2>{items.length} item{items.length === 1 ? "" : "s"}</h2></div>
      <ol className="list">
        {items.map((i) => (
          <li key={i.ref}><span><strong>{i.who}</strong> <span className="ref">{i.ref}</span><div className="sub">{i.kind.replaceAll("_", " ")}{i.detail ? ` · ${i.detail}` : ""}</div></span>
            <span className="num amount">{i.amount}</span></li>
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

export function CardView({ card, bump, onChanged }: { card: Card; bump: number; onChanged: () => void }) {
  switch (card.card) {
    case "proposal": return <ProposalCard id={card.proposal_id} bump={bump} onChanged={onChanged} />;
    case "receipt": return <ReceiptCard id={card.receipt_id} bump={bump} />;
    case "source": return <SourceCard id={card.document_id} highlight={card.highlight || []} bump={bump} />;
    case "budget": return <BudgetCard lineId={card.line_id} showLedger={false} bump={bump} />;
    case "ledger": return <BudgetCard lineId={card.line_id} showLedger bump={bump} />;
    case "record": return <RecordCard refId={card.ref} bump={bump} />;
    case "record_list": return <ListCard items={card.items || []} />;
    case "audit_trail": return <AuditCard refId={card.ref || undefined} bump={bump} />;
    default: return null;
  }
}

/** Collapse repeats: the newest card for the same object replaces the older one. */
export function cardKey(c: Card): string {
  return c.card + ":" + (c.proposal_id ?? c.receipt_id ?? c.document_id ?? c.line_id ?? c.ref ?? JSON.stringify(c.items?.map((i: any) => i.ref) ?? ""));
}
