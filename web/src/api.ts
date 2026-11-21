// Thin API client. Identity lives in the HttpOnly session cookie; writes carry the CSRF token.
let csrf = "";
let conversationId = "";

export function setSession(token: string) { csrf = token; }
export function setConversation(id: string) { conversationId = id; }
export function getConversation() { return conversationId; }

export class ApiError extends Error {
  constructor(public status: number, public body: any) { super(body?.message || body?.detail || `HTTP ${status}`); }
}

async function call<T>(method: string, path: string, body?: unknown, form?: FormData): Promise<T> {
  const headers: Record<string, string> = {};
  if (csrf && method !== "GET") headers["X-CSRF-Token"] = csrf;
  if (conversationId) headers["X-Conversation-Id"] = conversationId;
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const r = await fetch(path, { method, headers, credentials: "same-origin", body: form ?? (body !== undefined ? JSON.stringify(body) : undefined) });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new ApiError(r.status, data);
  return data as T;
}

export const api = {
  get: <T>(p: string) => call<T>("GET", p),
  post: <T>(p: string, b?: unknown) => call<T>("POST", p, b ?? {}),
  upload: <T>(p: string, f: File) => { const fd = new FormData(); fd.append("file", f); return call<T>("POST", p, undefined, fd); },
};

export type Card = { card: string; [k: string]: any };
export type Me = { id: number; name: string; role: string; csrf: string };
