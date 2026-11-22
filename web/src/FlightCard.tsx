// Flight options from search_flights (SerpAPI Google Flights, or labelled estimated fares). Sort and filter locally;
// "Book" asks Purser to propose that exact option (it still needs the user's confirmation).
import { motion } from "motion/react";
import { Plane } from "lucide-react";
import { useMemo, useState } from "react";
import { useAssistant } from "./components/assistant/PurserVoiceController";

type Opt = { id: number; airline: string; logo?: string | null; flight_no: string; depart_time: string; arrive_time: string; depart: string;
  arrive: string; duration_min: number; stops: number; layovers: string[]; price_inr: number; best?: boolean; overnight?: boolean };
type Sort = "best" | "cheapest" | "fastest" | "earliest";

const inr = (n: number) => "₹" + n.toLocaleString("en-IN");
const dur = (m: number) => `${Math.floor(m / 60)}h ${m % 60}m`;

export function FlightOptionsCard({ card }: { card: any }) {
  const A = useAssistant();
  const [sort, setSort] = useState<Sort>("best");
  const [nonstop, setNonstop] = useState(false);
  const [airline, setAirline] = useState<string | null>(null);
  const opts: Opt[] = card.options || [];
  const airlines = useMemo(() => [...new Set(opts.map((o) => o.airline))].slice(0, 6), [opts]);
  const cheapest = opts.length ? Math.min(...opts.map((o) => o.price_inr)) : 0;
  const fastest = opts.length ? Math.min(...opts.map((o) => o.duration_min)) : 0;
  const shown = useMemo(() => {
    let l = opts.filter((o) => (!nonstop || o.stops === 0) && (!airline || o.airline === airline));
    if (sort === "cheapest") l = [...l].sort((a, b) => a.price_inr - b.price_inr);
    if (sort === "fastest") l = [...l].sort((a, b) => a.duration_min - b.duration_min);
    if (sort === "earliest") l = [...l].sort((a, b) => a.depart.localeCompare(b.depart));
    return l;
  }, [opts, sort, nonstop, airline]);
  const day = new Date(card.date + "T00:00:00").toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short" });

  return (
    <section className="card flights">
      <div className="card-head">
        <span className="kind">{card.source === "sample" ? "Estimated fares" : "Google Flights · live"}</span>
        <h2><Plane size={16} aria-hidden="true" style={{ verticalAlign: -2 }} /> {card.origin?.city} → {card.destination?.city} · {day}</h2>
      </div>
      {card.note && <p className="flag flag-warn" role="note">{card.note}</p>}
      <div className="fl-tabs" role="tablist" aria-label="Sort flights">
        {(["best", "cheapest", "fastest", "earliest"] as Sort[]).map((s) => (
          <button key={s} role="tab" aria-selected={sort === s} className={`fl-tab ${sort === s ? "on" : ""}`} onClick={() => setSort(s)}>
            {s[0].toUpperCase() + s.slice(1)}
            {s === "cheapest" && opts.length > 0 && <span className="fl-tab-sub">{inr(cheapest)}</span>}
            {s === "fastest" && opts.length > 0 && <span className="fl-tab-sub">{dur(fastest)}</span>}
          </button>
        ))}
      </div>
      <div className="fl-filters">
        <button className={`fl-chip ${nonstop ? "on" : ""}`} aria-pressed={nonstop} onClick={() => setNonstop((v) => !v)}>Non-stop only</button>
        {airlines.map((a) => (
          <button key={a} className={`fl-chip ${airline === a ? "on" : ""}`} aria-pressed={airline === a} onClick={() => setAirline((x) => (x === a ? null : a))}>{a}</button>
        ))}
      </div>
      <ol className="fl-list">
        {shown.map((o, i) => (
          <motion.li key={o.id} className="fl-row" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: Math.min(i, 8) * 0.03 }}>
            <span className="fl-air">
              {o.logo ? <img src={o.logo} alt="" width={28} height={28} loading="lazy" referrerPolicy="no-referrer"
                onError={(e) => { e.currentTarget.style.display = "none"; }} /> : <span className="fl-logo-ph" aria-hidden="true">{o.airline[0]}</span>}
              <span><strong>{o.airline}</strong><span className="fl-sub">{o.flight_no}</span></span>
            </span>
            <span className="fl-times num">{o.depart_time} <span className="fl-arrow" aria-hidden="true">→</span> {o.arrive_time}{o.overnight ? "+1" : ""}
              <span className="fl-sub">{dur(o.duration_min)} · {o.stops === 0 ? "non-stop" : `${o.stops} stop${o.stops > 1 ? "s" : ""} ${o.layovers.join(", ")}`}</span></span>
            <span className="fl-price num">{inr(o.price_inr)}
              <span className="fl-sub">{o.price_inr === cheapest ? "cheapest" : o.duration_min === fastest ? "fastest" : o.best ? "best" : ""}</span></span>
            <button className="btn btn-sm" disabled={!A.ready}
              onClick={(e) => A.send(`Book option ${o.id}: ${o.airline} ${o.flight_no} at ${o.depart_time} for ${inr(o.price_inr)}`, e.currentTarget)}>Book</button>
          </motion.li>
        ))}
        {shown.length === 0 && <li className="hint">No flights match these filters.</li>}
      </ol>
      <p className="hint">Booking is simulated: Purser records it and emails a confirmation; no ticket is purchased.</p>
    </section>
  );
}

type Hotel = { id: number; name: string; stars?: number | null; rating?: number | null; reviews?: number | null; price_per_night_inr: number;
  total_inr: number; image?: string | null; link?: string | null; amenities: string[]; nearby: string[] };

export function HotelOptionsCard({ card }: { card: any }) {
  const A = useAssistant();
  const [sort, setSort] = useState<"best" | "cheapest" | "rating">("best");
  const opts: Hotel[] = card.options || [];
  const shown = useMemo(() => {
    if (sort === "cheapest") return [...opts].sort((a, b) => a.price_per_night_inr - b.price_per_night_inr);
    if (sort === "rating") return [...opts].sort((a, b) => (b.rating ?? 0) - (a.rating ?? 0));
    return opts;
  }, [opts, sort]);
  const d = (s: string) => new Date(s + "T00:00:00").toLocaleDateString("en-IN", { day: "numeric", month: "short" });
  return (
    <section className="card flights">
      <div className="card-head">
        <span className="kind">{card.source === "sample" ? "Estimated rates" : "Google Hotels · live"}</span>
        <h2>🏨 {card.city} · {d(card.check_in)} → {d(card.check_out)} · {card.nights} night{card.nights === 1 ? "" : "s"}</h2>
      </div>
      {card.note && <p className="flag flag-warn" role="note">{card.note}</p>}
      <div className="fl-tabs fl-tabs-3" role="tablist" aria-label="Sort hotels">
        {(["best", "cheapest", "rating"] as const).map((s) => (
          <button key={s} role="tab" aria-selected={sort === s} className={`fl-tab ${sort === s ? "on" : ""}`} onClick={() => setSort(s)}>
            {s === "best" ? "Best match" : s === "cheapest" ? "Cheapest" : "Top rated"}</button>
        ))}
      </div>
      <ol className="fl-list">
        {shown.map((h, i) => (
          <motion.li key={h.id} className="ht-row" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: Math.min(i, 8) * 0.03 }}>
            {h.image ? <img className="ht-img" src={h.image} alt="" loading="lazy" referrerPolicy="no-referrer"
              onError={(e) => { e.currentTarget.style.visibility = "hidden"; }} /> : <span className="ht-img" aria-hidden="true" />}
            <span className="ht-main">
              <strong>{h.name}</strong>
              <span className="fl-sub">{h.stars ? `${h.stars}★ · ` : ""}{h.rating ? `${h.rating}/5${h.reviews ? ` (${h.reviews.toLocaleString("en-IN")})` : ""}` : "unrated"}</span>
              {h.amenities.length > 0 && <span className="fl-sub">{h.amenities.slice(0, 3).join(" · ")}</span>}
            </span>
            <span className="fl-price num">{inr(h.price_per_night_inr)}<span className="fl-sub">/night · {inr(h.total_inr)} total</span></span>
            <button className="btn btn-sm" disabled={!A.ready}
              onClick={(e) => A.send(`Choose hotel option ${h.id}: ${h.name} for ${inr(h.total_inr)}`, e.currentTarget)}>Choose</button>
          </motion.li>
        ))}
      </ol>
    </section>
  );
}

type Pay = { what: string; label: string; detail?: string; method: "GET" | "POST"; url: string; post_data?: string | null; exact?: boolean };

/** Open a payment page in a new tab. Google's booking redirect needs a POST, so it goes through a short-lived form. */
function openPayment(p: Pay) {
  if (!/^https?:\/\//.test(p.url)) return;
  if (p.method === "POST" && p.post_data) {
    const f = document.createElement("form");
    f.method = "POST"; f.action = p.url; f.target = "_blank"; f.rel = "noopener";
    new URLSearchParams(p.post_data).forEach((v, k) => {
      const i = document.createElement("input"); i.type = "hidden"; i.name = k; i.value = v; f.appendChild(i);
    });
    document.body.appendChild(f); f.submit(); f.remove();
  } else {
    window.open(p.url, "_blank", "noopener");
  }
}

export function PaymentCard({ card }: { card: any }) {
  const items: Pay[] = card.items || [];
  const [opened, setOpened] = useState<Record<number, boolean>>({});
  return (
    <section className="card pay-card">
      <div className="card-head"><span className="kind">Complete payment</span><h2>Approved · {card.receipt}</h2></div>
      <p className="hint">Purser has approved and recorded this. Finish payment on the provider's own website.</p>
      <div className="pay-list">
        {items.map((p, i) => (
          <button key={i} className={`pay-btn ${opened[i] ? "done" : ""}`} onClick={() => { openPayment(p); setOpened((o) => ({ ...o, [i]: true })); }}>
            <span className="pay-what">{p.what === "flight" ? "✈" : "🏨"}</span>
            <span className="pay-main"><strong>{p.label}</strong><span className="fl-sub">{p.detail}{p.exact === false ? " · opens a search to pick this option" : ""}</span></span>
            <span className="pay-go">{opened[i] ? "Opened ↗" : "Pay ↗"}</span>
          </button>
        ))}
      </div>
    </section>
  );
}
