// Mail: inbox, sent, compose. Sending = server proposal -> confirmation -> confirm endpoint. While the confirm
// request runs, the message folds into an envelope that flies to the Mail icon; success shows only on a 2xx.
import { AnimatePresence, motion, useAnimate, useReducedMotion } from "motion/react";
import { CircleCheck, FilePen, Inbox, MailOpen, PenLine, RotateCcw, Send, Trash2 } from "lucide-react";
import { ReactElement, useEffect, useRef, useState } from "react";
import { api } from "../api";
import { ease, reveal } from "../animations/tokens";
import ConfirmationDialog from "../components/shared/ConfirmationDialog";
import { useFx } from "../components/shared/FxLayer";
import { useLoad, usePurser } from "../state/store";
import { ViewFrame } from "./ViewRouter";

type Draft = { id: string; to: number[]; subject: string; body: string; email: boolean; saved: string };
const DRAFTS_KEY = "purser.mail.drafts";
const loadDrafts = (): Draft[] => { try { return JSON.parse(localStorage.getItem(DRAFTS_KEY) || "[]"); } catch { return []; } };

const when = (iso: string) => new Date(iso).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });

export default function MailView() {
  const P = usePurser();
  const { fly } = useFx();
  const reduced = useReducedMotion();
  const [tab, setTab] = useState<"inbox" | "sent" | "drafts" | "compose">("inbox");
  const [sel, setSel] = useState<any>(null);
  const inbox = useLoad<any>("/api/inbox", P.bump);
  const sent = useLoad<any>("/api/messages/sent", P.bump);
  const people = useLoad<any>("/api/people");
  const [drafts, setDrafts] = useState<Draft[]>(loadDrafts);
  const [form, setForm] = useState<Draft>({ id: "", to: [], subject: "", body: "", email: false, saved: "" });
  const [touched, setTouched] = useState(false);
  const [dialog, setDialog] = useState<{ id: string; lines: string[]; title: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [phase, setPhase] = useState<"edit" | "sending" | "sent" | "failed">("edit");
  const [failMsg, setFailMsg] = useState<string | null>(null);
  const [scope, animate] = useAnimate();
  const composeRef = useRef<HTMLDivElement>(null);

  const errors = { to: form.to.length === 0 ? "Choose at least one recipient." : null, subject: !form.subject.trim() ? "Add a subject." : form.subject.length > 200 ? "Subject is too long." : null,
    body: !form.body.trim() ? "Write a message." : null };
  const valid = !errors.to && !errors.subject && !errors.body;

  const open = (m: any) => {
    setSel(m);
    if (m.unread) api.post(`/api/inbox/${m.ref}/read`).then(() => { inbox.reload(); P.reloadPriorities(); }).catch(() => {});
  };

  const saveDraft = async () => {
    const d = { ...form, id: form.id || `d${Date.now()}`, saved: new Date().toISOString() };
    const next = [d, ...drafts.filter((x) => x.id !== d.id)].slice(0, 10);
    setDrafts(next); localStorage.setItem(DRAFTS_KEY, JSON.stringify(next)); setForm(d);
    if (!reduced && composeRef.current) {
      await animate(composeRef.current, { scaleY: [1, 0.55, 1], scaleX: [1, 0.92, 1], borderRadius: ["18px", "8px", "18px"] }, { duration: 0.6, ease });
    }
    P.toast("info", "Draft saved on this device.");
  };

  const prepare = async () => {
    setTouched(true);
    if (!valid || busy) return;
    setBusy(true); setFailMsg(null);
    try {
      const r = await api.post<{ proposal_id: string; preview: { title: string; lines: string[] } }>("/api/messages/draft",
        { user_ids: form.to, subject: form.subject.trim(), body: form.body.trim(), email: form.email });
      setDialog({ id: r.proposal_id, lines: r.preview.lines, title: r.preview.title });
    } catch (e: any) { P.toast("error", e.message); P.flashOrb("error"); }
    finally { setBusy(false); }
  };

  const confirmSend = async () => {
    if (!dialog || phase === "sending") return;
    const pid = dialog.id;
    setDialog(null); setPhase("sending");
    const el = composeRef.current;
    // fold the message into an envelope, then let it fly to the sidebar Mail icon while the request runs
    const folding = !reduced && el ? animate(el, { scaleY: 0.06, scaleX: 0.3, opacity: 0.2, rotateX: 40 }, { duration: 0.42, ease }) : Promise.resolve();
    const req = api.post<any>(`/api/proposals/${pid}/confirm`);
    await folding;
    const flight = fly({ kind: "envelope", from: el, to: "#nav-mail", glow: true, duration: 1.0 });
    try {
      const r = await req;
      if (r.status !== "executed" && r.status !== "replayed") throw new Error("Recipients or records changed before sending. Nothing was sent; review and send again.");
      await flight;
      setPhase("sent");
      P.flashOrb("success");
      P.toast("success", r.receipt?.summary ?? "Message sent.");
      const rest = drafts.filter((x) => x.id !== form.id);
      setDrafts(rest); localStorage.setItem(DRAFTS_KEY, JSON.stringify(rest));
      setForm({ id: "", to: [], subject: "", body: "", email: false, saved: "" }); setTouched(false);
      P.refresh();
      window.setTimeout(() => { setPhase("edit"); setTab("sent"); }, 900);
    } catch (e: any) {
      await flight;
      setPhase("failed"); setFailMsg(e.message || "Sending failed. Your draft is kept.");
      P.flashOrb("error");
    } finally {
      if (el) animate(el, { scaleY: 1, scaleX: 1, opacity: 1, rotateX: 0 }, { duration: reduced ? 0 : 0.45, ease });
    }
  };

  useEffect(() => { if (tab !== "compose") setPhase("edit"); }, [tab]);

  const unread = (inbox.data?.messages ?? []).filter((m: any) => m.unread).length;
  const tabs: [typeof tab, string, ReactElement][] = [
    ["inbox", `Inbox${unread ? ` · ${unread}` : ""}`, <Inbox size={15} />], ["sent", "Sent", <Send size={15} />],
    ["drafts", `Drafts${drafts.length ? ` · ${drafts.length}` : ""}`, <FilePen size={15} />], ["compose", "Compose", <PenLine size={15} />],
  ];

  return (
    <ViewFrame title="Mail" sub="Your Purser inbox, announcements and messages. Email goes only to allow-listed demo addresses."
      actions={<div className="tabs" role="tablist">{tabs.map(([v, l, icon]) => (
        <button key={v} role="tab" aria-selected={tab === v} className="tab" onClick={() => { setTab(v); setSel(null); }}>
          {tab === v && <motion.span layoutId="mail-tab" className="tab-pill" transition={{ type: "spring", stiffness: 420, damping: 34 }} />}
          <span style={{ display: "inline-flex", gap: 6, alignItems: "center" }}>{icon}{l}</span>
        </button>))}</div>}>
      <div ref={scope}>
        {tab === "compose" ? (
          <div style={{ perspective: 900, maxWidth: 760 }}>
            <div ref={composeRef} className="compose glass" style={{ transformOrigin: "50% 30%" }}>
              <div className="field"><span>To</span>
                {people.data ? <div className="recips" role="group" aria-label="Recipients">{people.data.people.map((u: any) => (
                  <button key={u.id} className="recip" aria-pressed={form.to.includes(u.id)}
                    onClick={() => setForm((f) => ({ ...f, to: f.to.includes(u.id) ? f.to.filter((x) => x !== u.id) : [...f.to, u.id] }))}>{u.name}</button>))}</div>
                  : <div className="skeleton" style={{ height: 34 }} />}
                {touched && errors.to && <span className="invalid">{errors.to}</span>}
              </div>
              <label className="field"><span>Subject</span><input value={form.subject} maxLength={200} onChange={(e) => setForm({ ...form, subject: e.target.value })} />
                {touched && errors.subject && <span className="invalid">{errors.subject}</span>}</label>
              <label className="field"><span>Message</span><textarea value={form.body} onChange={(e) => setForm({ ...form, body: e.target.value })} />
                {touched && errors.body && <span className="invalid">{errors.body}</span>}</label>
              <label className="toggle"><input type="checkbox" checked={form.email} onChange={(e) => setForm({ ...form, email: e.target.checked })} /> Also send by email (allow-listed addresses only)</label>
              <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                <button className="btn btn-primary" onClick={prepare} disabled={busy || phase === "sending"}><Send size={16} /> {busy ? "Preparing…" : "Send"}</button>
                <button className="btn" onClick={saveDraft} disabled={phase === "sending" || (!form.subject && !form.body)}>Save draft</button>
                <AnimatePresence mode="wait">
                  {phase === "sending" && <motion.span key="s" className="fine" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>Sending…</motion.span>}
                  {phase === "sent" && <motion.span key="ok" className="fine" style={{ color: "var(--mint)", display: "inline-flex", gap: 6 }} initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }}><CircleCheck size={16} /> Delivered</motion.span>}
                </AnimatePresence>
              </div>
              {phase === "failed" && <div className="flag flag-danger" role="alert" style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <span style={{ flex: 1 }}>{failMsg} Your draft is kept.</span><button className="btn btn-sm" onClick={prepare}><RotateCcw size={14} /> Retry</button></div>}
            </div>
          </div>
        ) : tab === "drafts" ? (
          drafts.length === 0 ? <div className="glass empty-state">No drafts saved on this device.</div> : (
            <motion.ul className="rows glass" initial="hidden" animate="show"><AnimatePresence>{drafts.map((d, i) => (
              <motion.li key={d.id} variants={reveal} custom={i} exit={{ opacity: 0, scale: 0.95, filter: "blur(6px)", transition: { duration: 0.3 } }} className="row">
                <button style={{ textAlign: "left" }} onClick={() => { setForm(d); setTab("compose"); }}><span className="r-title">{d.subject || "(no subject)"}</span><div className="r-sub">{d.body.slice(0, 80)}</div></button>
                <span className="fine">{when(d.saved)}</span>
                <button className="icon-btn" aria-label={`Delete draft ${d.subject}`} onClick={() => { const rest = drafts.filter((x) => x.id !== d.id); setDrafts(rest); localStorage.setItem(DRAFTS_KEY, JSON.stringify(rest)); }}><Trash2 size={16} /></button>
              </motion.li>))}</AnimatePresence></motion.ul>)
        ) : (
          <div className="mail">
            <div className="mail-list glass" role="listbox" aria-label={tab === "inbox" ? "Inbox" : "Sent"}>
              {(tab === "inbox" ? inbox : sent).err ? <p className="error" style={{ padding: 16 }}>{(tab === "inbox" ? inbox : sent).err}</p>
                : !(tab === "inbox" ? inbox : sent).data ? <div style={{ padding: 12 }}><div className="skeleton" style={{ height: 200 }} /></div>
                : ((tab === "inbox" ? inbox.data.messages : sent.data.messages) as any[]).length === 0 ? <p className="empty-state">{tab === "inbox" ? "Inbox is empty." : "Nothing sent yet."}</p>
                : <AnimatePresence initial={false}>{((tab === "inbox" ? inbox.data.messages : sent.data.messages) as any[]).map((m) => (
                  <motion.button key={m.ref} layout role="option" aria-selected={sel?.ref === m.ref} className={`mail-item ${m.unread ? "unread" : ""}`} onClick={() => open(m)}
                    initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.3, ease }}>
                    <span className="dot" /><span style={{ minWidth: 0 }}><div className="m-subj">{m.subject}</div><div className="m-from">{tab === "inbox" ? m.from : `to ${m.to.join(", ")}`}</div></span>
                    <span className="m-time">{when(m.at)}</span>
                  </motion.button>))}</AnimatePresence>}
            </div>
            <div style={{ perspective: 1000 }}>
              <AnimatePresence mode="wait">
                {sel ? (
                  <motion.article key={sel.ref} className="mail-read glass" initial={{ opacity: 0, rotateX: -55, scaleY: 0.4 }} animate={{ opacity: 1, rotateX: 0, scaleY: 1 }}
                    exit={{ opacity: 0, scaleY: 0.6, transition: { duration: 0.2 } }} transition={{ duration: 0.55, ease }}>
                    <h2>{sel.subject}</h2>
                    <div className="meta">{tab === "inbox" ? `From ${sel.from}` : `To ${sel.to.join(", ")}`} · {when(sel.at)} · <span className="ref">{sel.ref}</span>
                      {tab === "sent" && sel.email?.length > 0 && <> · email {sel.email.map((x: any) => x.status).join(", ")}</>}</div>
                    <div className="body">{sel.body}</div>
                  </motion.article>
                ) : (
                  <motion.div key="none" className="glass empty-state" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                    <MailOpen size={28} style={{ marginBottom: 8 }} /><div>Select a message to open it.</div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        )}
      </div>
      <ConfirmationDialog open={!!dialog} title={dialog?.title ?? "Send message"} lines={dialog?.lines ?? []} confirmLabel="Send now" busy={false}
        onConfirm={confirmSend} onCancel={() => { if (dialog) api.post(`/api/proposals/${dialog.id}/cancel`).catch(() => {}); setDialog(null); }} />
    </ViewFrame>
  );
}
