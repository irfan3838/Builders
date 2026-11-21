// GPT-Live over WebRTC. The browser only carries audio and receives captions; the server owns the
// session (SDP exchange) and all tool use through its sideband. The data channel may only send session.close.
import { api } from "./api";

export type VoiceState = "idle" | "connecting" | "listening" | "speaking" | "error";
export type VoiceActivity = () => void;

export class LiveVoice {
  private pc?: RTCPeerConnection;
  private dc?: RTCDataChannel;
  private mic?: MediaStream;
  private audio = new Audio();
  private speakingTimer?: number;
  /** Streams for the orb's audio meter: microphone (listening) and Munshi's voice (speaking). */
  micStream?: MediaStream;
  outStream?: MediaStream;

  constructor(
    private onState: (s: VoiceState, detail?: string) => void,
    private onCaption: (who: "user" | "munshi", delta: string) => void,
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
      this.cleanup();
      this.onState("error", e?.message || String(e));
    }
  }

  private onEvent(ev: any) {
    switch (ev.type) {
      case "session.started": this.onState("listening"); break;
      case "session.input_transcript.delta": this.onCaption("user", ev.delta); this.onActivity(); break;
      case "session.output_transcript.delta":
        this.onCaption("munshi", ev.delta);
        this.onActivity();
        this.onState("speaking");
        clearTimeout(this.speakingTimer);
        this.speakingTimer = window.setTimeout(() => this.onState("listening"), 1200);
        break;
      case "session.closed": this.cleanup(); this.onState("idle"); break;
      case "error": this.onState("error", ev.error?.message || "Voice error"); break;
    }
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
