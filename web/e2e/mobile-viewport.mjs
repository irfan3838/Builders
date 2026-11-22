// Mobile viewport regression gate. No project deps: uses Playwright from the npx cache.
// Run: NODE_PATH=<npx cache node_modules containing playwright> node web/e2e/mobile-viewport.mjs
// Env: BASE_URL, E2E_EMAIL, E2E_PASSWORD, CHROME_PATH (optional chromium binary when the playwright-pinned build is not installed).
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const { chromium } = require("playwright");

const BASE = process.env.BASE_URL || "http://localhost:5173";
const EMAIL = process.env.E2E_EMAIL || "irfmed38@gmail.com";
const PASSWORD = process.env.E2E_PASSWORD || "purser-demo";

// Strict xfail registry: check name -> reason (evidence). A listed check that passes is reported as a FAILURE (XPASS strict).
const XFAIL = {};

const results = [];
const record = (name, ok, detail = "") => {
  const x = XFAIL[name];
  let status = ok ? "PASS" : "FAIL";
  if (x) status = ok ? "FAIL(XPASS strict)" : "XFAIL";
  results.push({ name, status, detail: ok && !x ? "" : detail + (x ? ` | reason: ${x}` : "") });
  console.log(`${status.padEnd(18)} ${name}${results.at(-1).detail ? "  -> " + results.at(-1).detail : ""}`);
};
const check = async (name, fn) => {
  try { const r = await fn(); record(name, r === true || r?.ok === true, r?.detail || ""); }
  catch (e) { record(name, false, "exception: " + String(e.message).split("\n")[0]); }
};

// Elements in .main whose right edge exceeds the viewport and which are not inside a horizontal scroller.
const overflowProbe = () => {
  const iw = innerWidth;
  const scroller = (el) => {
    for (let p = el.parentElement; p; p = p.parentElement) {
      const o = getComputedStyle(p).overflowX;
      if ((o === "auto" || o === "scroll") && p.scrollWidth > p.clientWidth) return true;
    }
    return false;
  };
  const bad = [];
  for (const el of document.querySelectorAll(".main *")) {
    const cs = getComputedStyle(el);
    if (cs.display === "none" || cs.visibility === "hidden") continue;
    const r = el.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) continue;
    if (r.right > iw + 1 && !scroller(el)) {
      bad.push(`${el.tagName.toLowerCase()}${el.className && typeof el.className === "string" ? "." + el.className.trim().split(/\s+/).join(".") : ""} right=${r.right.toFixed(1)}`);
    }
  }
  return { iw, bad: bad.slice(0, 6), n: bad.length };
};

const APP_ORIGIN = process.env.APP_ORIGIN || "http://localhost:8000"; // backend APP_ORIGIN; the vite dev server (5173) is rejected as "Unexpected origin"
// Rewrite the Origin header on API calls so the dev-server origin passes the backend CSRF origin check (test-only, no app change).
const fixOrigin = (ctx) => ctx.route("**/api/**", async (route) => {
  const req = route.request();
  if (!req.headers()["origin"]) return route.continue();
  const response = await route.fetch({ headers: { ...req.headers(), origin: APP_ORIGIN } });
  await route.fulfill({ response });
});
const browser = await chromium.launch({ executablePath: process.env.CHROME_PATH || undefined });
const login = async (page) => {
  await page.goto(BASE);
  await page.waitForSelector("input[type=password], .shell", { timeout: 20000 });
  if (await page.locator("input[type=password]").count()) {
    await page.fill("input[type=email]", EMAIL);
    await page.fill("input[type=password]", PASSWORD);
    await page.click("button[type=submit]");
  }
  await page.waitForSelector(".shell", { timeout: 20000 });
};
const settle = (page) => page.waitForTimeout(700); // view transition (blur/fade ~0.36s)

let storage;
{
  const c = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  await fixOrigin(c);
  const p = await c.newPage();
  await login(p);
  storage = await c.storageState();
  await c.close();
}

for (const w of [320, 375, 414]) {
  const ctx = await browser.newContext({ viewport: { width: w, height: 800 }, storageState: storage });
  await fixOrigin(ctx);
  const page = await ctx.newPage();
  await login(page);
  await page.waitForSelector(".m-bar", { state: "visible" });
  await page.click('.m-bar button[aria-label="Open navigation"]');
  await page.waitForTimeout(600);
  const labels = await page.$$eval(".sidebar .nav-item", (els) => els.map((e) => (e.textContent || "").trim().replace(/\d+$/, "").trim()));
  console.log(`-- ${w}px views: ${labels.join(", ")}`);
  await page.keyboard.press("Escape");
  await page.waitForTimeout(500);

  for (let i = 0; i < labels.length; i++) {
    const label = labels[i];
    await page.click('.m-bar button[aria-label="Open navigation"]');
    await page.waitForTimeout(550);
    await page.locator(".sidebar .nav-item").nth(i).click();
    await page.waitForTimeout(700);
    const tag = `${w}px ${label}`;
    await check(`${tag}: no horizontal overflow in .main`, async () => {
      const r = await page.evaluate(overflowProbe);
      return { ok: r.n === 0, detail: `viewport=${r.iw} offenders(${r.n})=${r.bad.join("; ")}` };
    });
    await check(`${tag}: #purser-input >= 150px wide`, async () => {
      const wd = await page.evaluate(() => document.querySelector("#purser-input")?.getBoundingClientRect().width ?? -1);
      return { ok: wd >= 150, detail: `width=${wd}` };
    });
    await check(`${tag}: drawer closed after navigation`, async () => {
      const r = await page.evaluate(() => document.querySelector(".sidebar").getBoundingClientRect().right);
      return { ok: r <= 0, detail: `sidebar.right=${r}` };
    });
  }

  // Claim panel
  await check(`${w}px claim panel fits viewport`, async () => {
    await page.click('.m-bar button[aria-label="Open navigation"]');
    await page.waitForTimeout(550);
    await page.locator(".sidebar .nav-item", { hasText: "Claims" }).click();
    await page.waitForTimeout(800);
    await page.locator("button.row").first().click();
    await page.waitForSelector(".panel", { timeout: 10000 });
    await page.waitForSelector("#panel-foot-slot button", { timeout: 15000 });
    await page.waitForTimeout(900);
    const m = await page.evaluate(() => {
      const iw = innerWidth;
      const p = document.querySelector(".panel").getBoundingClientRect();
      const btns = [...document.querySelectorAll("#panel-foot-slot button")].map((b) => {
        const r = b.getBoundingClientRect();
        return { t: (b.textContent || "").trim(), l: r.left, r: r.right, b: r.bottom, w: r.width };
      });
      return { iw, ih: innerHeight, pl: p.left, pr: p.right, pw: p.width, btns };
    });
    const btnOk = m.btns.length >= 2 && m.btns.every((b) => b.l >= -0.5 && b.r <= m.iw + 0.5 && b.b <= m.ih + 0.5 && b.w > 0);
    return { ok: m.pw <= m.iw + 0.5 && btnOk, detail: JSON.stringify(m) };
  });
  await ctx.close();
}

// Settings dialog at 375
{
  const ctx = await browser.newContext({ viewport: { width: 375, height: 800 }, storageState: storage });
  await fixOrigin(ctx);
  const page = await ctx.newPage();
  await login(page);
  let m = null;
  try {
    await page.click('.m-bar button[aria-label="Open navigation"]');
    await page.waitForTimeout(550);
    await page.locator(".profile-btn").click();
    await page.getByRole("menuitem", { name: /Settings/ }).click();
    await page.waitForSelector(".dialog", { timeout: 5000 });
    await page.waitForTimeout(800);
    m = await page.evaluate(() => {
      const r = document.querySelector(".dialog").getBoundingClientRect();
      const s = document.querySelector(".scrim").getBoundingClientRect();
      return { l: r.left, r: r.right, t: r.top, b: r.bottom, w: r.width, scrimW: s.width, scrimH: s.height, scrimL: s.left, scrimT: s.top, iw: innerWidth, ih: innerHeight };
    });
  } catch (e) { console.log("settings open failed: " + e.message.split("\n")[0]); }
  await check("375px Settings dialog fits inside viewport", async () => ({
    ok: !!m && m.l >= -0.5 && m.r <= m.iw + 0.5 && m.t >= -0.5 && m.b <= m.ih + 0.5, detail: JSON.stringify(m) }));
  await check("375px Settings scrim/overlay spans the whole viewport (not clipped to the drawer)", async () => ({
    ok: !!m && m.scrimW >= m.iw - 1 && m.scrimH >= m.ih - 1 && m.scrimL <= 0.5 && m.scrimT <= 0.5, detail: JSON.stringify(m) }));
  await check("375px Settings dialog closes on Escape", async () => {
    await page.keyboard.press("Escape");
    await page.waitForTimeout(2000);
    const st = await page.evaluate(() => {
      const d = document.querySelector(".dialog");
      return { inDom: !!d, right: d ? d.getBoundingClientRect().right : null, opacity: d ? getComputedStyle(d).opacity : null };
    });
    return { ok: !st.inDom, detail: JSON.stringify(st) };
  });
  await check("375px drawer stays open after Escape closes Settings", async () => {
    const st = await page.evaluate(() => {
      const r = document.querySelector(".sidebar").getBoundingClientRect();
      return { left: r.left, right: r.right };
    });
    return { ok: st.right > 0 && st.left >= -0.5, detail: JSON.stringify(st) };
  });
  await ctx.close();
}

// Desktop
{
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, storageState: storage });
  await fixOrigin(ctx);
  const page = await ctx.newPage();
  await login(page);
  await page.waitForTimeout(800);
  await check("1440px .m-bar is display:none", async () => {
    const d = await page.evaluate(() => getComputedStyle(document.querySelector(".m-bar")).display);
    return { ok: d === "none", detail: `display=${d}` };
  });
  await check("1440px .sidebar is position:relative", async () => {
    const d = await page.evaluate(() => getComputedStyle(document.querySelector(".sidebar")).position);
    return { ok: d === "relative", detail: `position=${d}` };
  });
  await check("1440px composer textarea visible", async () => {
    const v = await page.locator("textarea#purser-input, .shell-composer textarea").first().isVisible();
    return { ok: v, detail: `visible=${v}` };
  });
  await ctx.close();
}

await browser.close();
const count = (s) => results.filter((r) => r.status === s).length;
const failed = results.filter((r) => r.status.startsWith("FAIL")).length;
console.log(`\nSUMMARY: ${count("PASS")} passed, ${failed} failed, ${count("XFAIL")} xfailed, total ${results.length}`);
process.exit(failed ? 1 : 0);
