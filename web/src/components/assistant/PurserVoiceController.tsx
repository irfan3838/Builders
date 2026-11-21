// PurserVoiceController: owns the conversation, the server event stream, the live voice session, the wake word,
// typed turns and document uploads. It maps real events onto the orb state; it never invents results.
import { createContext, ReactNode, useCallback, useContext, useEffect, useRef, useState } from "react";
import { api, ApiError, Card, setConversation } from "../../api";
import { LiveVoice } from "../../services/purserVoice";
import { WakeWord, wakeSupported } from "../../services/wakeWord";
import { OrbState, usePurser } from "../../state/store";
import { useFx } from "../shared/FxLayer";

const IDLE_CLOSE_MS = 30_000;
const HANDSFREE_KEY = "purser.handsfree";
export const ACCEPT = ["application/pdf", "image/jpeg", "image/png", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"];
export const ACCEPT_ATTR = "application/pdf,image/jpeg,image/png,.docx," + ACCEPT[3];
const MAX_BYTES = 25 * 1024 * 1024;

export type VoiceMode = "off" | "asleep" | "waking" | "connecting" | "idle" | "listening" | "speaking" | "error" | "denied";

type Assistant = {
  ready: boolean;
  voice: VoiceMode;
  handsFree: boolean;
  setHandsFree: (v: boolean) => void;
  toggleVoice: () => void;
  level: () => number;
  sending: boolean;
  send: (text: string, from?: Element | null) => Promise<boolean>;
  cancel: () => void;
  upload: (files: File[], from?: Element | null) => void;
  lastFailed: string | null;
};

const AssistantContext = createContext<Assistant | null>(null);
export const useAssistant = () => {
  const c = useContext(AssistantContext);
  if (!c) throw new Error("useAssistant outside PurserVoiceController");
  return c;
};

/** Validate before any bytes leave the browser. */
export function validateFile(f: File): string | null {
  const okType = ACCEPT.includes(f.type) || /\.(pdf|jpe?g|png|docx)$/i.test(f.name);
  if (!okType) return `${f.name}: unsupported type. Use PDF, JPEG, PNG or DOCX.`;
  if (f.size > MAX_BYTES) return `${f.name} is ${(f.size / 1048576).toFixed(1)} MB; the limit is 25 MB.`;
  if (f.size === 0) return `${f.name} is empty.`;
  return null;
}

export function PurserVoiceController({ children }: { children: ReactNode }) {
  const P = usePurser();
  const { fly } = useFx();
  const [ready, setReady] = useState(false);
  const [voice, setVoice] = useState<VoiceMode>("off");
  const [handsFree, setHandsFreeState] = useState(() => wakeSupported && !!localStorage.getItem(HANDSFREE_KEY));
  const [sending, setSending] = useState(false);
  const [lastFailed, setLastFailed] = useState<string | null>(null);
  const live = useRef<LiveVoice | null>(null);
  const wake = useRef<WakeWord | null>(null);
  const idleTimer = useRef<number | undefined>(undefined);
  const abort = useRef<AbortController | null>(null);
  const turnsInFlight = useRef(0);
  const { setBaseOrb, say, addCards, flashOrb, toast, refresh, busy } = P;

  // ---- audio level for the orb: mic while listening, Purser's voice while speaking
  const audio = useRef<{ ctx?: AudioContext; an?: AnalyserNode; src?: MediaStreamAudioSourceNode; stream?: MediaStream; buf: Uint8Array<ArrayBuffer> }>({ buf: new Uint8Array(256) });
  const voiceRef = useRef(voice);
  voiceRef.current = voice;
  const level = useCallback(() => {
    const a = audio.current;
    const v = voiceRef.current;
    const want = v === "speaking" ? live.current?.outStream : v === "listening" ? live.current?.micStream : undefined;
    if (want !== a.stream) {
      a.src?.disconnect(); a.src = undefined; a.stream = want;
      if (want && want.getAudioTracks().length) {
        a.ctx ??= new AudioContext();
        a.an ??= Object.assign(a.ctx.createAnalyser(), { fftSize: 512, smoothingTimeConstant: 0.6 });
        a.src = a.ctx.createMediaStreamSource(want); a.src.connect(a.an);
      }
    }
    if (!a.an || !a.src) return 0;
    a.an.getByteTimeDomainData(a.buf);
    let sum = 0;
    for (const x of a.buf) { const d = (x - 128) / 128; sum += d * d; }
    return Math.min(1, Math.sqrt(sum / a.buf.length) * 4.5);
  }, []);

  // ---- orb base state from real activity
  useEffect(() => {
    const map: Record<VoiceMode, OrbState> = { off: "idle", asleep: "asleep", waking: "connecting", connecting: "connecting", idle: "idle",
      listening: "listening", speaking: "speaking", error: "error", denied: "error" };
    setBaseOrb(sending ? "processing" : map[voice]);
  }, [voice, sending, setBaseOrb]);

  // ---- conversation + server events
  useEffect(() => {
    let es: EventSource | null = null;
    let closed = false;
    const open = () => api.post<{ conversation_id: string }>("/api/conversations").then(({ conversation_id }) => {
      if (closed) return;
      setConversation(conversation_id); setReady(true);
      es = new EventSource(`/api/events?conversation_id=${conversation_id}`);
      es.onmessage = (m) => {
        const ev = JSON.parse(m.data);
        if (ev.type === "card") addCards([ev]);
        else if (ev.type === "user_turn") { turnsInFlight.current++; busy.current++; setSending(true); }
        else if (ev.type === "assistant_turn") {
          turnsInFlight.current = Math.max(0, turnsInFlight.current - 1);
          busy.current = Math.max(0, busy.current - 1);
          if (ev.text) say("purser", ev.text);
          if (!turnsInFlight.current && !abort.current) setSending(false);
          refresh();
        }
      };
    }).catch((e) => { if (!closed) { toast("error", `Could not start a Purser session: ${e.message}`, { label: "Retry", run: open }); } });
    open();
    return () => { closed = true; es?.close(); };
  }, [addCards, say, refresh, toast, busy]);

  // ---- live voice session + wake word
  const sleep = useCallback(() => {
    clearTimeout(idleTimer.current);
    if (wakeSupported && localStorage.getItem(HANDSFREE_KEY)) { setVoice("asleep"); wake.current?.start(); } else setVoice("off");
  }, []);

  const touch = useCallback(() => {
    clearTimeout(idleTimer.current);
    const check = () => {
      if (busy.current > 0) { idleTimer.current = window.setTimeout(check, 5_000); return; }
      live.current?.stop();
    };
    idleTimer.current = window.setTimeout(check, IDLE_CLOSE_MS);
  }, [busy]);

  const wakeUp = useCallback(async (rest = "") => {
    if (live.current?.active) return;
    wake.current?.stop();
    setVoice("waking");
    if (rest) say("user", rest);
    const v = new LiveVoice((s) => {
      if (s === "idle") { live.current = null; sleep(); return; }
      if (s === "error") {
        const denied = v.denied;
        live.current = null;
        setVoice(denied ? "denied" : "error");
        flashOrb("error");
        toast("error", denied ? "Microphone access is blocked. Allow it in the browser's site settings, then tap the mic." : "Voice is unavailable right now. You can type instead.",
          denied ? undefined : { label: "Retry", run: () => wakeUp() });
        return;
      }
      setVoice(s);
    }, (who, d) => say(who, d, true));
    v.onActivity = touch;
    live.current = v;
    await v.start(rest);
    touch();
  }, [say, sleep, touch, flashOrb, toast]);

  useEffect(() => {
    wake.current = new WakeWord((rest) => wakeUp(rest), (msg) => { localStorage.removeItem(HANDSFREE_KEY); setHandsFreeState(false); setVoice("denied"); toast("error", msg); });
    if (wakeSupported && localStorage.getItem(HANDSFREE_KEY)) { setVoice("asleep"); wake.current.start(); }
    return () => { wake.current?.stop(); live.current?.stop(); };
  }, [wakeUp, toast]);

  const setHandsFree = useCallback(async (on: boolean) => {
    if (on) {
      if (!wakeSupported) { toast("info", "Hands-free wake word needs Chrome or Edge. Tap the orb to talk instead."); return; }
      try { (await navigator.mediaDevices.getUserMedia({ audio: true })).getTracks().forEach((t) => t.stop()); }
      catch { setVoice("denied"); toast("error", "Microphone access is blocked. Allow it in the browser's site settings."); return; }
      localStorage.setItem(HANDSFREE_KEY, "1"); setHandsFreeState(true);
      if (!live.current?.active) { setVoice("asleep"); wake.current?.start(); }
    } else {
      localStorage.removeItem(HANDSFREE_KEY); setHandsFreeState(false); wake.current?.stop();
      if (!live.current?.active) setVoice("off");
    }
  }, [toast]);

  const toggleVoice = useCallback(() => {
    if (live.current?.active) { live.current.stop(); flashOrb("cancelled"); return; }
    wakeUp();
  }, [wakeUp, flashOrb]);

  // ---- typed turn
  const send = useCallback(async (text: string, from?: Element | null) => {
    const t = text.trim();
    if (!t || !ready) return false;
    say("user", t);
    setLastFailed(null);
    fly({ kind: "trail", from, to: "#purser-orb" });
    const ctl = new AbortController();
    abort.current = ctl; setSending(true); busy.current++;
    try {
      const r = await api.post<{ reply: string; ui: Card[] }>("/api/agent/text", { text: t }, ctl.signal);
      say("purser", r.reply);
      addCards(r.ui);
      refresh();
      return true;
    } catch (e: any) {
      if (e?.name === "AbortError") { say("app", "Cancelled. Nothing was changed."); flashOrb("cancelled"); return false; }
      setLastFailed(t);
      say("app", e instanceof ApiError && e.status === 401 ? "Your session expired. Sign in again." : e.message);
      flashOrb("error");
      return false;
    } finally {
      busy.current = Math.max(0, busy.current - 1);
      abort.current = null;
      if (!turnsInFlight.current) setSending(false);
    }
  }, [ready, say, fly, addCards, refresh, flashOrb, busy]);

  const cancel = useCallback(() => { abort.current?.abort(); }, []);

  // ---- uploads: real byte progress, then the agent reads the document (scan line) until the server answers
  const upload = useCallback((files: File[], from?: Element | null) => {
    for (const f of files) {
      const bad = validateFile(f);
      if (bad) { toast("error", bad); flashOrb("error"); continue; }
      const key = `up-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
      const ctl = new AbortController();
      P.setUploads((u) => [...u, { key, name: f.name, size: f.size, progress: 0, status: "uploading", cancel: () => ctl.abort() }]);
      P.setPanelOpen(true);
      fly({ kind: "sheet", from, to: "#artifact-panel" });
      say("app", `Reading ${f.name}…`);
      busy.current++; touch(); setSending(true);
      const patch = (p: Partial<{ progress: number; status: "uploading" | "reading" | "error" | "done"; error: string }>) =>
        P.setUploads((u) => u.map((x) => (x.key === key ? { ...x, ...p } : x)));
      api.upload<any>("/api/documents?announce=true", f, (p) => patch({ progress: p, status: p >= 1 ? "reading" : "uploading" }), ctl.signal)
        .then((r) => {
          if (r.outcome !== "accepted" && r.outcome !== "exact_replay") {
            patch({ status: "error", error: r.message || r.outcome });
            say("app", r.message || "That file could not be used."); flashOrb("error");
            return;
          }
          P.setUploads((u) => u.filter((x) => x.key !== key));
          const cards: Card[] = [];
          if (r.document_id) cards.push({ card: "source", document_id: r.document_id, highlight: [] });
          addCards([...cards, ...(r.ui || [])]);
          if (r.reply) say("purser", r.reply);
          refresh();
        })
        .catch((e) => {
          if (e?.name === "AbortError") { P.setUploads((u) => u.filter((x) => x.key !== key)); say("app", `Upload of ${f.name} cancelled.`); flashOrb("cancelled"); return; }
          patch({ status: "error", error: e.message }); say("app", `Upload failed: ${e.message}`); flashOrb("error");
        })
        .finally(() => { busy.current = Math.max(0, busy.current - 1); touch(); if (!turnsInFlight.current && !abort.current) setSending(false); });
    }
  }, [P, fly, say, touch, addCards, refresh, flashOrb, toast, busy]);

  return (
    <AssistantContext.Provider value={{ ready, voice, handsFree, setHandsFree, toggleVoice, level, sending, send, cancel, upload, lastFailed }}>
      {children}
    </AssistantContext.Provider>
  );
}
