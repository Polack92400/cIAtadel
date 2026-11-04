import uuid

from django.conf import settings
from django.db import models
from pgvector.django import HnswIndex, VectorField


class DocumentChunk(models.Model):
    """A retrievable passage. `tenant` and `matter` are denormalised from the
    document so the vector query can filter on them in the same statement as
    the similarity ordering."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="+")
    document = models.ForeignKey(
        "documents.Document", on_delete=models.CASCADE, related_name="chunks"
    )
    matter = models.ForeignKey(
        "matters.Matter", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    chunk_index = models.PositiveIntegerField()
    page_number = models.PositiveIntegerField(null=True, blank=True)
    content = models.TextField()
    embedding = VectorField(dimensions=settings.AI["EMBEDDING_DIM"])

    class Meta:
        ordering = ["document_id", "chunk_index"]
        indexes = [
            models.Index(fields=["tenant", "document"]),
            HnswIndex(
                name="chunk_embedding_hnsw",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            ),
        ]

    def __str__(self) -> str:
        return f"chunk {self.chunk_index} of {self.document_id}"
