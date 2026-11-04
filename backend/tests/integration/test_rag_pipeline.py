"""Upload → async processing → indexing → question → cited answer."""

import pytest

from apps.ai_engine.prompts import NOT_FOUND
from apps.conversations.models import Conversation, Message
from conftest import pdf_bytes, upload

pytestmark = pytest.mark.django_db


def test_end_to_end_question_answering_with_citations(as_user, run_tasks):
    client = as_user("bob")
    data = pdf_bytes(
        pages=[
            ["Master services agreement between Acme and Globex."],
            ["Either party may terminate for convenience with ninety days written notice."],
        ],
        title="MSA",
    )
    doc = run_tasks(upload, client, data, "msa.pdf", title="MSA").json()
    assert client.get(f"/api/v1/documents/{doc['id']}").json()["status"] == "ready"

    conv = client.post("/api/v1/conversations", {}, format="json").json()
    resp = client.post(
        f"/api/v1/conversations/{conv['id']}/messages",
        {"content": "What notice is required to terminate for convenience?"},
        format="json",
    )
    assert resp.status_code == 201, resp.content
    msg = resp.json()
    assert msg["role"] == "assistant" and "[S1]" in msg["content"]
    top = msg["citations"][0]
    assert top["used"] and top["document"] == doc["id"]
    assert top["page_number"] == 2 and "ninety days" in top["excerpt"]

    detail = client.get(f"/api/v1/conversations/{conv['id']}").json()
    assert [m["role"] for m in detail["messages"]] == ["user", "assistant"]
    assert detail["title"].startswith("What notice")
    assert Conversation.objects.get(pk=conv["id"]).tenant.slug == "firm-a"


def test_no_documents_means_explicit_insufficient_context(as_user):
    client = as_user("bob")
    conv = client.post("/api/v1/conversations", {}, format="json").json()
    msg = client.post(
        f"/api/v1/conversations/{conv['id']}/messages",
        {"content": "What is the liability cap?"},
        format="json",
    ).json()
    assert msg["content"] == NOT_FOUND
    assert msg["insufficient_context"] is True and msg["citations"] == []


def test_llm_outage_returns_503_and_persists_nothing(as_user, run_tasks, monkeypatch):
    from apps.ai_engine.providers import ProviderError
    from apps.conversations import assistant

    client = as_user("bob")
    run_tasks(upload, client, pdf_bytes("some content"))

    class Down:
        model = "down"

        def generate(self, messages):
            raise ProviderError("down")

    monkeypatch.setattr(assistant, "get_llm", lambda: Down())
    conv = client.post("/api/v1/conversations", {}, format="json").json()
    resp = client.post(
        f"/api/v1/conversations/{conv['id']}/messages", {"content": "some content?"}, format="json"
    )
    assert resp.status_code == 503
    assert not Message.objects.filter(conversation_id=conv["id"]).exists()


def test_dashboard_summarises_workspace(as_user, run_tasks):
    client = as_user("bob")
    run_tasks(upload, client, pdf_bytes("dash"))
    data = client.get("/api/v1/dashboard").json()
    assert data["document_total"] == 1 and data["documents_by_status"]["ready"] == 1
    assert data["tenant"]["name"] == "Firm A" and data["role"] == "member"


def test_refusal_appended_after_a_real_answer_is_not_flagged_insufficient(
    as_user, run_tasks, monkeypatch
):
    from apps.conversations import assistant

    class Chatty:
        model = "chatty"

        def generate(self, messages):
            return f"**From the documents:** Ninety days notice.\n\n**Interpretation:** {NOT_FOUND}"

    client = as_user("bob")
    run_tasks(upload, client, pdf_bytes("Termination requires ninety days notice."))
    monkeypatch.setattr(assistant, "get_llm", lambda: Chatty())
    conv = client.post("/api/v1/conversations", {}, format="json").json()
    msg = client.post(
        f"/api/v1/conversations/{conv['id']}/messages",
        {"content": "notice to terminate?"},
        format="json",
    ).json()
    assert msg["insufficient_context"] is False
    assert msg["citations"] and not any(c["used"] for c in msg["citations"])
