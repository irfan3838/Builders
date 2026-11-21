// The tiny sage-metal desk helper with a brass paper clip. A quiet detail with a small vocabulary:
// blink, look toward the receipt, raise the clip when matching starts, lean in, nod on success.
import { motion, useReducedMotion } from "motion/react";
import { useEffect, useState } from "react";

export type HelperPose = "neutral" | "look" | "raise" | "lean" | "nod" | "worried";

export default function PurserDeskHelper({ pose }: { pose: HelperPose }) {
  const reduced = useReducedMotion();
  const [blink, setBlink] = useState(false);
  useEffect(() => {
    if (reduced) return;
    let t: number;
    const loop = () => { t = window.setTimeout(() => { setBlink(true); window.setTimeout(() => setBlink(false), 140); loop(); }, 3800 + Math.random() * 4200); };
    loop();
    return () => clearTimeout(t);
  }, [reduced]);

  const head = {
    neutral: { rotate: 0, y: 0 }, look: { rotate: -12, y: 0 }, raise: { rotate: -6, y: -1 }, lean: { rotate: -10, y: 1 },
    nod: { rotate: 0, y: [0, 4, 0, 3, 0] }, worried: { rotate: 8, y: 1 },
  }[pose];
  const arm = { neutral: 0, look: 0, raise: -48, lean: -20, nod: -10, worried: 10 }[pose];
  const body = { neutral: 0, look: -2, raise: -3, lean: -8, nod: -2, worried: 2 }[pose];
  const t = reduced ? { duration: 0 } : { type: "spring" as const, stiffness: 170, damping: 14 };

  return (
    <svg className="helper" viewBox="0 0 74 96" aria-hidden="true">
      <defs>
        <radialGradient id="metal" cx="35%" cy="30%" r="80%"><stop offset="0" stopColor="#d3dfd5" /><stop offset=".45" stopColor="#8fa595" /><stop offset="1" stopColor="#3f5446" /></radialGradient>
        <linearGradient id="brass" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#f6dc9a" /><stop offset=".5" stopColor="#c9a04f" /><stop offset="1" stopColor="#8a6a2a" /></linearGradient>
        <radialGradient id="visor" cx="50%" cy="40%" r="70%"><stop offset="0" stopColor="#1d3a2f" /><stop offset="1" stopColor="#07130e" /></radialGradient>
      </defs>
      <motion.g style={{ originX: "40px", originY: "90px" }} animate={{ rotate: body }} transition={t}>
        {/* body */}
        <ellipse cx="42" cy="74" rx="17" ry="15" fill="url(#metal)" />
        <ellipse cx="42" cy="88" rx="13" ry="4" fill="#2a3a30" opacity=".5" />
        <circle cx="42" cy="73" r="3" fill="#8cf0bf" opacity=".55" />
        {/* arm + clip */}
        <motion.g style={{ originX: "28px", originY: "70px" }} animate={{ rotate: arm }} transition={t}>
          <path d="M28 70 Q18 66 14 56" stroke="url(#metal)" strokeWidth="6" strokeLinecap="round" fill="none" />
          <path d="M15 58 L8 26 Q6 18 12 17 Q18 16 19 24 L24 50 Q25 55 21 56 Q17 57 16 52 L12 32" fill="none" stroke="url(#brass)" strokeWidth="2.6" strokeLinecap="round" />
        </motion.g>
        {/* head */}
        <motion.g style={{ originX: "44px", originY: "56px" }} animate={head} transition={pose === "nod" ? { duration: reduced ? 0 : 0.9, ease: "easeInOut" } : t}>
          <line x1="46" y1="22" x2="47" y2="14" stroke="#8fa595" strokeWidth="2" />
          <circle cx="47" cy="12" r="3" fill={pose === "raise" || pose === "nod" ? "#8cf0bf" : "#cfd9d1"} />
          <circle cx="44" cy="38" r="18" fill="url(#metal)" />
          <ellipse cx="43" cy="39" rx="13" ry="10" fill="url(#visor)" />
          <motion.g animate={{ scaleY: blink ? 0.1 : pose === "worried" ? 0.7 : 1 }} style={{ originY: "39px" }} transition={{ duration: 0.08 }}>
            <ellipse cx="37" cy="39" rx="3" ry="3.6" fill={pose === "worried" ? "#f0b45a" : "#8cf0bf"} />
            <ellipse cx="49" cy="39" rx="3" ry="3.6" fill={pose === "worried" ? "#f0b45a" : "#8cf0bf"} />
          </motion.g>
          <path d="M30 28 Q40 22 54 27" stroke="rgba(255,255,255,.55)" strokeWidth="1.6" fill="none" strokeLinecap="round" />
        </motion.g>
      </motion.g>
    </svg>
  );
}
