// Application state for the Purser workspace: route, artifact cards, orb state, captions, toasts, priorities.
// Financial facts are never stored here as truth: cards and views reload them from the server by reference.
import { createContext, ReactNode, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { api, Card, Me } from "../api";
import { cardKey } from "../cards";

export type View = "workspace" | "dashboards" | "mail" | "expenses" | "travel" | "claims" | "payments" | "budgets" | "reports" | "tasks" | "helpdesk";
export const VIEWS: View[] = ["workspace", "dashboards", "mail", "expenses", "travel", "claims", "payments", "budgets", "reports", "tasks", "helpdesk"];

/** Base voice/agent state comes from real events; success/error/cancelled are short feedback overlays. */
export type OrbState = "idle" | "asleep" | "connecting" | "listening" | "processing" | "speaking" | "success" | "error" | "cancelled";
export type Who = "user" | "purser" | "app";
export type Caption = { who: Who; text: string; id: number } | null;
export type ToastKind = "success" | "error" | "info";
export type Toast = { id: number; kind: ToastKind; text: string; action?: { label: string; run: () => void } };
export type Priorities = { approvals: number; reimbursements: number; budget_alerts: number; claims_pending: number; unread_mail: number };
export type Suggestion = { label: string; utterance: string };
export type UploadItem = { key: string; name: string; size: number; progress: number; status: "uploading" | "reading" | "error" | "done"; error?: string; cancel?: () => void };

/** What the decision strip shows: set by the claim review artifact currently in focus. */
export type Decision = {
  ref: string | null; status: string; reservation: string | null; differencePaise: number | null; below: boolean | null;
  category: string | null; beforePaise: number | null; afterPaise: number | null; final: boolean; approvedAt?: number; proposalId?: string | null;
} | null;

/** An MCQ clarification from Purser (ask_choice): shown above the composer until answered. */
export type Choice = { id: string; question: string; options: { label: string; value: string }[]; step: number; max: number; answered?: string } | null;

type Ctx = {
  me: Me;
  view: View; go: (v: View) => void;
  cards: Card[]; addCards: (c: Card[]) => void; removeCard: (key: string) => void; clearCards: () => void;
  panelOpen: boolean; setPanelOpen: (v: boolean) => void;
  /** Bumped whenever a batch of Desk cards lands; `newKeys` are the cards in that batch (newest on top). */
  lastBatch: number; newKeys: Set<string>;
  /** True while the newest action is the claim under review (it owns the Desk footer and the decision strip). */
  claimFocus: boolean;
  bump: number; refresh: () => void;
  baseOrb: OrbState; setBaseOrb: (s: OrbState) => void; orb: OrbState; flashOrb: (s: "success" | "error" | "cancelled") => void;
  caption: Caption; say: (who: Who, text: string, append?: boolean) => void;
  toasts: Toast[]; toast: (kind: ToastKind, text: string, action?: Toast["action"]) => void; dismissToast: (id: number) => void;
  priorities: Priorities | null; reloadPriorities: () => void;
  decision: Decision; setDecision: (d: Decision) => void;
  uploads: UploadItem[]; setUploads: React.Dispatch<React.SetStateAction<UploadItem[]>>;
  suggestions: Suggestion[]; setSuggestions: (s: Suggestion[]) => void;
  choice: Choice; setChoice: React.Dispatch<React.SetStateAction<Choice>>;
  busy: React.MutableRefObject<number>;
  online: boolean;
};

const PurserContext = createContext<Ctx | null>(null);
export const usePurser = () => {
  const c = useContext(PurserContext);
  if (!c) throw new Error("usePurser outside provider");
  return c;
};

const viewFromHash = (): View => {
  const v = location.hash.replace(/^#\/?/, "").split("?")[0] as View;
  return VIEWS.includes(v) ? v : "workspace";
};

export function PurserProvider({ me, children }: { me: Me; children: ReactNode }) {
  const [view, setView] = useState<View>(viewFromHash);
  const [cards, setCards] = useState<Card[]>([]);
  const [panelOpen, setPanelOpenState] = useState(false);
  const [lastBatch, setLastBatch] = useState(0);
  const [newKeys, setNewKeys] = useState<Set<string>>(() => new Set());
  const [claimFocus, setClaimFocus] = useState(false);
  const closedAt = useRef(0);
  // The user closing the Desk is respected for a short while: a card landing right after must not yank it back open.
  const setPanelOpen = useCallback((v: boolean) => { if (!v) closedAt.current = Date.now(); setPanelOpenState(v); }, []);
  const [bump, setBump] = useState(0);
  const [baseOrb, setBaseOrb] = useState<OrbState>("idle");
  const [flash, setFlash] = useState<OrbState | null>(null);
  const [caption, setCaption] = useState<Caption>(null);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [priorities, setPriorities] = useState<Priorities | null>(null);
  const [decision, setDecision] = useState<Decision>(null);
  const [uploads, setUploads] = useState<UploadItem[]>([]);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [choice, setChoice] = useState<Choice>(null);
  const [online, setOnline] = useState(navigator.onLine);
  const flashTimer = useRef<number | undefined>(undefined);
  const busy = useRef(0);

  useEffect(() => {
    const onHash = () => setView(viewFromHash());
    const on = () => setOnline(true), off = () => setOnline(false);
    addEventListener("hashchange", onHash); addEventListener("online", on); addEventListener("offline", off);
    return () => { removeEventListener("hashchange", onHash); removeEventListener("online", on); removeEventListener("offline", off); };
  }, []);

  const go = useCallback((v: View) => { if (location.hash !== `#/${v}`) location.hash = `/${v}`; setView(v); }, []);
  const navRef = useRef<(v: View) => void>(go);
  navRef.current = go;

  const addCards = useCallback((all: Card[]) => {
    // next-step chips are not artifacts: they live under the composer, never in the panel
    const sugg = all.filter((c) => c.card === "suggestions");
    if (sugg.length) setSuggestions(((sugg[sugg.length - 1].items || []) as Suggestion[]).slice(0, 3));
    const ch = all.filter((c) => c.card === "choice");
    if (ch.length) { const c = ch[ch.length - 1]; setChoice({ id: c.id, question: c.question, options: c.options || [], step: c.step, max: c.max }); }
    else if (all.some((c) => c.card !== "suggestions")) setChoice(null);  // Purser moved on (chart, proposal, ...)
    const nav = all.filter((c) => c.card === "navigate");
    if (nav.length) navRef.current?.(nav[nav.length - 1].view);
    const incoming = all.filter((c) => !["suggestions", "choice", "navigate"].includes(c.card));
    if (!incoming.length) return;
    // within one batch the later card for the same object wins; then newest first, older copies dropped
    const byKey = new Map<string, Card>();
    for (const c of incoming) { byKey.delete(cardKey(c)); byKey.set(cardKey(c), c); }
    // a claim review leads its own batch (its proposal is folded into it); otherwise newest first
    const batch = [...byKey.values()].reverse().sort((a, b) => Number(b.card === "claim_review") - Number(a.card === "claim_review"));
    if (incoming.some((c) => c.card === "claim_review")) setClaimFocus(true);
    else if (incoming.some((c) => !CLAIM_FOLLOW_UPS.has(c.card))) setClaimFocus(false);  // Purser moved on to another action
    setCards((prev) => [...batch, ...prev.filter((c) => !byKey.has(cardKey(c)))].slice(0, 12));
    setBump((b) => b + 1);
    setNewKeys(new Set(byKey.keys()));
    setLastBatch((n) => n + 1);
    // Whatever Purser just showed is the current action: bring the Desk forward unless the user just closed it.
    if (Date.now() - closedAt.current > USER_CLOSE_GRACE_MS) setPanelOpenState(true);
  }, []);
  const removeCard = useCallback((key: string) => setCards((p) => p.filter((c) => cardKey(c) !== key)), []);
  const clearCards = useCallback(() => { setCards([]); setClaimFocus(false); }, []);
  const refresh = useCallback(() => setBump((b) => b + 1), []);

  const flashOrb = useCallback((s: "success" | "error" | "cancelled") => {
    clearTimeout(flashTimer.current);
    setFlash(s);
    flashTimer.current = window.setTimeout(() => setFlash(null), s === "success" ? 1900 : s === "error" ? 2200 : 1300);
  }, []);

  const say = useCallback((who: Who, text: string, append = false) => {
    setCaption((prev) => (append && prev && prev.who === who ? { ...prev, text: prev.text + text } : { who, text, id: (prev?.id ?? 0) + 1 }));
  }, []);

  const toastId = useRef(0);
  const dismissToast = useCallback((id: number) => setToasts((t) => t.filter((x) => x.id !== id)), []);
  const toast = useCallback((kind: ToastKind, text: string, action?: Toast["action"]) => {
    const id = ++toastId.current;
    setToasts((t) => [...t.slice(-3), { id, kind, text, action }]);
    window.setTimeout(() => dismissToast(id), kind === "error" ? 9000 : 5000);
  }, [dismissToast]);

  const reloadPriorities = useCallback(() => {
    api.get<Priorities>("/api/priorities").then(setPriorities).catch(() => {});
  }, []);
  useEffect(() => { reloadPriorities(); }, [reloadPriorities, bump]);
  useEffect(() => { const t = window.setInterval(reloadPriorities, 45_000); return () => clearInterval(t); }, [reloadPriorities]);

  const value = useMemo<Ctx>(() => ({
    me, view, go, cards, addCards, removeCard, clearCards, panelOpen, setPanelOpen, lastBatch, newKeys, claimFocus, bump, refresh,
    baseOrb, setBaseOrb, orb: flash ?? baseOrb, flashOrb, caption, say, toasts, toast, dismissToast,
    priorities, reloadPriorities, decision, setDecision, uploads, setUploads, suggestions, setSuggestions, choice, setChoice, busy, online,
  }), [me, view, go, cards, addCards, removeCard, clearCards, panelOpen, setPanelOpen, lastBatch, newKeys, claimFocus, bump, refresh, baseOrb, flash, flashOrb, caption, say, toasts, toast,
    dismissToast, priorities, reloadPriorities, decision, uploads, suggestions, choice, online]);

  return <PurserContext.Provider value={value}>{children}</PurserContext.Provider>;
}

const USER_CLOSE_GRACE_MS = 6_000;
/** Cards that follow up on the claim in focus (its receipt, history, source) and so do not take focus away from it. */
const CLAIM_FOLLOW_UPS = new Set(["receipt", "audit_trail", "source"]);

/** Load a server object by path; reloads when `bump` changes. */

export function useLoad<T>(path: string | null, bump = 0) {
  const [data, setData] = useState<T | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [n, setN] = useState(0);
  useEffect(() => {
    if (!path) return;
    let live = true;
    setErr(null);
    api.get<T>(path).then((d) => live && setData(d)).catch((e) => live && setErr(e.message));
    return () => { live = false; };
  }, [path, bump, n]);
  return { data, err, loading: !data && !err, reload: () => setN((x) => x + 1) };
}
