import logging
import uuid

from django.db import IntegrityError, transaction

from .models import Document
from .storage import document_key, get_storage

logger = logging.getLogger(__name__)


class DuplicateDocument(Exception):
    def __init__(self, existing: Document):
        self.existing = existing


def create_document(*, tenant, user, matter, title, filename, data: bytes, sha256: str) -> Document:
    """Store the object, create the row, queue processing after commit.

    Ordering keeps state consistent: if the DB insert fails the object is
    removed; the Celery task is only sent once the row is committed.
    """
    existing = Document.objects.for_tenant(tenant).filter(sha256=sha256).first()
    if existing:
        raise DuplicateDocument(existing)

    doc_id = uuid.uuid4()
    key = document_key(tenant.id, doc_id)
    storage = get_storage()
    storage.put(key, data, "application/pdf")
    try:
        with transaction.atomic():
            doc = Document.objects.create(
                id=doc_id,
                tenant=tenant,
                matter=matter,
                title=title[:255],
                original_filename=filename,
                size_bytes=len(data),
                sha256=sha256,
                storage_key=key,
                uploaded_by=user,
            )
    except IntegrityError:
        storage.delete(key)
        existing = Document.objects.for_tenant(tenant).filter(sha256=sha256).first()
        if existing:
            raise DuplicateDocument(existing) from None
        raise
    except Exception:
        storage.delete(key)
        raise
    queue_processing(doc)
    return doc


def queue_processing(doc: Document) -> None:
    from apps.rag.tasks import process_document

    tenant_id, doc_id = str(doc.tenant_id), str(doc.id)
    transaction.on_commit(lambda: process_document.delay(tenant_id, doc_id))


def delete_document(doc: Document) -> None:
    key = doc.storage_key
    doc.delete()  # chunks cascade; citations keep a title snapshot only

    def _remove_object():
        try:
            get_storage().delete(key)
        except Exception:  # noqa: BLE001 — orphan object is logged, not fatal
            logger.exception("Failed to delete object for document")

    transaction.on_commit(_remove_object)
