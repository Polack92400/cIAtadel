"""Vector retrieval must filter by tenant and matter *before* ranking."""

import pytest

from apps.accounts.models import Membership
from apps.ai_engine.providers import get_embedder
from apps.documents.models import Document
from apps.matters.models import Matter
from apps.rag.models import DocumentChunk
from apps.rag.retrieval import search

pytestmark = [pytest.mark.django_db, pytest.mark.security]

SECRET = "zebra quantum merger price ninety nine million"


def _doc_with_chunk(tenant, text, matter=None):
    doc = Document.objects.create(
        tenant=tenant,
        matter=matter,
        title=text[:30],
        original_filename="x.pdf",
        size_bytes=1,
        sha256=str(hash(text)),
        storage_key="k",
        status=Document.Status.READY,
    )
    DocumentChunk.objects.create(
        tenant=tenant,
        document=doc,
        matter=matter,
        chunk_index=0,
        page_number=1,
        content=text,
        embedding=get_embedder().embed_documents([text])[0],
    )
    return doc


def test_other_tenant_chunks_are_never_candidates(world):
    _doc_with_chunk(world["b"], SECRET)  # exact match lives in firm B
    own = _doc_with_chunk(world["a"], "unrelated lease clause about parking")
    alice_m = Membership.objects.get(user=world["alice"])
    hits = search(membership=alice_m, query_embedding=get_embedder().embed_query(SECRET), top_k=50)
    assert [h.chunk.document_id for h in hits] == [own.id]
    assert all(h.chunk.tenant_id == world["a"].id for h in hits)


def test_restricted_matter_chunks_excluded_for_non_allowed_member(world):
    wall = Matter.objects.create(tenant=world["a"], name="Wall", is_restricted=True)
    _doc_with_chunk(world["a"], SECRET, matter=wall)
    bob_m = Membership.objects.get(user=world["bob"])
    alice_m = Membership.objects.get(user=world["alice"])  # owner sees everything
    q = get_embedder().embed_query(SECRET)
    assert search(membership=bob_m, query_embedding=q) == []
    assert len(search(membership=alice_m, query_embedding=q)) == 1


def test_documents_not_ready_are_not_retrievable(world):
    doc = _doc_with_chunk(world["a"], SECRET)
    doc.status = Document.Status.PROCESSING
    doc.save()
    alice_m = Membership.objects.get(user=world["alice"])
    assert search(membership=alice_m, query_embedding=get_embedder().embed_query(SECRET)) == []


def test_matter_scoped_conversation_only_searches_that_matter(world):
    m1 = Matter.objects.create(tenant=world["a"], name="M1")
    m2 = Matter.objects.create(tenant=world["a"], name="M2")
    _doc_with_chunk(world["a"], SECRET, matter=m1)
    d2 = _doc_with_chunk(world["a"], SECRET + " copy", matter=m2)
    alice_m = Membership.objects.get(user=world["alice"])
    hits = search(membership=alice_m, matter=m2, query_embedding=get_embedder().embed_query(SECRET))
    assert [h.chunk.document_id for h in hits] == [d2.id]
