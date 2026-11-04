import pytest

from apps.rag.chunking import chunk_pages
from apps.rag.extraction import ExtractionError, extract_pages
from conftest import pdf_bytes


def test_chunks_keep_page_numbers_and_respect_size():
    pages = [(1, "word " * 600), (2, "Second page text.")]
    chunks = chunk_pages(pages, size=500, overlap=50)
    assert {c.page_number for c in chunks} == {1, 2}
    assert all(len(c.content) <= 500 for c in chunks)
    assert chunks[-1].content == "Second page text."


def test_extraction_returns_text_per_page():
    data = pdf_bytes(pages=[["First page."], ["Second page."]])
    pages = extract_pages(data)
    assert [p for p, _ in pages] == [1, 2]
    assert "Second page." in pages[1][1]


@pytest.mark.parametrize("data", [b"%PDF-1.4\n%%EOF", b"%PDF-" + b"\x00" * 100, b"not a pdf"])
def test_garbage_raises_typed_error(data):
    with pytest.raises(ExtractionError):
        extract_pages(data)


def test_page_limit(settings):
    settings.AI = {**settings.AI, "PDF_MAX_PAGES": 1}
    with pytest.raises(ExtractionError) as exc:
        extract_pages(pdf_bytes(pages=[["a"], ["b"]]))
    assert exc.value.code == "too_many_pages"
