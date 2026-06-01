## ADDED Requirements

### Requirement: Allowed chatbot scope includes curated local municipal knowledge
The citizen-facing chatbot MUST treat questions grounded in the indexed markdown corpus under `data/rag` as supported municipal queries, even when they are not direct SQL transparency-data questions.

#### Scenario: Curated municipal service question is admitted
- **WHEN** a user asks a question such as `Qual o telefone da ouvidoria?` or `Qual o horario do onibus para Formiga?` and the answer exists in indexed markdown
- **THEN** pre-agent scope evaluation admits the request as allowed
- **AND** the chatbot may answer through the RAG retrieval path

#### Scenario: Unrelated general question remains blocked
- **WHEN** a user asks a question that is neither covered by the SQL transparency domains nor grounded in the indexed markdown corpus
- **THEN** the system blocks the request as out of scope
- **AND** the language model is not invoked

### Requirement: Chatbot chooses SQL or RAG according to source-of-truth boundaries
The chatbot MUST route structured transparency questions to SQL-backed tools and document-style municipal knowledge questions to the RAG retrieval layer.

#### Scenario: Document-style municipal question uses RAG
- **WHEN** a user asks about phones, schedules, institutional structure, institutional roles, or other content covered only by indexed markdown
- **THEN** the assistant uses the RAG retrieval capability rather than a SQL tool as the primary source of truth
- **AND** the answer reflects the grounded retrieved content

#### Scenario: Structured transparency question stays on SQL
- **WHEN** a user asks for totals, rankings, salaries, contracts, licitacoes, despesas, receitas, patrimonios, quadro de pessoal, or other structured transparency data
- **THEN** the assistant uses the relevant SQL tool flow as the source of truth
- **AND** it does not answer that structured query from RAG passages alone

### Requirement: RAG-backed chat responses preserve source clarity
When the chatbot uses retrieved markdown knowledge, it MUST make the document source visible to the user and keep hybrid answers auditable.

#### Scenario: RAG-backed answer cites its source
- **WHEN** the assistant answers a user question using retrieved markdown passages
- **THEN** the visible response includes source identifiers such as document title, file name, or section heading
- **AND** the answer does not present the retrieved content as uncited free-form prior knowledge

#### Scenario: Hybrid answer distinguishes SQL and retrieved content
- **WHEN** one user request requires both indexed markdown context and structured transparency data
- **THEN** the assistant may combine both result types in one response
- **AND** it clearly distinguishes which parts came from retrieved documents and which parts came from SQL-backed public data
