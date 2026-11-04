"""LLM and embedding providers, selected by configuration.

Business code imports only `get_llm()` / `get_embedder()` and the protocols
below — never a vendor SDK. Adding Bedrock means adding one module here.
"""

from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol

from django.conf import settings


@dataclass
class ChatMessage:
    role: str  # "system" | "user" | "assistant"
    content: str


class ProviderError(Exception):
    """Raised when a provider is unreachable or returns an invalid answer."""


class LLMProvider(Protocol):
    name: str
    model: str

    def generate(self, messages: list[ChatMessage]) -> str: ...


class EmbeddingProvider(Protocol):
    dimensions: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...
    def embed_query(self, text: str) -> list[float]: ...


@lru_cache(maxsize=1)
def get_llm() -> LLMProvider:
    cfg = settings.AI
    if cfg["LLM_PROVIDER"] == "ollama":
        from .ollama import OllamaLLM

        return OllamaLLM(cfg)
    if cfg["LLM_PROVIDER"] == "fake":
        from .fake import FakeLLM

        return FakeLLM()
    raise ValueError(f"Unknown LLM_PROVIDER {cfg['LLM_PROVIDER']!r}")


@lru_cache(maxsize=1)
def get_embedder() -> EmbeddingProvider:
    cfg = settings.AI
    if cfg["EMBEDDING_PROVIDER"] == "ollama":
        from .ollama import OllamaEmbeddings

        return OllamaEmbeddings(cfg)
    if cfg["EMBEDDING_PROVIDER"] == "fake":
        from .fake import FakeEmbeddings

        return FakeEmbeddings(cfg["EMBEDDING_DIM"])
    raise ValueError(f"Unknown EMBEDDING_PROVIDER {cfg['EMBEDDING_PROVIDER']!r}")
