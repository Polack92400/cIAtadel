"""Defensive PDF text extraction.

Uploaded PDFs are untrusted. pypdf is pure Python (no native parser
exploits), runs in the Celery worker under soft/hard time limits, and we cap
pages and characters to bound memory. Any failure becomes a typed
ExtractionError that the task records on the document.
"""

import io
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


class ExtractionError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def extract_pages(data: bytes) -> list[tuple[int, str]]:
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    max_pages = settings.AI["PDF_MAX_PAGES"]
    max_chars = settings.AI["PDF_MAX_CHARS"]
    try:
        reader = PdfReader(io.BytesIO(data), strict=False)
        if reader.is_encrypted:
            raise ExtractionError("encrypted", "Password-protected PDFs are not supported.")
        n = len(reader.pages)
    except ExtractionError:
        raise
    except (PdfReadError, ValueError, KeyError, TypeError, OSError, RecursionError) as exc:
        raise ExtractionError(
            "malformed", "The PDF could not be read (corrupted or malformed)."
        ) from exc
    if n == 0:
        raise ExtractionError("empty", "The PDF has no pages.")
    if n > max_pages:
        raise ExtractionError("too_many_pages", f"The PDF has more than {max_pages} pages.")

    pages: list[tuple[int, str]] = []
    total = 0
    for i, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:  # noqa: BLE001 — one bad page must not kill the doc
            logger.warning("Text extraction failed on page %s", i)
            text = ""
        text = text.replace("\x00", "").strip()
        total += len(text)
        if total > max_chars:
            raise ExtractionError("too_much_text", "The PDF contains too much text.")
        if text:
            pages.append((i, text))
    if not pages:
        raise ExtractionError(
            "no_text", "No extractable text (scanned PDF?). OCR is not supported in this POC."
        )
    return pages
