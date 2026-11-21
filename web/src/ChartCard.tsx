// Generic chart card. It renders whatever ResultSnapshot the agent built: the server decides the numbers,
// labels, title and chart type; this file only maps a snapshot onto an ECharts option (snapshotToOption).
import { useEffect, useRef, useState } from "react";
import * as echarts from "echarts/core";
import { BarChart, LineChart, PieChart } from "echarts/charts";
import { GridComponent, LegendComponent, TooltipComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import type { EChartsCoreOption } from "echarts/core";
import { api } from "./api";

echarts.use([BarChart, LineChart, PieChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer]);

// Equal greens. Single series = brand green. Multi-series slots validated for lightness band, CVD and
// normal-vision separation (dataviz validate_palette.js); "Other" is neutral gray. Table view is always one click away.
const SERIES = ["#00b140", "#1d6b57", "#7fa800"];
const OTHER = "#9aa0a6";
const INK = "#212121", MUTED = "#5f6368", LINE = "#e8e8e8", DEEP = "#0f362d", SURFACE = "#ffffff";

type Row = { key: string; label: string; series: string | null; values: Record<string, number>; refs: string[] };
type Meta = {
  title: string; chart: string; measures: { name: string; label: string; unit: string }[];
  dimension: { name: string; label: string; kind: string } | null; series_by: { name: string; label: string } | null;
  filters_applied: string[]; as_of: string; scope: string; record_label: string; source_label: string; lineage?: string;
};
export type Snapshot = { id: string; rows: Row[]; meta: Meta; totals: Record<string, { value: number; display: string }> };

const fullInr = (paise: number) => "₹" + Math.round(paise / 100).toLocaleString("en-IN");
/** Indian compact units for axes: K, L (lakh), Cr (crore). */
function compactInr(paise: number): string {
  const r = paise / 100, a = Math.abs(r);
  const t = (n: number) => String(Number(n.toFixed(2)));
  if (a >= 1e7) return `₹${t(r / 1e7)}Cr`;
  if (a >= 1e5) return `₹${t(r / 1e5)}L`;
  if (a >= 1e3) return `₹${t(r / 1e3)}K`;
  return `₹${t(r)}`;
}
const fmtFull = (v: number, unit: string) => (unit === "paise" ? fullInr(v) : v.toLocaleString("en-IN"));
const fmtAxis = (v: number, unit: string) => (unit === "paise" ? compactInr(v) : v.toLocaleString("en-IN"));

/** Pivot snapshot rows into categories × series. Series = series_by values, else one per measure. */
function pivot(s: Snapshot) {
  const cats: string[] = [];
  for (const r of s.rows) if (!cats.includes(r.label)) cats.push(r.label);
  const ms = s.meta.measures;
  if (s.meta.series_by) {
    const names: string[] = [];
    for (const r of s.rows) if (r.series && !names.includes(r.series)) names.push(r.series);
    names.sort((a, b) => Number(a === "Other") - Number(b === "Other"));
    const m = ms[0].name;
    return { cats, series: names.map((n) => ({ name: n, data: cats.map((c) => s.rows.find((r) => r.label === c && r.series === n)?.values[m] ?? 0) })) };
  }
  return { cats, series: ms.map((m) => ({ name: m.label, data: cats.map((c) => s.rows.find((r) => r.label === c)?.values[m.name] ?? 0) })) };
}

export function snapshotToOption(s: Snapshot, highlight?: string | null): EChartsCoreOption {
  const unit = s.meta.measures[0].unit;
  const { cats, series } = pivot(s);
  const multi = series.length > 1;
  const color = (i: number, name: string) => (name === "Other" ? OTHER : multi ? SERIES[i % SERIES.length] : SERIES[0]);
  const axisText = { color: MUTED, fontFamily: "DM Sans, sans-serif", fontSize: 12 };
  const tooltip = {
    trigger: s.meta.chart === "donut" ? "item" : "axis", confine: true,
    axisPointer: { type: s.meta.chart === "line" || s.meta.chart === "area" ? "line" : "shadow", lineStyle: { color: LINE } },
    borderColor: LINE, textStyle: { color: INK, fontFamily: "DM Sans, sans-serif" },
    valueFormatter: (v: number) => fmtFull(v, unit),
  };
  const legend = multi ? { top: 0, left: 0, icon: "roundRect", itemWidth: 10, itemHeight: 10, textStyle: { color: INK } } : undefined;

  if (s.meta.chart === "donut") {
    const sr = series[0];
    return {
      tooltip, legend: { bottom: 0, icon: "roundRect", itemWidth: 10, itemHeight: 10, textStyle: { color: INK } },
      series: [{
        type: "pie", radius: ["52%", "78%"], center: ["50%", "45%"], padAngle: 1,
        itemStyle: { borderColor: SURFACE, borderWidth: 2, borderRadius: 4 },
        label: { show: true, color: INK, formatter: (p: any) => `${p.name}\n${fmtAxis(p.value, unit)}` },
        data: cats.map((c, i) => ({ name: c, value: sr.data[i],
          itemStyle: { color: c === "Other" ? OTHER : ["#00b140", "#1d6b57", "#7fa800", "#5f8f7f", "#b7d98a", "#0f362d"][i % 6],
                       opacity: highlight && c !== highlight ? 0.35 : 1 } })),
      }],
    };
  }

  const horizontal = s.meta.chart === "horizontal_bar";
  const isLine = s.meta.chart === "line" || s.meta.chart === "area";
  const stacked = s.meta.chart === "stacked_bar";
  const catAxis = { type: "category", data: cats, axisTick: { show: false }, axisLine: { lineStyle: { color: LINE } },
                    axisLabel: { ...axisText, ...(horizontal ? { width: 140, overflow: "truncate" } : { interval: 0, hideOverlap: true }) },
                    inverse: horizontal };
  const valAxis = { type: "value", splitLine: { lineStyle: { color: LINE } }, axisLabel: { ...axisText, formatter: (v: number) => fmtAxis(v, unit) } };
  const radius = horizontal ? [0, 4, 4, 0] : [4, 4, 0, 0];
  return {
    tooltip, legend,
    grid: { left: 8, right: 16, top: multi ? 34 : 12, bottom: 8, containLabel: true },
    xAxis: horizontal ? valAxis : catAxis,
    yAxis: horizontal ? catAxis : valAxis,
    series: series.map((sr, i) => isLine ? {
      type: "line", name: sr.name, data: sr.data, smooth: false, symbol: "circle", symbolSize: 8, showSymbol: true,
      lineStyle: { width: 2, color: color(i, sr.name) }, itemStyle: { color: color(i, sr.name), borderColor: SURFACE, borderWidth: 2 },
      areaStyle: s.meta.chart === "area" ? { color: color(i, sr.name), opacity: 0.12 } : undefined,
    } : {
      type: "bar", name: sr.name, stack: stacked ? "total" : undefined, barMaxWidth: 36, barGap: "12%",
      data: sr.data.map((v, j) => ({
        value: v,
        itemStyle: {
          color: !multi && highlight === cats[j] ? DEEP : color(i, sr.name),
          opacity: highlight && cats[j] !== highlight ? 0.4 : 1,
          borderRadius: stacked && i < series.length - 1 ? 0 : radius,
          borderColor: SURFACE, borderWidth: stacked ? 1 : 0,
        },
      })),
      // Selective direct label: only the highlighted bar (read aloud), or every bar when there are few.
      label: { show: !multi && (highlight ? true : cats.length <= 6), position: horizontal ? "right" : "top", color: INK,
               formatter: (p: any) => (!highlight || p.name === highlight ? fmtAxis(p.value, unit) : "") },
    }),
  };
}

function useSnapshot(id: string, bump: number) {
  const [data, setData] = useState<Snapshot | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    let live = true;
    api.get<Snapshot>(`/api/snapshots/${id}`).then((d) => live && setData(d)).catch((e) => live && setErr(e.message));
    return () => { live = false; };
  }, [id, bump]);
  return { data, err };
}

function Plot({ snap, highlight }: { snap: Snapshot; highlight?: string | null }) {
  const el = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!el.current) return;
    const chart = echarts.init(el.current, undefined, { renderer: "canvas" });
    chart.setOption(snapshotToOption(snap, highlight));
    const ro = new ResizeObserver(() => chart.resize());
    ro.observe(el.current);
    return () => { ro.disconnect(); chart.dispose(); };
  }, [snap, highlight]);
  const n = new Set(snap.rows.map((r) => r.label)).size;
  const h = snap.meta.chart === "horizontal_bar" ? Math.max(180, n * 34 + 40) : snap.meta.chart === "donut" ? 280 : 240;
  return <div ref={el} className="plot" style={{ height: h }} role="img" aria-label={`${snap.meta.title}. Use the table view for exact values.`} />;
}

function DataTable({ snap, highlight }: { snap: Snapshot; highlight?: string | null }) {
  const ms = snap.meta.measures;
  return (
    <div className="table-wrap">
      <table className="data">
        <thead><tr>
          <th>{snap.meta.dimension?.label ?? ""}</th>{snap.meta.series_by && <th>{snap.meta.series_by.label}</th>}
          {ms.map((m) => <th key={m.name} className="amount">{m.label}</th>)}<th>Source {snap.meta.record_label}</th>
        </tr></thead>
        <tbody>
          {snap.rows.map((r, i) => (
            <tr key={i} className={highlight === r.label ? "hl" : ""}>
              <td>{r.label}</td>{snap.meta.series_by && <td>{r.series}</td>}
              {ms.map((m) => <td key={m.name} className="amount num">{fmtFull(r.values[m.name], m.unit)}</td>)}
              <td className="ref">{r.refs.join(", ") || "—"}</td>
            </tr>
          ))}
        </tbody>
        <tfoot><tr>
          <td>Total</td>{snap.meta.series_by && <td />}
          {ms.map((m) => <td key={m.name} className="amount num">{snap.totals[m.name]?.display}</td>)}<td />
        </tr></tfoot>
      </table>
    </div>
  );
}

function Kpi({ snap }: { snap: Snapshot }) {
  return (
    <div className="kpis">
      {snap.meta.measures.map((m) => (
        <div key={m.name} className="kpi"><div className="kind">{m.label}</div><div className="kpi-num num">{snap.totals[m.name]?.display}</div></div>
      ))}
    </div>
  );
}

export function ChartCard({ id, highlight, bump, display, compact }:
  { id: string; highlight?: string | null; bump: number; display?: string; compact?: boolean }) {
  const { data, err } = useSnapshot(id, bump);
  const [table, setTable] = useState(display === "table");
  if (err) return <section className="card"><p className="error">Could not load chart: {err}</p></section>;
  if (!data) return <section className="card" aria-busy="true"><p className="hint">Loading chart…</p></section>;
  const kpi = display === "kpi" || data.meta.chart === "kpi" || !data.meta.dimension;
  const asTable = !kpi && (table || data.meta.chart === "table");
  const Wrap = compact ? "div" : "section";
  return (
    <Wrap className={compact ? "view-item" : "card chart-card"}>
      <div className="card-head">
        <span className="kind">{data.meta.source_label}</span>
        {!kpi && data.meta.chart !== "table" && (
          <button className="link" onClick={() => setTable(!table)} aria-pressed={table}>{table ? "Chart" : "Table"}</button>
        )}
      </div>
      <h2 className="chart-title">{data.meta.title}</h2>
      {kpi ? <Kpi snap={data} /> : asTable ? <DataTable snap={data} highlight={highlight} /> : <Plot snap={data} highlight={highlight} />}
      {!kpi && data.meta.measures.length === 1 && (
        <p className="hint num">Total {data.totals[data.meta.measures[0].name]?.display}</p>
      )}
      {data.meta.filters_applied.length > 0 && <p className="hint">Filters: {data.meta.filters_applied.join(" · ")}</p>}
      <p className="hint">As of {new Date(data.meta.as_of).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })}
        {data.meta.scope !== "whole workspace" ? ` · ${data.meta.scope}` : ""} · {new Set(data.rows.flatMap((r) => r.refs)).size} source {data.meta.record_label}</p>
    </Wrap>
  );
}

export function ViewCard({ title, items, bump }: { title: string; items: { snapshot_id: string; display: string }[]; bump: number }) {
  return (
    <section className="card view-card">
      <div className="card-head"><span className="kind">View</span><h2>{title}</h2></div>
      <div className="view-grid">
        {items.map((it) => <ChartCard key={it.snapshot_id + it.display} id={it.snapshot_id} bump={bump} display={it.display} compact />)}
      </div>
    </section>
  );
}
