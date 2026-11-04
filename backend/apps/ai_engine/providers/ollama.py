import httpx

from . import ChatMessage, ProviderError


class OllamaLLM:
    name = "ollama"

    def __init__(self, cfg):
        self.model = cfg["LLM_MODEL"]
        self.base_url = cfg["LLM_BASE_URL"].rstrip("/")
        self.timeout = cfg["LLM_TIMEOUT_SECONDS"]
        self.options = {"temperature": cfg["LLM_TEMPERATURE"], "num_ctx": cfg["LLM_NUM_CTX"]}

    def generate(self, messages: list[ChatMessage]) -> str:
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            "options": self.options,
        }
        try:
            resp = httpx.post(f"{self.base_url}/api/chat", json=payload, timeout=self.timeout)
            resp.raise_for_status()
            content = resp.json()["message"]["content"]
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise ProviderError(f"LLM request failed: {type(exc).__name__}") from exc
        return content.strip()


class OllamaEmbeddings:
    BATCH = 32

    def __init__(self, cfg):
        self.model = cfg["EMBEDDING_MODEL"]
        self.base_url = cfg["EMBEDDING_BASE_URL"].rstrip("/")
        self.dimensions = cfg["EMBEDDING_DIM"]
        self.query_prefix = cfg["EMBEDDING_QUERY_PREFIX"]
        self.doc_prefix = cfg["EMBEDDING_DOCUMENT_PREFIX"]
        self.timeout = cfg["LLM_TIMEOUT_SECONDS"]

    def _embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for i in range(0, len(texts), self.BATCH):
            batch = texts[i : i + self.BATCH]
            try:
                resp = httpx.post(
                    f"{self.base_url}/api/embed",
                    json={"model": self.model, "input": batch},
                    timeout=self.timeout,
                )
                resp.raise_for_status()
                vectors = resp.json()["embeddings"]
            except (httpx.HTTPError, KeyError, ValueError) as exc:
                raise ProviderError(f"Embedding request failed: {type(exc).__name__}") from exc
            for v in vectors:
                if len(v) != self.dimensions:
                    raise ProviderError(
                        f"Embedding size {len(v)} != EMBEDDING_DIM {self.dimensions}"
                    )
            out.extend(vectors)
        return out

    def embed_documents(self, texts):
        return self._embed([self.doc_prefix + t for t in texts])

    def embed_query(self, text):
        return self._embed([self.query_prefix + text])[0]
