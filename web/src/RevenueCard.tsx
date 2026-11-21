// Revenue cards (customer invoices, ported from the copilot Revenue module). Every figure comes from the server
// read models (/api/revenue/*), the same ones the agent speaks from. Status is always a word plus a colour.
import { useEffect, useRef, useState } from "react";
import { api } from "./api";

function useLoad<T>(path: string | null, bump = 0) {
  const [data, setData] = useState<T | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    if (!path) return;
    let live = true;
    setErr(null);
    api.get<T>(path).then((d) => live && setData(d)).catch((e) => live && setErr(e.message));
    return () => { live = false; };
  }, [path, bump]);
  return { data, err };
}

const STATUS: Record<string, string> = {
  to_raise: "To raise", sent: "Sent", part_paid: "Part paid", paid: "Paid", written_off: "Written off", merged: "Merged",
};
const SHORT: Record<string, string> = {
  to_raise: "Raise", sent: "Sent", part_paid: "Part", paid: "Paid", written_off: "Off", merged: "Merged",
};

function Shell({ kind, title, refId, children }: { kind: string; title: string; refId?: string; children: React.ReactNode }) {
  return (
    <section className="card">
      <div className="card-head"><span className="kind">{kind}</span><h2>{title}</h2>{refId && <span className="ref">{refId}</span>}</div>
      {children}
    </section>
  );
}

function State({ what, err }: { what: string; err: string | null }) {
  return err
    ? <section className="card"><p className="error">Could not load {what}: {err}</p></section>
    : <section className="card" aria-busy="true"><p className="hint">Loading {what}…</p></section>;
}

export function RevenueCard({ fy, period, clientId, bump, onOpen }: {
  fy?: string; period?: string; clientId?: number | null; bump: number; onOpen?: (ref: string) => void;
}) {
  const q = new URLSearchParams();
  if (fy) q.set("fy", fy);
  if (period && period !== "fy") q.set("period", period);
  if (clientId) q.set("client_id", String(clientId));
  const { data, err } = useLoad<any>(`/api/revenue/overview?${q}`, bump);
  const wrap = useRef<HTMLDivElement>(null);
  const nowKey = data?.as_of?.slice(0, 7);
  useEffect(() => {  // bring the current month into view in the narrow panel
    const el = wrap.current?.querySelector<HTMLElement>(`[data-month="${nowKey}"]`);
    if (el && wrap.current) wrap.current.scrollLeft = Math.max(0, el.offsetLeft - wrap.current.clientWidth / 2);
  }, [data, nowKey]);
  if (!data) return <State what="revenue" err={err} />;
  const k = data.kpis;
  const tiles: [string, string, string?][] = [
    ["Projected", k.projected], ["Received", k.received],
    ["Outstanding", k.outstanding, k.overdue_count ? `${k.overdue} overdue (${k.overdue_count})` : undefined],
    ["To raise", k.to_raise, k.to_raise_due_count ? `${k.to_raise_due_count} due by now` : undefined],
  ];
  const rows = data.grid.filter((g: any) => Object.keys(g.cells).length);
  // Only the span of months that has invoices (an FY grid is mostly empty early in the year).
  const used = data.months.map((m: any, i: number) => (rows.some((g: any) => g.cells[m.key]) ? i : -1)).filter((i: number) => i >= 0);
  const months = used.length ? data.months.slice(used[0], used[used.length - 1] + 1) : data.months;
  return (
    <Shell kind="Revenue" title={data.period_label}>
      <div className="kpis rev-kpis">
        {tiles.map(([label, v, sub]) => (
          <div key={label}>
            <div className="hint">{label}</div>
            <div className="kpi-num num">{v}</div>
            {sub && <div className={`sub num ${label === "Outstanding" ? "danger-text" : ""}`}>{sub}</div>}
          </div>
        ))}
      </div>
      {rows.length > 0 && (
        <div className="rev-grid-wrap" role="region" aria-label="Invoices by client and month" tabIndex={0} ref={wrap}>
          <table className="data rev-grid">
            <thead>
              <tr><th scope="col">Client</th>
                {months.map((m: any) => <th key={m.key} scope="col" data-month={m.key} className={`num ${m.key === nowKey ? "rev-now" : ""}`}>{m.label}</th>)}
                <th scope="col" className="amount">Total</th></tr>
            </thead>
            <tbody>
              {rows.map((g: any) => (
                <tr key={g.client_id} className={g.state !== "active" ? "rev-inactive" : ""}>
                  <th scope="row">{g.client}{g.state !== "active" && <span className="sub"> · {g.state === "ended" ? "project over" : g.state}</span>}</th>
                  {months.map((m: any) => {
                    const c = g.cells[m.key];
                    if (!c) return <td key={m.key} className="rev-empty" aria-label="no invoice">·</td>;
                    const label = `${STATUS[c.status] ?? c.status}${c.overdue ? ", overdue" : ""}: ${c.billed}`;
                    return (
                      <td key={m.key} className={`rev-cell st-${c.status}${c.overdue ? " overdue" : ""}`}>
                        <button type="button" className="rev-btn" title={`${label} (${c.refs.join(", ")})`} aria-label={`${g.client} ${m.label}: ${label}`}
                          onClick={() => onOpen?.(c.refs[0])}>
                          <span className="num">{c.billed}</span>
                          <span className="rev-st">{c.overdue ? "! Overdue" : SHORT[c.status] ?? c.status}</span>
                        </button>
                      </td>
                    );
                  })}
                  <td className="amount num">{g.total}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {data.exposure.length > 0 && (
        <p className="hint num">Foreign exposure: {data.exposure.map((e: any) => `${e.amount} (${e.inr})`).join(" · ")}</p>
      )}
      <p className="hint">As of {data.as_of}. {data.definitions}.</p>
    </Shell>
  );
}

export function InvoiceCard({ refId, bump }: { refId: string; bump: number }) {
  const { data, err } = useLoad<any>(`/api/revenue/invoices/${encodeURIComponent(refId)}`, bump);
  if (!data) return <State what="invoice" err={err} />;
  const foreign = data.currency !== "INR";
  const src: Record<string, string> = { manual: "rate you set", month: "month rate", ecb: `ECB reference${data.fx_date ? ` ${data.fx_date}` : ""}`, inr: "" };
  return (
    <Shell kind="Invoice" title={data.label} refId={data.number ? `${data.ref} · ${data.number}` : data.ref}>
      <p className={`rev-badge st-${data.status}${data.overdue_days ? " overdue" : ""}`}>
        {data.status_label}{data.overdue_days ? ` · ${data.overdue_days} days overdue` : ""}
      </p>
      <dl className="facts num">
        <dt>Amount</dt><dd>{data.amount}{foreign && <> at ₹{data.rate} <span className="sub">({src[data.fx_source] ?? data.fx_source})</span></>}</dd>
        <dt>Total (INR)</dt><dd><strong>{data.total}</strong></dd>
        <dt>Received</dt><dd>{data.received}</dd>
        <dt>Still due</dt><dd>{data.remaining}</dd>
        {data.period && <><dt>Period</dt><dd>{data.period}</dd></>}
        {data.sent_on && <><dt>Sent</dt><dd>{data.sent_on}</dd></>}
        {data.due_on && <><dt>Due</dt><dd>{data.due_on}</dd></>}
        {data.raise_on && <><dt>Raise on</dt><dd>{data.raise_on}</dd></>}
        {data.moved && <><dt>Moved on</dt><dd>{data.moved} → {data.moved_to}</dd></>}
        {data.notes && <><dt>Notes</dt><dd>{data.notes}</dd></>}
      </dl>
      {data.payments.length > 0 && (
        <table className="data">
          <thead><tr><th scope="col">Payment received</th><th scope="col" className="amount">Amount</th></tr></thead>
          <tbody>{data.payments.map((p: any, i: number) => (
            <tr key={i}><td className="num">{p.received_on ?? "date not recorded"}</td><td className="amount num">{p.amount}</td></tr>
          ))}</tbody>
        </table>
      )}
    </Shell>
  );
}

export function FxRatesCard({ fy, bump }: { fy?: string; bump: number }) {
  const { data, err } = useLoad<any>(`/api/revenue/fx${fy ? `?fy=${encodeURIComponent(fy)}` : ""}`, bump);
  if (!data) return <State what="conversion rates" err={err} />;
  return (
    <Shell kind="Conversion rates" title={`FY ${data.fy}`}>
      {data.rows.length === 0 ? <p className="hint">No foreign-currency clients this year.</p> : (
        <div className="rev-grid-wrap" role="region" aria-label="Rates by month" tabIndex={0}>
          <table className="data rev-grid">
            <thead><tr><th scope="col">Currency</th>{data.months.map((m: string) => <th key={m} scope="col">{m}</th>)}<th scope="col">ECB latest</th></tr></thead>
            <tbody>{data.rows.map((r: any) => {
              const q = data.ecb[r.currency];
              return (
                <tr key={r.currency}><th scope="row">{r.currency}</th>
                  {r.cells.map((c: any) => (
                    <td key={c.key} className={`num ${c.rate ? "fx-set" : c.carried ? "fx-carried" : "rev-empty"}`}
                      title={c.rate ? "Set for this month" : c.carried ? "Carried from an earlier month" : "No month rate: ECB is used"}>
                      {c.rate ?? (c.carried ? <span className="sub">↳ {c.carried}</span> : "·")}
                      {c.invoices > 0 && <span className="sub"> ({c.invoices})</span>}
                    </td>
                  ))}
                  <td className="num">{q ? <>{q.rate}<span className="sub"> {q.date}{q.stale ? " · stale" : ""}</span></> : "—"}</td>
                </tr>
              );
            })}</tbody>
          </table>
        </div>
      )}
      <p className="hint">Bold: rate set for that month. ↳ carried from an earlier month. (n) invoices in the month. ECB reference rates via Frankfurter.</p>
      {data.history?.length > 0 && (
        <table className="data">
          <thead><tr><th scope="col">When</th><th scope="col">What</th><th scope="col">Rate</th><th scope="col">Repriced</th></tr></thead>
          <tbody>{data.history.slice(0, 6).map((h: any, i: number) => (
            <tr key={i}><td className="num">{new Date(h.at).toLocaleString("en-IN", { dateStyle: "short", timeStyle: "short" })}</td>
              <td>{h.currency} {h.what}</td><td className="num">{h.old} → {h.new}</td><td>{h.repriced.length || "—"}</td></tr>
          ))}</tbody>
        </table>
      )}
    </Shell>
  );
}
