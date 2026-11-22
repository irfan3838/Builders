// Spotlight tour: the screen is blurred and dimmed except for a hole around the current control, with a
// tooltip card pointing at it. Steps whose anchor is not on screen (role, collapsed sidebar, empty lists) are skipped.
import { motion } from "motion/react";
import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { ArrowLeft, ArrowRight, X } from "lucide-react";
import { ease } from "../../animations/tokens";
import { usePurser } from "../../state/store";
import { allowedViews } from "../../roles";
import { TOUR_STEPS, TourStep, visible } from "./tourSteps";

type Rect = { top: number; left: number; width: number; height: number };
const PAD = 8, GUTTER = 16, GAP = 14, CARD_W = 340;
const PHONE = "(max-width: 760px)";

const find = (s: TourStep) => document.querySelector<HTMLElement>(s.selector);
const same = (a: Rect | null, b: Rect | null) =>
  !!a && !!b && Math.abs(a.top - b.top) < 0.5 && Math.abs(a.left - b.left) < 0.5 && Math.abs(a.width - b.width) < 0.5 && Math.abs(a.height - b.height) < 0.5;

type Place = { top: number; left: number; side: "top" | "bottom" | "left" | "right" | "sheet"; arrow: number };

function place(r: Rect, card: { w: number; h: number }, phone: boolean): Place {
  const vw = innerWidth, vh = innerHeight;
  const clampX = (x: number) => Math.max(GUTTER, Math.min(x, vw - GUTTER - card.w));
  const clampY = (y: number) => Math.max(GUTTER, Math.min(y, vh - GUTTER - card.h));
  if (phone) {
    // Bottom sheet, moved to the top when the target sits in the lower half (the composer).
    const below = r.top + r.height / 2 > vh / 2;
    return { side: "sheet", left: GUTTER, top: below ? GUTTER + 52 : vh - GUTTER - card.h, arrow: 0 };
  }
  const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
  const roomR = vw - (r.left + r.width) - GAP - GUTTER, roomB = vh - (r.top + r.height) - GAP - GUTTER, roomT = r.top - GAP - GUTTER;
  let p: Place;
  if (r.height > vh * 0.6 || (r.left < 300 && roomR >= card.w)) {
    // Tall or left-docked targets (the sidebar and its items): card to the right.
    const top = clampY(cy - card.h / 2);
    p = { side: "right", left: r.left + r.width + GAP, top, arrow: Math.max(18, Math.min(card.h - 18, cy - top)) };
  } else if (roomB >= card.h) {
    const left = clampX(cx - card.w / 2);
    p = { side: "bottom", left, top: r.top + r.height + GAP, arrow: Math.max(18, Math.min(card.w - 18, cx - left)) };
  } else if (roomT >= card.h) {
    const left = clampX(cx - card.w / 2);
    p = { side: "top", left, top: r.top - GAP - card.h, arrow: Math.max(18, Math.min(card.w - 18, cx - left)) };
  } else {
    const top = clampY(cy - card.h / 2);
    p = { side: "left", left: Math.max(GUTTER, r.left - GAP - card.w), top, arrow: Math.max(18, Math.min(card.h - 18, cy - top)) };
  }
  return p;
}

export default function ProductTour({ setNavOpen, onFinish, onSkip }: { setNavOpen: (o: boolean) => void; onFinish: () => void; onSkip: () => void }) {
  const P = usePurser();
  const allowed = allowedViews(P.me.role);
  const phone = matchMedia(PHONE).matches;
  // Resolve once at start: role-allowed steps whose anchor exists (off-canvas drawer items still exist in the DOM).
  const [steps] = useState(() => visible(TOUR_STEPS, allowed).filter((s) => find(s)));
  const [i, setI] = useState(0);
  const [rect, setRect] = useState<Rect | null>(null);
  const [card, setCard] = useState({ w: CARD_W, h: 200 });
  const cardRef = useRef<HTMLDivElement>(null);
  const step = steps[i];

  useEffect(() => { if (!steps.length) onFinish(); }, [steps, onFinish]);

  // Phone: open the drawer for sidebar steps, close it otherwise. Bring the target into view.
  useEffect(() => {
    if (!step) return;
    if (phone) setNavOpen(!!step.nav);
    find(step)?.scrollIntoView({ block: "nearest", inline: "nearest" });
  }, [step, phone, setNavOpen]);

  // Track the target every frame: drawers slide, the sidebar animates its width, lists reflow.
  useEffect(() => {
    if (!step) return;
    let raf = 0, last: Rect | null = null;
    const tick = () => {
      const el = find(step);
      if (el) {
        const b = el.getBoundingClientRect();
        const r = { top: b.top - PAD, left: b.left - PAD, width: b.width + PAD * 2, height: b.height + PAD * 2 };
        if (!same(r, last)) { last = r; setRect(r); }
      }
      raf = requestAnimationFrame(tick);
    };
    tick();
    return () => cancelAnimationFrame(raf);
  }, [step]);

  useLayoutEffect(() => {
    const el = cardRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setCard({ w: el.offsetWidth, h: el.offsetHeight }));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const next = useCallback(() => { if (i >= steps.length - 1) onFinish(); else setI(i + 1); }, [i, steps.length, onFinish]);
  const back = useCallback(() => setI((x) => Math.max(0, x - 1)), []);

  useEffect(() => {
    const k = (e: KeyboardEvent) => {
      if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); onSkip(); }
      else if (e.key === "ArrowRight") { e.preventDefault(); next(); }
      else if (e.key === "ArrowLeft") { e.preventDefault(); back(); }
      else if (e.key === "Tab" && cardRef.current) {
        const f = [...cardRef.current.querySelectorAll<HTMLElement>("button:not([disabled])")];
        if (!f.length) return;
        const first = f[0], last = f[f.length - 1];
        if (!cardRef.current.contains(document.activeElement)) { e.preventDefault(); first.focus(); }
        else if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    };
    addEventListener("keydown", k, true);
    return () => removeEventListener("keydown", k, true);
  }, [next, back, onSkip]);

  useEffect(() => { cardRef.current?.querySelector<HTMLElement>("[data-autofocus]")?.focus({ preventScroll: true }); }, [i]);

  const pos = useMemo(() => (rect ? place(rect, card, phone) : null), [rect, card, phone]);
  // No slide-in from off-screen: positions only animate once the card has been placed.
  const [placed, setPlaced] = useState(false);
  useEffect(() => { if (pos && !placed) requestAnimationFrame(() => setPlaced(true)); }, [pos, placed]);
  if (!step) return null;
  const body = typeof step.body === "function" ? step.body(allowed) : step.body;
  const r = rect ?? { top: innerHeight / 2, left: innerWidth / 2, width: 0, height: 0 };
  const last = i === steps.length - 1;

  return (
    <motion.div className="tour" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.25 }}>
      {/* Four blurred panes around the hole. They swallow clicks so the tour cannot be clicked through. */}
      <div className="tour-pane" style={{ top: 0, left: 0, right: 0, height: Math.max(0, r.top) }} />
      <div className="tour-pane" style={{ top: r.top + r.height, left: 0, right: 0, bottom: 0 }} />
      <div className="tour-pane" style={{ top: r.top, left: 0, width: Math.max(0, r.left), height: r.height }} />
      <div className="tour-pane" style={{ top: r.top, left: r.left + r.width, right: 0, height: r.height }} />
      <div className="tour-ring" style={{ top: r.top, left: r.left, width: r.width, height: r.height }} aria-hidden="true" />

      <motion.div ref={cardRef} className={`tour-card glass ${pos?.side ?? ""}`} role="dialog" aria-modal="true"
        aria-labelledby="tour-title" aria-describedby="tour-body"
        style={{ top: pos?.top ?? -9999, left: pos?.left ?? -9999, transition: placed ? undefined : "none", ["--arrow" as string]: `${pos?.arrow ?? 0}px` }}
        initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.28, ease }}>
        <span className="tour-arrow" aria-hidden="true" />
        <div className="tour-head">
          <span className="tour-count">{i + 1} / {steps.length}</span>
          <button className="icon-btn tour-x" onClick={onSkip} aria-label="Skip tour"><X size={16} /></button>
        </div>
        <motion.div key={step.id} initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.22, ease }}>
          <h3 id="tour-title">{step.title}</h3>
          <p id="tour-body">{body}</p>
        </motion.div>
        <div className="tour-dots" aria-hidden="true">{steps.map((s, j) => <span key={s.id} className={j === i ? "on" : ""} />)}</div>
        <div className="tour-actions">
          <button className="btn btn-ghost btn-sm" onClick={onSkip}>Skip tour</button>
          <span style={{ flex: 1 }} />
          {i > 0 && <button className="btn btn-sm" onClick={back} aria-label="Previous step"><ArrowLeft size={15} /></button>}
          <button className="btn btn-primary btn-sm" onClick={next} data-autofocus>
            {last ? "Finish" : <>Next <ArrowRight size={15} /></>}
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
}
