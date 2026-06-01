## ADDED Requirements

### Requirement: Markdown corpus is indexed into persistent Chroma storage
The system MUST build a persistent Chroma vector index from markdown documents located under `data/rag`.

#### Scenario: Successful markdown index build
- **WHEN** an operator runs the knowledge-index build workflow and markdown files exist under `data/rag`
- **THEN** the system reads each `*.md` file under that tree, splits the content into retrieval chunks, embeds the chunks, and persists them to a local Chroma collection
- **AND** each stored chunk includes source metadata sufficient to identify the originating file and chunk position

#### Scenario: Non-markdown assets are ignored in v1
- **WHEN** the source tree also contains CSV, PDF, or other non-markdown files
- **THEN** the v1 index build ignores those non-markdown assets
- **AND** the build does not fail solely because those files are present alongside the markdown corpus

### Requirement: Index rebuilds are repeatable and inspectable
The system MUST allow operators to rebuild and inspect the markdown knowledge index without deleting unrelated application data.

#### Scenario: Rebuild reflects markdown edits
- **WHEN** an indexed markdown file changes and the operator runs the rebuild workflow
- **THEN** the persisted index updates the affected stored content to reflect the new file content
- **AND** the index manifest records updated source fingerprint or build metadata for that file set

#### Scenario: Status reports missing or empty index
- **WHEN** an operator checks index status before any successful build or after the persisted index is removed
- **THEN** the system reports that the markdown knowledge index is unavailable or empty
- **AND** it does not report the RAG corpus as ready for grounded retrieval
