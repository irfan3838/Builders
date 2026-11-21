// Shared motion vocabulary. Durations follow the Purser spec (seconds, as Motion expects).
export const ease = [0.22, 1, 0.36, 1] as const;
export const easeInOut = [0.65, 0, 0.35, 1] as const;

export const dur = {
  hover: 0.16,
  press: 0.2,
  card: 0.38,
  sidebar: 0.38,
  panel: 0.42,
  document: 0.75,
  mail: 0.95,
  approval: 1.0,
} as const;

export const spring = {
  soft: { type: "spring", stiffness: 260, damping: 30, mass: 0.9 },
  snappy: { type: "spring", stiffness: 520, damping: 36 },
  nav: { type: "spring", stiffness: 420, damping: 34 },
} as const;

/** Card reveal used by the panel and the views (stagger via `custom` index). */
export const reveal = {
  hidden: { opacity: 0, y: 14, filter: "blur(4px)" },
  show: (i = 0) => ({ opacity: 1, y: 0, filter: "blur(0px)", transition: { duration: dur.card, ease, delay: i * 0.06 } }),
  exit: { opacity: 0, y: -8, scale: 0.98, filter: "blur(4px)", transition: { duration: 0.22, ease } },
};

export const palette = {
  mint: "#8cf0bf",
  sage: "#8aa892",
  gold: "#e7c77f",
  amber: "#f0b45a",
  ivory: "#f1ebdd",
  muted: "#9fb2a7",
  line: "rgba(178,206,188,.14)",
};
