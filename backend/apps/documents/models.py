from django.db import models

from apps.core.models import TenantOwnedModel


class Document(TenantOwnedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Queued"
        PROCESSING = "processing", "Processing"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"

    matter = models.ForeignKey(
        "matters.Matter",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="documents",
    )
    title = models.CharField(max_length=255)
    original_filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100, default="application/pdf")
    size_bytes = models.PositiveBigIntegerField()
    sha256 = models.CharField(max_length=64)
    # Internal only: never serialized to the client.
    storage_key = models.CharField(max_length=512, editable=False)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    error_code = models.CharField(max_length=64, blank=True)
    error_message = models.CharField(max_length=500, blank=True)
    page_count = models.PositiveIntegerField(null=True, blank=True)
    chunk_count = models.PositiveIntegerField(default=0)
    uploaded_by = models.ForeignKey(
        "accounts.User", null=True, on_delete=models.SET_NULL, related_name="+"
    )
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            # Duplicate detection is per firm: two firms may hold the same file.
            models.UniqueConstraint(fields=["tenant", "sha256"], name="uniq_document_per_tenant")
        ]
        indexes = [models.Index(fields=["tenant", "-created_at"])]

    def __str__(self) -> str:
        return self.title
