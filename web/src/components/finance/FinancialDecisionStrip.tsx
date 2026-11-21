// The decision strip under the composer: matched reservation, difference, and budget before -> after approval.
// Values come from the claim review in focus (server data). After approval the number counts to the confirmed value.
import { AnimatePresence, motion } from "motion/react";
import { ease } from "../../animations/tokens";
import { inr } from "../../api";
import { usePurser } from "../../state/store";
import AnimatedCounter from "../shared/AnimatedCounter";

export default function FinancialDecisionStrip() {
  const { decision: d } = usePurser();
  return (
    <AnimatePresence mode="wait" initial={false}>
      {!d ? (
        <motion.div key="empty" className="strip glass empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
          Decisions appear here when Purser matches a receipt or opens a claim.
        </motion.div>
      ) : (
        <motion.section key={`${d.ref}-${d.status}`} className={`strip glass ${d.below === false ? "warn" : ""}`} aria-label="Financial decision"
          initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.45, ease }}>
          <div>
            <span className="s-label">Matched reservation</span>
            <span className="s-value">{d.reservation ?? "None"}</span>
          </div>
          <div>
            <span className="s-label">{d.below === false ? "Above reservation" : "Below reservation"}</span>
            <span className="s-value num">{d.differencePaise == null ? "—" : inr(Math.abs(d.differencePaise))}</span>
          </div>
          <div>
            <span className="s-label">{d.category ?? "Budget"} available {d.final ? "now" : "after approval"}</span>
            {d.beforePaise == null || d.afterPaise == null ? <span className="s-value">—</span> : (
              <span className="s-flow num">
                {!d.final && <><span className="s-value">{inr(d.beforePaise)}</span><span className="arrow" aria-hidden="true">→</span></>}
                <span className="s-big" id="strip-after">
                  {d.final ? <AnimatedCounter value={d.afterPaise} from={d.beforePaise} duration={1.4} /> : inr(d.afterPaise)}
                </span>
                {d.final && <span className="sr-only">, was {inr(d.beforePaise)}</span>}
              </span>
            )}
            <span className="s-status">{d.final ? `Approved · was ${inr(d.beforePaise)}` : d.status === "submitted" ? "Pending decision" : d.status === "receipt" ? "Not yet a claim" : d.status}</span>
          </div>
        </motion.section>
      )}
    </AnimatePresence>
  );
}
