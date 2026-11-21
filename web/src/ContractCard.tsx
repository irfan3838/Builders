// Contract cards. Each loads its facts from the server by reference (document id, contract ref, finding id, filters);
// risk is always written as text, never colour alone.
import { ReactNode, useEffect, useState } from "react";
import { api } from "./api";

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

const Shell = ({ what, err }: { what: string; err?: string | null }) => (
  <section className="card" aria-busy={!err}>
    <p className={err ? "error" : "hint"}>{err ? `Could not load ${what}: ${err}` : `Loading ${what}…`}</p>
  </section>
);

const KIND: Record<string, string> = { expiry: "Contract ends", renewal_notice: "Renewal notice cut-off", survival_end: "Surviving duties end" };
const STATE: Record<string, string> = { proposed: "To review", accepted: "Accepted", modified: "Modified", rejected: "Rejected", tagged: "Standard" };
const fmtDate = (d?: string | null) => d ? new Date(d + "T00:00:00").toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" }) : "not stated";

const Risk = ({ risk }: { risk: string }) => <span className={`risk risk-${risk}`}>{risk === "standard" ? "Standard" : `${risk[0].toUpperCase()}${risk.slice(1)} risk`}</span>;

function Bearer({ who, term }: { who?: string | null; term?: string | null }) {
  if (!who) return null;
  return <span className={`bearer bearer-${who}`}>{who === "us" ? "Binds us" : who === "counterparty" ? "Binds them" : who === "mutual" ? "Both sides" : "Bearer unclear"}{term ? ` · ${term}` : ""}</span>;
}

function Liability({ f }: { f: any }) {
  return (
    <li className="liab">
      <div className="liab-head">
        <strong>{f.clause}</strong>
        <Risk risk={f.risk} />
        {f.state && f.state !== "proposed" && <span className="state">{STATE[f.state] ?? f.state}</span>}
        {f.finding_id && <span className="ref">#{f.finding_id}{f.contract ? ` · ${f.contract}` : ""}</span>}
      </div>
      <div className="liab-meta"><Bearer who={f.bearer} term={f.bearer_term} />
        {f.counterparty && <span className="fine">{f.counterparty}</span>}
        {f.notice_days && <span className="fine">{f.notice_days} days' notice</span>}</div>
      <blockquote className="quote">“{f.quote}”</blockquote>
    </li>
  );
}

function Caps({ caps }: { caps: any[] }) {
  if (!caps?.length) return null;
  return (
    <div className="caps">
      <h3 className="sub-h">Liability cap</h3>
      {caps.map((c, i) => (
        <div key={i} className="cap">
          <p className="num"><strong>{c.cap ?? (c.cap_basis === "no cap" ? "No cap" : "Cap without a fixed amount")}</strong>
            {c.cap_basis && c.cap_basis !== "no cap" && <span className="fine"> — {c.cap_basis}</span>}</p>
          {c.carve_outs?.length > 0 && <ul className="carve">{c.carve_outs.map((q: string, j: number) => <li key={j}><span className="kind">Outside the cap:</span> “{q}”</li>)}</ul>}
        </div>
      ))}
    </div>
  );
}

function Deadlines({ rows }: { rows: any[] }) {
  if (!rows?.length) return null;
  return (
    <div>
      <h3 className="sub-h">Dates to track</h3>
      <ul className="list">{rows.map((d, i) => (
        <li key={i}><span>{KIND[d.kind] ?? d.kind}{d.contract ? <span className="ref"> · {d.contract}</span> : null}
          {d.counterparty && <div className="sub">{d.counterparty}</div>}</span>
          <span className="num">{fmtDate(d.due_on)}{typeof d.days_left === "number" && <div className="sub">in {d.days_left} days</div>}</span></li>
      ))}</ul>
    </div>
  );
}

const Caveat = ({ note }: { note?: string | null }) => (
  <p className="hint">{note ? `${note} ` : ""}Automated reading of the wording for Legal to confirm; an empty list does not certify the contract.</p>
);

export function ContractReviewCard({ documentId, bump }: { documentId: number; bump: number }) {
  const [tick, setTick] = useState(0);
  const { data, err } = useLoad<any>(`/api/contracts/review/${documentId}`, bump + tick);
  useEffect(() => { if (data?.pending) { const t = setTimeout(() => setTick((x) => x + 1), 2500); return () => clearTimeout(t); } }, [data]);
  if (err || !data) return <Shell what="contract review" err={err} />;
  if (data.pending) return <section className="card" aria-busy="true"><p className="hint">Reading the contract…</p></section>;
  return (
    <section className="card contract" aria-labelledby={`cr-${documentId}`}>
      <div className="card-head"><span className="kind">Contract review · not saved</span><h2 id={`cr-${documentId}`}>{data.title}</h2></div>
      <dl className="kv"><dt>With</dt><dd>{data.counterparty || "not identified"}</dd><dt>Type</dt><dd>{data.type}</dd>
        <dt>Runs</dt><dd className="num">{fmtDate(data.effective_on)} – {fmtDate(data.expiry_on)}</dd></dl>
      {data.flags_for_review.length > 0 ? <ul className="liabs">{data.flags_for_review.map((f: any, i: number) => <Liability key={i} f={{ ...f, bearer: whoKey(f.who_bears) }} />)}</ul>
        : <p className="hint">No risky clauses were flagged.</p>}
      <Caps caps={data.caps} />
      <Deadlines rows={data.deadlines} />
      {data.standard_clauses.length > 0 && <p className="fine">Also found: {data.standard_clauses.join(", ")}.</p>}
      <Caveat note={data.coverage_note} />
    </section>
  );
}

const whoKey = (w?: string | null) => w === "binds us" ? "us" : w === "binds the other party" ? "counterparty" : w === "binds both sides" ? "mutual" : w ? "unclear" : null;

export function ContractCard({ refId, bump }: { refId: string; bump: number }) {
  const { data, err } = useLoad<any>(`/api/contracts/${encodeURIComponent(refId)}`, bump);
  if (err || !data) return <Shell what="contract" err={err} />;
  return (
    <section className="card contract" aria-labelledby={`c-${data.ref}`}>
      <div className="card-head"><span className="kind">Contract</span><h2 id={`c-${data.ref}`}>{data.title}</h2><span className="ref">{data.ref}</span></div>
      <dl className="kv"><dt>With</dt><dd>{data.counterparty || "not identified"}</dd><dt>Type</dt><dd>{data.type} · {data.status}</dd>
        <dt>Runs</dt><dd className="num">{fmtDate(data.effective_on)} – {fmtDate(data.expiry_on)}</dd>
        <dt>Flags</dt><dd role="status">{data.open_flags} to review · {data.binds_us} bind us</dd></dl>
      {data.liabilities.length > 0 ? <ul className="liabs">{data.liabilities.map((f: any) => <Liability key={f.finding_id} f={f} />)}</ul>
        : <p className="hint">No standing liabilities.</p>}
      <Caps caps={data.caps} />
      <Deadlines rows={data.deadlines} />
      <Caveat note={data.coverage?.note} />
    </section>
  );
}

export function LiabilitiesCard({ filters, bump }: { filters: Record<string, any>; bump: number }) {
  const q = new URLSearchParams(Object.entries(filters).filter(([, v]) => v !== null && v !== undefined && v !== false).map(([k, v]) => [k, String(v)])).toString();
  const { data, err } = useLoad<any>(`/api/contracts/liabilities${q ? "?" + q : ""}`, bump);
  if (err || !data) return <Shell what="liabilities" err={err} />;
  const title = filters.undecided_only ? "Flags waiting for review" : filters.bearer === "us" ? "Liabilities on us" : "Contract liabilities";
  return (
    <section className="card contract" aria-label={title}>
      <div className="card-head"><span className="kind">Contracts</span><h2>{title}</h2>
        <span className="ref" role="status">{data.rows.length} across {new Set(data.rows.map((r: any) => r.contract)).size} contract(s)</span></div>
      {data.rows.length ? <ul className="liabs">{data.rows.map((f: any) => <Liability key={f.finding_id} f={f} />)}</ul> : <p className="hint">Nothing matches.</p>}
      <Caveat />
    </section>
  );
}

export function ContractDeadlinesCard({ days, bump }: { days: number; bump: number }) {
  const { data, err } = useLoad<any>(`/api/contracts/deadlines?days=${days || 90}`, bump);
  if (err || !data) return <Shell what="deadlines" err={err} />;
  return (
    <section className="card contract" aria-label="Contract deadlines">
      <div className="card-head"><span className="kind">Contracts</span><h2>Next {data.days} days</h2></div>
      {data.rows.length ? <Deadlines rows={data.rows} /> : <p className="hint">No contract dates in this window.</p>}
    </section>
  );
}

export function ContractClauseCard({ findingId, bump }: { findingId: number; bump: number }) {
  const { data, err } = useLoad<any>(`/api/contracts/findings/${findingId}/context`, bump);
  if (err || !data) return <Shell what="clause" err={err} />;
  const marks = [...data.marks].sort((a: any, b: any) => a.start - b.start);
  const parts: ReactNode[] = [];
  let at = 0;
  marks.forEach((m: any, i: number) => {
    if (m.start < at) return;
    parts.push(<span key={`t${i}`}>{data.excerpt.slice(at, m.start)}</span>);
    parts.push(<mark key={`m${i}`} className={`hl hl-${m.kind}`} title={m.kind === "carve_out" ? "Outside the cap" : data.clause}>{data.excerpt.slice(m.start, m.stop)}</mark>);
    at = m.stop;
  });
  parts.push(<span key="end">{data.excerpt.slice(at)}</span>);
  return (
    <section className="card contract" aria-labelledby={`cl-${findingId}`}>
      <div className="card-head"><span className="kind">{data.contract} · {data.counterparty}</span><h2 id={`cl-${findingId}`}>{data.clause}</h2><Risk risk={data.risk} /></div>
      <div className="liab-meta"><Bearer who={data.bearer} term={data.bearer_term} />{data.beneficiary && <span className="fine">for {data.beneficiary}</span>}</div>
      <p className="clause-text">{data.clipped_start && "… "}{parts}{data.clipped_end && " …"}</p>
      {marks.some((m: any) => m.kind === "carve_out") && <p className="fine"><mark className="hl hl-carve_out">Underlined</mark> text is outside the cap.</p>}
    </section>
  );
}
