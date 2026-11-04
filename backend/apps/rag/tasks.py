import logging

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from django.conf import settings
from django.utils import timezone

from apps.ai_engine.providers import ProviderError, get_embedder
from apps.core.tenancy import tenant_context
from apps.documents.models import Document
from apps.documents.storage import get_storage

from .chunking import chunk_pages
from .extraction import ExtractionError, extract_pages
from .models import DocumentChunk

logger = logging.getLogger(__name__)


@shared_task(bind=True, acks_late=True, max_retries=3)
def process_document(self, tenant_id: str, document_id: str) -> str:
    """Extract → chunk → embed → index one document.

    Arguments are IDs produced server-side. The document is looked up by
    (tenant, id) inside that tenant's RLS context, so a forged pair simply
    finds nothing. Chunks are replaced atomically and the status only becomes
    READY after they are committed; any failure leaves status FAILED with a
    safe message and no partial chunks.
    """
    with tenant_context(tenant_id):
        doc = (
            Document.objects.select_for_update().filter(tenant_id=tenant_id, pk=document_id).first()
        )
        if doc is None:
            logger.warning("process_document: document not found (deleted?)")
            return "missing"
        if doc.status == Document.Status.READY:
            return "already_ready"
        doc.status = Document.Status.PROCESSING
        doc.error_code = doc.error_message = ""
        doc.save(update_fields=["status", "error_code", "error_message", "updated_at"])
        storage_key, matter_id = doc.storage_key, doc.matter_id

    try:
        data = get_storage().get(storage_key)
        pages = extract_pages(data)
        cfg = settings.AI
        chunks = chunk_pages(pages, cfg["RAG_CHUNK_SIZE"], cfg["RAG_CHUNK_OVERLAP"])
        vectors = get_embedder().embed_documents([c.content for c in chunks])
    except ExtractionError as exc:
        _fail(tenant_id, document_id, exc.code, exc.message)
        return exc.code
    except ProviderError as exc:
        if self.request.retries < self.max_retries and not self.request.is_eager:
            _set_status(tenant_id, document_id, Document.Status.PENDING)
            raise self.retry(exc=exc, countdown=30 * (self.request.retries + 1)) from exc
        _fail(
            tenant_id,
            document_id,
            "embedding_unavailable",
            "The embedding service is unavailable. Try reprocessing later.",
        )
        return "embedding_unavailable"
    except SoftTimeLimitExceeded:
        _fail(tenant_id, document_id, "timeout", "Processing took too long.")
        return "timeout"
    except Exception:
        logger.exception("Unexpected processing failure")
        _fail(tenant_id, document_id, "internal_error", "Unexpected processing error.")
        return "internal_error"

    with tenant_context(tenant_id):
        doc = (
            Document.objects.select_for_update().filter(tenant_id=tenant_id, pk=document_id).first()
        )
        if doc is None:  # deleted while we were working
            return "missing"
        DocumentChunk.objects.filter(document=doc).delete()
        DocumentChunk.objects.bulk_create(
            [
                DocumentChunk(
                    tenant_id=tenant_id,
                    document=doc,
                    matter_id=matter_id,
                    chunk_index=i,
                    page_number=c.page_number,
                    content=c.content,
                    embedding=v,
                )
                for i, (c, v) in enumerate(zip(chunks, vectors, strict=True))
            ],
            batch_size=200,
        )
        doc.status = Document.Status.READY
        doc.page_count = max(p for p, _ in pages)
        doc.chunk_count = len(chunks)
        doc.processed_at = timezone.now()
        doc.save(
            update_fields=["status", "page_count", "chunk_count", "processed_at", "updated_at"]
        )
    return "ready"


def _set_status(tenant_id, document_id, status):
    with tenant_context(tenant_id):
        Document.objects.filter(tenant_id=tenant_id, pk=document_id).update(status=status)


def _fail(tenant_id, document_id, code, message):
    logger.warning("Document processing failed: %s", code)
    with tenant_context(tenant_id):
        Document.objects.filter(tenant_id=tenant_id, pk=document_id).update(
            status=Document.Status.FAILED,
            error_code=code,
            error_message=message[:500],
            chunk_count=0,
            updated_at=timezone.now(),
        )
        DocumentChunk.objects.filter(tenant_id=tenant_id, document_id=document_id).delete()
