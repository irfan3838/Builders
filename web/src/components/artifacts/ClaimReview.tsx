// Claim review artifact: receipt vs reservation vs budget, with the approval decision.
// Every number comes from /api/claim-review (SQL). Approve = server proposal -> confirmation dialog -> confirm endpoint;
// success is shown only from the confirm response, and the budget figures then reload from the server.
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { CalendarDays, Check, CircleCheck, ExternalLink, TriangleAlert, X } from "lucide-react";
import { Fragment, useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { api, ApiError } from "../../api";
import { ease } from "../../animations/tokens";
import { usePurser } from "../../state/store";
import { useFx } from "../shared/FxLayer";
import AnimatedCounter from "../shared/AnimatedCounter";
import ConfirmationDialog from "../shared/ConfirmationDialog";
import PurserDeskHelper, { HelperPose } from "./PurserDeskHelper";

type Review = {
  ref: string | null; status: string; employee: string | null;
  document: { id: number; filename: string; pages: number } | null; extracted: boolean;
  receipt: { vendor: string | null; guest: string | null; date: string | null; invoice_no: string | null; items: { label: string; amount: string }[];
    taxes: { label: string; amount: string }[]; total_paise: number | null; total: string | null; arithmetic: string | null } | null;
  reservation: { ref: string; description: string; amount_paise: number; amount: string; status: string; trip: string | null; kind: string; start: string | null; end: string | null } | null;
  comparison: { reserved_paise: number; claimed_paise: number; difference_paise: number; difference: string; below: boolean } | null;
  checks: { label: string; ok: boolean }[];
  impact: { category: string; before_paise: number; after_paise: number; before: string; after: string; final: boolean; receipt?: string } | null;
  proposal: { id: string; kind: string; title: string; lines: string[] } | null;
};

const fmtDate = (d: string | null) => (d ? new Date(d + "T00:00:00").toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" }) : "—");

function Lightbox({ doc, onClose }: { doc: { id: number; filename: string; pages: number }; onClose: () => void }) {
  const [page, setPage] = useState(1);
  useEffect(() => { const k = (e: KeyboardEvent) => e.key === "Escape" && onClose(); addEventListener("keydown", k); return () => removeEventListener("keydown", k); }, [onClose]);
  return createPortal(
    <motion.div className="scrim" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <motion.div className="lightbox glass" role="dialog" aria-modal="true" aria-label={`Full receipt: ${doc.filename}`}
        initial={{ scale: 0.92, y: 20, opacity: 0 }} animate={{ scale: 1, y: 0, opacity: 1 }} exit={{ scale: 0.95, opacity: 0 }} transition={{ duration: 0.35, ease }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
          <strong style={{ flex: 1, color: "var(--ivory)" }}>{doc.filename}</strong>
          {doc.pages > 1 && <>
            <button className="btn btn-sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>Prev</button>
            <span className="fine">Page {page} / {doc.pages}</span>
            <button className="btn btn-sm" disabled={page >= doc.pages} onClick={() => setPage(page + 1)}>Next</button></>}
          <button className="icon-btn" onClick={onClose} aria-label="Close" autoFocus><X size={18} /></button>
        </div>
        <img src={`/api/documents/${doc.id}/pages/${page}`} alt={`Page ${page} of ${doc.filename}`} />
      </motion.div>
    </motion.div>, document.body);
}

export default function ClaimReview({ card, bump, primary }: { card: { document_id?: number; ref?: string; reservation_id?: number }; bump: number; primary: boolean }) {
  const P = usePurser();
  const { fly } = useFx();
  const reduced = useReducedMotion();
  const qs = new URLSearchParams();
  if (card.ref) qs.set("ref", card.ref);
  if (card.document_id) qs.set("document_id", String(card.document_id));
  if (card.reservation_id) qs.set("reservation_id", String(card.reservation_id));
  const path = `/api/claim-review?${qs}`;
  const [data, setData] = useState<Review | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [n, setN] = useState(0);
  const [pose, setPose] = useState<HelperPose>("look");
  const [dialog, setDialog] = useState<{ id: string; title: string; lines: string[] } | null>(null);
  const [busy, setBusy] = useState(false);
  const [dlgErr, setDlgErr] = useState<string | null>(null);
  const [result, setResult] = useState<"success" | null>(null);
  const [full, setFull] = useState(false);
  const [slot, setSlot] = useState<HTMLElement | null>(null);
  const approveBtn = useRef<HTMLButtonElement>(null);
  const prevAvail = useRef<number | null>(null);

  useEffect(() => {
    let live = true;
    api.get<Review>(path).then((d) => { if (live) { setData(d); setErr(null); } }).catch((e) => live && setErr(e.message));
    return () => { live = false; };
  }, [path, bump, n]);
  const reload = useCallback(() => setN((x) => x + 1), []);

  useEffect(() => { setSlot(document.getElementById("panel-foot-slot")); }, [primary]);

  // helper choreography follows the reveal: look at receipt -> raise clip as matching starts -> lean -> nod/worry
  useEffect(() => {
    if (!data) return;
    const ok = data.checks.length > 0 && data.checks.every((c) => c.ok);
    const steps: [number, HelperPose][] = data.reservation
      ? [[0, "look"], [550, "raise"], [1150, "lean"], [1750, ok ? "nod" : "worried"], [2900, "neutral"]]
      : [[0, "look"], [1400, "neutral"]];
    const ts = steps.map(([ms, p]) => window.setTimeout(() => setPose(p), reduced ? 0 : ms));
    return () => ts.forEach(clearTimeout);
  }, [data?.ref, data?.document?.id, data?.reservation?.ref, data?.checks.length, reduced]);  // eslint-disable-line react-hooks/exhaustive-deps

  // publish to the decision strip
  const { setDecision } = P;
  useEffect(() => {
    if (!primary || !data) return;
    setDecision({
      ref: data.ref, status: data.status, reservation: data.reservation?.trip ?? data.reservation?.description ?? null,
      differencePaise: data.comparison?.difference_paise ?? null, below: data.comparison?.below ?? null,
      category: data.impact?.category ?? null, beforePaise: data.impact?.before_paise ?? null, afterPaise: data.impact?.after_paise ?? null,
      final: !!data.impact?.final, approvedAt: data.status === "approved" ? Date.now() : undefined, proposalId: data.proposal?.id ?? null,
    });
  }, [primary, data, setDecision]);
  useEffect(() => () => { if (primary) setDecision(null); }, [primary, setDecision]);

  const openApproval = async () => {
    if (!data) return;
    setDlgErr(null);
    if (data.proposal) { setDialog({ id: data.proposal.id, title: data.proposal.title, lines: data.proposal.lines }); return; }
    if (data.status !== "submitted" || !data.ref) return;
    setBusy(true);
    try {
      const r = await api.post<{ proposal_id: string; preview: { title: string; lines: string[] } }>(`/api/records/${data.ref}/prepare-approval`);
      setDialog({ id: r.proposal_id, title: r.preview.title, lines: r.preview.lines });
    } catch (e: any) {
      P.toast("error", e instanceof ApiError && e.body?.code === "SELF_APPROVAL" ? "You cannot approve your own reimbursement." : e.message);
      P.flashOrb("error");
    } finally { setBusy(false); }
  };

  const confirm = async () => {
    if (!dialog || busy) return;
    setBusy(true); setDlgErr(null);
    prevAvail.current = data?.impact?.before_paise ?? null;
    try {
      const r = await api.post<any>(`/api/proposals/${dialog.id}/confirm`);
      if (r.status === "executed" || r.status === "replayed") {
        setDialog(null);
        setResult("success");
        P.flashOrb("success");
        setPose("nod");
        P.say("purser", r.receipt?.summary ?? "Done.");
        P.toast("success", `${r.receipt?.summary ?? "Done"}${r.receipt?.ref ? ` · ${r.receipt.ref}` : ""}`);
        fly({ kind: "trail", from: approveBtn.current, to: "#strip-after", duration: 0.8, arc: 120, glow: true });
        reload(); P.refresh();
        window.setTimeout(() => setResult(null), 2400);
      } else {
        setDlgErr("Records changed since this preview, so nothing was executed. Review the refreshed figures and try again.");
        reload();
        if (r.new_proposal_id) setDialog(null);
      }
    } catch (e: any) {
      setDlgErr(e.message || "The approval could not be completed. Nothing was changed.");
      P.flashOrb("error");
    } finally { setBusy(false); }
  };

  const cancelDecision = async () => {
    if (data?.proposal) {
      try { await api.post(`/api/proposals/${data.proposal.id}/cancel`); P.toast("info", "Cancelled. Nothing was changed."); P.flashOrb("cancelled"); reload(); }
      catch (e: any) { P.toast("error", e.message); }
    } else {
      P.flashOrb("cancelled");
      P.removeCard("claim_review");
    }
  };

  if (err) return <section className="card"><p className="error">Could not load the claim: {err}</p><button className="link" onClick={reload}>Retry</button></section>;
  if (!data) return (
    <div className="cr" aria-busy="true">
      <div className="skeleton" style={{ height: 300 }} /><div className="skeleton" style={{ height: 96 }} /><div className="skeleton" style={{ height: 110 }} />
    </div>
  );

  const rc = data.receipt;
  const cmp = data.comparison;
  const max = cmp ? Math.max(cmp.reserved_paise, cmp.claimed_paise) : 1;
  const allOk = data.checks.length > 0 && data.checks.every((c) => c.ok);
  const approved = data.status === "approved";
  const isSubmit = data.proposal?.kind === "submit_claim";
  const canAct = !!data.proposal || (data.status === "submitted" && !!data.ref);
  const actionLabel = isSubmit ? "Submit claim" : "Approve claim";
  const d = (s: number) => (reduced ? 0 : s);

  return (
    <div className="cr">
      {/* receipt */}
      <motion.div className="cr-receipt" initial={{ opacity: 0, x: 36, rotate: 1.5 }} animate={{ opacity: 1, x: 0, rotate: 0 }} transition={{ duration: 0.6, ease }}>
        <div className="paper" aria-label={`Receipt from ${rc?.vendor ?? "unknown vendor"}`}>
          <h3>{rc?.vendor ?? "Receipt"}</h3>
          <dl>
            {(data.employee || rc?.guest) && <><dt>Guest</dt><dd><strong>{rc?.guest ?? data.employee}</strong></dd></>}
            {rc?.date && <><dt>Date</dt><dd>{fmtDate(rc.date)}</dd></>}
            {data.reservation?.start && <><dt>Stay (trip)</dt><dd>{fmtDate(data.reservation.start)} – {fmtDate(data.reservation.end)}</dd></>}
            {rc?.invoice_no && <><dt>Invoice</dt><dd>{rc.invoice_no}</dd></>}
            {(rc?.items.length || rc?.taxes.length) ? <hr /> : null}
            {rc?.items.map((i, k) => <Fragment key={`i${k}`}><dt>{i.label}</dt><dd className="num">{i.amount}</dd></Fragment>)}
            {rc?.taxes.map((i, k) => <Fragment key={`t${k}`}><dt>{i.label}</dt><dd className="num">{i.amount}</dd></Fragment>)}
          </dl>
          <div className="total"><span>Total</span><span className="num">{rc?.total ?? "—"}</span></div>
          {/* scanning: once on reveal; continuously while the document is still being read */}
          <motion.div className="scanline" aria-hidden="true" initial={{ top: "-12%", opacity: 0 }}
            animate={data.extracted || !data.document ? { top: ["-12%", "105%"], opacity: [0, 1, 1, 0] } : { top: ["-12%", "105%"], opacity: [0, 1, 1, 0] }}
            transition={data.extracted || !data.document ? { duration: d(1.3), delay: d(0.35), ease: "easeInOut" } : { duration: 1.6, repeat: Infinity, ease: "easeInOut" }} />
        </div>
        {rc?.arithmetic === "mismatch" && <p className="flag flag-danger">The printed breakdown does not add up to the total.</p>}
        <button className="view-full" onClick={() => setFull(true)} disabled={!data.document} title={data.document ? undefined : "No source document on file"}>
          <ExternalLink size={16} /> View full receipt
        </button>
      </motion.div>

      {/* reservation match */}
      {data.reservation && (
        <motion.div className={`cr-block ${allOk ? "lit" : data.checks.some((c) => !c.ok) ? "mismatch" : ""}`} initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, delay: d(0.35), ease }}>
          <PurserDeskHelper pose={pose} />
          <h3>Reservation match</h3>
          <div className="match-row">
            <span className="match-icon"><CalendarDays size={22} /></span>
            <div>
              <div className="match-title">{data.reservation.trip ?? data.reservation.description}</div>
              <div className="match-sub">{data.reservation.kind} · {data.reservation.ref} · reserved {data.reservation.amount}</div>
            </div>
          </div>
          {data.checks.length > 0 && (
            <ul className="checks" aria-label="Matching evidence">
              {data.checks.map((c, i) => (
                <motion.li key={c.label} className={c.ok ? "" : "bad"} initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: d(0.9 + i * 0.12), type: "spring", stiffness: 400, damping: 22 }}>
                  {c.ok ? <Check size={12} /> : <TriangleAlert size={12} />} {c.label}
                </motion.li>
              ))}
            </ul>
          )}
        </motion.div>
      )}

      {/* comparison bars: same baseline, scaled to the larger amount */}
      {cmp && (
        <motion.div className="cr-block" initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, delay: d(0.55), ease }}>
          <h3>Claim comparison</h3>
          <div className="bars" role="img" aria-label={`Reserved ${data.reservation?.amount}, claimed ${rc?.total}`}>
            <span className="b-label">Reserved</span>
            <span className="track"><motion.i className="fill reserved" style={{ width: `${(cmp.reserved_paise / max) * 100}%` }}
              initial={{ scaleX: 0 }} animate={{ scaleX: 1 }} transition={{ duration: d(0.9), delay: d(0.85), ease }} /></span>
            <span className="b-amt num"><AnimatedCounter value={cmp.reserved_paise} from={0} duration={d(0.9) || 0.01} /></span>
            <span className="b-label">Claimed</span>
            <span className="track"><motion.i className={`fill ${cmp.below ? "claimed" : "over"}`} style={{ width: `${(cmp.claimed_paise / max) * 100}%` }}
              initial={{ scaleX: 0 }} animate={{ scaleX: 1 }} transition={{ duration: d(0.9), delay: d(1.0), ease }} /></span>
            <span className="b-amt num"><AnimatedCounter value={cmp.claimed_paise} from={0} duration={d(1.0) || 0.01} /></span>
          </div>
          <p className="hint">{cmp.below ? `${cmp.difference} below the reservation` : `${cmp.difference} above the reservation`}</p>
        </motion.div>
      )}

      {!cmp && !data.reservation && data.impact && (
        <div className="cr-block"><h3>Budget impact</h3><p className="num" style={{ margin: 0 }}>{data.impact.category} available {data.impact.before} → <strong>{data.impact.after}</strong></p></div>
      )}

      <AnimatePresence>
        {approved && (
          <motion.div className="cr-done" initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.4, ease }}>
            <CircleCheck size={22} />
            <span>Claim {data.ref} approved{data.impact?.receipt ? ` · ${data.impact.receipt}` : ""}. {data.impact ? `${data.impact.category} available is now ${data.impact.after}.` : ""}</span>
          </motion.div>
        )}
      </AnimatePresence>
      {!approved && data.status !== "submitted" && !data.proposal && data.status !== "receipt" && (
        <p className="cr-status">Status: <span className={`state state-${data.status}`}>{data.status}</span></p>
      )}

      {/* decision controls live in the panel footer (screenshot layout) */}
      {primary && slot && createPortal(
        <>
          <div className="approve-wrap">
            <motion.button ref={approveBtn} className="btn btn-ok" style={{ width: "100%" }} disabled={!canAct || busy || approved}
              onClick={openApproval} whileTap={{ scale: 0.97 }} aria-busy={busy}
              animate={result === "success" ? { boxShadow: ["0 0 0 0 rgba(140,240,191,.0)", "0 0 0 10px rgba(140,240,191,.25)", "0 0 40px 4px rgba(140,240,191,.35)"] } : {}}
              transition={{ duration: 0.9 }}>
              {approved ? <><Check size={18} /> Approved</> : busy && !dialog ? "Preparing…" : actionLabel}
            </motion.button>
            <AnimatePresence>{result === "success" && (
              <motion.span className="approve-ring" initial={{ opacity: 0.9, scale: 1 }} animate={{ opacity: 0, scale: 1.18 }} exit={{ opacity: 0 }} transition={{ duration: 1.1, ease }} />
            )}</AnimatePresence>
          </div>
          <button className="btn" onClick={cancelDecision} disabled={busy}>{approved ? "Close" : "Cancel"}</button>
        </>, slot)}

      <ConfirmationDialog open={!!dialog} title={dialog?.title ?? ""} lines={dialog?.lines ?? []} confirmLabel={isSubmit ? "Submit claim" : "Approve claim"}
        busy={busy} error={dlgErr} onConfirm={confirm} onCancel={() => { setDialog(null); setDlgErr(null); }}>
        <p className="fine" style={{ marginTop: -6 }}>Purser records the decision and updates the budget only after you confirm. No money moves.</p>
      </ConfirmationDialog>
      <AnimatePresence>{full && data.document && <Lightbox doc={data.document} onClose={() => setFull(false)} />}</AnimatePresence>
    </div>
  );
}
