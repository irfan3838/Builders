"""Document reading (vision extraction) shared by the upload path and the inspect_document tool.

Upload starts reading immediately in the background; inspect_document awaits the same task, so the
agent's first model step and the extraction overlap instead of running one after the other."""

from __future__ import annotations

import asyncio
import logging

from app import db
from app.actor import Actor
from app.agent import extractor
from app.models import Extraction
from app.services import intake, records, storage
from app.services.contracts import review as contract_review

log = logging.getLogger("purser.reading")
_tasks: dict[tuple[int, int], asyncio.Task] = {}


async def _read(actor: Actor, document_id: int) -> Extraction:
    async with db.session_scope() as s:
        doc = await records.document(s, actor, document_id)
        ex = await records.extraction(s, actor, doc.id)
        if ex is not None:
            return ex
        key, media = doc.storage_key, doc.media_type
    if media == intake.DOCX:
        # Word files are agreements in Purser (bills arrive as PDF or photos); the contract reader takes the text.
        async with db.session_scope() as s:
            doc = await records.document(s, actor, document_id)
            ex = await records.extraction(s, actor, doc.id) or await intake.save_extraction(
                s, actor, doc, "contract", {"doc_type_reason": "Word document, read as an agreement", "contract_parties": []},
                {}, "none", 0)
        contract_review.prefetch(actor, document_id)
        return ex
    pages = intake.render_pages(await storage.get(key), media)
    parsed, ms, model = await extractor.extract(pages, media)
    fields, evidence = extractor.to_fields(parsed)
    async with db.session_scope() as s:
        doc = await records.document(s, actor, document_id)
        ex = await records.extraction(s, actor, doc.id) or await intake.save_extraction(
            s, actor, doc, parsed.doc_type, fields, evidence, model, ms)
    if ex.doc_type == "contract":
        contract_review.prefetch(actor, document_id)  # clause scan + liabilities start while the agent replies
    return ex


def prefetch(actor: Actor, document_id: int) -> None:
    k = (actor.workspace_id, document_id)
    if k not in _tasks:
        task = asyncio.create_task(_read(actor, document_id))
        _tasks[k] = task
        task.add_done_callback(lambda t: t.exception() and log.warning("prefetch failed doc=%s: %r", document_id, t.exception()))


async def ensure_extraction(actor: Actor, document_id: int) -> Extraction:
    k = (actor.workspace_id, document_id)
    task = _tasks.get(k)
    try:
        if task is not None:
            return await asyncio.shield(task)
        return await _read(actor, document_id)
    finally:
        if task is not None and task.done():
            _tasks.pop(k, None)
