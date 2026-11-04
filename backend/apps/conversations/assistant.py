"""Question answering: authorize → retrieve → prompt → generate → persist."""

import logging
import re
import time

from django.db import transaction

from apps.ai_engine.prompts import NOT_FOUND, Source, build_messages
from apps.ai_engine.providers import ChatMessage, get_embedder, get_llm
from apps.rag.retrieval import search

from .models import Citation, Conversation, Message

logger = logging.getLogger(__name__)
_CITE = re.compile(r"\[(\d{1,2})\]")
HISTORY_TURNS = 4


def answer(*, conversation: Conversation, membership, question: str) -> Message:
    tenant = membership.tenant
    with transaction.atomic():
        Message.objects.create(
            tenant=tenant, conversation=conversation, role=Message.Role.USER, content=question
        )
        if conversation.title == "New conversation":
            conversation.title = question[:80]
        conversation.save(update_fields=["title", "updated_at"])

    started = time.monotonic()
    query_vec = get_embedder().embed_query(question)
    hits = search(membership=membership, query_embedding=query_vec, matter=conversation.matter)
    sources = [
        Source(i, h.chunk.document.title, h.chunk.page_number, h.chunk.content)
        for i, h in enumerate(hits, start=1)
    ]

    llm = get_llm()
    if not sources:
        text, insufficient = NOT_FOUND, True
    else:
        history = [
            ChatMessage(m.role, m.content)
            for m in list(conversation.messages.order_by("-created_at")[1 : 1 + HISTORY_TURNS * 2])[
                ::-1
            ]
        ]
        text = llm.generate(build_messages(question, sources, history))
        insufficient = NOT_FOUND.lower()[:40] in text.lower()

    used = {int(n) for n in _CITE.findall(text)}
    with transaction.atomic():
        msg = Message.objects.create(
            tenant=tenant,
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content=text,
            insufficient_context=insufficient,
            model_name=getattr(llm, "model", ""),
            latency_ms=int((time.monotonic() - started) * 1000),
        )
        Citation.objects.bulk_create(
            [
                Citation(
                    tenant=tenant,
                    message=msg,
                    number=s.number,
                    used=s.number in used,
                    document=h.chunk.document,
                    chunk=h.chunk,
                    document_title=s.document_title,
                    page_number=s.page_number,
                    score=round(1 - h.distance, 4),
                )
                for s, h in zip(sources, hits, strict=True)
            ]
        )
        conversation.save(update_fields=["updated_at"])
    return msg
