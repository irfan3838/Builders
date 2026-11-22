// AppShell: sidebar | main column (workspace or a view, composer) | Artifact Panel, over the ambient ribbons.
import { AnimatePresence, motion } from "motion/react";
import { useEffect, useState } from "react";
import { ease } from "../../animations/tokens";
import { usePurser } from "../../state/store";
import AmbientRibbons from "../assistant/AmbientRibbons";
import PurserComposer from "../assistant/PurserComposer";
import { useAssistant } from "../assistant/PurserVoiceController";
import ArtifactPanel from "../artifacts/ArtifactPanel";
import ToastManager from "../shared/ToastManager";
import PurserSidebar from "./PurserSidebar";
import WorkspaceView from "../../views/WorkspaceView";
import { ViewRouter } from "../../views/ViewRouter";
import { canSee } from "../../roles";

export default function AppShell() {
  const P = usePurser();
  const A = useAssistant();
  const [dragging, setDragging] = useState(false);
  const energy = { listening: 1, speaking: 0.8, processing: 0.6, connecting: 0.4, success: 0.7 }[P.orb as string] ?? 0;

  useEffect(() => {
    let depth = 0;
    const has = (e: DragEvent) => e.dataTransfer?.types.includes("Files");
    const enter = (e: DragEvent) => { if (has(e)) { depth++; setDragging(true); } };
    const over = (e: DragEvent) => { if (has(e)) e.preventDefault(); };
    const leave = (e: DragEvent) => { if (has(e) && --depth <= 0) { depth = 0; setDragging(false); } };
    const drop = (e: DragEvent) => {
      if (!has(e)) return;
      e.preventDefault(); depth = 0; setDragging(false);
      const fs = [...(e.dataTransfer?.files || [])];
      if (fs.length) A.upload(fs, { x: e.clientX, y: e.clientY } as any);
    };
    addEventListener("dragenter", enter); addEventListener("dragover", over); addEventListener("dragleave", leave); addEventListener("drop", drop);
    return () => { removeEventListener("dragenter", enter); removeEventListener("dragover", over); removeEventListener("dragleave", leave); removeEventListener("drop", drop); };
  }, [A]);

  return (
    <div className="shell" data-view={P.view === "workspace" ? "workspace" : "other"}>
      <AmbientRibbons energy={energy} anchor="#purser-orb, .mini-orb" />
      <div className="vignette" />
      <PurserSidebar />
      <main className="main" id="main">
        {!P.online && <div className="flag flag-warn" role="status" style={{ margin: "12px 40px 0" }}>You are offline. Purser will reconnect when the network returns; nothing is lost.</div>}
        <AnimatePresence mode="wait" initial={false}>
          <motion.div key={P.view === "workspace" ? "ws" : P.view} style={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column" }}
            initial={{ opacity: 0, y: 12, filter: "blur(6px)" }} animate={{ opacity: 1, y: 0, filter: "blur(0px)", transitionEnd: { filter: "none" } }} exit={{ opacity: 0, y: -10, filter: "blur(6px)" }}
            transition={{ duration: 0.36, ease }}>
            {P.view === "workspace" || !canSee(P.me.role, P.view) ? <WorkspaceView /> : <ViewRouter view={P.view} />}
          </motion.div>
        </AnimatePresence>
        {/* One composer for every view: typed text and chips survive navigation. */}
        <div className="shell-composer"><PurserComposer /></div>
      </main>
      <ArtifactPanel />
      <ToastManager />
      <AnimatePresence>{dragging && (
        <motion.div className="drop-veil" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.18 }}>
          <motion.p initial={{ scale: 0.94 }} animate={{ scale: 1 }}>Drop to hand it to Purser</motion.p>
        </motion.div>)}</AnimatePresence>
    </div>
  );
}
