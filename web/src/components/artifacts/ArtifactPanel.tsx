// Desk panel: the tall glass inspector. Shows only what Purser or the user opened (agent-composed cards),
// plus in-flight uploads. Decision controls for the focused claim render into the footer slot.
import { AnimatePresence, motion } from "motion/react";
import { FileText, PanelRightOpen, X } from "lucide-react";
import { useEffect } from "react";
import { cardKey, CardView } from "../../cards";
import { dur, ease, reveal } from "../../animations/tokens";
import { UploadItem, usePurser } from "../../state/store";
import ClaimReview from "./ClaimReview";

function UploadCard({ u }: { u: UploadItem }) {
  const P = usePurser();
  return (
    <div className="card up-card" aria-live="polite">
      <div className="card-head"><span className="kind">{u.status === "error" ? "Upload failed" : u.status === "reading" ? "Reading" : "Uploading"}</span>
        {u.status !== "error" && <button className="link" onClick={() => u.cancel?.()}>Cancel</button>}
        {u.status === "error" && <button className="link" onClick={() => P.setUploads((x) => x.filter((y) => y.key !== u.key))}>Dismiss</button>}</div>
      <div className="up-name"><FileText size={14} style={{ verticalAlign: -2, marginRight: 6 }} />{u.name}</div>
      {u.status === "uploading" && <div className="up-bar" role="progressbar" aria-valuenow={Math.round(u.progress * 100)} aria-valuemin={0} aria-valuemax={100}>
        <motion.i animate={{ width: `${u.progress * 100}%` }} transition={{ duration: 0.2 }} /></div>}
      {u.status === "reading" && (
        <div className="up-sheet">
          <div className="lines" />
          <motion.div className="scanline" animate={{ top: ["-15%", "100%"] }} transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }} />
        </div>
      )}
      {u.status === "reading" && <p className="hint">Purser is reading the document and checking it against your records…</p>}
      {u.status === "error" && <p className="flag flag-danger">{u.error}</p>}
    </div>
  );
}

export default function ArtifactPanel() {
  const P = usePurser();
  const hasClaim = P.cards.some((c) => c.card === "claim_review");
  const visible = P.cards
    .filter((c) => !(c.card === "proposal" && hasClaim && c.proposal_id === P.decision?.proposalId))
    .sort((a, b) => Number(b.card === "claim_review") - Number(a.card === "claim_review"));  // the claim under review leads
  const empty = !visible.length && !P.uploads.length;

  useEffect(() => {
    if (!P.panelOpen) return;
    const k = (e: KeyboardEvent) => { if (e.key === "Escape" && !document.querySelector(".scrim")) P.setPanelOpen(false); };
    addEventListener("keydown", k);
    return () => removeEventListener("keydown", k);
  }, [P.panelOpen, P]);

  return (
    <>
      <AnimatePresence initial={false}>
        {P.panelOpen && (
          <motion.aside id="artifact-panel" key="panel" className="panel glass" aria-label="Desk"
            initial={{ opacity: 0, x: 60 }} animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 60 }} transition={{ duration: dur.panel, ease }}>
            <div className="panel-head">
              <h2>Desk</h2>
              <motion.button className="icon-btn" onClick={() => P.setPanelOpen(false)} aria-label="Close Desk" whileHover={{ rotate: 90 }} transition={{ duration: 0.2 }}>
                <X size={22} />
              </motion.button>
            </div>
            <div className="panel-body">
              {empty && <p className="panel-empty">Nothing open yet. Ask Purser about a claim, a budget or a bill, or hand it a receipt, and the evidence appears here.</p>}
              <AnimatePresence mode="popLayout" initial={false}>
                {P.uploads.map((u) => (
                  <motion.div key={u.key} layout variants={reveal} initial="hidden" animate="show" exit="exit"><UploadCard u={u} /></motion.div>
                ))}
                {visible.map((c, i) => (
                  <motion.div key={cardKey(c)} layout variants={reveal} initial="hidden" animate="show" exit="exit" custom={i}>
                    {c.card === "claim_review"
                      ? <ClaimReview card={c as any} bump={P.bump} primary />
                      : <CardView card={c} bump={P.bump} onChanged={P.refresh} onOpen={(n) => P.addCards([n])} />}
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
            <div className="panel-foot" id="panel-foot-slot" style={hasClaim ? undefined : { display: "none" }} />
          </motion.aside>
        )}
      </AnimatePresence>
      <AnimatePresence>
        {!P.panelOpen && (P.cards.length > 0 || P.uploads.length > 0) && (
          <motion.button className="panel-tab glass" onClick={() => P.setPanelOpen(true)} initial={{ x: 40, opacity: 0 }} animate={{ x: 0, opacity: 1 }} exit={{ x: 40, opacity: 0 }}
            aria-label={`Open Desk, ${P.cards.length} items`}>
            <PanelRightOpen size={16} style={{ marginBottom: 6 }} /> Desk · {P.cards.length}
          </motion.button>
        )}
      </AnimatePresence>
    </>
  );
}
