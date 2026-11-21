// BriefingView: the home screen. Everything here comes from GET /api/briefing (SQL + Google for the linked login);
// the layout only knows two section types (kpi_strip, list). Tapping any row asks Purser in words, like speaking it.
import { motion } from "motion/react";
import { ArrowUpRight, CalendarClock, RefreshCw, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import { reveal } from "../../animations/tokens";
import { useLoad, usePurser } from "../../state/store";
import { useAssistant } from "../assistant/PurserVoiceController";

type Item = { title?: string; sub?: string; meta?: string; tone?: string | null; utterance?: string | null; url?: string | null;
  label?: string; value?: string };
type Section = { type: "kpi_strip" | "list"; title?: string; items: Item[]; empty?: string; source?: string };
type Briefing = { greeting: string; role: string; as_of: string; next_action: { title: string; why: string; utterance: string } | null;
  sections: Section[]; notes: string[]; google: boolean };

export function useBriefing() {
  const P = usePurser();
  const [n, setN] = useState(0);
  // refresh when the server reports a change (P.bump) but at most once every 20 s, plus every 5 minutes
  const [tick, setTick] = useState(0);
  useEffect(() => { const t = setInterval(() => setTick((x) => x + 1), 300_000); return () => clearInterval(t); }, []);
  const [slowBump, setSlowBump] = useState(0);
  useEffect(() => { const t = setTimeout(() => setSlowBump(P.bump), 20_000); return () => clearTimeout(t); }, [P.bump]);
  const r = useLoad<Briefing>(`/api/briefing${n ? "?fresh=true" : ""}`, slowBump + tick + n);
  return { ...r, refresh: () => setN((x) => x + 1) };
}

function Row({ it, ask }: { it: Item; ask: (u: string, el: Element) => void }) {
  const body = (
    <>
      <span className="b-row-main">
        <span className="b-row-title">{it.title}</span>
        {it.sub && <span className="b-row-sub">{it.sub}</span>}
      </span>
      {it.meta && <span className={`b-meta ${it.tone === "warn" ? "warn" : ""}`}>{it.meta}</span>}
    </>
  );
  if (it.url) return <a className={`b-row ${it.tone ?? ""}`} href={it.url} target="_blank" rel="noreferrer">{body}<ArrowUpRight size={14} aria-hidden="true" /></a>;
  if (it.utterance) return <button className={`b-row ${it.tone ?? ""}`} onClick={(e) => ask(it.utterance!, e.currentTarget)} title={`Ask: ${it.utterance}`}>{body}</button>;
  return <div className={`b-row ${it.tone ?? ""}`}>{body}</div>;
}

export default function BriefingView() {
  const A = useAssistant();
  const { data, err, refresh } = useBriefing();
  const ask = (u: string, el: Element) => { A.send(u, el); };

  if (err) return <div className="briefing"><p className="b-note">Briefing unavailable: {err} <button className="link-btn" onClick={refresh}>Retry</button></p></div>;
  if (!data) return (
    <div className="briefing" aria-busy="true">
      <div className="skeleton" style={{ height: 96 }} />
      <div className="b-kpis">{[0, 1, 2, 3].map((i) => <div key={i} className="skeleton" style={{ height: 72 }} />)}</div>
      <div className="b-lists">{[0, 1].map((i) => <div key={i} className="skeleton" style={{ height: 180 }} />)}</div>
    </div>
  );

  const kpis = data.sections.filter((s) => s.type === "kpi_strip").flatMap((s) => s.items);
  const lists = data.sections.filter((s) => s.type === "list");
  return (
    <div className="briefing">
      {data.next_action ? (
        <motion.button className="b-hero glass" onClick={(e) => ask(data.next_action!.utterance, e.currentTarget)}
          initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.45 }} whileHover={{ y: -2 }}>
          <span className="b-hero-kicker"><Sparkles size={14} aria-hidden="true" /> Next best action</span>
          <span className="b-hero-title">{data.next_action.title}</span>
          <span className="b-hero-why">{data.next_action.why}</span>
          <span className="b-hero-cta">Ask Purser <ArrowUpRight size={15} aria-hidden="true" /></span>
        </motion.button>
      ) : (
        <div className="b-hero glass calm"><span className="b-hero-kicker"><Sparkles size={14} aria-hidden="true" /> All clear</span>
          <span className="b-hero-title">Nothing urgent right now.</span></div>
      )}
      {kpis.length > 0 && (
        <div className="b-kpis" role="list">
          {kpis.map((k, i) => (
            <motion.button key={k.label} role="listitem" className={`b-kpi glass ${k.tone === "warn" ? "warn" : ""}`} variants={reveal} custom={i}
              initial="hidden" animate="show" onClick={(e) => k.utterance && ask(k.utterance, e.currentTarget)} disabled={!k.utterance}
              aria-label={`${k.label}: ${k.value}${k.sub ? `, ${k.sub}` : ""}${k.tone === "warn" ? " (needs attention)" : ""}`}>
              <span className="b-kpi-label">{k.label}</span>
              <span className="b-kpi-value num">{k.value}</span>
              {k.sub && <span className="b-kpi-sub">{k.sub}</span>}
            </motion.button>
          ))}
        </div>
      )}
      <div className="b-lists">
        {lists.map((s, i) => (
          <motion.section key={s.title ?? i} className="b-list glass" variants={reveal} custom={i + 2} initial="hidden" animate="show">
            <h2 className="b-list-h">
              {s.title === "Today" && <CalendarClock size={15} aria-hidden="true" />}{s.title}
              {s.source === "purser" && <span className="b-tag">Purser</span>}
              {s.source === "google_calendar" && <span className="b-tag">Google</span>}
            </h2>
            {s.items.length === 0 ? <p className="b-empty">{s.empty}</p> : (
              <div className="b-rows">{s.items.slice(0, 6).map((it, j) => <Row key={j} it={it} ask={ask} />)}</div>
            )}
          </motion.section>
        ))}
      </div>
      <p className="b-note">
        Updated {new Date(data.as_of).toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit" })}
        {data.notes.length > 0 && ` · ${data.notes.join(" · ")}`}
        {" · "}<button className="link-btn" onClick={refresh} aria-label="Refresh briefing"><RefreshCw size={12} /> Refresh</button>
      </p>
    </div>
  );
}
