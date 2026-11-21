// Purser Workspace: greeting, the glass orb, "Ask Purser", live captions, the composer and the decision strip.
import { AnimatePresence, motion } from "motion/react";
import { Mic } from "lucide-react";
import { useEffect, useRef } from "react";
import { ease } from "../animations/tokens";
import { usePurser } from "../state/store";
import PurserComposer from "../components/assistant/PurserComposer";
import PurserOrb from "../components/assistant/PurserOrb";
import { useAssistant } from "../components/assistant/PurserVoiceController";
import FinancialDecisionStrip from "../components/finance/FinancialDecisionStrip";

export function useOrbLabels() {
  const P = usePurser();
  const A = useAssistant();
  const live = ["listening", "speaking", "connecting", "waking"].includes(A.voice);
  const status: Record<string, string> = {
    idle: A.handsFree ? "Say “Hey Purser” or tap the orb" : "Tap the orb or press Ask Purser to talk",
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
      <div>
        <motion.h1 className="greeting" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7, ease }}>
          Welcome, {first}.
        </motion.h1>
        <motion.p className="greeting-sub" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4, duration: 0.6 }}>
          {hour < 12 ? "Good morning." : hour < 17 ? "Good afternoon." : "Good evening."} {P.priorities?.approvals ? `${P.priorities.approvals} item${P.priorities.approvals === 1 ? "" : "s"} await your decision.` : "Nothing waiting on you."}
        </motion.p>
      </div>
      <div className="stage">
        <PurserOrb state={P.orb} level={A.level} onActivate={A.toggleVoice} label={label} pressed={live} disabled={!A.ready} />
        <motion.button className="ask" data-state={A.voice} onClick={A.toggleVoice} disabled={!A.ready} aria-pressed={live}
          whileHover={{ y: -2 }} whileTap={{ scale: 0.97 }} transition={{ duration: 0.16 }}>
          {live ? <motion.span className="live-dot" animate={{ scale: [1, 1.5, 1], opacity: [1, 0.5, 1] }} transition={{ repeat: Infinity, duration: 1.4 }} /> : <Mic size={22} strokeWidth={1.6} />}
          {live ? "Listening" : "Ask Purser"}
        </motion.button>
        <div className="status-line" aria-live="polite">{status}</div>
        <AnimatePresence mode="wait">
          <motion.p ref={cap} key={P.caption?.id ?? 0} className={`caption ${P.caption?.who ?? ""}`} aria-live="polite"
            initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.25 }}>
            {P.caption?.text ?? ""}
          </motion.p>
        </AnimatePresence>
      </div>
      <PurserComposer />
      <FinancialDecisionStrip />
    </div>
  );
}
