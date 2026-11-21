"""A contract file -> its plain text. Text layer first (deterministic), the vision model for pages without one
(a scanned agreement). DOCX paragraphs come from word/document.xml with the standard library (copilot
`documents.py`). The text feeds the clause scan and highlights; the original stays in storage."""

from __future__ import annotations

import asyncio
import io
import re
import zipfile
from dataclasses import dataclass, field
from xml.etree import ElementTree

from app.errors import VALIDATION, DomainError
from app.services.contracts import llm

DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
MIN_TEXT_CHARS = 30  # a page with fewer meaningful characters is a scan
VISION_BATCH = 4  # pages per transcription call (calls run concurrently)
RENDER_SCALE = 2.0  # ~144 DPI
_MEANINGFUL = re.compile(r"[A-Za-z0-9]")
_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


@dataclass
class Read:
    text: str
    source: str  # pdf_text | vision | mixed | docx
    pages: int
    vision_pages: list[int] = field(default_factory=list)  # 1-based pages read by the model
    unread_pages: list[int] = field(default_factory=list)  # scanned pages the model could not read

    def coverage_note(self) -> str | None:
        if self.unread_pages:
            return f"Pages {', '.join(map(str, self.unread_pages))} could not be read; findings there are missing."
        return None


def meaningful(s: str) -> int:
    return len(_MEANINGFUL.findall(s))


def docx_text(data: bytes) -> str:
    """Paragraphs of a .docx in order (table cells are paragraphs too)."""
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        xml = z.read("word/document.xml")
    root = ElementTree.fromstring(xml)  # expat refuses entity expansion bombs (Python >= 3.11)
    lines: list[str] = []
    for p in root.iter(f"{_W}p"):
        parts: list[str] = []
        for node in p.iter():
            if node.tag == f"{_W}t" and node.text:
                parts.append(node.text)
            elif node.tag == f"{_W}tab":
                parts.append("\t")
            elif node.tag in (f"{_W}br", f"{_W}cr"):
                parts.append("\n")
        lines.append("".join(parts))
    # a blank line between paragraphs gives the scanner its segment boundaries
    return "\n\n".join(x for x in lines if x.strip()).strip()


def _layer(data: bytes) -> list[str]:
    from pypdf import PdfReader

    out = []
    for page in PdfReader(io.BytesIO(data)).pages:
        try:
            out.append(page.extract_text() or "")
        except Exception:  # noqa: BLE001 - a broken page is treated as a scan
            out.append("")
    return out


def _render(data: bytes, indexes: list[int]) -> list[bytes]:
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(data)
    out = []
    for i in indexes:
        buf = io.BytesIO()
        pdf[i].render(scale=RENDER_SCALE).to_pil().save(buf, format="PNG")
        out.append(buf.getvalue())
    return out


async def read(data: bytes, media: str) -> Read:
    if media == DOCX:
        try:
            text = docx_text(data)
        except (zipfile.BadZipFile, KeyError, ElementTree.ParseError) as e:
            raise DomainError(VALIDATION, "I could not read this Word file. Upload it as PDF instead.") from e
        if meaningful(text) < MIN_TEXT_CHARS:
            raise DomainError(VALIDATION, "This Word file has almost no text.")
        return Read(text, "docx", 1)
    if media in ("image/png", "image/jpeg"):
        try:
            text = await llm.transcribe([data])
        except llm.LLMUnavailable as e:
            raise DomainError(VALIDATION, "Reading a photographed contract needs the vision model, which is not answering. Try again.") from e
        if meaningful(text) < MIN_TEXT_CHARS:
            raise DomainError(VALIDATION, "I could not read enough text from this image.")
        return Read(text, "vision", 1, [1])

    layer = await asyncio.to_thread(_layer, data)
    scans = [i for i, t in enumerate(layer) if meaningful(t) < MIN_TEXT_CHARS]
    texts = list(layer)
    unread: list[int] = []
    if scans:
        images = await asyncio.to_thread(_render, data, scans)
        groups = [(scans[a: a + VISION_BATCH], images[a: a + VISION_BATCH]) for a in range(0, len(scans), VISION_BATCH)]

        async def one(idx: list[int], imgs: list[bytes]) -> tuple[list[int], str | None]:
            try:
                return idx, await llm.transcribe(imgs)
            except llm.LLMUnavailable:
                return idx, None

        for idx, text in await asyncio.gather(*(one(i, g) for i, g in groups)):
            if text is None or meaningful(text) < MIN_TEXT_CHARS:
                unread.extend(i + 1 for i in idx)
                continue
            texts[idx[0]] = text  # a batch's transcript stands for its pages, in order
            for i in idx[1:]:
                texts[i] = ""
    full = "\n\n".join(t.strip() for t in texts if t.strip())
    if meaningful(full) < MIN_TEXT_CHARS:
        raise DomainError(VALIDATION, "I could not read any text from this PDF (a scan the vision model could not read).")
    vision = [i + 1 for i in scans if i + 1 not in unread]
    source = "pdf_text" if not vision else ("vision" if len(vision) == len(layer) else "mixed")
    return Read(full, source, len(layer), vision, sorted(unread))
