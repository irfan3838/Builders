// PurserComposer: type, attach, speak, send. Enter sends, Shift+Enter adds a line, Escape cancels the turn in flight.
import { AnimatePresence, motion } from "motion/react";
import { FileText, Keyboard, Sparkles, Mic, MicOff, Paperclip, RotateCcw, SendHorizontal, Square, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { usePurser } from "../../state/store";
import { ACCEPT_ATTR, useAssistant } from "./PurserVoiceController";

export default function PurserComposer() {
  const A = useAssistant();
  const { uploads, setUploads, suggestions } = usePurser();
  const [text, setText] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const ta = useRef<HTMLTextAreaElement>(null);
  const file = useRef<HTMLInputElement>(null);
  const box = useRef<HTMLDivElement>(null);
  const listening = ["listening", "speaking", "connecting", "waking"].includes(A.voice);

  useEffect(() => {  // autosize
    const el = ta.current;
    if (!el) return;
    el.style.height = "0px";
    el.style.height = Math.min(140, el.scrollHeight) + "px";
  }, [text]);

  const submit = async () => {
    const t = text.trim();
    if (!t) { setErr("Type a request first."); ta.current?.focus(); return; }
    if (t.length > 2000) { setErr("Keep requests under 2,000 characters."); return; }
    setErr(null);
    setText("");
    const ok = await A.send(t, box.current);
    if (!ok && !text) setText((cur) => cur || "");
  };

  const onKey = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); if (!A.sending) submit(); }
    if (e.key === "Escape") { if (A.sending) A.cancel(); else if (text) setText(""); }
  };

  const visibleChips = uploads.filter((u) => u.status === "uploading" || u.status === "error");

  return (
    <div className="composer-row">
      <AnimatePresence>
        {suggestions.length > 0 && !A.sending && (
          <motion.div className="suggest-row" role="group" aria-label="Suggested next steps"
            initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 6 }} transition={{ duration: 0.22 }}>
            {suggestions.map((sg) => (
              <button key={sg.utterance} className="suggest-chip" title={sg.utterance} aria-label={`Suggested: ${sg.utterance}`}
                onClick={(e) => A.send(sg.utterance, e.currentTarget)} disabled={!A.ready}>
                <Sparkles size={13} aria-hidden="true" /><span>{sg.label}</span>
              </button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
      <motion.div ref={box} className="composer glass" layout transition={{ duration: 0.3 }}
        onDragOver={(e) => e.preventDefault()}>
        <div className="chips" aria-live="polite">
          <AnimatePresence>
            {visibleChips.map((u) => (
              <motion.div key={u.key} className={`chip ${u.status === "error" ? "error" : ""}`} initial={{ opacity: 0, y: 14, rotate: -4, scale: 0.9 }}
                animate={{ opacity: 1, y: 0, rotate: 0, scale: 1 }} exit={{ opacity: 0, y: -18, scale: 0.9 }} transition={{ type: "spring", stiffness: 380, damping: 26 }}>
                <FileText size={14} />
                <span title={u.name}>{u.status === "error" ? `${u.name}: ${u.error}` : u.name}</span>
                {u.status === "uploading" && <span className="bar" aria-label={`${Math.round(u.progress * 100)}% uploaded`}><i style={{ width: `${u.progress * 100}%` }} /></span>}
                <button aria-label={u.status === "error" ? "Dismiss" : `Cancel upload of ${u.name}`}
                  onClick={() => (u.status === "error" ? setUploads((x) => x.filter((y) => y.key !== u.key)) : u.cancel?.())}><X size={13} /></button>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
        <button className="icon-btn" aria-label="Focus the text box" title="Type" onClick={() => ta.current?.focus()}><Keyboard size={20} /></button>
        <label className="sr-only" htmlFor="purser-input">Ask Purser</label>
        <textarea id="purser-input" ref={ta} rows={1} value={text} placeholder="Ask Purser anything about your finances…"
          onChange={(e) => { setText(e.target.value); if (err) setErr(null); }} onKeyDown={onKey} aria-invalid={!!err}
          aria-describedby={err ? "composer-err" : undefined} disabled={!A.ready} />
        {A.lastFailed && !A.sending && !text && (
          <button className="icon-btn" aria-label="Retry last request" title="Retry" onClick={() => A.send(A.lastFailed!, box.current)}><RotateCcw size={18} /></button>
        )}
        <button className="upload-pill" onClick={() => file.current?.click()} aria-label="Upload a receipt, bill or contract">
          <Paperclip size={17} /> <span>Upload file</span>
        </button>
        <button className="icon-btn mic-btn" aria-pressed={listening} onClick={A.toggleVoice} disabled={!A.ready}
          aria-label={listening ? "Stop voice" : A.voice === "denied" ? "Microphone blocked" : "Talk to Purser"} title={listening ? "Stop" : "Talk"}>
          {A.voice === "denied" ? <MicOff size={19} /> : <Mic size={19} />}
        </button>
        <span className="divider" aria-hidden="true" />
        {A.sending ? (
          <button className="send-btn" onClick={A.cancel} aria-label="Cancel request" title="Cancel (Esc)"><Square size={18} /></button>
        ) : (
          <motion.button className="send-btn" onClick={submit} disabled={!A.ready || !text.trim()} aria-label="Send" whileTap={{ scale: 0.86, x: 3 }}>
            <SendHorizontal size={24} />
          </motion.button>
        )}
        <input ref={file} type="file" accept={ACCEPT_ATTR} multiple hidden
          onChange={(e) => { const fs = [...(e.target.files || [])]; if (fs.length) A.upload(fs, box.current); e.target.value = ""; }} />
      </motion.div>
      {err && <p id="composer-err" className="composer-err" role="alert">{err}</p>}
    </div>
  );
}
