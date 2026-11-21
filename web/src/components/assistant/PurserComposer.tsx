// PurserComposer: type, attach, speak, send. Enter sends, Shift+Enter adds a line, Escape cancels the turn in flight.
import { AnimatePresence, motion } from "motion/react";
import { FileText, Sparkles, Mic, MicOff, Paperclip, RotateCcw, SendHorizontal, Square, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { usePurser } from "../../state/store";
import { ACCEPT_ATTR, useAssistant } from "./PurserVoiceController";

export default function PurserComposer() {
  const A = useAssistant();
  const { uploads, setUploads, suggestions, choice, setChoice } = usePurser();
  const showChoice = !!choice && (!choice.answered || A.sending);
  const answer = (label: string, el: Element) => { setChoice((c) => (c ? { ...c, answered: label } : c)); A.send(label, el); };
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
    if (!A.ready) { setErr(A.connError ? "Purser is offline. Retry the connection first." : "Connecting to Purser, one moment…"); return; }
    setErr(null);
    setText("");
    const ok = await A.send(t, box.current);
    // Give the words back if the turn failed and the user has not started typing something else.
    if (!ok) setText((cur) => cur || t);
  };

  const onKey = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing && e.keyCode !== 229) {
      e.preventDefault();
      if (A.sending) setErr("Purser is still answering. Press Esc to stop it, or wait a moment.");
      else submit();
    }
    if (e.key === "Escape") { if (A.sending) A.cancel(); else if (text) setText(""); }
  };

  const visibleChips = uploads.filter((u) => u.status === "uploading" || u.status === "error");

  return (
    <div className="composer-row">
      <AnimatePresence mode="wait">
        {showChoice && choice && (
          <motion.div key={choice.id} className="choice-card glass" role="group" aria-labelledby={`q-${choice.id}`}
            initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 6 }} transition={{ duration: 0.22 }}>
            <p className="choice-q" id={`q-${choice.id}`}>
              <span className="choice-step">Question {choice.step} of up to {choice.max}</span>{choice.question}
            </p>
            <div className="choice-opts">
              {choice.options.map((o, i) => (
                <button key={o.value} className={`choice-opt ${choice.answered === o.label ? "picked" : ""}`} disabled={!!choice.answered || !A.ready}
                  onClick={(e) => answer(o.label, e.currentTarget)} aria-pressed={choice.answered === o.label}>
                  <span className="choice-num" aria-hidden="true">{i + 1}</span>{o.label}
                </button>
              ))}
            </div>
            <p className="choice-hint">Tap an answer or just say it.</p>
          </motion.div>
        )}
      </AnimatePresence>
      <AnimatePresence>
        {!showChoice && suggestions.length > 0 && !A.sending && (
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
        <label className="sr-only" htmlFor="purser-input">Ask Purser</label>
        <textarea id="purser-input" ref={ta} rows={1} value={text} placeholder={A.ready ? "Ask Purser anything…" : "Connecting to Purser…"}
          onChange={(e) => { setText(e.target.value); if (err) setErr(null); }} onKeyDown={onKey} aria-invalid={!!err}
          aria-describedby={err ? "composer-err" : undefined} />
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
      {A.connError && (
        <p className="composer-err" role="alert">
          {A.connError} <button className="link-btn" onClick={A.reconnect}>Retry</button>
        </p>
      )}
      {err && !A.connError && <p id="composer-err" className="composer-err" role="alert">{err}</p>}
    </div>
  );
}
