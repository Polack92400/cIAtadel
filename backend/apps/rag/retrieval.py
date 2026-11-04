"""Tenant- and matter-filtered vector search.

The authorization filter (tenant, accessible matters, ready documents) is in
the SAME SQL statement as the similarity ORDER BY / LIMIT, so chunks from
another tenant are never candidates — they are not fetched and then
discarded, they are never read. RLS enforces the same rule underneath.
"""

from dataclasses import dataclass

from django.conf import settings
from django.db import connection
from pgvector.django import CosineDistance

from apps.documents.models import Document
from apps.matters.models import matter_scope_q

from .models import DocumentChunk


@dataclass
class RetrievedChunk:
    chunk: DocumentChunk
    distance: float


def search(*, membership, query_embedding, matter=None, document_ids=None, top_k=None):
    top_k = top_k or settings.AI["RAG_TOP_K"]
    qs = (
        DocumentChunk.objects.filter(tenant_id=membership.tenant_id)
        .filter(matter_scope_q(membership))
        .filter(document__status=Document.Status.READY)
        .select_related("document")
    )
    if matter is not None:
        qs = qs.filter(matter=matter)
    if document_ids:
        qs = qs.filter(document_id__in=document_ids)
    if connection.vendor == "postgresql" and connection.in_atomic_block:
        # pgvector >= 0.8: keep scanning the HNSW index until enough rows pass
        # the tenant/matter filter (otherwise filtered ANN can return < k).
        with connection.cursor() as cur:
            cur.execute("SET LOCAL hnsw.iterative_scan = strict_order")
    qs = qs.annotate(distance=CosineDistance("embedding", query_embedding)).order_by("distance")
    return [RetrievedChunk(c, float(c.distance)) for c in qs[:top_k]]
