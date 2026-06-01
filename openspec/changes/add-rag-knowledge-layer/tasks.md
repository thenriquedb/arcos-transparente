## 1. Dependencies and Configuration

- [x] 1.1 Add the Chroma and retrieval-support dependencies needed for markdown chunking, vector persistence, and retriever access.
- [x] 1.2 Add configuration defaults for the RAG persist directory, embedding model, and any required environment variables.
- [x] 1.3 Update ignore/config files so generated vector-store artifacts and manifests are handled correctly in local development.

## 2. Markdown Knowledge Indexing

- [x] 2.1 Implement discovery of `data/rag/**/*.md` files and exclude non-markdown assets from the v1 indexing flow.
- [x] 2.2 Implement markdown parsing and heading-aware chunking with stable source metadata for each chunk.
- [x] 2.3 Implement persistent Chroma index creation plus manifest generation for source fingerprints and build metadata.
- [x] 2.4 Add a rebuild path that refreshes changed markdown content without requiring unrelated application data to be reset.

## 3. Operator Workflow

- [x] 3.1 Add CLI commands for building or rebuilding the markdown knowledge index.
- [x] 3.2 Add a CLI status command that reports whether the persisted index is missing, empty, or ready.
- [x] 3.3 Ensure operator-facing failures for missing credentials or unreadable index state are clear and actionable.

## 4. Retrieval Layer

- [x] 4.1 Implement a LangChain-based retriever service that opens the persisted Chroma index and returns grounded passages with source metadata.
- [x] 4.2 Implement structured outcomes for successful retrieval, no grounded result, and unavailable index states.
- [x] 4.3 Register a new public RAG tool that exposes curated municipal knowledge retrieval to the chatbot runtime.

## 5. Chatbot Orchestration and Guardrails

- [x] 5.1 Update pre-agent scope enforcement so questions grounded in the indexed markdown corpus are allowed while unrelated open-domain questions remain blocked.
- [x] 5.2 Update prompt and tool contracts so the chatbot distinguishes SQL-only, RAG-only, and hybrid question flows.
- [x] 5.3 Ensure RAG-backed answers include visible source references and hybrid answers clearly separate retrieved content from SQL-backed data.

## 6. Verification and Documentation

- [x] 6.1 Add tests for markdown-only indexing, rebuild behavior, and status reporting.
- [x] 6.2 Add tests for retrieval hits, retrieval misses, and unavailable-index behavior.
- [x] 6.3 Add chatbot regression coverage for allowed RAG questions, blocked unrelated questions, SQL-versus-RAG routing, and hybrid answers.
- [x] 6.4 Update the relevant architecture and operator docs to describe the new RAG layer, indexing workflow, and scope boundary.
