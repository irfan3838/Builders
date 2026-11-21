// GPT-Live over WebRTC. The browser only carries audio and receives captions; the server owns the
// session (SDP exchange) and all tool use through its sideband. The data channel may only send session.close.
import { api } from "../api";

export type VoiceState = "idle" | "connecting" | "listening" | "speaking" | "error";
export type VoiceActivity = () => void;

/** A pause longer than this between transcript deltas starts a new caption (e.g. filler, then the answer). */
const CAPTION_GAP_MS = 1500;

export class LiveVoice {
  /** Set when the browser refused microphone access (permission denied). */
  denied = false;
  private pc?: RTCPeerConnection;
  private dc?: RTCDataChannel;
  private mic?: MediaStream;
  private audio = new Audio();
  private speakingTimer?: number;
  private lastCaption = { who: "", at: 0 };
  /** Streams for the orb's audio meter: microphone (listening) and Purser's voice (speaking). */
  micStream?: MediaStream;
  outStream?: MediaStream;

  constructor(
    private onState: (s: VoiceState, detail?: string) => void,
    /** `fresh` = this delta starts a new utterance (speaker changed or a pause), so the caption restarts. */
    private onCaption: (who: "user" | "purser", delta: string, fresh: boolean) => void,
  ) { this.audio.autoplay = true; }

  onActivity: VoiceActivity = () => {};

  async start(wakeText?: string) {
    this.onState("connecting");
    try {
      const pc = (this.pc = new RTCPeerConnection());
      pc.ontrack = (e) => { this.outStream = new MediaStream([e.track]); this.audio.srcObject = this.outStream; this.audio.play().catch(() => {}); };
      this.mic = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
      this.micStream = this.mic;
      this.mic.getAudioTracks().forEach((t) => pc.addTrack(t, this.mic!));
      const dc = (this.dc = pc.createDataChannel("oai-events"));
      dc.onmessage = ({ data }) => this.onEvent(JSON.parse(data));
      dc.onclose = () => this.onState("idle");
      await pc.setLocalDescription(await pc.createOffer());
      await new Promise<void>((res) => {
        if (pc.iceGatheringState === "complete") return res();
        pc.onicegatheringstatechange = () => pc.iceGatheringState === "complete" && res();
        setTimeout(res, 4000);
      });
      const r = await api.post<{ transport: { sdp: string } }>("/api/voice/session", { sdp: pc.localDescription!.sdp, wake_text: wakeText || null });
      await pc.setRemoteDescription({ type: "answer", sdp: r.transport.sdp });
    } catch (e: any) {
      this.denied = e?.name === "NotAllowedError" || e?.name === "SecurityError";
      this.cleanup();
      this.onState("error", e?.message || String(e));
    }
  }

  private onEvent(ev: any) {
    switch (ev.type) {
      case "session.started": this.onState("listening"); break;
      case "session.input_transcript.delta": this.caption("user", ev.delta); this.onActivity(); break;
      case "session.output_transcript.delta":
        this.caption("purser", ev.delta);
        this.onActivity();
        this.onState("speaking");
        clearTimeout(this.speakingTimer);
        this.speakingTimer = window.setTimeout(() => this.onState("listening"), 1200);
        break;
      case "session.closed": this.cleanup(); this.onState("idle"); break;
      case "error": this.onState("error", ev.error?.message || "Voice error"); break;
    }
  }

  private caption(who: "user" | "purser", delta: string) {
    const now = Date.now();
    const fresh = this.lastCaption.who !== who || now - this.lastCaption.at > CAPTION_GAP_MS;
    this.lastCaption = { who, at: now };
    this.onCaption(who, delta, fresh);
  }

  stop() {
    if (this.dc?.readyState === "open") this.dc.send(JSON.stringify({ type: "session.close" }));
    setTimeout(() => this.cleanup(), 4000);
  }

  get active() { return Boolean(this.pc); }

  private cleanup() {
    this.mic?.getTracks().forEach((t) => t.stop());
    this.dc?.close();
    this.pc?.close();
    this.pc = undefined; this.dc = undefined; this.mic = undefined; this.micStream = undefined; this.outStream = undefined;
  }
}
