// Settings > My routines: describe a routine in plain words, review the compiled steps, save; list, run, delete.
// The server compiles + validates (tools limited to this role); nothing is saved until Save is clicked.
import { Loader2, Play, Trash2, Users } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "../../api";

type Routine = { id: number; title: string; when: string; checklist: string[]; tools: string[]; shared: boolean; owner: string;
  mine: boolean; editable: boolean; run: string };
type Draft = { title: string; when: string; examples: string[]; tools: string[]; checklist: string[]; shared: boolean; source_prompt: string };
type ListOut = { items: Routine[]; can_share: boolean; can_create: boolean };

const msg = (e: unknown) => (e instanceof ApiError ? e.message : "Something went wrong. Try again.");
const toolLabel = (t: string) => t.replace(/^propose_/, "prepare ").replace(/_/g, " ");

export default function RoutinesPanel({ onRun }: { onRun: (utterance: string) => void }) {
  const [list, setList] = useState<ListOut | null>(null);
  const [prompt, setPrompt] = useState("");
  const [shared, setShared] = useState(false);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [busy, setBusy] = useState<"" | "draft" | "save" | number>("");
  const [err, setErr] = useState("");

  const load = useCallback(async () => {
    try { setList(await api.get<ListOut>("/api/workflows")); } catch (e) { setErr(msg(e)); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const makeDraft = async () => {
    setErr(""); setDraft(null); setBusy("draft");
    try {
      const r = await api.post<{ draft: Draft; warnings: string[] }>("/api/workflows/draft", { prompt, shared });
      setDraft(r.draft); setWarnings(r.warnings);
    } catch (e) { setErr(msg(e)); } finally { setBusy(""); }
  };
  const save = async () => {
    if (!draft) return;
    setErr(""); setBusy("save");
    try {
      await api.post("/api/workflows", draft);
      setDraft(null); setPrompt(""); setShared(false); await load();
    } catch (e) { setErr(msg(e)); } finally { setBusy(""); }
  };
  const remove = async (r: Routine) => {
    setErr(""); setBusy(r.id);
    try { await api.del(`/api/workflows/${r.id}`); await load(); } catch (e) { setErr(msg(e)); } finally { setBusy(""); }
  };

  return (
    <section className="routines" aria-labelledby="rt-title" aria-busy={busy !== ""}>
      <h3 id="rt-title">My routines</h3>
      <p className="fine">Describe steps you repeat. Purser saves them as a routine you can run by saying “Run &lt;name&gt;”.
        Anything that changes data still waits for your yes.</p>

      {list?.can_create !== false && (
        <div className="field">
          <span id="rt-label">Describe a routine</span>
          <textarea className="rt-input" aria-labelledby="rt-label" aria-describedby={err ? "rt-err" : undefined} maxLength={2000}
            placeholder="Every Monday, show my tasks, my meetings this week and my leave balance"
            value={prompt} onChange={(e) => { setPrompt(e.target.value); setErr(""); }} />
          {list?.can_share && (
            <label className="toggle"><input type="checkbox" checked={shared} onChange={(e) => setShared(e.target.checked)} />
              Share with everyone in the workspace</label>)}
          <div className="dlg-actions" style={{ marginTop: 6 }}>
            <button className="btn btn-sm" disabled={prompt.trim().length < 8 || busy !== ""} onClick={makeDraft}>
              {busy === "draft" ? <><Loader2 size={15} className="spin" aria-hidden="true" /> Drafting… (5-10 s)</> : "Draft routine"}
            </button>
          </div>
        </div>)}
      {err && <p id="rt-err" className="dlg-err" role="alert">{err}</p>}

      {draft && (
        <div className="rt-preview" aria-live="polite">
          <div className="rt-head"><strong>{draft.title}</strong>{draft.shared && <span className="rt-badge"><Users size={12} aria-hidden="true" /> shared</span>}</div>
          <ol>{draft.checklist.map((c, i) => <li key={i}>{c}</li>)}</ol>
          <div className="rt-tools">{draft.tools.map((t) => <span key={t} className="rt-tool">{toolLabel(t)}</span>)}</div>
          <p className="fine">To run it, say: “Run {draft.title}”</p>
          {warnings.map((w) => <p key={w} className="fine rt-warn">{w}</p>)}
          <div className="dlg-actions">
            <button className="btn btn-sm btn-ghost" onClick={() => setDraft(null)} disabled={busy !== ""}>Discard</button>
            <button className="btn btn-sm btn-primary" onClick={save} disabled={busy !== ""}>
              {busy === "save" ? <><Loader2 size={15} className="spin" aria-hidden="true" /> Saving…</> : "Save routine"}
            </button>
          </div>
        </div>)}

      {list && (list.items.length ? (
        <ul className="rt-list">
          {list.items.map((r) => (
            <li key={r.id}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div className="rt-head"><strong>{r.title}</strong>
                  {r.shared && <span className="rt-badge"><Users size={12} aria-hidden="true" /> {r.mine ? "shared" : `by ${r.owner}`}</span>}</div>
                <div className="fine">{r.checklist.length} steps · {r.tools.map(toolLabel).join(", ")}</div>
              </div>
              <button className="icon-btn" aria-label={`Run ${r.title}`} title="Run" onClick={() => onRun(r.run)}><Play size={16} /></button>
              {r.editable && (
                <button className="icon-btn" aria-label={`Delete ${r.title}`} title="Delete" disabled={busy !== ""} onClick={() => remove(r)}>
                  {busy === r.id ? <Loader2 size={16} className="spin" /> : <Trash2 size={16} />}
                </button>)}
            </li>))}
        </ul>) : <p className="fine">No routines yet.</p>)}
    </section>
  );
}
