// Sidebar views. Each reads real server data (read-only endpoints) and hands actions to Purser or the panel.
import { AnimatePresence, motion } from "motion/react";
import { ArrowRight, Check, CircleCheck, Clock, FileText, Plane, RotateCcw } from "lucide-react";
import { ReactNode, useState } from "react";
import { reveal } from "../animations/tokens";
import { ChartCard } from "../ChartCard";
import PurserComposer from "../components/assistant/PurserComposer";
import PurserOrb from "../components/assistant/PurserOrb";
import { useAssistant } from "../components/assistant/PurserVoiceController";
import AnimatedCounter from "../components/shared/AnimatedCounter";
import { useLoad, usePurser, View } from "../state/store";
import MailView from "./MailView";
import { useOrbLabels } from "./WorkspaceView";

const fmtDate = (d: string) => new Date(d.length === 10 ? d + "T00:00:00" : d).toLocaleDateString("en-IN", { day: "numeric", month: "short" });

export function ViewFrame({ title, sub, actions, children }: { title: string; sub?: string; actions?: ReactNode; children: ReactNode }) {
  const P = usePurser();
  const A = useAssistant();
  const { live, label } = useOrbLabels();
  return (
    <>
      <div className="view">
        <div className="view-head">
          <div><h1>{title}</h1>{sub && <p>{sub}</p>}</div>
          <span className="spacer" />
          {actions}
          <PurserOrb size="mini" state={P.orb} level={A.level} onActivate={A.toggleVoice} label={label} pressed={live} disabled={!A.ready} />
        </div>
        {children}
      </div>
      <div style={{ padding: "0 40px 0 48px" }}><PurserComposer /></div>
    </>
  );
}

function Loading() { return <div className="grid" aria-busy="true">{[0, 1, 2].map((i) => <div key={i} className="skeleton" style={{ height: 64 }} />)}</div>; }
function Failed({ err, retry }: { err: string; retry: () => void }) {
  return <div className="glass empty-state" role="alert"><p className="error">{err}</p><button className="btn btn-sm" onClick={retry} style={{ marginTop: 12 }}><RotateCcw size={14} /> Retry</button></div>;
}
const Rows = ({ children }: { children: ReactNode }) => <motion.ul className="rows glass" initial="hidden" animate="show">{children}</motion.ul>;

function AskChip({ q }: { q: string }) {
  const A = useAssistant();
  return <button className="btn btn-sm" onClick={(e) => A.send(q, e.currentTarget)} disabled={!A.ready || A.sending}>{q} <ArrowRight size={14} /></button>;
}

// ---------------------------------------------------------------- Claims

function ClaimsView() {
  const P = usePurser();
  const [tab, setTab] = useState<"submitted" | "approved" | "all">("submitted");
  const { data, err, reload } = useLoad<any>(`/api/claims${tab === "all" ? "" : `?state=${tab}`}`, P.bump);
  const bills = useLoad<any>(P.me.role === "employee" ? null : "/api/bills", P.bump);
  const pendingBills = (bills.data?.bills ?? []).filter((b: any) => b.state === "submitted");
  return (
    <ViewFrame title="Claims" sub="Reimbursement claims and items awaiting your decision."
      actions={<Tabs value={tab} onChange={setTab} options={[["submitted", "Awaiting approval"], ["approved", "Approved"], ["all", "All"]]} />}>
      {err ? <Failed err={err} retry={reload} /> : !data ? <Loading /> : (
        <div className="grid">
          {data.claims.length === 0 ? <div className="glass empty-state">No claims here. Hand Purser a receipt to start one.</div> : (
            <Rows>{data.claims.map((c: any, i: number) => (
              <motion.li key={c.ref} variants={reveal} custom={i}>
                <button className="row" onClick={() => P.addCards([{ card: "claim_review", ref: c.ref }])} aria-label={`Review claim ${c.ref}`}>
                  <span><span className="r-title">{c.employee} · {c.merchant}</span><div className="r-sub">{c.ref} · {c.category} · {fmtDate(c.date)}{c.reservation ? " · linked to reservation" : ""}</div></span>
                  <span className={`state state-${c.state}`}>{c.state === "submitted" ? "Awaiting approval" : c.state}</span>
                  <span className="r-amt">{c.amount}</span>
                </button>
              </motion.li>))}</Rows>
          )}
          {tab === "submitted" && pendingBills.length > 0 && (
            <>
              <h2 className="sub-h">Vendor bills awaiting approval</h2>
              <Rows>{pendingBills.map((b: any, i: number) => (
                <motion.li key={b.ref} variants={reveal} custom={i}>
                  <button className="row" onClick={() => P.addCards([{ card: "record", ref: b.ref }])}>
                    <span><span className="r-title">{b.vendor}</span><div className="r-sub">{b.ref} · {b.category} · due {b.due ? fmtDate(b.due) : "—"}</div></span>
                    <span className="state state-submitted">Awaiting approval</span><span className="r-amt">{b.amount}</span>
                  </button>
                </motion.li>))}</Rows>
              <div><AskChip q="Approve the bills due this week" /></div>
            </>
          )}
        </div>
      )}
    </ViewFrame>
  );
}

function Tabs<T extends string>({ value, onChange, options }: { value: T; onChange: (v: T) => void; options: [T, string][] }) {
  return (
    <div className="tabs" role="tablist">
      {options.map(([v, l]) => (
        <button key={v} role="tab" aria-selected={value === v} className="tab" onClick={() => onChange(v)}>
          {value === v && <motion.span layoutId={`tab-${options.map((o) => o[0]).join()}`} className="tab-pill" transition={{ type: "spring", stiffness: 420, damping: 34 }} />}
          <span>{l}</span>
        </button>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------- Expenses (bills + documents)

function ExpensesView() {
  const P = usePurser();
  const bills = useLoad<any>(P.me.role === "employee" ? null : "/api/bills", P.bump);
  const docs = useLoad<any>("/api/documents", P.bump);
  return (
    <ViewFrame title="Expenses" sub="Vendor bills and the documents Purser has read.">
      <div className="grid cols-2" style={{ alignItems: "start" }}>
        <section>
          <h2 className="sub-h">Vendor bills</h2>
          {bills.err ? <Failed err={bills.err} retry={bills.reload} /> : !bills.data ? <Loading /> : bills.data.bills.length === 0 ? <div className="glass empty-state">No bills yet.</div> : (
            <Rows>{bills.data.bills.map((b: any, i: number) => (
              <motion.li key={b.ref} variants={reveal} custom={i}>
                <button className="row" onClick={() => P.addCards([{ card: "record", ref: b.ref }])}>
                  <span><span className="r-title">{b.vendor}</span><div className="r-sub">{b.ref} · {b.category} · {b.description || b.invoice_no || ""}</div></span>
                  <span className={`state state-${b.settlement_state === "settled" ? "settled" : b.state}`}>{b.settlement_state === "settled" ? "Paid" : b.state}</span>
                  <span className="r-amt">{b.amount}</span>
                </button>
              </motion.li>))}</Rows>)}
        </section>
        <section>
          <h2 className="sub-h">Documents</h2>
          {docs.err ? <Failed err={docs.err} retry={docs.reload} /> : !docs.data ? <Loading /> : docs.data.documents.length === 0 ? <div className="glass empty-state">Drop a receipt or bill anywhere to hand it to Purser.</div> : (
            <Rows>{docs.data.documents.map((d: any, i: number) => (
              <motion.li key={d.id} variants={reveal} custom={i}>
                <button className="row" onClick={() => P.addCards([{ card: "source", document_id: d.id, highlight: [] }])}>
                  <span><span className="r-title"><FileText size={14} style={{ verticalAlign: -2, marginRight: 6 }} />{d.filename}</span><div className="r-sub">D{d.id} · {fmtDate(d.at)}</div></span>
                  <span className="state">{(d.outcome || d.status).replaceAll("_", " ")}</span><span />
                </button>
              </motion.li>))}</Rows>)}
        </section>
      </div>
    </ViewFrame>
  );
}

// ---------------------------------------------------------------- Travel

function TravelView() {
  const P = usePurser();
  const { data, err, reload } = useLoad<any>("/api/trips", P.bump);
  return (
    <ViewFrame title="Travel" sub="Trips, reservations held against the budget, and the claims that replace them.">
      {err ? <Failed err={err} retry={reload} /> : !data ? <Loading /> : data.trips.length === 0 ? <div className="glass empty-state">No trips.</div> : (
        <div className="grid cols-2">{data.trips.map((t: any, i: number) => (
          <motion.section key={t.id} className="glass tile" variants={reveal} initial="hidden" animate="show" custom={i}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}><Plane size={18} color="var(--mint)" /><h3>{t.city} Trip</h3></div>
            <p className="fine" style={{ margin: "2px 0 12px" }}>{t.employee} · {fmtDate(t.start)} – {fmtDate(t.end)} · {t.purpose}</p>
            <ul className="list">{t.reservations.map((r: any) => (
              <li key={r.ref}><span><span style={{ color: "var(--ivory)" }}>{r.description}</span><div className="sub">{r.ref} · {r.status === "open" ? "held against budget" : r.status}
                {r.claim ? ` · claim ${r.claim.ref} ${r.claim.state} (${r.claim.amount})` : " · no claim yet"}</div></span>
                <span className="r-amt" style={{ fontFamily: "var(--serif)", color: "var(--ivory)" }}>{r.amount}</span></li>))}</ul>
            {t.reservations.some((r: any) => r.claim) && (
              <button className="link" style={{ marginTop: 10 }} onClick={() => P.addCards([{ card: "claim_review", ref: t.reservations.find((r: any) => r.claim).claim.ref }])}>Open claim review</button>)}
          </motion.section>))}</div>
      )}
    </ViewFrame>
  );
}

// ---------------------------------------------------------------- Payments

function PaymentsView() {
  const P = usePurser();
  const { data, err, reload } = useLoad<any>(P.me.role === "employee" ? null : "/api/payments", P.bump);
  if (P.me.role === "employee") return <ViewFrame title="Payments"><div className="glass empty-state">Payments are visible to finance approvers.</div></ViewFrame>;
  return (
    <ViewFrame title="Payments" sub="Purser records payments made outside it; it never moves money. Approved is not paid.">
      {err ? <Failed err={err} retry={reload} /> : !data ? <Loading /> : (
        <div className="grid">
          <h2 className="sub-h">Approved, awaiting payment</h2>
          {data.awaiting.length === 0 ? <div className="glass empty-state">Nothing awaiting payment.</div> : (
            <Rows>{data.awaiting.map((p: any, i: number) => (
              <motion.li key={p.id} variants={reveal} custom={i} className="row">
                <span><span className="r-title">{p.payee}</span><div className="r-sub">{p.record} · {p.method} · due {fmtDate(p.date)}</div></span>
                <span className="pay-status awaiting"><motion.span className="pulse-dot" animate={{ opacity: [1, 0.35, 1] }} transition={{ repeat: Infinity, duration: 1.8 }} /> Awaiting payment</span>
                <span className="r-amt">{p.amount}</span>
              </motion.li>))}</Rows>)}
          {data.awaiting.length > 0 && <div><AskChip q={`Record payment for ${data.awaiting[0].record}`} /></div>}
          <h2 className="sub-h">Payment history</h2>
          <Rows>{data.history.map((p: any, i: number) => (
            <motion.li key={p.id} variants={reveal} custom={i} className="row">
              <span><span className="r-title">{p.payee ?? p.record}</span><div className="r-sub">{p.method} · {p.reference} · {fmtDate(p.date)}</div></span>
              <span className="pay-status settled"><CircleCheck size={14} /> Settled</span>
              <span className="r-amt">{p.amount}</span>
            </motion.li>))}</Rows>
        </div>
      )}
    </ViewFrame>
  );
}

// ---------------------------------------------------------------- Budgets

function BudgetsView() {
  const P = usePurser();
  const { data, err, reload } = useLoad<any>("/api/budget/lines", P.bump);
  const alerts = useLoad<any>("/api/budget/alerts", P.bump);
  const alertCats = new Set((alerts.data?.alerts ?? []).map((a: any) => a.category));
  return (
    <ViewFrame title="Budgets" sub="Available = allocated − reserved − committed − spent. Pending claims are shown separately until approved.">
      {alerts.data?.alerts?.length > 0 && (
        <div className="grid" style={{ marginBottom: 14 }}>{alerts.data.alerts.map((a: any) => (
          <motion.div key={a.category} className="flag flag-warn" initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }}>
            {a.category}: {a.alert} · {a.spent} of {a.budget} this month · {a.remaining} left</motion.div>))}</div>)}
      {err ? <Failed err={err} retry={reload} /> : !data ? <Loading /> : (
        <div className="grid cols-3">{data.lines.map((l: any, i: number) => {
          const pct = (p: number) => `${Math.max(0, Math.min(100, (p / Math.max(1, l.allocated_paise)) * 100))}%`;
          return (
            <motion.button key={l.line_id} className="glass tile" style={{ textAlign: "left" }} variants={reveal} initial="hidden" animate="show" custom={i}
              onClick={() => P.addCards([{ card: "ledger", line_id: l.line_id }])} whileHover={{ y: -3 }} aria-label={`${l.category} budget, ${l.available} available`}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}><h3 style={{ flex: 1 }}>{l.category}</h3>{alertCats.has(l.category) && <span className="state state-open">Alert</span>}</div>
              <div className="fine">{l.department} · {l.fy}</div>
              <div className="usage" aria-hidden="true">
                <motion.i className="u-spent" initial={{ width: 0 }} animate={{ width: pct(l.spent_paise) }} transition={{ duration: 0.9, delay: 0.1 + i * 0.05 }} />
                <motion.i className="u-committed" initial={{ width: 0 }} animate={{ width: pct(l.committed_paise) }} transition={{ duration: 0.9, delay: 0.2 + i * 0.05 }} />
                <motion.i className="u-reserved" initial={{ width: 0 }} animate={{ width: pct(l.reserved_paise) }} transition={{ duration: 0.9, delay: 0.3 + i * 0.05 }} />
              </div>
              <div className="big num"><AnimatedCounter value={l.available_paise} from={0} /></div>
              <div className="fine">available of {l.allocated}{l.pending_claims_paise > 0 ? ` · ${l.pending_claims} pending claims` : ""}</div>
            </motion.button>
          );
        })}</div>
      )}
      <div className="legend" style={{ marginTop: 14 }}><span><i style={{ background: "var(--sage)" }} />Spent</span><span><i style={{ background: "#6fb894" }} />Committed</span><span><i style={{ background: "rgba(231,199,127,.6)" }} />Reserved</span></div>
    </ViewFrame>
  );
}

// ---------------------------------------------------------------- Dashboards (agent-built charts + live budget figures)

function DashboardsView() {
  const P = usePurser();
  const A = useAssistant();
  const lines = useLoad<any>("/api/budget/lines", P.bump);
  const charts = P.cards.filter((c) => c.card === "chart");
  const total = (k: string) => (lines.data?.lines ?? []).reduce((s: number, l: any) => s + l[k], 0);
  return (
    <ViewFrame title="Dashboards" sub="Ask Purser for any chart; it builds it from your books. Figures below are live totals.">
      <div className="grid cols-3" style={{ marginBottom: 16 }}>
        {[["Allocated", "allocated_paise"], ["Spent", "spent_paise"], ["Available", "available_paise"]].map(([l, k], i) => (
          <motion.div key={k} className="glass tile" variants={reveal} initial="hidden" animate="show" custom={i}>
            <div className="fine">{l} · all budget lines</div>
            <div className="big num">{lines.data ? <AnimatedCounter value={total(k)} from={0} /> : <span className="skeleton" style={{ display: "inline-block", width: 120, height: 30 }} />}</div>
          </motion.div>))}
      </div>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 16 }}>
        <AskChip q="Show monthly spend by category this year" /><AskChip q="Chart travel budget vs actual by month" /><AskChip q="Show receivables by client" />
      </div>
      <AnimatePresence>{charts.length === 0 && !A.sending && <motion.div className="glass empty-state" exit={{ opacity: 0 }}>Charts Purser builds for you collect here.</motion.div>}</AnimatePresence>
      {A.sending && <div className="skeleton" style={{ height: 260, marginBottom: 14 }} />}
      <div className="grid cols-2">{charts.map((c, i) => (
        <motion.div key={c.snapshot_id} variants={reveal} initial="hidden" whileInView="show" viewport={{ once: true }} custom={i}>
          <ChartCard id={c.snapshot_id} highlight={c.highlight} bump={P.bump} />
        </motion.div>))}</div>
    </ViewFrame>
  );
}

// ---------------------------------------------------------------- Reports (decision history)

function ReportsView() {
  const P = usePurser();
  const audit = useLoad<any>(P.me.role === "employee" ? null : "/api/audit", P.bump);
  const sent = useLoad<any>("/api/messages/sent", P.bump);
  return (
    <ViewFrame title="Reports" sub="Every decision with who made it and the receipt that proves it.">
      <div className="grid cols-2" style={{ alignItems: "start" }}>
        <section>
          <h2 className="sub-h">Decision history</h2>
          {P.me.role === "employee" ? <div className="glass empty-state">Visible to finance approvers.</div> : audit.err ? <Failed err={audit.err} retry={audit.reload} /> : !audit.data ? <Loading /> : (
            <Rows>{audit.data.events.map((e: any, i: number) => (
              <motion.li key={e.id} variants={reveal} custom={i} className="row clickable" onClick={() => e.record && P.addCards([{ card: e.record.startsWith("C") ? "claim_review" : "audit_trail", ref: e.record }])}>
                <span><span className="r-title">{e.action.replace(".", " ")} {e.record ? `· ${e.record}` : ""}</span><div className="r-sub">{e.by || "system"} · {new Date(e.at).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" })}</div></span>
                <span className="ref">{e.receipt || ""}</span>{e.receipt ? <Check size={14} color="var(--mint)" /> : <span />}
              </motion.li>))}</Rows>)}
        </section>
        <section>
          <h2 className="sub-h">Quick reports</h2>
          <div className="glass tile" style={{ display: "grid", gap: 8, justifyItems: "start" }}>
            <AskChip q="Summarise our travel spending" /><AskChip q="Show last month's expenses" /><AskChip q="What needs my attention today?" /><AskChip q="Show the decision history for this week" />
          </div>
          <h2 className="sub-h">Messages sent</h2>
          {sent.data && <Rows>{sent.data.messages.slice(0, 5).map((m: any, i: number) => (
            <motion.li key={m.ref} variants={reveal} custom={i} className="row"><span><span className="r-title">{m.subject}</span><div className="r-sub">to {m.to.join(", ") || "—"}</div></span>
              <Clock size={14} color="var(--faint)" /><span className="fine">{fmtDate(m.at)}</span></motion.li>))}</Rows>}
        </section>
      </div>
    </ViewFrame>
  );
}

export function ViewRouter({ view }: { view: View }) {
  switch (view) {
    case "claims": return <ClaimsView />;
    case "expenses": return <ExpensesView />;
    case "travel": return <TravelView />;
    case "payments": return <PaymentsView />;
    case "budgets": return <BudgetsView />;
    case "dashboards": return <DashboardsView />;
    case "reports": return <ReportsView />;
    case "mail": return <MailView />;
    default: return null;
  }
}

