"""Deterministic offline providers for tests and CI (no network, no GPU).

FakeEmbeddings is a hashed bag-of-words: texts sharing words get similar
vectors, which is enough to test retrieval ranking and tenant filtering.
"""

import hashlib
import math
import re

from . import ChatMessage

_WORD = re.compile(r"[a-zA-Z0-9]{3,}")


class FakeEmbeddings:
    def __init__(self, dimensions: int):
        self.dimensions = dimensions

    def _vec(self, text: str) -> list[float]:
        v = [0.0] * self.dimensions
        for word in _WORD.findall(text.lower()):
            h = int.from_bytes(hashlib.sha256(word.encode()).digest()[:4], "big")
            v[h % self.dimensions] += 1.0
        if not any(v):
            v[0] = 1.0
        norm = math.sqrt(sum(x * x for x in v))
        return [x / norm for x in v]

    def embed_documents(self, texts):
        return [self._vec(t) for t in texts]

    def embed_query(self, text):
        return self._vec(text)


class FakeLLM:
    name = "fake"
    model = "fake-llm"

    def generate(self, messages: list[ChatMessage]) -> str:
        user = messages[-1].content
        first = re.search(r'<source id="S(\d+)"[^>]*>\s*(.+?)\s*</source>', user, re.S)
        if not first:
            return "The available documents do not contain enough information to answer."
        sentence = first.group(2).split(". ")[0].strip()[:300]
        return (
            f"**From the documents:** {sentence} [S{first.group(1)}]\n\n"
            "**Interpretation:** This is a deterministic test answer."
        )
