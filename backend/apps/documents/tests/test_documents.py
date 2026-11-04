import pytest
from pypdf import PdfWriter

from apps.audit.models import AuditEvent
from apps.documents.models import Document
from apps.documents.storage import get_storage
from apps.rag.models import DocumentChunk
from conftest import pdf_bytes, upload

pytestmark = pytest.mark.django_db


def test_upload_is_stored_processed_and_indexed(as_user, run_tasks):
    client = as_user("bob")
    resp = run_tasks(upload, client, pdf_bytes(), "contract.pdf", title="Contract")
    assert resp.status_code == 201, resp.content
    body = resp.json()
    assert "storage_key" not in body and "sha256" not in body
    doc = Document.objects.get(pk=body["id"])
    assert doc.status == Document.Status.READY
    assert doc.chunk_count >= 1 and doc.page_count == 1
    assert doc.storage_key.startswith(f"tenants/{doc.tenant_id}/documents/")
    assert doc.storage_key in get_storage().objects
    chunk = DocumentChunk.objects.get(document=doc)
    assert chunk.tenant_id == doc.tenant_id and chunk.page_number == 1
    assert AuditEvent.objects.filter(action="document.uploaded", target_id=str(doc.pk)).exists()


def test_duplicate_upload_is_rejected_within_a_firm_only(as_user, run_tasks):
    data = pdf_bytes("unique text for dedup")
    assert run_tasks(upload, as_user("bob"), data).status_code == 201
    dup = upload(as_user("alice"), data)
    assert dup.status_code == 409
    assert dup.json()["error"]["existing_id"]
    # Same file in another firm is fine (and reveals nothing about firm A).
    assert run_tasks(upload, as_user("dave"), data).status_code == 201


@pytest.mark.parametrize(
    "name,data,expected",
    [
        ("notes.txt", b"%PDF-1.4 hello", "Only PDF"),
        ("fake.pdf", b"MZ\x90\x00 this is an executable", "not a valid PDF"),
        ("empty.pdf", b"", "empty"),
    ],
)
def test_invalid_files_are_rejected(as_user, name, data, expected):
    resp = upload(as_user("bob"), data, name)
    assert resp.status_code == 400
    assert expected in str(resp.json())
    assert Document.objects.count() == 0


def test_oversized_file_rejected(as_user, settings):
    settings.DOCUMENT_MAX_UPLOAD_BYTES = 1024
    resp = upload(as_user("bob"), b"%PDF-1.4\n" + b"0" * 2048)
    assert resp.status_code == 400
    assert "too large" in str(resp.json())


def test_malformed_pdf_fails_safely(as_user, run_tasks):
    resp = run_tasks(upload, as_user("bob"), b"%PDF-1.7\n1 0 obj << /Type /Catalog >>\ngarbage")
    doc = Document.objects.get(pk=resp.json()["id"])
    assert doc.status == Document.Status.FAILED
    assert doc.error_code in {"malformed", "empty"}
    assert not DocumentChunk.objects.filter(document=doc).exists()


def test_encrypted_pdf_fails_with_clear_reason(as_user, run_tasks):
    import io

    from pypdf import PdfReader

    w = PdfWriter()
    for p in PdfReader(io.BytesIO(pdf_bytes())).pages:
        w.add_page(p)
    w.encrypt("secret")
    buf = io.BytesIO()
    w.write(buf)
    resp = run_tasks(upload, as_user("bob"), buf.getvalue())
    doc = Document.objects.get(pk=resp.json()["id"])
    assert (doc.status, doc.error_code) == (Document.Status.FAILED, "encrypted")


def test_path_traversal_filename_is_sanitised(as_user, run_tasks):
    resp = run_tasks(upload, as_user("bob"), pdf_bytes(), "../../etc/passwd.pdf")
    assert resp.json()["original_filename"] == "passwd.pdf"


def test_viewer_cannot_upload_or_delete(as_user, run_tasks):
    assert upload(as_user("carol"), pdf_bytes()).status_code == 403
    doc_id = run_tasks(upload, as_user("bob"), pdf_bytes()).json()["id"]
    assert as_user("carol").delete(f"/api/v1/documents/{doc_id}").status_code == 403


def test_member_cannot_delete_colleagues_document_but_admin_can(as_user, run_tasks, world):
    from apps.accounts.models import Membership

    doc_id = run_tasks(upload, as_user("alice"), pdf_bytes()).json()["id"]
    Membership.objects.filter(user=world["bob"]).update(role="member")
    assert as_user("bob").delete(f"/api/v1/documents/{doc_id}").status_code == 403
    assert as_user("alice").delete(f"/api/v1/documents/{doc_id}").status_code == 204


def test_delete_removes_row_chunks_and_object(as_user, run_tasks):
    client = as_user("bob")
    doc_id = run_tasks(upload, client, pdf_bytes()).json()["id"]
    key = Document.objects.get(pk=doc_id).storage_key
    resp = run_tasks(client.delete, f"/api/v1/documents/{doc_id}")
    assert resp.status_code == 204
    assert not Document.objects.filter(pk=doc_id).exists()
    assert not DocumentChunk.objects.filter(document_id=doc_id).exists()
    assert key not in get_storage().objects
    assert AuditEvent.objects.filter(action="document.deleted").exists()


def test_download_streams_file_and_is_audited(as_user, run_tasks):
    client = as_user("bob")
    data = pdf_bytes("downloadable")
    doc_id = run_tasks(upload, client, data).json()["id"]
    resp = client.get(f"/api/v1/documents/{doc_id}/download")
    assert resp.status_code == 200
    assert b"".join(resp.streaming_content) == data
    assert resp["Cache-Control"] == "private, no-store"
    assert AuditEvent.objects.filter(action="document.downloaded").exists()


def test_search_and_status_filters(as_user, run_tasks):
    client = as_user("bob")
    run_tasks(upload, client, pdf_bytes("alpha"), "alpha.pdf", title="Alpha lease")
    run_tasks(upload, client, pdf_bytes("beta"), "beta.pdf", title="Beta contract")
    titles = [d["title"] for d in client.get("/api/v1/documents?search=lease").json()["results"]]
    assert titles == ["Alpha lease"]
    assert client.get("/api/v1/documents?status=failed").json()["count"] == 0
    assert client.get("/api/v1/documents?matter=not-a-uuid").json()["count"] == 0
