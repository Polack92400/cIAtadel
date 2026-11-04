import hashlib
import os
import re
import unicodedata

from django.conf import settings
from rest_framework import serializers

PDF_MAGIC = b"%PDF-"


def safe_display_name(name: str) -> str:
    """Strip any path, control characters and odd unicode from a filename."""
    name = os.path.basename(name.replace("\\", "/"))
    name = unicodedata.normalize("NFKC", name)
    name = re.sub(r"[\x00-\x1f\x7f]", "", name).strip() or "document.pdf"
    return name[:200]


def read_and_validate_pdf(upload) -> tuple[bytes, str]:
    """Return (bytes, sha256) or raise ValidationError.

    This is a *front-door* check only (size, extension, magic bytes). The
    real parsing happens later in a time-limited worker.
    """
    limit = settings.DOCUMENT_MAX_UPLOAD_BYTES
    if upload.size is None or upload.size == 0:
        raise serializers.ValidationError({"file": "The file is empty."})
    if upload.size > limit:
        raise serializers.ValidationError(
            {"file": f"File too large (max {limit // (1024 * 1024)} MB)."}
        )
    if not upload.name.lower().endswith(".pdf"):
        raise serializers.ValidationError({"file": "Only PDF files are accepted."})
    data = upload.read(limit + 1)
    if len(data) > limit:
        raise serializers.ValidationError({"file": "File too large."})
    # Real PDFs start with %PDF- within the first 1 KB (spec tolerance).
    if PDF_MAGIC not in data[:1024]:
        raise serializers.ValidationError({"file": "This file is not a valid PDF."})
    return data, hashlib.sha256(data).hexdigest()
