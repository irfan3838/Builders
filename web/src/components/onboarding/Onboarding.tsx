// First-login onboarding: welcome modal, then a spotlight tour. Shown once per user (localStorage, per user id);
// replayable from Settings via useOnboarding().replay().
import { createContext, ReactNode, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { AnimatePresence } from "motion/react";
import { usePurser } from "../../state/store";
import WelcomeModal from "./WelcomeModal";
import ProductTour from "./ProductTour";

type Stage = "idle" | "welcome" | "tour";
type Ctx = { stage: Stage; replay: () => void };

const OnboardingContext = createContext<Ctx>({ stage: "idle", replay: () => {} });
export const useOnboarding = () => useContext(OnboardingContext);

const key = (id: string | number) => `purser.tour.v1.${id}`;
const read = (id: string | number) => { try { return localStorage.getItem(key(id)); } catch { return "done"; } };
const write = (id: string | number, v: string) => { try { localStorage.setItem(key(id), v); } catch { /* private mode */ } };

export function OnboardingProvider({ children, setNavOpen }: { children: ReactNode; setNavOpen: (open: boolean) => void }) {
  const P = usePurser();
  const [stage, setStage] = useState<Stage>("idle");

  useEffect(() => {
    if (read(P.me.id)) return;
    const t = window.setTimeout(() => setStage("welcome"), 700);  // let the shell paint first
    return () => clearTimeout(t);
  }, [P.me.id]);

  const end = useCallback((how: "done" | "skipped") => {
    write(P.me.id, how);
    setStage("idle");
    setNavOpen(false);
    if (how === "done") P.toast("success", "You're set. Try saying “Hey Purser”.");
  }, [P, setNavOpen]);

  const startTour = useCallback(() => {
    P.go("workspace");
    P.setPanelOpen(false);
    setStage("tour");
  }, [P]);

  const replay = useCallback(() => setStage("welcome"), []);
  const value = useMemo(() => ({ stage, replay }), [stage, replay]);

  return (
    <OnboardingContext.Provider value={value}>
      {children}
      {createPortal(
        <AnimatePresence>
          {stage === "welcome" && <WelcomeModal key="welcome" onTour={startTour} onSkip={() => end("skipped")} />}
          {stage === "tour" && <ProductTour key="tour" setNavOpen={setNavOpen} onFinish={() => end("done")} onSkip={() => end("skipped")} />}
        </AnimatePresence>,
        document.body,
      )}
    </OnboardingContext.Provider>
  );
}
