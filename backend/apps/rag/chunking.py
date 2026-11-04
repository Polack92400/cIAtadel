"""Page-aware text chunking.

Chunks never span pages, so every chunk carries an exact page number for
citations. Inside a page we split on paragraph, then sentence, then word
boundaries, with a character overlap between consecutive chunks.
"""

import re
from dataclasses import dataclass


@dataclass
class Chunk:
    page_number: int
    content: str


_SEPARATORS = ["\n\n", "\n", ". ", " "]


def _split(text: str, size: int, seps: list[str]) -> list[str]:
    if len(text) <= size:
        return [text]
    if not seps:
        return [text[i : i + size] for i in range(0, len(text), size)]
    sep, rest = seps[0], seps[1:]
    parts = text.split(sep)
    out, buf = [], ""
    for part in parts:
        candidate = f"{buf}{sep}{part}" if buf else part
        if len(candidate) <= size:
            buf = candidate
            continue
        if buf:
            out.append(buf)
        if len(part) > size:
            out.extend(_split(part, size, rest))
            buf = ""
        else:
            buf = part
    if buf:
        out.append(buf)
    return out


def chunk_pages(pages: list[tuple[int, str]], size: int, overlap: int) -> list[Chunk]:
    chunks: list[Chunk] = []
    for page_number, text in pages:
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        pieces = _split(text, max(size - overlap, 200), _SEPARATORS)
        prev_tail = ""
        for piece in pieces:
            piece = piece.strip()
            if not piece:
                continue
            content = f"{prev_tail} {piece}".strip() if prev_tail else piece
            chunks.append(Chunk(page_number, content))
            prev_tail = piece[-overlap:] if overlap else ""
            # start the overlap on a word boundary
            if " " in prev_tail:
                prev_tail = prev_tail.split(" ", 1)[1]
    return chunks
