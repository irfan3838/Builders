// Purser Workspace (home): greeting, the role briefing, and a compact voice stage (orb, status, captions).
import { AnimatePresence, motion } from "motion/react";
import { useEffect, useRef } from "react";
import { ease } from "../animations/tokens";
import { usePurser } from "../state/store";
import BriefingView from "../components/briefing/BriefingView";
import PurserOrb from "../components/assistant/PurserOrb";
import { useAssistant } from "../components/assistant/PurserVoiceController";
import FinancialDecisionStrip from "../components/finance/FinancialDecisionStrip";

export function useOrbLabels() {
  const P = usePurser();
  const A = useAssistant();
  const live = ["listening", "speaking", "connecting", "waking"].includes(A.voice);
  const status: Record<string, string> = {
    idle: A.handsFree ? "Say “Hey Purser” or tap the orb" : "Tap the orb to talk",
    asleep: "Say “Hey Purser” to talk", connecting: "Connecting…", listening: "Listening…", processing: "Purser is working on it…",
    speaking: "Purser is speaking", success: "Done", error: A.voice === "denied" ? "Microphone blocked · allow it in site settings" : "Something went wrong",
    cancelled: "Cancelled",
  };
  return { live, status: status[P.orb] ?? "", label: live ? "Stop talking to Purser" : "Talk to Purser" };
}

export default function WorkspaceView() {
  const P = usePurser();
  const A = useAssistant();
  const { live, status, label } = useOrbLabels();
  const first = P.me.name.split(" ")[0];
  const hour = new Date().getHours();
  const cap = useRef<HTMLParagraphElement>(null);
  useEffect(() => { const el = cap.current; if (el) el.scrollTop = el.scrollHeight; }, [P.caption?.text]);  // newest words stay visible

  return (
    <div className="workspace">
      <header className="ws-head">
        <motion.h1 className="greeting" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7, ease }}>
          {hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening"}, {first}.
        </motion.h1>
        <p className="greeting-sub">Here is what matters today. Ask anything by voice or text.</p>
      </header>
      <div className="ws-body">
        <BriefingView />
        <aside className="stage" aria-label="Purser voice">
          <PurserOrb state={P.orb} level={A.level} onActivate={A.toggleVoice} label={label} pressed={live} disabled={!A.ready} />
          <div className="status-line" aria-live="polite">{status}</div>
          <AnimatePresence mode="wait">
            <motion.p ref={cap} key={P.caption?.id ?? 0} className={`caption ${P.caption?.who ?? ""}`} aria-live="polite"
              initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.25 }}>
              {P.caption?.text ?? ""}
            </motion.p>
          </AnimatePresence>
          {P.decision && <FinancialDecisionStrip />}
        </aside>
      </div>
    </div>
  );
}
