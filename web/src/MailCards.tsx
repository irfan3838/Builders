// Meetings and mail cards. The rows come from the tool result (Google Calendar / Gmail for the linked account,
// Purser meetings otherwise); the card never adds anything of its own.
import { CalendarClock, Mail, Video } from "lucide-react";

const time = (iso?: string) => {
  if (!iso) return "";
  const d = new Date(iso);
  return isNaN(+d) ? iso : d.toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit" });
};
const day = (iso?: string) => {
  if (!iso) return "";
  const d = new Date(iso);
  return isNaN(+d) ? "" : d.toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short" });
};

export function MeetingsCard({ title, source, items }: { title?: string; source?: string; items: any[] }) {
  return (
    <section className="card">
      <div className="card-head">
        <span className="kind">{source === "google_calendar" ? "Google Calendar" : "Purser calendar"}</span>
        <h2>{title || "Meetings"}</h2>
      </div>
      {items.length === 0 ? <p className="hint">No meetings in this window.</p> : (
        <ol className="list">
          {items.map((m) => (
            <li key={m.event_id}>
              <span><CalendarClock size={14} aria-hidden="true" style={{ verticalAlign: -2, marginRight: 6 }} /><strong>{m.title}</strong>
                <div className="sub">{m.all_day ? `${day(m.start)} · all day` : `${day(m.start)} · ${time(m.start)}–${time(m.end)}`}
                  {m.attendees?.length ? ` · ${m.attendees.filter(Boolean).slice(0, 3).join(", ")}` : ""}</div></span>
              {m.meet_url && <a className="ref" href={m.meet_url} target="_blank" rel="noreferrer"><Video size={14} aria-hidden="true" /> Join</a>}
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

export function MailListCard({ title, items }: { title?: string; items: any[] }) {
  return (
    <section className="card">
      <div className="card-head"><span className="kind">Gmail</span><h2>{items.length} message{items.length === 1 ? "" : "s"}</h2></div>
      {title && <p className="hint">Search: {title}</p>}
      <ol className="list">
        {items.map((m) => (
          <li key={m.id}>
            <span><Mail size={14} aria-hidden="true" style={{ verticalAlign: -2, marginRight: 6 }} />
              {m.unread ? <strong>{m.from}</strong> : m.from} <span className="sub">· {m.subject}</span>
              <div className="sub">{m.snippet}</div></span>
          </li>
        ))}
      </ol>
    </section>
  );
}

export function MailThreadCard({ messages }: { messages: any[] }) {
  return (
    <section className="card">
      <div className="card-head"><span className="kind">Gmail thread</span><h2>{messages[messages.length - 1]?.subject || "Thread"}</h2></div>
      {messages.map((m, i) => (
        <div key={i} style={{ marginBottom: 12 }}>
          <div className="sub"><strong>{m.from}</strong> · {m.date}</div>
          <p style={{ whiteSpace: "pre-wrap", margin: "4px 0 0", fontSize: ".9rem" }}>{m.body}</p>
        </div>
      ))}
    </section>
  );
}

export function TasksCard({ items }: { items: any[] }) {
  return (
    <section className="card">
      <div className="card-head"><span className="kind">Tasks</span><h2>{items.length} open</h2></div>
      {items.length === 0 ? <p className="hint">No open tasks.</p> : (
        <ol className="list">{items.map((t) => (
          <li key={t.ref}><span><strong>{t.title}</strong> <span className="ref">{t.ref}</span>
            <div className="sub">{t.due_on ? `due ${t.due_on}` : "no date"} · {t.priority}{t.assignee ? ` · ${t.assignee}` : ""}</div></span></li>))}</ol>
      )}
    </section>
  );
}

export function TicketsCard({ items }: { items: any[] }) {
  return (
    <section className="card">
      <div className="card-head"><span className="kind">Helpdesk</span><h2>{items.length} ticket{items.length === 1 ? "" : "s"}</h2></div>
      <ol className="list">{items.map((t) => (
        <li key={t.ref}><span><strong>{t.title}</strong> <span className="ref">{t.ref}</span>
          <div className="sub">{t.category} · {t.status.replace("_", " ")}{t.requester ? ` · ${t.requester}` : ""}</div></span></li>))}</ol>
    </section>
  );
}
