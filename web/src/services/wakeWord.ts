// Hands-free wake word ("Purser"), like "Alexa" / "OK Google".
// Uses the browser's built-in speech recognition (Chrome/Edge). Note: Chrome's recogniser streams audio
// to the browser vendor's speech service while armed. The wake phrase only opens the Purser session;
// words heard here are treated as a request, never as a confirmation (the server must hear "yes" itself).

const WAKE = /\b(purser|pursar|purser ji|pursur|perser|parser|pursuer|purse her|pur sir)\b|पर्सर|पर्सार/i;

type SR = any;
const Recognition: SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

export const wakeSupported = Boolean(Recognition);

export class WakeWord {
  private rec: SR | null = null;
  private armed = false;
  private fired = false;
  private settleTimer?: number;

  constructor(private onWake: (rest: string) => void, private onError: (msg: string) => void) {}

  start() {
    if (!Recognition || this.armed) return;
    this.armed = true;
    this.fired = false;
    this.listen();
  }

  stop() {
    this.armed = false;
    clearTimeout(this.settleTimer);
    try { this.rec?.abort(); } catch { /* already stopped */ }
    this.rec = null;
  }

  private listen() {
    const rec = (this.rec = new Recognition());
    rec.lang = "en-IN";
    rec.continuous = true;
    rec.interimResults = true;
    rec.onresult = (e: any) => {
      if (this.fired) return;
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const text: string = e.results[i][0].transcript;
        const m = WAKE.exec(text);
        if (!m) continue;
        const rest = text.slice(m.index + m[0].length).replace(/^[\s,.!?ji]+/i, "").trim();
        clearTimeout(this.settleTimer);
        // Wait briefly for the rest of the sentence ("Purser, travel budget kitna hai"), then wake.
        const fire = () => { if (!this.fired) { this.fired = true; this.stop(); this.onWake(rest); } };
        if (e.results[i].isFinal) fire();
        else this.settleTimer = window.setTimeout(fire, 1400);
        return;
      }
    };
    rec.onerror = (e: any) => {
      if (e.error === "not-allowed" || e.error === "service-not-allowed") { this.armed = false; this.onError("Microphone permission is needed for hands-free."); }
    };
    rec.onend = () => { if (this.armed && !this.fired) setTimeout(() => this.armed && this.listen(), 250); };
    try { rec.start(); } catch { /* start race; onend restarts */ }
  }
}
