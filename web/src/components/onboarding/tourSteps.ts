// First-login onboarding content: welcome-modal capabilities and spotlight tour steps.
// Everything is filtered by role (allowedViews) and, for tour steps, by whether the anchor is on screen.
import type { View } from "../../state/store";

export type TourStep = {
  id: string;
  /** CSS selector(s); the first match is spotlighted. */
  selector: string;
  title: string;
  body: string | ((views: View[]) => string);
  /** Shown only when the role can see at least one of these views. */
  views?: View[];
  /** Lives in the sidebar: on phones the drawer is opened for it. */
  nav?: boolean;
};

const has = (vs: View[], v: View) => vs.includes(v);

export const TOUR_STEPS: TourStep[] = [
  { id: "orb", selector: "#purser-orb", title: "Talk to Purser",
    body: "Tap the orb, or just say “Hey Purser”. Speak in English, Hindi or Hinglish and Purser answers out loud." },
  { id: "composer", selector: ".composer", title: "Or type it",
    body: "Anything you can say, you can type here. Ask a question, give an instruction, or describe what you need done." },
  { id: "upload", selector: ".upload-pill", title: "Hand over documents",
    body: "Attach a receipt, bill or contract (or drop it anywhere on the screen). Purser reads it, extracts the details and files it for you." },
  { id: "suggest", selector: ".suggest-row", title: "Next steps, suggested",
    body: "Purser offers follow-ups based on what you are doing. One tap runs them." },
  { id: "nav", selector: '[data-tour="primary-nav"]', nav: true, title: "Your workspaces",
    body: "Every area you have access to lives here. You can also ask Purser to open any of them for you." },
  { id: "dashboards", selector: '[data-tour="nav-dashboards"]', nav: true, views: ["dashboards"], title: "Dashboards on demand",
    body: "Ask for a chart in plain words, like “travel spend by team this quarter”. It is built live from your books and you can pin it here." },
  { id: "mail", selector: "#nav-mail", nav: true, views: ["mail"], title: "Mail",
    body: "Your inbox, with Purser able to summarise threads, draft replies and send on your approval." },
  { id: "compartments", selector: '[data-tour="compartments"]', nav: true,
    views: ["expenses", "travel", "claims", "payments", "budgets", "reports"], title: "Compartments",
    body: (vs) => {
      const names = (["expenses", "travel", "claims", "payments", "budgets", "reports"] as View[]).filter((v) => has(vs, v));
      return `${names.map((n) => n[0].toUpperCase() + n.slice(1)).join(", ")}: each one is a live view of your records. Nothing consequential happens without your confirmation.`;
    } },
  { id: "notes", selector: '[data-tour="notifications"]', nav: true, title: "Notifications",
    body: "New mail, approvals and filed documents show up here as they happen." },
  { id: "profile", selector: ".profile-btn", nav: true, title: "Settings",
    body: "Turn hands-free wake word on or off, save routines, and replay this tour any time from Settings." },
];

export type Capability = { icon: "voice" | "upload" | "chart" | "mail" | "approve" | "budget" | "tasks" | "people"; title: string; text: string; views?: View[] };

export const CAPABILITIES: Capability[] = [
  { icon: "voice", title: "Voice first", text: "Talk or type in English, Hindi or Hinglish. Hands-free with “Hey Purser”." },
  { icon: "upload", title: "Reads your documents", text: "Receipts, bills and contracts are read, checked and filed for you." },
  { icon: "chart", title: "Live dashboards", text: "Ask for any chart in plain words; it is composed from your real data.", views: ["dashboards"] },
  { icon: "approve", title: "Claims and payments", text: "Submit claims, review bills and record payments, always with a confirmation step.", views: ["claims", "payments"] },
  { icon: "budget", title: "Budgets and reports", text: "Check what is left, move budget, and pull reports on request.", views: ["budgets", "reports"] },
  { icon: "mail", title: "Mail and calendar", text: "Summarise threads, draft replies and schedule meetings.", views: ["mail"] },
  { icon: "tasks", title: "Tasks and helpdesk", text: "Track to-dos and raise or answer helpdesk tickets.", views: ["tasks", "helpdesk"] },
];

export const EXAMPLES: { text: string; views?: View[] }[] = [
  { text: "What needs my attention today?" },
  { text: "Show travel spend by team this quarter", views: ["dashboards"] },
  { text: "How much budget is left for marketing?", views: ["budgets"] },
  { text: "Mera last claim kahan tak pahuncha?", views: ["claims"] },
];

export const visible = <T extends { views?: View[] }>(items: T[], allowed: View[]) =>
  items.filter((i) => !i.views || i.views.some((v) => allowed.includes(v)));
