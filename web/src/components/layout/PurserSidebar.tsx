// PurserSidebar: glass control surface. Navigation with a travelling active indicator, live priority counters,
// notifications from the audit trail and inbox, profile menu. Collapses to icons (preference remembered).
import { AnimatePresence, LayoutGroup, motion } from "motion/react";
import { allowedViews, roleLabel } from "../../roles";
import {
  Building2, ChartColumn, ChevronDown, ChevronsLeft, ChevronsRight, CreditCard, FileText, Folder, House, Layers, LayoutGrid, LifeBuoy, ListTodo,
  LogOut, Mail, Settings, User, X,
} from "lucide-react";
import { createPortal } from "react-dom";
import { ReactNode, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "../../api";
import { dur, ease, spring } from "../../animations/tokens";
import { usePurser, View } from "../../state/store";
import { useAssistant } from "../assistant/PurserVoiceController";
import AnimatedCounter from "../shared/AnimatedCounter";
import RoutinesPanel from "../settings/RoutinesPanel";

const COLLAPSE_KEY = "purser.sidebar.collapsed";

type NavDef = { view: View; label: string; icon: ReactNode; count?: number };

function Wordmark({ collapsed }: { collapsed: boolean }) {
  const letters = collapsed ? ["p"] : [..."purser"];
  return (
    <motion.p className="wordmark" aria-label="purser" initial="rest" whileHover="hover" animate="rest">
      {letters.map((l, i) => (
        <motion.span key={i} aria-hidden="true" variants={{ rest: { y: 0, textShadow: "0 0 24px rgba(140,240,191,.35)" },
          hover: { y: -3, textShadow: "0 0 30px rgba(140,240,191,.8)", transition: { delay: i * 0.035, type: "spring", stiffness: 500, damping: 14 } } }}>{l}</motion.span>
      ))}
    </motion.p>
  );
}

function NavButton({ def, active, collapsed, onClick, id }: { def: NavDef; active: boolean; collapsed: boolean; onClick: () => void; id?: string }) {
  const [tip, setTip] = useState(false);
  return (
    <button id={id} className="nav-item" aria-current={active ? "page" : undefined} onClick={onClick}
      onMouseEnter={() => setTip(true)} onMouseLeave={() => setTip(false)} onFocus={() => setTip(true)} onBlur={() => setTip(false)}
      aria-label={collapsed ? `${def.label}${def.count ? `, ${def.count}` : ""}` : undefined}>
      <span className="nav-hover" />
      {active && <motion.span layoutId="nav-active" className="nav-active" transition={spring.nav} />}
      {def.icon}
      {!collapsed && <span className="nav-text">{def.label}</span>}
      {!collapsed && !!def.count && <motion.span className="count" key={def.count} initial={{ scale: 1.35 }} animate={{ scale: 1 }} transition={spring.snappy}>
        <AnimatedCounter value={def.count} format="int" duration={0.5} /></motion.span>}
      {collapsed && !!def.count && <span className="nav-dot" aria-hidden="true" />}
      <AnimatePresence>{collapsed && tip && (
        <motion.span className="tip" role="tooltip" initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.14 }}>
          {def.label}{def.count ? ` · ${def.count}` : ""}</motion.span>)}</AnimatePresence>
    </button>
  );
}

const ago = (iso: string) => {
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.round(s / 60)}m ago`;
  if (s < 86400) return `${Math.round(s / 3600)}h ago`;
  return `${Math.round(s / 86400)}d ago`;
};

const ACTION_WORDS: Record<string, string> = {
  "claim.submitted": "Claim submitted", "claim.approved": "Claim approved", "bill.submitted": "Bill entered", "bill.approved": "Bill approved",
  "record.settled": "Payment recorded", "document.extracted": "Document read", "document.closed": "Document filed", "message.sent": "Message sent",
  "announcement.sent": "Announcement sent", "budget.changed": "Budget changed",
};

const humanize = (a: string) => {
  const [obj, verb] = a.split(".");
  const t = `${obj} ${(verb ?? "").replaceAll("_", " ")}`.trim();
  return t.charAt(0).toUpperCase() + t.slice(1);
};

type Note = { id: string; title: string; detail: string; at: string; ref?: string | null; inbox?: string; source: "audit" | "inbox" };

function Notifications() {
  const P = usePurser();
  const [items, setItems] = useState<Note[]>([]);
  const [seen, setSeen] = useState<Set<string>>(() => new Set(JSON.parse(localStorage.getItem("purser.seen") || "[]")));
  const [open, setOpen] = useState<string | null>(null);
  const isApprover = P.me.role === "admin" || P.me.role === "finance_approver";

  useEffect(() => {
    let live = true;
    const load = async () => {
      const [audit, inbox] = await Promise.all([
        isApprover ? api.get<any>("/api/audit").catch(() => ({ events: [] })) : Promise.resolve({ events: [] }),
        api.get<any>("/api/inbox").catch(() => ({ messages: [] })),
      ]);
      const a: Note[] = audit.events.filter((e: any) => !e.action.startsWith("document.extracted")).slice(0, 6).map((e: any) => ({
        id: `a${e.id}`, source: "audit", at: e.at, ref: e.record,
        title: `${ACTION_WORDS[e.action] ?? humanize(e.action)}${e.record ? ` · ${e.record}` : ""}`,
        detail: [e.by ? `by ${e.by}` : null, e.receipt ? `receipt ${e.receipt}` : null, e.after?.amount_paise ? `₹${new Intl.NumberFormat("en-IN").format(e.after.amount_paise / 100)}` : null]
          .filter(Boolean).join(" · "),
      }));
      const m: Note[] = inbox.messages.filter((x: any) => x.unread).slice(0, 3).map((x: any) => ({
        id: `m${x.ref}`, source: "inbox", at: x.at, inbox: x.ref, title: x.subject, detail: `${x.from}: ${x.body.slice(0, 120)}`,
      }));
      if (live) setItems([...m, ...a].sort((x, y) => y.at.localeCompare(x.at)).slice(0, 4));
    };
    load();
    return () => { live = false; };
  }, [P.bump, isApprover]);

  const markRead = useCallback((n: Note) => {
    setSeen((s) => { const x = new Set(s); x.add(n.id); localStorage.setItem("purser.seen", JSON.stringify([...x].slice(-200))); return x; });
    if (n.inbox) api.post(`/api/inbox/${n.inbox}/read`).then(() => P.reloadPriorities()).catch(() => {});
  }, [P]);

  const openNote = (n: Note) => {
    markRead(n);
    if (n.source === "inbox") { P.go("mail"); return; }
    if (n.ref?.startsWith("C")) P.addCards([{ card: "claim_review", ref: n.ref }]);
    else if (n.ref?.startsWith("B")) P.addCards([{ card: "record", ref: n.ref }]);
    else P.go("reports");
  };

  if (!items.length) return <p className="note-time" style={{ padding: "2px 10px" }}>Nothing new.</p>;
  return (
    <ul className="notes">
      <AnimatePresence initial={false}>
        {items.map((n) => {
          const unread = !seen.has(n.id);
          return (
            <motion.li key={n.id} layout initial={{ opacity: 0, x: -14 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, height: 0 }} transition={{ duration: 0.32, ease }}>
              <div className={`note ${unread ? "unread" : ""}`}>
                <motion.span className="dot" aria-hidden="true" initial={unread ? { scale: 2.2, opacity: 0.4 } : false} animate={{ scale: 1, opacity: 1 }} transition={{ duration: 0.7 }} />
                <div>
                  <button className="note-title" style={{ textAlign: "left" }} onClick={() => setOpen(open === n.id ? null : n.id)} aria-expanded={open === n.id}>
                    {n.title}{unread && <span className="sr-only"> (unread)</span>}
                  </button>
                  <div className="note-time">{ago(n.at)}</div>
                  <AnimatePresence>{open === n.id && (
                    <motion.div className="note-detail" initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.24 }}>
                      <div style={{ paddingTop: 4 }}>{n.detail || "No further detail."}</div>
                      <div className="note-actions">
                        <button onClick={() => openNote(n)}>Open</button>
                        {unread && <button onClick={() => markRead(n)}>Mark read</button>}
                      </div>
                    </motion.div>)}</AnimatePresence>
                </div>
              </div>
            </motion.li>
          );
        })}
      </AnimatePresence>
    </ul>
  );
}

function SettingsDialog({ onClose }: { onClose: () => void }) {
  const A = useAssistant();
  const P = usePurser();
  useEffect(() => { const k = (e: KeyboardEvent) => e.key === "Escape" && onClose(); addEventListener("keydown", k); return () => removeEventListener("keydown", k); }, [onClose]);
  return (
    <motion.div className="scrim" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <motion.div className="dialog dialog-settings glass" role="dialog" aria-modal="true" aria-labelledby="set-title" initial={{ y: 16, opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ y: 10, opacity: 0 }}>
        <div style={{ display: "flex", alignItems: "center" }}><h2 id="set-title" style={{ flex: 1 }}>Settings</h2>
          <button className="icon-btn" onClick={onClose} aria-label="Close settings"><X size={18} /></button></div>
        <label className="toggle" style={{ marginBottom: 12 }}>
          <input type="checkbox" checked={A.handsFree} onChange={(e) => A.setHandsFree(e.target.checked)} autoFocus />
          Hands-free: wake Purser by saying “Purser” (Chrome/Edge; uses the browser's speech service while armed)
        </label>
        <RoutinesPanel onRun={(u) => { onClose(); A.send(u); }} />
        <p className="fine">Signed in as {P.me.name} · {P.me.role.replace("_", " ")}.</p>
      </motion.div>
    </motion.div>
  );
}

function Profile({ collapsed }: { collapsed: boolean }) {
  const P = usePurser();
  const [open, setOpen] = useState(false);
  const [settings, setSettings] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const off = (e: MouseEvent) => { if (!ref.current?.contains(e.target as Node)) setOpen(false); };
    const esc = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    addEventListener("mousedown", off); addEventListener("keydown", esc);
    return () => { removeEventListener("mousedown", off); removeEventListener("keydown", esc); };
  }, [open]);
  const role = roleLabel(P.me.role);
  const signOut = async () => {
    try { await api.post("/api/auth/logout"); } finally { location.hash = ""; location.reload(); }
  };
  return (
    <div className="profile" ref={ref}>
      <AnimatePresence>{open && (
        <motion.div className="menu glass" role="menu" initial={{ opacity: 0, y: 8, scale: 0.97 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: 6 }} transition={{ duration: 0.18 }}>
          <div className="menu-info"><User size={14} style={{ verticalAlign: -2, marginRight: 6 }} />{P.me.name} · {role}</div>
          <button role="menuitem" onClick={() => { setOpen(false); setSettings(true); }}><Settings size={16} /> Settings</button>
          <button role="menuitem" onClick={signOut}><LogOut size={16} /> Sign out</button>
        </motion.div>)}</AnimatePresence>
      <button className="profile-btn" onClick={() => setOpen((o) => !o)} aria-haspopup="menu" aria-expanded={open} aria-label={`Account menu for ${P.me.name}`}>
        <span className="avatar" aria-hidden="true">{P.me.name.slice(0, 1)}</span>
        {!collapsed && <span style={{ flex: 1, minWidth: 0 }}><div className="profile-name">{P.me.name.split(" ")[0]}</div><div className="profile-role">{role}</div></span>}
        {!collapsed && <motion.span animate={{ rotate: open ? 180 : 0 }}><ChevronDown size={18} color="var(--muted)" /></motion.span>}
      </button>
      {/* Portal: the phone drawer is transformed, which would trap a fixed overlay inside it. */}
      {createPortal(<AnimatePresence>{settings && <SettingsDialog onClose={() => setSettings(false)} />}</AnimatePresence>, document.body)}
    </div>
  );
}

const PHONE = "(max-width: 760px)";

function usePhone() {
  const [phone, setPhone] = useState(() => matchMedia(PHONE).matches);
  useEffect(() => {
    const m = matchMedia(PHONE);
    const on = () => setPhone(m.matches);
    m.addEventListener("change", on);
    return () => m.removeEventListener("change", on);
  }, []);
  return phone;
}

export default function PurserSidebar({ open = false, onNavigate }: { open?: boolean; onNavigate?: () => void }) {
  const P = usePurser();
  const phone = usePhone();
  const [pref, setCollapsed] = useState(() => localStorage.getItem(COLLAPSE_KEY) === "1" || innerWidth < 900);
  const collapsed = phone ? false : pref;  // the phone drawer is always full width
  const go = (v: View) => { P.go(v); onNavigate?.(); };
  const toggle = () => setCollapsed((c) => { localStorage.setItem(COLLAPSE_KEY, c ? "0" : "1"); return !c; });
  const pr = P.priorities;
  const ic = 21;
  const allow = allowedViews(P.me.role);
  const primary: NavDef[] = useMemo(() => ([
    { view: "workspace", label: "Workspace", icon: <House size={ic} strokeWidth={1.6} /> },
    { view: "dashboards", label: "Dashboards", icon: <LayoutGrid size={ic} strokeWidth={1.6} /> },
    { view: "mail", label: "Mail", icon: <Mail size={ic} strokeWidth={1.6} />, count: pr?.unread_mail },
    { view: "tasks", label: "Tasks", icon: <ListTodo size={ic} strokeWidth={1.6} /> },
    { view: "helpdesk", label: "Helpdesk", icon: <LifeBuoy size={ic} strokeWidth={1.6} /> },
  ] as NavDef[]).filter((d) => allow.includes(d.view)), [pr, allow]);
  const compartments: NavDef[] = useMemo(() => ([
    { view: "expenses", label: "Expenses", icon: <Layers size={ic} strokeWidth={1.6} /> },
    { view: "travel", label: "Travel", icon: <Building2 size={ic} strokeWidth={1.6} /> },
    { view: "claims", label: "Claims", icon: <FileText size={ic} strokeWidth={1.6} />, count: pr?.claims_pending },
    { view: "payments", label: "Payments", icon: <CreditCard size={ic} strokeWidth={1.6} /> },
    { view: "budgets", label: "Budgets", icon: <ChartColumn size={ic} strokeWidth={1.6} /> },
    { view: "reports", label: "Reports", icon: <Folder size={ic} strokeWidth={1.6} /> },
  ] as NavDef[]).filter((d) => allow.includes(d.view)), [pr, allow]);

  return (
    <motion.nav id="purser-nav" className={`sidebar ${open ? "open" : ""}`} aria-label="Purser navigation" initial={false} animate={{ width: phone ? 264 : collapsed ? 78 : 240 }} transition={{ duration: dur.sidebar, ease }}>
      <div className="sb-top">
        <Wordmark collapsed={collapsed} />
        <button className="icon-btn sb-collapse" onClick={toggle} aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"} aria-expanded={!collapsed}
          style={collapsed ? { position: "absolute", top: 22, left: 40 } : undefined}>
          {collapsed ? <ChevronsRight size={16} /> : <ChevronsLeft size={16} />}
        </button>
      </div>
      <div className="sb-scroll">
        <LayoutGroup id="nav">
          <div className="sb-section">
            {primary.map((d) => <NavButton key={d.view} def={d} active={P.view === d.view} collapsed={collapsed} onClick={() => go(d.view)} id={d.view === "mail" ? "nav-mail" : undefined} />)}
          </div>
          <div className="sb-section">
            {!collapsed && compartments.length > 0 && <div className="sb-label">Compartments</div>}
            {compartments.map((d) => <NavButton key={d.view} def={d} active={P.view === d.view} collapsed={collapsed} onClick={() => go(d.view)} id={`nav-${d.view}`} />)}
          </div>
        </LayoutGroup>
        {!collapsed && (
          <div className="sb-section">
            <div className="sb-label">Notifications</div>
            <Notifications />
          </div>
        )}
      </div>
      <Profile collapsed={collapsed} />
    </motion.nav>
  );
}
