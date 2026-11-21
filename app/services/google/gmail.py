"""Gmail for the linked account. Message bodies are UNTRUSTED data: stripped to text, truncated, never instructions."""

from __future__ import annotations

import asyncio
import base64
import html
import re
from email.message import EmailMessage
from email.utils import getaddresses, parseaddr

from app.services.google.auth import call

BASE = "https://gmail.googleapis.com/gmail/v1/users/me"
BODY_LIMIT = 2000


def _hdr(msg: dict, name: str) -> str:
    for h in msg.get("payload", {}).get("headers", []):
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def _decode(data: str) -> str:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode("utf-8", "replace")


def _text(payload: dict) -> str:
    """Prefer text/plain; fall back to text/html with tags removed."""
    plain, rich = [], []

    def walk(p: dict) -> None:
        mt, data = p.get("mimeType", ""), (p.get("body") or {}).get("data")
        if data and mt == "text/plain":
            plain.append(_decode(data))
        elif data and mt == "text/html":
            rich.append(_decode(data))
        for c in p.get("parts", []) or []:
            walk(c)

    walk(payload)
    if plain:
        out = "\n".join(plain)
    else:
        raw = "\n".join(rich)
        raw = re.sub(r"(?is)<(script|style).*?</\1>", " ", raw)
        out = html.unescape(re.sub(r"<[^>]+>", " ", raw))
    out = re.sub(r"\n\s*\n+", "\n\n", re.sub(r"[ \t ]+", " ", out)).strip()
    return out[:BODY_LIMIT] + (" …[truncated]" if len(out) > BODY_LIMIT else "")


def summary(msg: dict) -> dict:
    labels = msg.get("labelIds", [])
    name, addr = parseaddr(_hdr(msg, "From"))
    return {"id": msg["id"], "thread_id": msg.get("threadId"), "from": name or addr, "from_email": addr,
            "subject": _hdr(msg, "Subject") or "(no subject)", "date": _hdr(msg, "Date"), "snippet": html.unescape(msg.get("snippet", ""))[:200],
            "unread": "UNREAD" in labels, "important": "IMPORTANT" in labels, "in_inbox": "INBOX" in labels}


async def search(query: str = "in:inbox", max_results: int = 8) -> list[dict]:
    q = query.strip() or "in:inbox"
    found = await call("GET", f"{BASE}/messages", params={"q": q, "maxResults": max(1, min(max_results, 15))})
    ids = [m["id"] for m in found.get("messages", [])]
    msgs = await asyncio.gather(*[call("GET", f"{BASE}/messages/{i}", params={"format": "metadata",
                                       "metadataHeaders": ["From", "Subject", "Date"]}) for i in ids])
    return [summary(m) for m in msgs]


async def get_thread(thread_id: str) -> dict:
    t = await call("GET", f"{BASE}/threads/{thread_id}", params={"format": "full"})
    out = []
    for m in t.get("messages", [])[-5:]:  # the latest five messages are enough to answer or reply
        s = summary(m)
        s.update(to=_hdr(m, "To"), cc=_hdr(m, "Cc"), message_id_header=_hdr(m, "Message-ID"),
                 references=_hdr(m, "References"), body=_text(m.get("payload", {})))
        out.append(s)
    return {"thread_id": thread_id, "messages": out}


def build_raw(sender: str, to: list[str], subject: str, body: str, cc: list[str] | None = None,
              in_reply_to: str | None = None, references: str | None = None) -> str:
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = ", ".join(to)
    if cc:
        msg["Cc"] = ", ".join(cc)
    msg["Subject"] = " ".join(subject.split())[:250]  # header-safe: no newlines
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
        msg["References"] = f"{references} {in_reply_to}".strip() if references else in_reply_to
    msg.set_content(body)
    return base64.urlsafe_b64encode(msg.as_bytes()).decode()


async def reply_context(thread_id: str) -> dict:
    """Recipient, subject and threading headers for a reply to the latest message in a thread."""
    t = await get_thread(thread_id)
    if not t["messages"]:
        raise ValueError("empty thread")
    last = t["messages"][-1]
    subj = last["subject"]
    return {"to": [last["from_email"]], "subject": subj if subj.lower().startswith("re:") else f"Re: {subj}",
            "in_reply_to": last["message_id_header"], "references": last["references"], "thread_id": thread_id,
            "replying_to": f"{last['from']} — {subj}"}


async def send(sender: str, to: list[str], subject: str, body: str, *, cc: list[str] | None = None, thread_id: str | None = None,
               in_reply_to: str | None = None, references: str | None = None) -> dict:
    payload: dict = {"raw": build_raw(sender, to, subject, body, cc, in_reply_to, references)}
    if thread_id:
        payload["threadId"] = thread_id
    return await call("POST", f"{BASE}/messages/send", json=payload)


async def create_draft(sender: str, to: list[str], subject: str, body: str, *, thread_id: str | None = None,
                       in_reply_to: str | None = None, references: str | None = None) -> dict:
    message: dict = {"raw": build_raw(sender, to, subject, body, None, in_reply_to, references)}
    if thread_id:
        message["threadId"] = thread_id
    return await call("POST", f"{BASE}/drafts", json={"message": message})


async def labels() -> list[dict]:
    return (await call("GET", f"{BASE}/labels")).get("labels", [])


async def modify(ids: list[str], add: list[str] | None = None, remove: list[str] | None = None) -> dict:
    return await call("POST", f"{BASE}/messages/batchModify", json={"ids": ids, "addLabelIds": add or [], "removeLabelIds": remove or []})


def addresses(raw: str) -> list[str]:
    return [a for _, a in getaddresses([raw]) if a]
