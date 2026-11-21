// Gmail for the linked login: real inbox, search and threads (read-only here). Replies, archiving and labels are
// asked of Purser, so they go through the same preview -> confirm path as every other change.
import { motion } from "motion/react";
import { Archive, Mail, RefreshCw, Reply, Search, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../api";
import { reveal } from "../animations/tokens";
import { useAssistant } from "../components/assistant/PurserVoiceController";
import { useLoad } from "../state/store";

const FOLDERS = [
  { key: "in:inbox", label: "Inbox" },
  { key: "in:inbox is:unread", label: "Unread" },
  { key: "is:important newer_than:7d", label: "Important" },
  { key: "in:sent", label: "Sent" },
];

const when = (raw: string) => {
  const d = new Date(raw);
  return isNaN(+d) ? raw : d.toLocaleString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
};

export default function GmailPane() {
  const A = useAssistant();
  const [q, setQ] = useState("in:inbox");
  const [text, setText] = useState("");
  const [n, setN] = useState(0);
  const list = useLoad<any>(`/api/gmail?q=${encodeURIComponent(q)}&max=20`, n);
  const [sel, setSel] = useState<any>(null);
  const [thread, setThread] = useState<any>(null);
  const [terr, setTerr] = useState<string | null>(null);

  useEffect(() => {
    if (!sel) return;
    let live = true;
    setThread(null); setTerr(null);
    api.get<any>(`/api/gmail/thread/${sel.thread_id}`).then((t) => live && setThread(t)).catch((e) => live && setTerr(e.message));
    return () => { live = false; };
  }, [sel]);

  const ask = (u: string, el: Element) => A.send(u, el);
  const last = thread?.messages?.[thread.messages.length - 1];

  return (
    <div className="gmail">
      <div className="gm-bar">
        <div className="gm-folders" role="tablist" aria-label="Gmail folders">
          {FOLDERS.map((f) => (
            <button key={f.key} role="tab" aria-selected={q === f.key} className={`fl-tab ${q === f.key ? "on" : ""}`}
              onClick={() => { setQ(f.key); setSel(null); }}>{f.label}</button>
          ))}
        </div>
        <form className="gm-search" onSubmit={(e) => { e.preventDefault(); if (text.trim()) { setQ(text.trim()); setSel(null); } }}>
          <Search size={15} aria-hidden="true" />
          <label className="sr-only" htmlFor="gm-q">Search Gmail</label>
          <input id="gm-q" value={text} onChange={(e) => setText(e.target.value)} placeholder="Search mail (e.g. from:hdfc invoice)" />
        </form>
        <button className="icon-btn" aria-label="Refresh" onClick={() => setN((x) => x + 1)}><RefreshCw size={16} /></button>
      </div>
      <div className="gm-body">
        <div className="gm-list glass" aria-busy={!list.data && !list.err}>
          {list.err ? <p className="error" style={{ padding: 16 }}>{list.err}</p> : !list.data ? (
            [0, 1, 2, 3].map((i) => <div key={i} className="skeleton" style={{ height: 58, margin: 8 }} />)
          ) : list.data.messages.length === 0 ? <p className="hint" style={{ padding: 16 }}>No messages for “{q}”.</p> : (
            <ul>{list.data.messages.map((m: any, i: number) => (
              <motion.li key={m.id} variants={reveal} custom={i} initial="hidden" animate="show">
                <button className={`gm-item ${sel?.id === m.id ? "on" : ""} ${m.unread ? "unread" : ""}`} onClick={() => setSel(m)}>
                  <span className="gm-from">{m.from}{m.important && <span className="b-tag" style={{ marginLeft: 6 }}>important</span>}</span>
                  <span className="gm-date">{when(m.date)}</span>
                  <span className="gm-subj">{m.subject}</span>
                  <span className="gm-snip">{m.snippet}</span>
                </button>
              </motion.li>))}</ul>
          )}
        </div>
        <div className="gm-read glass">
          {!sel ? (
            <div className="empty-state"><Mail size={22} aria-hidden="true" /><p>Pick a message, or say “any important mails today?”</p></div>
          ) : terr ? <p className="error">{terr}</p> : !thread ? <div className="skeleton" style={{ height: 200 }} /> : (
            <>
              <h2 className="gm-h">{last?.subject}</h2>
              <div className="gm-actions">
                <button className="btn btn-sm" onClick={(e) => ask(`Summarise the email thread from ${sel.from} about "${sel.subject}"`, e.currentTarget)}>
                  <Sparkles size={14} /> Summarise</button>
                <button className="btn btn-sm" onClick={(e) => ask(`Draft a reply to ${sel.from} about "${sel.subject}" (thread ${sel.thread_id})`, e.currentTarget)}>
                  <Reply size={14} /> Reply with Purser</button>
                <button className="btn btn-sm" onClick={(e) => ask(`Archive the email from ${sel.from} about "${sel.subject}" (message ${sel.id})`, e.currentTarget)}>
                  <Archive size={14} /> Archive</button>
              </div>
              {thread.messages.map((m: any) => (
                <article key={m.id} className="gm-msg">
                  <div className="gm-msg-h"><strong>{m.from}</strong> <span className="fine">&lt;{m.from_email}&gt; · {when(m.date)}</span></div>
                  <p className="gm-text">{m.body || "(no text content)"}</p>
                </article>
              ))}
              <p className="fine">Replies and inbox changes go through Purser and need your “yes” before anything is sent or changed.</p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
