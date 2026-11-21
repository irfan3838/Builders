import { AnimatePresence, motion } from "motion/react";
import { CircleCheck, Info, TriangleAlert, X } from "lucide-react";
import { usePurser } from "../../state/store";

export default function ToastManager() {
  const { toasts, dismissToast } = usePurser();
  return (
    <div className="toasts" role="region" aria-label="Notifications" aria-live="polite">
      <AnimatePresence>
        {toasts.map((t) => (
          <motion.div key={t.id} layout className={`toast glass ${t.kind}`} role={t.kind === "error" ? "alert" : "status"}
            initial={{ opacity: 0, y: 16, scale: 0.96 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, x: 30, transition: { duration: 0.2 } }}
            transition={{ type: "spring", stiffness: 380, damping: 30 }}>
            {t.kind === "success" ? <CircleCheck size={18} /> : t.kind === "error" ? <TriangleAlert size={18} /> : <Info size={18} />}
            <span>{t.text}</span>
            {t.action && <button onClick={() => { t.action!.run(); dismissToast(t.id); }}>{t.action.label}</button>}
            <button className="icon-btn" style={{ width: 26, height: 26 }} aria-label="Dismiss" onClick={() => dismissToast(t.id)}><X size={14} /></button>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
