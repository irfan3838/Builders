// PurserOrb: a hand-blown smoky glass sphere drawn by one fragment shader (three.js full-screen quad).
// Every visual state is driven by real application state (voice session, agent turn, confirmed results)
// plus the live audio level of the microphone (listening) or Purser's voice (speaking).
import { useReducedMotion } from "motion/react";
import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import type { OrbState } from "../../state/store";

const VERT = /* glsl */ `void main() { gl_Position = vec4(position.xy, 0.0, 1.0); }`;

const FRAG = /* glsl */ `
precision highp float;
float sq(float x) { return x * x; }
uniform vec2 uRes; uniform float uTime; uniform float uLevel; uniform vec2 uMouse;
uniform float uHover, uListen, uProcess, uSpeak, uWarn, uGlow, uWave, uCalm, uRadius;

float hash(float n) { return fract(sin(n) * 43758.5453); }
float noise(vec2 p) { vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
  float n = i.x + i.y * 57.0;
  return mix(mix(hash(n), hash(n + 1.0), f.x), mix(hash(n + 57.0), hash(n + 58.0), f.x), f.y); }
mat2 rot(float a) { float c = cos(a), s = sin(a); return mat2(c, -s, s, c); }

// silk threads seen through the glass
vec3 silk(vec2 q, float t, out float a) {
  vec3 col = vec3(0.0); a = 0.0;
  float speed = 0.18 + uProcess * 0.9 + uSpeak * 0.35;
  for (int i = 0; i < 14; i++) {
    float fi = float(i) / 13.0;
    float off = (fi - 0.5) * (0.22 + 0.08 * sin(t * 0.21 + q.x * 1.3));
    float y = -0.08 + off * (0.55 + 0.45 * cos(q.x * 1.7 - t * 0.15)) + 0.2 * sin(q.x * 2.3 + t * speed + fi * 0.6) + uProcess * 0.05 * sin(q.x * 9.0 - t * 2.0 + fi * 6.0);
    float w = 0.006 + 0.004 * uLevel;
    float l = exp(-sq((q.y - y) / w));
    vec3 c = mix(vec3(0.55, 0.94, 0.75), vec3(0.93, 0.68, 0.76), smoothstep(0.2, 0.9, fi));
    c = mix(c, vec3(0.95, 0.82, 0.52), smoothstep(0.75, 1.0, fi) * 0.7);
    float fade = smoothstep(-0.95, -0.2, q.x) * smoothstep(0.95, 0.25, q.x);
    col += c * l * fade * 0.55; a += l * fade * 0.4;
  }
  return col;
}

void main() {
  vec2 p = (gl_FragCoord.xy - 0.5 * uRes) / (0.5 * min(uRes.x, uRes.y));
  p -= uMouse * 0.035 * uHover;
  float t = uTime;
  float breathe = 1.0 + 0.012 * sin(t * 0.9) * uCalm;
  float pulse = 1.0 - 0.025 * uProcess * (0.5 + 0.5 * sin(t * 3.2));
  float R = uRadius * breathe * pulse * (1.0 + 0.03 * uHover) * (1.0 + 0.07 * uLevel * (uListen + uSpeak));
  float ang = atan(p.y, p.x);
  float wob = 1.0 + (0.006 + 0.03 * uLevel * (uListen + uSpeak)) * (noise(vec2(ang * 2.5 + t * 0.6, t * 0.4)) - 0.5) * 2.0;
  float r = R * wob;
  float d = length(p);
  vec3 col = vec3(0.0); float alpha = 0.0;

  vec3 mint = vec3(0.55, 0.94, 0.75), amber = vec3(0.95, 0.64, 0.32);
  vec3 tint = mix(mint, amber, uWarn);

  // outer glow + rings
  float edge = d - r;
  float glow = exp(-max(edge, 0.0) * 9.0) * (0.06 + 0.22 * uGlow + 0.12 * uHover + 0.25 * uLevel * (uListen + uSpeak)) * step(0.0, edge);
  col += tint * glow; alpha += glow;
  for (int k = 0; k < 3; k++) {
    float ph = fract(t * 0.42 + float(k) / 3.0);
    float rr = r + ph * 0.36;
    float ring = exp(-sq((d - rr) * 70.0)) * (1.0 - ph) * (uListen * (0.35 + uLevel) + uSpeak * 0.5 * uLevel);
    col += mint * ring; alpha += ring * 0.9;
  }
  if (uWave >= 0.0) {
    float rr = r + uWave * 0.42;
    float ring = exp(-sq((d - rr) * 38.0)) * (1.0 - uWave) * 1.4;
    col += tint * ring; alpha += ring;
  }
  // processing: tiny particles drawn toward the orb
  if (uProcess > 0.01) {
    for (int i = 0; i < 18; i++) {
      float fi = float(i);
      float a0 = hash(fi * 7.1) * 6.2832 + t * 0.15;
      float ph = fract(t * (0.35 + hash(fi) * 0.3) + hash(fi * 3.3));
      vec2 pp = vec2(cos(a0), sin(a0)) * (r + (1.0 - ph) * 0.38);
      float s = exp(-dot(p - pp, p - pp) * 9000.0) * uProcess * smoothstep(0.0, 0.2, ph) * (1.0 - ph * 0.6);
      col += vec3(0.95, 0.85, 0.6) * s; alpha += s;
    }
  }

  if (d < r) {
    vec2 sp = p / r;
    float z = sqrt(max(0.0, 1.0 - dot(sp, sp)));
    vec3 n = normalize(vec3(sp, z));
    float fres = pow(1.0 - n.z, 2.2);
    // refraction-ish: magnify and swirl the interior
    vec2 q = sp * (0.72 + 0.18 * z);
    q *= rot(0.25 * sin(t * 0.07) + uProcess * t * 0.35);
    float sa; vec3 inner = silk(q, t, sa);
    inner *= (0.55 + 0.45 * z);
    // smoky body, darker lower edge
    float lower = smoothstep(0.05, -0.95, sp.y);
    vec3 body = mix(vec3(0.05, 0.11, 0.09), vec3(0.01, 0.03, 0.02), lower);
    float bodyA = 0.18 + 0.38 * lower * fres + 0.12 * fres;
    // rim
    vec3 rim = mix(vec3(0.75, 0.86, 0.8), tint, 0.35 + 0.5 * uGlow) * fres * (0.75 + 0.6 * uHover + 0.8 * uGlow);
    // iridescent film at the edge
    vec3 irid = 0.5 + 0.5 * cos(6.2832 * (fres * 1.3 + vec3(0.0, 0.33, 0.67)) + t * 0.2);
    rim += irid * fres * fres * 0.18;
    // moving reflections: big window highlight upper-left, small sharp one, faint caustic bottom-right
    vec3 L1 = normalize(vec3(-0.55 + 0.05 * sin(t * 0.3), 0.6, 0.6));
    float spec1 = pow(max(dot(n, L1), 0.0), 26.0);
    vec3 L2 = normalize(vec3(-0.35, 0.72, 0.62));
    float spec2 = pow(max(dot(n, L2), 0.0), 260.0) * 1.4;
    float caustic = exp(-sq(length(sp - vec2(0.42, -0.55)) * 4.0)) * 0.22;
    float band = exp(-sq((n.y - 0.15 + 0.02 * sin(t * 0.4)) * 14.0)) * fres * 0.3;
    vec3 c = body * bodyA + inner + rim + vec3(1.0) * (spec1 * 0.55 + spec2) + vec3(0.8, 1.0, 0.9) * (caustic + band);
    c += tint * uGlow * 0.18 * (1.0 - z * 0.6);
    c += tint * uLevel * (uListen + uSpeak) * 0.12;
    float a = clamp(bodyA + sa + fres * 0.55 + spec1 * 0.5 + spec2 + caustic + uGlow * 0.12, 0.0, 1.0);
    // anti-aliased edge
    float aa = smoothstep(r, r - 0.006, d);
    col = mix(col, c, aa); alpha = mix(alpha, a, aa);
    // contact line
    col += vec3(0.85, 0.95, 0.9) * exp(-sq((d - r) * 220.0)) * 0.5;
  }
  alpha = clamp(alpha, 0.0, 1.0);
  gl_FragColor = vec4(col, alpha); // premultiplied (col already scaled by coverage)
}`;

type Props = {
  state: OrbState;
  level: () => number;     // 0..1 live audio level
  size?: "hero" | "mini";
  onActivate: () => void;
  label: string;
  pressed: boolean;
  disabled?: boolean;
};

const TARGETS: Record<OrbState, { listen: number; process: number; speak: number; warn: number; glow: number; calm: number }> = {
  idle:       { listen: 0, process: 0, speak: 0, warn: 0, glow: 0.05, calm: 1 },
  asleep:     { listen: 0, process: 0, speak: 0, warn: 0, glow: 0.15, calm: 1 },
  connecting: { listen: 0.2, process: 0.5, speak: 0, warn: 0, glow: 0.4, calm: 0.6 },
  listening:  { listen: 1, process: 0, speak: 0, warn: 0, glow: 0.75, calm: 0.5 },
  processing: { listen: 0, process: 1, speak: 0, warn: 0, glow: 0.45, calm: 0.3 },
  speaking:   { listen: 0, process: 0, speak: 1, warn: 0, glow: 0.6, calm: 0.5 },
  success:    { listen: 0, process: 0, speak: 0, warn: 0, glow: 1, calm: 1 },
  error:      { listen: 0, process: 0, speak: 0, warn: 1, glow: 0.8, calm: 1 },
  cancelled:  { listen: 0, process: 0, speak: 0, warn: 0, glow: 0, calm: 1 },
};

export default function PurserOrb({ state, level, size = "hero", onActivate, label, pressed, disabled }: Props) {
  const host = useRef<HTMLDivElement>(null);
  const wrap = useRef<HTMLDivElement>(null);
  const stateRef = useRef(state);
  const hover = useRef(0);
  const mouse = useRef({ x: 0, y: 0 });
  const waveAt = useRef(-1);
  const [webgl, setWebgl] = useState(true);
  const reduced = useReducedMotion();

  useEffect(() => {
    if ((state === "success" || state === "error") && stateRef.current !== state) waveAt.current = performance.now();
    stateRef.current = state;
  }, [state]);

  useEffect(() => {
    const el = host.current;
    if (!el) return;
    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ alpha: true, antialias: false, premultipliedAlpha: true, powerPreference: "high-performance" });
    } catch { setWebgl(false); return; }
    renderer.setPixelRatio(Math.min(devicePixelRatio, size === "mini" ? 2 : 1.75));
    renderer.setClearColor(0x000000, 0);
    el.appendChild(renderer.domElement);
    const scene = new THREE.Scene();
    const cam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
    const u = {
      uRes: { value: new THREE.Vector2(1, 1) }, uTime: { value: 0 }, uLevel: { value: 0 }, uMouse: { value: new THREE.Vector2() },
      uHover: { value: 0 }, uListen: { value: 0 }, uProcess: { value: 0 }, uSpeak: { value: 0 }, uWarn: { value: 0 }, uGlow: { value: 0 },
      uWave: { value: -1 }, uCalm: { value: 1 }, uRadius: { value: 0.72 },
    };
    const mat = new THREE.ShaderMaterial({ vertexShader: VERT, fragmentShader: FRAG, uniforms: u, transparent: true, premultipliedAlpha: true, depthTest: false });
    scene.add(new THREE.Mesh(new THREE.PlaneGeometry(2, 2), mat));
    const resize = () => {
      const { width, height } = el.getBoundingClientRect();
      renderer.setSize(Math.max(1, width), Math.max(1, height), false);
      renderer.getDrawingBufferSize(u.uRes.value);
    };
    const ro = new ResizeObserver(resize);
    ro.observe(el);
    resize();

    let raf = 0, last = performance.now(), t = 0;
    const lerp = (a: number, b: number, k: number) => a + (b - a) * k;
    const frame = (now: number) => {
      raf = requestAnimationFrame(frame);
      if (document.hidden) { last = now; return; }
      const dt = Math.min(0.05, (now - last) / 1000); last = now;
      const target = TARGETS[stateRef.current];
      const k = reduced ? 1 : 1 - Math.pow(0.02, dt);  // ~ 0.25s settle
      t += reduced ? 0 : dt * (0.7 + target.process * 0.6);
      u.uTime.value = t + 12.0;
      u.uListen.value = lerp(u.uListen.value, target.listen, k);
      u.uProcess.value = lerp(u.uProcess.value, target.process, k);
      u.uSpeak.value = lerp(u.uSpeak.value, target.speak, k);
      u.uWarn.value = lerp(u.uWarn.value, target.warn, k * 0.8);
      u.uGlow.value = lerp(u.uGlow.value, target.glow, stateRef.current === "cancelled" ? k * 0.4 : k);
      u.uCalm.value = lerp(u.uCalm.value, target.calm, k);
      u.uHover.value = lerp(u.uHover.value, hover.current, k * 0.8);
      u.uLevel.value = lerp(u.uLevel.value, level(), 0.35);
      u.uMouse.value.set(lerp(u.uMouse.value.x, mouse.current.x, k), lerp(u.uMouse.value.y, mouse.current.y, k));
      const w = waveAt.current < 0 ? -1 : (now - waveAt.current) / 1400;
      u.uWave.value = reduced || w > 1 ? -1 : w;
      if (w > 1) waveAt.current = -1;
      renderer.render(scene, cam);
    };
    raf = requestAnimationFrame(frame);
    const lost = (e: Event) => { e.preventDefault(); setWebgl(false); };
    renderer.domElement.addEventListener("webglcontextlost", lost);
    return () => {
      cancelAnimationFrame(raf); ro.disconnect();
      renderer.domElement.removeEventListener("webglcontextlost", lost);
      mat.dispose(); renderer.dispose(); renderer.domElement.remove();
    };
  }, [level, reduced, size]);

  const onMove = (e: React.PointerEvent) => {
    const r = wrap.current!.getBoundingClientRect();
    mouse.current = { x: ((e.clientX - r.left) / r.width - 0.5) * 2, y: -((e.clientY - r.top) / r.height - 0.5) * 2 };
  };

  return (
    <div ref={wrap} id={size === "hero" ? "purser-orb" : undefined} className={size === "hero" ? "orb-wrap" : "mini-orb"} data-state={state}
      onPointerMove={onMove} onPointerEnter={() => (hover.current = 1)} onPointerLeave={() => { hover.current = 0; mouse.current = { x: 0, y: 0 }; }}>
      <div ref={host} className="orb-canvas" aria-hidden="true" />
      {!webgl && <div className="orb-fallback" aria-hidden="true" />}
      <button className="orb-btn" onClick={onActivate} aria-label={label} aria-pressed={pressed} disabled={disabled} />
    </div>
  );
}
