## Why

The project already ships curated municipal reference material in `data/rag`, but the current chatbot cannot retrieve or cite that knowledge at runtime. This leaves common citizen questions about services, contacts, schedules, institutional structure, and explanatory context outside the strongest part of the product even though the source content is already present in the repository.

## What Changes

- Add a markdown-first knowledge indexing flow that reads `data/rag/**/*.md`, splits content into retrieval chunks, and persists embeddings plus source metadata in a local Chroma vector store.
- Add a retrieval capability for curated municipal knowledge so the chatbot can answer document-style questions using LangChain/LangGraph rather than only SQL-backed public-data tools.
- Teach the chatbot runtime to distinguish when a question should use SQL tools, when it should use RAG retrieval, and when it should combine both while preserving existing guardrails.
- Add operator workflows and regression coverage for building, refreshing, and validating the local knowledge index.

## Capabilities

### New Capabilities
- `markdown-knowledge-indexing`: Builds and refreshes a local vector index from markdown documents stored under `data/rag`.
- `public-knowledge-rag`: Retrieves grounded municipal reference context from the vector index and surfaces source-backed answers to the chatbot.
- `knowledge-aware-chat-orchestration`: Extends the citizen-facing chatbot so allowed queries can route to the curated knowledge retrieval layer in addition to the existing SQL tool surface.

### Modified Capabilities
- None.

## Impact

- Affected code: `agents/chatbot/*`, `agents/tools/registry.py`, `cli.py`, `pyproject.toml`, and new indexing/retrieval modules for the vector store.
- Affected systems: local developer/operator workflow for indexing `data/rag`, runtime agent orchestration, and answer composition rules for source-backed document responses.
- Affected dependencies: Chroma integration, text-splitting/retrieval helpers, and embedding configuration for the vector store.
- Risk areas: SQL-vs-RAG routing mistakes, stale or missing vector indexes, ungrounded summaries, and overlap/conflict between retrieved document knowledge and structured SQL answers.
