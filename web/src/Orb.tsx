// A glossy, lit sphere with a swirling liquid core (Equal greens). It breathes when idle and swells
// with the live audio level: the microphone while listening, Munshi's voice while speaking.
import { useEffect, useRef } from "react";

type Props = {
  mode: string;
  streams: () => { mic?: MediaStream; out?: MediaStream };
  onClick: () => void;
  disabled?: boolean;
  label: string;
  pressed: boolean;
};

export default function Orb({ mode, streams, onClick, disabled, label, pressed }: Props) {
  const ref = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    let ctx: AudioContext | null = null;
    let analyser: AnalyserNode | null = null;
    let src: MediaStreamAudioSourceNode | null = null;
    let current: MediaStream | undefined;
    let raf = 0;
    let level = 0;
    const buf = new Uint8Array(256);

    const tick = () => {
      const s = streams();
      const want = mode === "speaking" ? s.out : mode === "listening" ? s.mic : undefined;
      if (want !== current) {
        src?.disconnect(); src = null; current = want;
        if (want && want.getAudioTracks().length) {
          ctx ??= new AudioContext();
          analyser ??= Object.assign(ctx.createAnalyser(), { fftSize: 512, smoothingTimeConstant: 0.6 });
          src = ctx.createMediaStreamSource(want);
          src.connect(analyser);
        }
      }
      let target = 0;
      if (analyser && src) {
        analyser.getByteTimeDomainData(buf);
        let sum = 0;
        for (const v of buf) { const d = (v - 128) / 128; sum += d * d; }
        target = Math.min(1, Math.sqrt(sum / buf.length) * 4.5);
      }
      level += (target - level) * (target > level ? 0.35 : 0.08);
      el.style.setProperty("--level", level.toFixed(3));
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => { cancelAnimationFrame(raf); src?.disconnect(); ctx?.close(); };
  }, [mode, streams]);

  return (
    <button ref={ref} className="orb3d" data-mode={mode} onClick={onClick} disabled={disabled} aria-label={label} aria-pressed={pressed}>
      <span className="halo" aria-hidden="true" />
      <span className="sphere" aria-hidden="true">
        <span className="liquid a" />
        <span className="liquid b" />
        <span className="liquid c" />
        <span className="shade" />
        <span className="gloss" />
      </span>
      <span className="floor" aria-hidden="true" />
    </button>
  );
}
