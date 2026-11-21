// Purser web app: sign-in gate, then the workspace shell.
import { MotionConfig, motion } from "motion/react";
import { useEffect, useState } from "react";
import { api, ApiError, Me, setSession } from "./api";
import AmbientRibbons from "./components/assistant/AmbientRibbons";
import { PurserVoiceController } from "./components/assistant/PurserVoiceController";
import AppShell from "./components/layout/AppShell";
import { FxProvider } from "./components/shared/FxLayer";
import { ease } from "./animations/tokens";
import { PurserProvider } from "./state/store";

function Login({ onDone }: { onDone: (m: Me) => void }) {
  const [email, setEmail] = useState("priya@purser.demo");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const submit = async (e: React.FormEvent) => {
    e.preventDefault(); setErr(null); setBusy(true);
    try {
      const r = await api.post<{ user: any; csrf: string }>("/api/auth/login", { email, password });
      setSession(r.csrf); onDone({ ...r.user, csrf: r.csrf });
    } catch (e: any) { setErr(e instanceof ApiError && e.status === 401 ? "Email or password is incorrect." : e.message); }
    finally { setBusy(false); }
  };
  return (
    <main className="login">
      <AmbientRibbons energy={0.2} anchor="#login-anchor" />
      <div className="vignette" />
      <motion.form className="glass" onSubmit={submit} aria-label="Sign in to Purser" initial={{ opacity: 0, y: 20, scale: 0.98 }} animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.6, ease }}>
        <p className="wordmark" id="login-anchor">purser</p>
        <p className="fine" style={{ margin: "-6px 0 6px" }}>Voice-first finance for Indian businesses.</p>
        <label>Email<input type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} required /></label>
        <label>Password<input type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required autoFocus /></label>
        {err && <motion.p className="error" role="alert" initial={{ x: -6 }} animate={{ x: [6, -4, 2, 0] }} transition={{ duration: 0.35 }}>{err}</motion.p>}
        <button className="btn btn-primary" type="submit" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button>
        <p className="fine">Demo workspace with synthetic data.</p>
      </motion.form>
    </main>
  );
}

export default function App() {
  const [me, setMe] = useState<Me | null | undefined>(undefined);
  useEffect(() => { api.get<Me>("/api/me").then((m) => { setSession(m.csrf); setMe(m); }).catch(() => setMe(null)); }, []);
  if (me === undefined) return null;
  return (
    <MotionConfig reducedMotion="user">
      <FxProvider>
        {me ? (
          <PurserProvider me={me}>
            <PurserVoiceController>
              <AppShell />
            </PurserVoiceController>
          </PurserProvider>
        ) : <Login onDone={setMe} />}
      </FxProvider>
    </MotionConfig>
  );
}
