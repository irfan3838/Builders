// Welcome modal: what Purser can do for this role, example prompts, then "Take the tour" or skip.
import { motion } from "motion/react";
import { useEffect, useRef } from "react";
import { ChartColumn, CircleCheck, LayoutGrid, ListTodo, Mail, Mic, Paperclip, Sparkles, Users, X } from "lucide-react";
import { ease } from "../../animations/tokens";
import { usePurser } from "../../state/store";
import { allowedViews, roleLabel } from "../../roles";
import { useAssistant } from "../assistant/PurserVoiceController";
import { CAPABILITIES, Capability, EXAMPLES, visible } from "./tourSteps";

const ICONS: Record<Capability["icon"], typeof Mic> = {
  voice: Mic, upload: Paperclip, chart: LayoutGrid, mail: Mail, approve: CircleCheck, budget: ChartColumn, tasks: ListTodo, people: Users,
};

export default function WelcomeModal({ onTour, onSkip }: { onTour: () => void; onSkip: () => void }) {
  const P = usePurser();
  const A = useAssistant();
  const box = useRef<HTMLDivElement>(null);
  const allowed = allowedViews(P.me.role);
  const caps = visible(CAPABILITIES, allowed);
  const examples = visible(EXAMPLES, allowed).slice(0, 3);

  useEffect(() => {
    const prev = document.activeElement as HTMLElement | null;
    const t = window.setTimeout(() => box.current?.querySelector<HTMLElement>("[data-autofocus]")?.focus(), 60);
    const k = (e: KeyboardEvent) => {
      if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); onSkip(); }
      if (e.key === "Tab" && box.current) {
        const f = [...box.current.querySelectorAll<HTMLElement>("button:not([disabled])")];
        if (!f.length) return;
        const first = f[0], last = f[f.length - 1];
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    };
    addEventListener("keydown", k, true);
    return () => { clearTimeout(t); removeEventListener("keydown", k, true); prev?.focus?.(); };
  }, [onSkip]);

  const tryIt = (text: string) => { onSkip(); A.send(text); };

  return (
    <motion.div className="scrim onb-scrim" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.25 }}>
      <motion.div ref={box} className="dialog glass welcome" role="dialog" aria-modal="true" aria-labelledby="welcome-title" aria-describedby="welcome-sub"
        initial={{ opacity: 0, y: 22, scale: 0.96 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: 12, scale: 0.97 }}
        transition={{ duration: 0.4, ease }}>
        <button className="icon-btn welcome-x" onClick={onSkip} aria-label="Close welcome"><X size={18} /></button>
        <p className="welcome-kicker"><Sparkles size={14} /> Welcome, {P.me.name.split(" ")[0]} · {roleLabel(P.me.role)}</p>
        <h2 id="welcome-title">Meet Purser, your finance munshi</h2>
        <p id="welcome-sub" className="welcome-sub">An assistant you talk to. It reads your documents, answers from your real books, and does the work, asking before anything consequential.</p>
        <ul className="welcome-grid">
          {caps.map((c, i) => {
            const I = ICONS[c.icon];
            return (
              <motion.li key={c.title} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.12 + i * 0.05, duration: 0.3, ease }}>
                <span className="welcome-ic" aria-hidden="true"><I size={18} strokeWidth={1.7} /></span>
                <span><strong>{c.title}</strong><span>{c.text}</span></span>
              </motion.li>
            );
          })}
        </ul>
        {examples.length > 0 && (
          <div className="welcome-try">
            <span className="welcome-try-label">Try saying</span>
            <div className="welcome-chips">
              {examples.map((e) => <button key={e.text} className="suggest-chip" onClick={() => tryIt(e.text)}>“{e.text}”</button>)}
            </div>
          </div>
        )}
        <div className="dlg-actions">
          <button className="btn btn-ghost" onClick={onSkip}>Skip for now</button>
          <button className="btn btn-primary" onClick={onTour} data-autofocus>Take the tour</button>
        </div>
      </motion.div>
    </motion.div>
  );
}
