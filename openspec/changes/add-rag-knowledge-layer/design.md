## Context

The repository already contains curated municipal reference documents under `data/rag`, including FAQs, phone lists, bus schedules, institutional descriptions, and organizational structure. Those documents are useful for citizen questions, but the active chatbot runtime only exposes SQL-backed public-data tools and has no retrieval pipeline, vector store, or source-grounded document answer path.

The current chatbot architecture has three relevant constraints:

- the citizen-facing runtime is centered on `agents/chatbot/agent.py` plus `agents/chatbot/core.py`
- LangChain/LangGraph are already present in the stack and power the current agent runtime
- hard guardrails must remain deterministic and pre-model, regardless of any new retrieval capability

There is also an important product-boundary implication: several markdown documents describe municipal services or civic context that are not currently admitted by the "transparency data only" scope wording in the guardrails and prompt. Adding RAG therefore requires an explicit, bounded scope expansion to "curated municipal knowledge committed in `data/rag`", not just a new tool.

The repository also includes non-markdown files in `data/rag` such as CSV and PDF assets, but the requested scope is specifically to read the markdown corpus first and use that as the initial knowledge base.

## Goals / Non-Goals

**Goals:**
- Build a repeatable local indexing flow for `data/rag/**/*.md`.
- Persist embeddings and retrieval metadata in a local Chroma database.
- Expose a grounded RAG capability that the chatbot can use for document-style municipal questions.
- Expand the supported citizen-facing scope to include the curated local markdown corpus while keeping unrelated questions blocked.
- Preserve the current hard-guardrail boundary and the existing SQL tool surface.
- Make SQL-versus-RAG behavior explicit enough to test and evolve.

**Non-Goals:**
- Replacing the SQL tools or moving numeric/aggregate transparency queries to RAG.
- Indexing PDFs, CSVs, or XML files in the first version.
- Introducing a remote vector database or a separate retrieval service.
- Auto-crawling external websites at runtime.
- Rebuilding the chatbot as a fully custom LangGraph workflow if the current `create_agent` path remains sufficient.

## Decisions

### 1. Start with a markdown-only ingestion boundary

Version 1 will index only `data/rag/**/*.md`. PDFs and CSVs in the same tree will be ignored by the builder but left available for a later expansion.

Rationale:
- This matches the user request exactly.
- Markdown files already contain clean, human-curated content that is easier to chunk than tabular or scanned assets.
- It reduces the first implementation to one parsing path and one metadata model.

Alternatives considered:
- Index every file type in `data/rag` immediately: rejected because PDF extraction and CSV normalization introduce separate quality and testing problems.
- Convert non-markdown assets into markdown during the same change: rejected because it couples source curation to retrieval architecture.

### 2. Persist a local Chroma index with deterministic document metadata

The indexing flow will build a local Chroma collection from markdown chunks. Each stored chunk should carry deterministic metadata such as:
- source relative path
- document title
- heading/section lineage when available
- chunk position
- content hash or source fingerprint
- indexing timestamp or manifest version

The system should also write a lightweight manifest describing the indexed files, embedding model, chunk count, and source fingerprints so operators can detect stale or missing indexes.

Rationale:
- Chroma is the requested vector store and fits the repo's local-first workflow.
- Stable metadata makes answer citations, debugging, and reindex behavior much easier.
- A manifest provides a simple operational contract without needing a separate database table.

Alternatives considered:
- In-memory vector storage only: rejected because the index would vanish between runs and make local operations brittle.
- Persist only raw vectors without a manifest: rejected because stale-index failures would be harder to diagnose.

### 3. Use LangChain retrievers behind a dedicated public RAG tool

The chatbot should gain a new public tool dedicated to curated municipal knowledge retrieval. That tool will:
- query the Chroma retriever
- return the best matching passages plus source metadata
- provide a structured "no grounded result" outcome when retrieval confidence is weak or no documents match

The agent runtime can continue to use `create_agent(...)`, which already relies on LangGraph internally. This keeps LangGraph as the orchestration runtime while adding a new retrieval capability through the existing tool contract model.

Rationale:
- This is the smallest architectural extension that fits the current agent design.
- It preserves the registry pattern already used for SQL tools.
- It avoids rewriting the chatbot into a custom graph before the RAG behavior is proven.

Alternatives considered:
- Insert retrieval outside the agent as an unconditional pre-step: rejected because many questions should stay SQL-only and unconditional retrieval would add noise.
- Replace the current agent with a fully custom graph now: rejected because it expands migration risk without being necessary for the first RAG slice.

### 4. Use the existing OpenAI provider path for embeddings by default

The first implementation should default to OpenAI embeddings so the project can reuse the provider family it already depends on for the citizen chatbot. Embedding model selection should be configurable by environment variable, and the index builder should fail clearly when the required credentials are missing.

Rationale:
- The repo already depends on `langchain-openai` and treats OpenAI as the official provider in the current phase.
- This avoids adding a second model-serving stack just for indexing.
- One provider path keeps configuration and troubleshooting simpler during the first rollout.

Alternatives considered:
- Local sentence-transformer embeddings: rejected for v1 because they would add a second inference path, new dependency weight, and different operational assumptions from the rest of the active stack.
- Hard-code one embedding model with no override: rejected because retrieval quality/cost may need tuning.

### 5. Expand supported scope only to curated local municipal knowledge

The hard guardrail boundary will remain deterministic, but the allowed scope must widen from "structured transparency data only" to "structured transparency data plus curated municipal knowledge that is explicitly indexed from `data/rag/**/*.md`".

Rationale:
- Without this change, questions such as bus schedules or useful municipal contact numbers would still be blocked before retrieval can run.
- The expansion remains bounded to local, auditable source files committed in the repository.
- It preserves a strong distinction between supported local knowledge and arbitrary open-domain chat.

Alternatives considered:
- Keep the current scope wording and rely on prompt/tool behavior to admit these questions: rejected because the guardrail layer would still block them first.
- Open the scope broadly to general municipal assistance: rejected because it would weaken the deterministic safety boundary and increase hallucination risk.

### 6. Make SQL-versus-RAG routing explicit in prompt and tool contracts

The chatbot must preserve a clear boundary:
- SQL tools remain the authority for structured transparency data, totals, rankings, and period-filtered financial questions.
- The RAG tool handles curated explanatory or service-oriented content from `data/rag`, such as contacts, bus schedules, institutional descriptions, and FAQ-style guidance.
- Hybrid answers are allowed when a single user request spans both categories, but the response must keep the source of each part clear.

RAG-backed answers should include source references derived from the stored metadata, such as document title or file name.

Rationale:
- The biggest failure mode here is not building the vector index; it is using RAG where SQL is the better source of truth, or vice versa.
- The current project already leans on prompt and tool contracts for orchestration ownership.

Alternatives considered:
- Let the model infer the boundary without explicit contract changes: rejected because the existing prompt is SQL-first and would not describe the new retrieval surface well enough.

### 7. Add explicit operator workflows for build, rebuild, and status

The CLI should expose dedicated RAG commands, such as indexing/rebuilding and status inspection, instead of hiding vector creation inside chatbot startup.

Rationale:
- Index builds may be slow or credential-dependent.
- Operators need a visible way to refresh the knowledge base after editing markdown files.
- Startup should fail predictably when the index is absent, not silently rebuild it in the background.

Alternatives considered:
- Auto-build on first chatbot request: rejected because it hides operational latency and makes failure cases less understandable.
- Rebuild during XML import: rejected because `data/rag` content changes independently from XML ingestion.

## Risks / Trade-offs

- [Risk] RAG answers may overlap with SQL domains and produce weaker or less authoritative answers. -> Mitigation: keep strict contract guidance that structured financial or personnel queries stay on SQL, and add routing regression tests.
- [Risk] The vector index may become stale after markdown edits. -> Mitigation: write a manifest, expose CLI status, and make missing/stale index states visible.
- [Risk] Retrieved passages may be too broad or too shallow depending on chunk size. -> Mitigation: use heading-aware chunking and cover representative documents in retrieval tests.
- [Risk] Embedding generation depends on OpenAI credentials and network availability during indexing. -> Mitigation: fail fast with clear operator errors and keep the index persistent once built.
- [Risk] The model may answer from prior knowledge instead of grounded passages. -> Mitigation: require tool use for document-backed answers and require source references in the response contract.

## Migration Plan

1. Add the vector-store and text-splitting dependencies plus configuration for the embedding model and persist directory.
2. Introduce a markdown indexing module that scans `data/rag`, chunks markdown, embeds the chunks, and persists them to Chroma with a manifest.
3. Add CLI commands for `rag index` and `rag status`.
4. Add a new public retrieval tool and register it alongside the existing SQL tools.
5. Update the chatbot prompt/contracts so it knows when to use SQL, RAG, or both.
6. Add regression tests for indexing, retrieval misses, routing boundaries, and representative citizen questions.

Rollback strategy:
- Leave the current SQL-only chatbot behavior available by disabling the RAG tool registration or omitting the RAG configuration.
- If retrieval quality is poor, the vector index and tool can be removed without affecting the existing SQL storage pipeline.

## Open Questions

- Should the first answer format cite file names only, or also include section headings/snippets in the visible response?
- Should stale-index detection merely warn operators, or should it block chatbot startup when source files changed after the last build?
- Do we want a single hybrid knowledge tool, or later split it into operator-facing retrieval/debug commands and a separate citizen-facing tool contract?
