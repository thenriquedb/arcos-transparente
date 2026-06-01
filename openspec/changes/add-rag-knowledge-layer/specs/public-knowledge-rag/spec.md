## ADDED Requirements

### Requirement: Retrieval returns grounded municipal knowledge from indexed markdown
The system MUST retrieve supporting context for municipal knowledge questions from the indexed markdown corpus and expose source metadata with the retrieved passages.

#### Scenario: FAQ question returns grounded passages
- **WHEN** a user asks a question answered in an indexed FAQ-style markdown file such as how to emit a second copy of IPTU
- **THEN** the retrieval layer returns one or more relevant passages from the indexed markdown corpus
- **AND** each returned passage includes source identifiers such as document title, file path, or section metadata

#### Scenario: Service-information question retrieves the relevant document
- **WHEN** a user asks a question about bus schedules, useful phones, organizational structure, or similar content covered only by indexed markdown
- **THEN** the retrieval layer returns passages from the relevant markdown source
- **AND** it does not depend on structured SQL tables for that document-style answer

### Requirement: Retrieval misses are explicit and safe
The retrieval layer MUST produce a structured no-grounded-result outcome when the vector index cannot support a reliable answer.

#### Scenario: No relevant passage is found
- **WHEN** the retriever cannot find sufficiently relevant indexed passages for the user question
- **THEN** the retrieval layer returns an explicit no-grounded-result outcome
- **AND** the chatbot can decline, clarify, or fall back without inventing unsupported document content

#### Scenario: Persisted index is unavailable at query time
- **WHEN** the Chroma index is missing, unreadable, or otherwise unavailable when retrieval is attempted
- **THEN** the retrieval layer returns an unavailable state that explains the operational problem
- **AND** it does not masquerade as an empty factual answer
