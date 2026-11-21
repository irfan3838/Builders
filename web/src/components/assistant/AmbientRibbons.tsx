// Silk ribbons flowing from the lower left, through the orb, toward the Artifact Panel, with rare gold motes.
// One full-screen fragment shader, rendered at reduced resolution and ~30 fps; paused when the tab is hidden.
import { useReducedMotion } from "motion/react";
import { useEffect, useRef, useState } from "react";
import * as THREE from "three";

const FRAG = /* glsl */ `
precision highp float;
float sq(float x) { return x * x; }
uniform vec2 uRes; uniform float uTime; uniform vec2 uOrb; uniform float uEnergy; uniform float uAspect;

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }

float baseY(float x, float t) {
  // passes the orb centre; rises from lower-left, keeps rising gently to the right
  float left = uOrb.y + 0.36 * pow(clamp((uOrb.x - x) / uOrb.x, 0.0, 1.0), 1.15);
  float right = uOrb.y - 0.2 * clamp((x - uOrb.x) / max(0.001, uAspect - uOrb.x), 0.0, 1.0);
  float y = x < uOrb.x ? left : right;
  return y + 0.03 * sin(x * 2.4 + t * 0.12) ;
}

vec3 ribbon(vec2 uv, float t, float seed, float width, float bright, float speed) {
  vec3 col = vec3(0.0);
  float by = baseY(uv.x, t + seed * 4.0) + seed * 0.05;
  float twist = sin(uv.x * 2.1 - t * 0.09 * speed + seed * 3.0);          // ribbon twists along its length
  float w = width * (0.25 + 0.75 * abs(twist));
  for (int i = 0; i < 22; i++) {
    float fi = float(i) / 21.0;
    float off = (fi - 0.5) * w * 2.0;
    float y = by + off + 0.012 * sin(uv.x * 7.0 + t * 0.5 * speed + fi * 5.0) * (1.0 + uEnergy);
    float thick = 0.0012 + 0.0009 * (1.0 - abs(twist));
    float l = exp(-sq((uv.y - y) / thick));
    vec3 c = mix(vec3(0.52, 0.92, 0.72), vec3(0.92, 0.62, 0.72), fi);
    c = mix(c, vec3(0.96, 0.84, 0.55), smoothstep(0.55, 1.0, sin(fi * 3.14 + uv.x * 1.2 + seed)) * 0.55);
    col += c * l * (0.3 + 0.7 * abs(twist));
  }
  // soft luminous body around the threads
  float body = exp(-sq((uv.y - by) / (w + 0.02))) * 0.06;
  col += vec3(0.5, 0.85, 0.7) * body;
  float fadeL = smoothstep(-0.05, 0.35, uv.x);
  float fadeR = smoothstep(uAspect + 0.05, uAspect * 0.75, uv.x);
  return col * bright * fadeL * fadeR;
}

void main() {
  vec2 uv = vec2(gl_FragCoord.x, uRes.y - gl_FragCoord.y) / uRes.y;   // top-down, height-normalised
  float t = uTime;
  vec3 col = ribbon(uv, t, 0.0, 0.055, 0.42 + 0.18 * uEnergy, 1.0 + uEnergy * 1.5);
  col += ribbon(uv, t * 0.8, 1.7, 0.035, 0.22 + 0.1 * uEnergy, 0.8 + uEnergy);
  // gold motes: sparse, slow drift, twinkle
  vec2 g = uv * 26.0 + vec2(t * 0.05, -t * 0.03);
  vec2 cell = floor(g), f = fract(g) - 0.5;
  float h = hash(cell);
  if (h > 0.965) {
    vec2 o = vec2(hash(cell + 3.1), hash(cell + 7.7)) - 0.5;
    float tw = 0.5 + 0.5 * sin(t * (0.6 + h * 1.5) + h * 40.0);
    float near = exp(-abs(uv.y - baseY(uv.x, t)) * 7.0);
    col += vec3(0.95, 0.8, 0.5) * exp(-dot(f - o * 0.6, f - o * 0.6) * 900.0) * tw * (0.35 + 0.9 * near);
  }
  col = 1.0 - exp(-col * 1.2);  // soft tone-map: converging threads glow instead of clipping to white
  float a = clamp(max(col.r, max(col.g, col.b)), 0.0, 1.0);
  gl_FragColor = vec4(col, a);
}`;

export default function AmbientRibbons({ energy, anchor }: { energy: number; anchor: string }) {
  const host = useRef<HTMLDivElement>(null);
  const energyRef = useRef(energy);
  const [fallback, setFallback] = useState(false);
  const reduced = useReducedMotion();
  useEffect(() => { energyRef.current = energy; }, [energy]);

  useEffect(() => {
    const el = host.current;
    if (!el) return;
    let renderer: THREE.WebGLRenderer;
    try { renderer = new THREE.WebGLRenderer({ alpha: true, antialias: false, premultipliedAlpha: true, powerPreference: "low-power" }); }
    catch { setFallback(true); return; }
    renderer.setPixelRatio(Math.min(devicePixelRatio, 1.25) * 0.8);
    renderer.setClearColor(0, 0);
    el.appendChild(renderer.domElement);
    const u = { uRes: { value: new THREE.Vector2(1, 1) }, uTime: { value: 0 }, uOrb: { value: new THREE.Vector2(0.7, 0.45) }, uEnergy: { value: 0 }, uAspect: { value: 1.6 } };
    const mat = new THREE.ShaderMaterial({ vertexShader: `void main(){gl_Position=vec4(position.xy,0.,1.);}`, fragmentShader: FRAG, uniforms: u,
      transparent: true, blending: THREE.AdditiveBlending, depthTest: false });
    const scene = new THREE.Scene();
    scene.add(new THREE.Mesh(new THREE.PlaneGeometry(2, 2), mat));
    const cam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
    let box = el.getBoundingClientRect();
    const place = () => {
      box = el.getBoundingClientRect();
      renderer.setSize(Math.max(1, box.width), Math.max(1, box.height), false);
      renderer.getDrawingBufferSize(u.uRes.value);
      u.uAspect.value = box.width / Math.max(1, box.height);
    };
    const ro = new ResizeObserver(place); ro.observe(el); place();
    let raf = 0, last = 0, t = 0, skip = false;
    const frame = (now: number) => {
      raf = requestAnimationFrame(frame);
      if (document.hidden) { last = now; return; }
      skip = !skip; if (skip && !reduced) return;  // ~30 fps is plenty for slow silk
      const dt = last ? Math.min(0.1, (now - last) / 1000) : 0; last = now;
      t += reduced ? 0 : dt * (0.6 + energyRef.current * 0.9);
      u.uTime.value = t + 30;
      u.uEnergy.value += (energyRef.current - u.uEnergy.value) * 0.05;
      const orb = document.querySelector(anchor);
      if (orb) {
        const r = orb.getBoundingClientRect();
        const ox = (r.left + r.width / 2 - box.left) / box.height, oy = (r.top + r.height / 2 - box.top) / box.height;
        u.uOrb.value.set(u.uOrb.value.x + (ox - u.uOrb.value.x) * 0.08, u.uOrb.value.y + (oy - u.uOrb.value.y) * 0.08);
      }
      renderer.render(scene, cam);
    };
    raf = requestAnimationFrame(frame);
    return () => { cancelAnimationFrame(raf); ro.disconnect(); mat.dispose(); renderer.dispose(); renderer.domElement.remove(); };
  }, [anchor, reduced]);

  return <div ref={host} className={`ribbons ${fallback ? "fallback" : ""}`} aria-hidden="true" />;
}
