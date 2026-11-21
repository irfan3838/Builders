// Counts smoothly to a server-verified value. Formats as INR from paise, or as a plain integer.
import { animate } from "motion";
import { useReducedMotion } from "motion/react";
import { useEffect, useRef } from "react";

const fmtInr = (paise: number) => "₹" + new Intl.NumberFormat("en-IN").format(Math.round(paise / 100));

export default function AnimatedCounter({ value, format = "inr", from, duration = 1.1, className }:
  { value: number; format?: "inr" | "int"; from?: number; duration?: number; className?: string }) {
  const ref = useRef<HTMLSpanElement>(null);
  const prev = useRef<number>(from ?? value);
  const reduced = useReducedMotion();
  const fmt = format === "inr" ? fmtInr : (v: number) => String(Math.round(v));
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const start = prev.current;
    prev.current = value;
    if (reduced || start === value) { el.textContent = fmt(value); return; }
    const ctl = animate(start, value, { duration, ease: [0.22, 1, 0.36, 1], onUpdate: (v) => { el.textContent = fmt(v); } });
    return () => ctl.stop();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);
  return <span ref={ref} className={className}>{fmt(from ?? value)}</span>;
}
