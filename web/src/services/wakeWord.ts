// Hands-free wake word ("Hey Purser" or just "Purser"), like "Alexa" / "OK Google".
// Uses the browser's built-in speech recognition (Chrome/Edge). Note: Chrome's recogniser streams audio
// to the browser vendor's speech service while armed. The wake phrase only opens the Purser session;
// words heard here are treated as a request, never as a confirmation (the server must hear "yes" itself).

// "Hey Purser" first: Chrome often hears it as "hey person / hey parcel / hey pusser", so those near-misses count, but
// only right after a greeting ("person" or "parcel" in normal speech never wakes Purser). The bare name still works.
const GREETED = /\b(?:hey|hay|hi|hii|ok|okay|hello)[\s,]+(?:purser|pursar|pursur|perser|parser|pursuer|person|parcel|pusser|purse|prosser|percer|pursa)(?:\s+ji)?\b|(?:हे|है|हाय)\s*(?:पर्सर|पर्सार|पर्सन|पार्सल)/i;
const BARE = /\b(purser|pursar|purser ji|pursur|perser|pursuer|purse her|pur sir)\b|पर्सर|पर्सार/i;
export const matchWake = (text: string) => GREETED.exec(text) ?? BARE.exec(text);

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
        const m = matchWake(text);
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
