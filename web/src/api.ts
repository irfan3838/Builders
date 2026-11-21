// Thin API client. Identity lives in the HttpOnly session cookie; writes carry the CSRF token.
let csrf = "";
let conversationId = "";

export function setSession(token: string) { csrf = token; }
export function setConversation(id: string) { conversationId = id; }
export function getConversation() { return conversationId; }

export class ApiError extends Error {
  constructor(public status: number, public body: any) {
    super(typeof body?.message === "string" ? body.message : typeof body?.detail === "string" ? body.detail : status === 0 ? "You appear to be offline." : `HTTP ${status}`);
  }
}

function headers(json: boolean, method: string) {
  const h: Record<string, string> = {};
  if (csrf && method !== "GET") h["X-CSRF-Token"] = csrf;
  if (conversationId) h["X-Conversation-Id"] = conversationId;
  if (json) h["Content-Type"] = "application/json";
  return h;
}

// A hung request must not keep the composer busy forever; the server's agent turn times out at 90 s.
const REQUEST_TIMEOUT_MS = 95_000;

function withTimeout(signal?: AbortSignal): AbortSignal | undefined {
  if (typeof AbortSignal === "undefined" || !("timeout" in AbortSignal)) return signal;
  const t = AbortSignal.timeout(REQUEST_TIMEOUT_MS);
  return signal && "any" in AbortSignal ? AbortSignal.any([signal, t]) : signal ?? t;
}

async function call<T>(method: string, path: string, body?: unknown, signal?: AbortSignal): Promise<T> {
  let r: Response;
  try {
    r = await fetch(path, { method, headers: headers(body !== undefined, method), credentials: "same-origin", body: body !== undefined ? JSON.stringify(body) : undefined, signal: withTimeout(signal) });
  } catch (e: any) {
    if (e?.name === "TimeoutError") throw new ApiError(0, { message: "Purser took too long to answer. Try again." });
    if (e?.name === "AbortError") throw e;
    throw new ApiError(0, { message: "Network unavailable. Check your connection and retry." });
  }
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new ApiError(r.status, data);
  return data as T;
}

/** Multipart upload with real byte progress (XHR), cancellable. */
function uploadWithProgress<T>(path: string, file: File, onProgress: (p: number) => void, signal?: AbortSignal): Promise<T> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", path);
    xhr.withCredentials = true;
    Object.entries(headers(false, "POST")).forEach(([k, v]) => xhr.setRequestHeader(k, v));
    xhr.upload.onprogress = (e) => { if (e.lengthComputable) onProgress(e.loaded / e.total); };
    xhr.upload.onload = () => onProgress(1);
    xhr.onload = () => {
      let data: any = {};
      try { data = JSON.parse(xhr.responseText); } catch { /* non-JSON */ }
      if (xhr.status >= 200 && xhr.status < 300) resolve(data as T); else reject(new ApiError(xhr.status, data));
    };
    xhr.onerror = () => reject(new ApiError(0, { message: "Upload failed: network unavailable." }));
    xhr.onabort = () => reject(Object.assign(new Error("Upload cancelled"), { name: "AbortError" }));
    signal?.addEventListener("abort", () => xhr.abort());
    const fd = new FormData();
    fd.append("file", file);
    xhr.send(fd);
  });
}

export const api = {
  get: <T>(p: string, signal?: AbortSignal) => call<T>("GET", p, undefined, signal),
  post: <T>(p: string, b?: unknown, signal?: AbortSignal) => call<T>("POST", p, b ?? {}, signal),
  del: <T>(p: string, signal?: AbortSignal) => call<T>("DELETE", p, undefined, signal),
  upload: uploadWithProgress,
};

export type Card = { card: string; [k: string]: any };
export type Me = { id: number; name: string; role: string; csrf: string; google?: boolean };

export const inr = (paise: number | null | undefined) => paise == null ? "—" : "₹" + new Intl.NumberFormat("en-IN").format(Math.round(paise / 100));
