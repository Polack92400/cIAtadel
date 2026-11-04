# ADR 0004 — AI providers and vector store

**Decision.**
- `ai_engine` exposes `LLMProvider` (`generate`, `stream`) and
  `EmbeddingProvider` (`embed_documents`, `embed_query`) protocols, selected
  by `LLM_PROVIDER` / `EMBEDDING_PROVIDER`. Adapters: `ollama` (local),
  `fake` (deterministic, used by all tests and CI). `bedrock` later.
- Custom lightweight orchestration instead of LangChain: the pipeline is small
  (retrieve → prompt → generate → cite) and we need tight control over the
  tenant filter and prompt layout. Revisit if agents/tools are added.
- pgvector inside the main PostgreSQL: chunks share transactions and RLS with
  their documents; the tenant filter and similarity ranking run in one SQL
  query. HNSW index with cosine distance.
- Defaults: `llama3.2:3b` (runs on a laptop CPU) and `nomic-embed-text`
  (768-d). The vector dimension is configuration (`EMBEDDING_DIM`) and part of
  the migration; changing models requires re-indexing.
