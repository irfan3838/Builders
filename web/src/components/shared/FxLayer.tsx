// Overlay for "physical" motion between parts of the workspace: envelopes fly to the Mail icon, paper sheets
// travel to the Artifact Panel, light trails travel into the orb. Purely visual; callers never wait on it to act.
import { animate } from "motion";
import { useReducedMotion } from "motion/react";
import { createContext, ReactNode, useCallback, useContext, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { ease } from "../../animations/tokens";

type Pt = { x: number; y: number };
type Target = Element | string | Pt | null | undefined;
export type FlyKind = "envelope" | "sheet" | "trail";
type Flight = { id: number; kind: FlyKind; from: Pt; to: Pt; arc: number; duration: number; glow?: Element | null; done: () => void };
type FlyOpts = { kind: FlyKind; from: Target; to: Target; duration?: number; arc?: number; glow?: boolean };

const FxContext = createContext<{ fly: (o: FlyOpts) => Promise<void> }>({ fly: async () => {} });
export const useFx = () => useContext(FxContext);

function resolve(t: Target): { pt: Pt | null; el: Element | null } {
  const el = typeof t === "string" ? document.querySelector(t) : t instanceof Element ? t : null;
  if (el) { const r = el.getBoundingClientRect(); return { pt: { x: r.left + r.width / 2, y: r.top + r.height / 2 }, el }; }
  return { pt: (t as Pt) ?? null, el: null };
}

function Envelope() {
  return (
    <svg className="envelope" viewBox="0 0 64 44" aria-hidden="true">
      <defs><linearGradient id="envg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#f6f2e8" /><stop offset="1" stopColor="#ded5c2" /></linearGradient></defs>
      <rect x="1" y="1" width="62" height="42" rx="4" fill="url(#envg)" stroke="#8cf0bf" strokeOpacity=".6" />
      <path d="M2 4 L32 25 L62 4" fill="none" stroke="#9a907c" strokeWidth="1.4" />
      <path d="M2 42 L24 21 M62 42 L40 21" stroke="#b9b09c" strokeWidth="1" />
      <circle cx="32" cy="25" r="4" fill="#1f6a50" />
    </svg>
  );
}

function FlightItem({ f }: { f: Flight }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const c = { x: (f.from.x + f.to.x) / 2, y: Math.min(f.from.y, f.to.y) - f.arc };
    let glowed = false;
    const ctl = animate(0, 1, {
      duration: f.duration, ease: f.kind === "trail" ? [0.5, 0, 0.75, 0] : ease,
      onUpdate: (t) => {
        const u = 1 - t;
        const x = u * u * f.from.x + 2 * u * t * c.x + t * t * f.to.x;
        const y = u * u * f.from.y + 2 * u * t * c.y + t * t * f.to.y;
        // tangent for rotation
        const dx = 2 * u * (c.x - f.from.x) + 2 * t * (f.to.x - c.x), dy = 2 * u * (c.y - f.from.y) + 2 * t * (f.to.y - c.y);
        const rot = f.kind === "trail" ? 0 : Math.max(-28, Math.min(28, (Math.atan2(dy, dx) * 180) / Math.PI * 0.25));
        const lift = f.kind === "envelope" ? 1 + Math.sin(Math.PI * Math.min(1, t * 1.4)) * 0.25 : 1;
        const s = (f.kind === "trail" ? 1 - t * 0.4 : t > 0.8 ? 1 - (t - 0.8) * 3.2 : 1) * lift;
        el.style.transform = `translate(${x}px, ${y}px) translate(-50%, -50%) rotate(${rot}deg) scale(${Math.max(0.2, s)})`;
        el.style.opacity = String(t > 0.9 ? 1 - (t - 0.9) * 10 : Math.min(1, t * 8));
        if (!glowed && t > 0.72 && f.glow) { glowed = true; f.glow.classList.add("glow"); window.setTimeout(() => f.glow?.classList.remove("glow"), 1400); }
      },
      onComplete: f.done,
    });
    return () => ctl.stop();
  }, [f]);
  return (
    <div ref={ref} className="fx-item" style={{ opacity: 0 }}>
      {f.kind === "envelope" ? <Envelope /> : f.kind === "sheet" ? <div className="sheet" /> : <div className="trail" />}
    </div>
  );
}

export function FxProvider({ children }: { children: ReactNode }) {
  const [flights, setFlights] = useState<Flight[]>([]);
  const reduced = useReducedMotion();
  const n = useRef(0);
  const fly = useCallback((o: FlyOpts) => new Promise<void>((done) => {
    const a = resolve(o.from), b = resolve(o.to);
    if (reduced || !a.pt || !b.pt || document.hidden) {
      if (o.glow && b.el) { b.el.classList.add("glow"); window.setTimeout(() => b.el?.classList.remove("glow"), 1200); }
      done(); return;
    }
    const id = ++n.current;
    const dist = Math.hypot(b.pt.x - a.pt.x, b.pt.y - a.pt.y);
    const f: Flight = {
      id, kind: o.kind, from: a.pt, to: b.pt, arc: o.arc ?? Math.min(220, dist * 0.35), duration: o.duration ?? (o.kind === "envelope" ? 0.95 : o.kind === "sheet" ? 0.75 : 0.55),
      glow: o.glow ? b.el : null, done: () => { setFlights((x) => x.filter((y) => y.id !== id)); done(); },
    };
    setFlights((x) => [...x, f]);
  }), [reduced]);
  return (
    <FxContext.Provider value={{ fly }}>
      {children}
      {createPortal(<div className="fx" aria-hidden="true">{flights.map((f) => <FlightItem key={f.id} f={f} />)}</div>, document.body)}
    </FxContext.Provider>
  );
}
