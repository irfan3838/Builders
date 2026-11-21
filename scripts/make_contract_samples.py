"""Write the synthetic agreements in seed/contract_samples.py as files under evals/contracts/: text-layer PDFs (a tiny
standard-library PDF writer, Helvetica), one DOCX, and one scanned-style PDF (page images only) to exercise vision.

    uv run python -m scripts.make_contract_samples
"""

from __future__ import annotations

import io
import textwrap
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

from seed.contract_samples import LIVE_DEMO, SEEDED

OUT = Path("evals/contracts")


def _pdf_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)").encode("latin-1", "replace").decode("latin-1")


def text_pdf(text: str) -> bytes:
    """A real PDF with a text layer: wrapped lines, 50 per page, Helvetica 10pt on A4."""
    lines: list[str] = []
    for para in text.split("\n"):
        lines.extend(textwrap.wrap(para, 95) or [""])
    pages = [lines[i: i + 50] for i in range(0, len(lines), 50)] or [[]]
    objs: list[bytes] = []
    kids = []
    font_id = 3
    for pg in pages:
        ops = ["BT", "/F1 10 Tf", "14 TL", "50 800 Td"] + [f"({_pdf_escape(ln)}) Tj T*" for ln in pg] + ["ET"]
        stream = "\n".join(ops).encode("latin-1", "replace")
        content_id = 4 + len(objs)
        objs.append(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
        page_id = 4 + len(objs)
        objs.append(b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 %d 0 R >> >> "
                    b"/Contents %d 0 R >>" % (font_id, content_id))
        kids.append(page_id)
    head = [b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [%s] /Count %d >>" % (b" ".join(b"%d 0 R" % k for k in kids), len(kids)),
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    allobjs = head + objs
    buf = io.BytesIO()
    buf.write(b"%PDF-1.4\n")
    offsets = []
    for i, o in enumerate(allobjs, start=1):
        offsets.append(buf.tell())
        buf.write(b"%d 0 obj\n" % i + o + b"\nendobj\n")
    xref = buf.tell()
    buf.write(b"xref\n0 %d\n0000000000 65535 f \n" % (len(allobjs) + 1))
    for off in offsets:
        buf.write(b"%010d 00000 n \n" % off)
    buf.write(b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(allobjs) + 1, xref))
    return buf.getvalue()


def scanned_pdf(text: str) -> bytes:
    """Page images only (no text layer), like a scanned agreement."""
    from PIL import Image, ImageDraw, ImageFont

    lines: list[str] = []
    for para in text.split("\n"):
        lines.extend(textwrap.wrap(para, 80) or [""])
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 22)
    except OSError:
        font = ImageFont.load_default()
    imgs = []
    for i in range(0, len(lines), 40):
        img = Image.new("RGB", (1240, 1754), "white")
        d = ImageDraw.Draw(img)
        for j, ln in enumerate(lines[i: i + 40]):
            d.text((90, 90 + j * 38), ln, fill="black", font=font)
        imgs.append(img)
    buf = io.BytesIO()
    imgs[0].save(buf, format="PDF", save_all=True, append_images=imgs[1:], resolution=150)
    return buf.getvalue()


def docx(text: str) -> bytes:
    body = "".join(f"<w:p><w:r><w:t xml:space=\"preserve\">{escape(p)}</w:t></w:r></w:p>" for p in text.split("\n") if p.strip())
    doc = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
           f"<w:body>{body}</w:body></w:document>")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml",
                   '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                   '<Default Extension="xml" ContentType="application/xml"/>'
                   '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
                   "</Types>")
        z.writestr("_rels/.rels",
                   '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
                   "</Relationships>")
        z.writestr("word/document.xml", doc)
    return buf.getvalue()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for key, c in SEEDED.items():
        (OUT / f"{key}_synthetic.pdf").write_bytes(text_pdf(c["text"]))
    (OUT / "live_demo_northwind_msa_synthetic.pdf").write_bytes(text_pdf(LIVE_DEMO["text"]))
    (OUT / "live_demo_northwind_msa_synthetic.docx").write_bytes(docx(LIVE_DEMO["text"]))
    (OUT / "live_demo_northwind_msa_scanned_synthetic.pdf").write_bytes(scanned_pdf(LIVE_DEMO["text"]))
    for p in sorted(OUT.iterdir()):
        print(p, p.stat().st_size)


if __name__ == "__main__":
    main()
