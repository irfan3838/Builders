// Modal confirmation for consequential actions. Focus is trapped; Escape cancels; Confirm is single-flight.
import { AnimatePresence, motion } from "motion/react";
import { ReactNode, useEffect, useRef } from "react";
import { ease } from "../../animations/tokens";

type Props = {
  open: boolean; title: string; lines: string[]; confirmLabel: string; busy?: boolean; error?: string | null;
  onConfirm: () => void; onCancel: () => void; children?: ReactNode;
};

export default function ConfirmationDialog({ open, title, lines, confirmLabel, busy, error, onConfirm, onCancel, children }: Props) {
  const box = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const prev = document.activeElement as HTMLElement | null;
    const t = window.setTimeout(() => box.current?.querySelector<HTMLElement>("[data-autofocus]")?.focus(), 40);
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !busy) { e.preventDefault(); onCancel(); }
      if (e.key === "Tab" && box.current) {
        const f = [...box.current.querySelectorAll<HTMLElement>("button:not([disabled]), [href], input, textarea")];
        if (!f.length) return;
        const first = f[0], last = f[f.length - 1];
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    };
    addEventListener("keydown", key);
    return () => { clearTimeout(t); removeEventListener("keydown", key); prev?.focus?.(); };
  }, [open, busy, onCancel]);
  return (
    <AnimatePresence>
      {open && (
        <motion.div className="scrim" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.2 }}
          onMouseDown={(e) => { if (e.target === e.currentTarget && !busy) onCancel(); }}>
          <motion.div ref={box} className="dialog glass" role="dialog" aria-modal="true" aria-labelledby="dlg-title"
            initial={{ opacity: 0, y: 18, scale: 0.96 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: 10, scale: 0.97 }}
            transition={{ duration: 0.32, ease }}>
            <h2 id="dlg-title">{title}</h2>
            <ul>{lines.map((l, i) => <motion.li key={i} className="num" initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.08 + i * 0.05, duration: 0.25 }}>{l}</motion.li>)}</ul>
            {children}
            {error && <p className="dlg-err" role="alert">{error}</p>}
            <div className="dlg-actions">
              <button className="btn" onClick={onCancel} disabled={busy}>Go back</button>
              <button className="btn btn-primary" onClick={onConfirm} disabled={busy} data-autofocus aria-busy={busy}>
                {busy ? "Working…" : confirmLabel}
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
