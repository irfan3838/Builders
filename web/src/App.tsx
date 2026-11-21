import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError, Card, Me, setConversation, setSession } from "./api";
import { CardView, cardKey } from "./cards";
import { LiveVoice, VoiceState } from "./voice";
import { WakeWord, wakeSupported } from "./wake";
import Orb from "./Orb";

type Mode = "off" | "asleep" | "waking" | VoiceState | "thinking";
const IDLE_CLOSE_MS = 30_000; // close the live session after 30 s of silence and go back to wake-word listening
const HANDSFREE_KEY = "munshi.handsfree";

function Login({ onDone }: { onDone: (m: Me) => void }) {
  const [email, setEmail] = useState("priya@munshi.demo");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const submit = async (e: React.FormEvent) => {
    e.preventDefault(); setErr(null);
    try {
      const r = await api.post<{ user: any; csrf: string }>("/api/auth/login", { email, password });
      setSession(r.csrf); onDone({ ...r.user, csrf: r.csrf });
    } catch (e: any) { setErr(e instanceof ApiError && e.status === 401 ? "Email or password is incorrect." : e.message); }
  };
  return (
    <main className="login">
      <form onSubmit={submit} aria-label="Sign in to Munshi">
        <p className="wordmark">munshi</p>
        <label>Email<input type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} required /></label>
        <label>Password<input type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required /></label>
        {err && <p className="error" role="alert">{err}</p>}
        <button className="btn btn-primary" type="submit">Sign in</button>
        <p className="fine">Demo workspace with synthetic data.</p>
      </form>
    </main>
  );
}

const STATUS: Record<Mode, string> = {
  off: "Tap to turn on hands-free",
  asleep: "Say “Munshi”",
  waking: "Haan ji…",
  connecting: "Connecting…",
  idle: "Say “Munshi”",
  listening: "Listening",
  thinking: "Checking the books",
  speaking: "Speaking",
  error: "Voice unavailable — tap to retry",
};

function Desk({ me }: { me: Me }) {
  const [mode, setMode] = useState<Mode>("off");
  const [line, setLine] = useState<{ who: "user" | "munshi" | "app"; text: string } | null>(null);
  const [cards, setCards] = useState<Card[]>([]);
  const [bump, setBump] = useState(0);
  const [panel, setPanel] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [typing, setTyping] = useState(false);
  const [text, setText] = useState("");
  const [convo, setConvo] = useState<string | null>(null);
  const live = useRef<LiveVoice | null>(null);
  const wake = useRef<WakeWord | null>(null);
  const idleTimer = useRef<number | undefined>(undefined);
  const fileInput = useRef<HTMLInputElement>(null);
  const streams = useCallback(() => ({ mic: live.current?.micStream, out: live.current?.outStream }), []);

  const addCards = useCallback((incoming: Card[]) => {
    if (!incoming.length) return;
    setCards((prev) => {
      const keys = new Set(incoming.map(cardKey));
      return [...[...incoming].reverse(), ...prev.filter((c) => !keys.has(cardKey(c)))].slice(0, 10);
    });
    setBump((b) => b + 1);
    setPanel(true);
  }, []);

  const say = useCallback((who: "user" | "munshi" | "app", delta: string, append = true) => {
    setLine((prev) => (append && prev && prev.who === who ? { who, text: prev.text + delta } : { who, text: delta }));
  }, []);

  // ---- conversation + server events
  useEffect(() => {
    let es: EventSource | null = null;
    api.post<{ conversation_id: string }>("/api/conversations").then(({ conversation_id }) => {
      setConversation(conversation_id); setConvo(conversation_id);
      es = new EventSource(`/api/events?conversation_id=${conversation_id}`);
      es.onmessage = (m) => {
        const ev = JSON.parse(m.data);
        if (ev.type === "card") addCards([ev]);
        else if (ev.type === "user_turn") { busy.current++; setMode("thinking"); }
        else if (ev.type === "assistant_turn") {
          busy.current = Math.max(0, busy.current - 1);
          if (ev.text) setLine({ who: "munshi", text: ev.text });
          setMode((v) => (v === "thinking" ? "listening" : v)); setBump((b) => b + 1);
        }
      };
    });
    return () => es?.close();
  }, [addCards]);

  // ---- wake word -> live session -> back to sleep after silence
  const sleep = useCallback(() => {
    clearTimeout(idleTimer.current);
    if (wakeSupported && localStorage.getItem(HANDSFREE_KEY)) { setMode("asleep"); wake.current?.start(); }
    else setMode("off");
  }, []);

  const busy = useRef(0); // uploads / agent turns in flight: never close the voice session under them
  const touch = useCallback(() => {
    clearTimeout(idleTimer.current);
    const check = () => {
      if (busy.current > 0) { idleTimer.current = window.setTimeout(check, 5_000); return; }
      live.current?.stop();
    };
    idleTimer.current = window.setTimeout(check, IDLE_CLOSE_MS);
  }, []);

  const wakeUp = useCallback(async (rest = "") => {
    if (live.current?.active) return;
    wake.current?.stop();
    setMode("waking");
    if (rest) say("user", rest, false);
    const v = new LiveVoice((s) => {
      if (s === "idle") { live.current = null; sleep(); return; }
      setMode(s);
    }, (who, d) => say(who, d));
    v.onActivity = touch;
    live.current = v;
    await v.start(rest);
    touch();
  }, [say, sleep, touch]);

  useEffect(() => {
    wake.current = new WakeWord((rest) => wakeUp(rest), () => { localStorage.removeItem(HANDSFREE_KEY); setMode("off"); });
    if (wakeSupported && localStorage.getItem(HANDSFREE_KEY)) { setMode("asleep"); wake.current.start(); }
    return () => { wake.current?.stop(); live.current?.stop(); };
  }, [wakeUp]);

  const orb = async () => {
    if (live.current?.active) { live.current.stop(); return; }
    if (mode === "off" && wakeSupported) {
      try { (await navigator.mediaDevices.getUserMedia({ audio: true })).getTracks().forEach((t) => t.stop()); } catch { return; }
      localStorage.setItem(HANDSFREE_KEY, "1");
    }
    wakeUp();
  };

  // ---- typing + upload fallbacks
  const send = async (e: React.FormEvent) => {
    e.preventDefault();
    const t = text.trim(); if (!t) return;
    setText(""); say("user", t, false); setMode((m) => (live.current?.active ? m : "thinking"));
    try {
      const r = await api.post<{ reply: string; ui: Card[] }>("/api/agent/text", { text: t });
      say("munshi", r.reply, false); addCards(r.ui);
    } catch (err: any) { say("app", err.message, false); } finally { setMode((m) => (m === "thinking" && !live.current?.active ? (localStorage.getItem(HANDSFREE_KEY) ? "asleep" : "off") : m)); }
  };

  const upload = async (f: File) => {
    say("app", `Reading ${f.name}…`, false);
    const wasLive = live.current?.active;
    busy.current++; touch();
    setMode("thinking");
    try {
      const r = await api.upload<any>("/api/documents?announce=true", f);
      if (r.document_id) addCards([{ card: "source", document_id: r.document_id, highlight: [] }]);
      if (r.reply) say("munshi", r.reply, false); else if (r.outcome !== "accepted") say("app", r.message, false);
      addCards(r.ui || []);
    } catch (err: any) { say("app", `Upload failed: ${err.message}`, false); }
    finally {
      busy.current--; touch();
      if (live.current?.active) setMode("listening");
      else if (!wasLive) setMode(localStorage.getItem(HANDSFREE_KEY) && wakeSupported ? "asleep" : "off");
    }
  };

  useEffect(() => {
    const over = (e: DragEvent) => { if (e.dataTransfer?.types.includes("Files")) { e.preventDefault(); setDragging(true); } };
    const leave = (e: DragEvent) => { if (!e.relatedTarget) setDragging(false); };
    const drop = (e: DragEvent) => { e.preventDefault(); setDragging(false); const f = e.dataTransfer?.files[0]; if (f) upload(f); };
    window.addEventListener("dragover", over); window.addEventListener("dragleave", leave); window.addEventListener("drop", drop);
    return () => { window.removeEventListener("dragover", over); window.removeEventListener("dragleave", leave); window.removeEventListener("drop", drop); };
  });

  const active = ["connecting", "waking", "listening", "speaking", "thinking"].includes(mode);
  return (
    <div className={`stage ${panel && cards.length ? "with-panel" : ""}`}>
      <header className="bar">
        <span className="wordmark">munshi</span>
        <span className="fine">synthetic demo data</span>
        <span className="me" title={me.role === "finance_approver" ? "Finance approver" : "Employee"}>{me.name}</span>
      </header>

      <main className="center">
        <Orb mode={mode} onClick={orb} disabled={!convo} pressed={active} streams={streams}
          label={active ? "Stop listening" : mode === "off" ? "Turn on hands-free voice" : "Wake Munshi"} />
        <p className="status" aria-live="polite">{STATUS[mode]}</p>
        <p className={`line ${line?.who ?? ""}`} aria-live="polite">{line?.text ?? ""}</p>

        <div className="tools">
          <button className="icon" onClick={() => fileInput.current?.click()} aria-label="Give Munshi a receipt or bill" title="Receipt or bill">
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M21 12.5 12.6 21a5.5 5.5 0 0 1-7.8-7.8l8.5-8.5a3.7 3.7 0 0 1 5.2 5.2l-8.5 8.5a1.8 1.8 0 0 1-2.6-2.6l7.9-7.9" /></svg>
          </button>
          <button className="icon" onClick={() => setTyping((t) => !t)} aria-label="Type instead" aria-expanded={typing} title="Type instead">
            <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="6" width="18" height="12" rx="2" /><path d="M7 10h.01M11 10h.01M15 10h.01M7 14h10" /></svg>
          </button>
          {cards.length > 0 && !panel && (
            <button className="icon" onClick={() => setPanel(true)} aria-label={`Show ${cards.length} artifacts`} title="Artifacts">
              <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="4" y="4" width="16" height="16" rx="3" /><path d="M14 4v16" /></svg>
            </button>
          )}
        </div>
        {typing && (
          <form className="type" onSubmit={send}>
            <label className="sr-only" htmlFor="say">Message Munshi</label>
            <input id="say" autoFocus value={text} onChange={(e) => setText(e.target.value)} placeholder="Travel budget kitna bacha hai?" />
          </form>
        )}
        <input ref={fileInput} type="file" accept="application/pdf,image/jpeg,image/png" hidden
          onChange={(e) => { const f = e.target.files?.[0]; if (f) upload(f); e.target.value = ""; }} />
      </main>

      {panel && cards.length > 0 && (
        <aside className="panel" aria-label="Artifacts">
          <div className="panel-head">
            <span>Artifacts</span>
            <button className="icon small" onClick={() => setPanel(false)} aria-label="Hide artifacts">
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18" /></svg>
            </button>
          </div>
          <div className="panel-body">
            {cards.map((c) => <CardView key={cardKey(c)} card={c} bump={bump} onChanged={() => setBump((b) => b + 1)} />)}
          </div>
        </aside>
      )}

      {dragging && <div className="dropveil" aria-hidden="true"><p>Drop to hand it to Munshi</p></div>}
    </div>
  );
}

export default function App() {
  const [me, setMe] = useState<Me | null | undefined>(undefined);
  useEffect(() => { api.get<Me>("/api/me").then((m) => { setSession(m.csrf); setMe(m); }).catch(() => setMe(null)); }, []);
  if (me === undefined) return null;
  return me ? <Desk me={me} /> : <Login onDone={setMe} />;
}
