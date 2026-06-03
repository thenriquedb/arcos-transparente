# public-transferencias-financeiras-agent-access Specification

## Purpose
TBD - created by archiving change extend-transferencias-financeiras-ingestion-and-agent-tools. Update Purpose after archive.
## Requirements
### Requirement: Public tools expose imported `transferencias-financeiras` records from SQL
The system MUST expose imported `transferencias-financeiras` data through dedicated public SQL tools for lookup and aggregation, using the local dedicated tables as the source of truth.

#### Scenario: Lookup tool returns transfer-movement records with supported filters
- **WHEN** imported transfer-movement records match supported filters such as year, conceding unit, receiving unit, movement type, purpose, or funding source
- **THEN** the public lookup capability returns the matching transfer records from SQL
- **AND** the response includes only the supported source-backed fields exposed by the public contract

#### Scenario: Lookup tool returns parliamentary-amendment records with supported filters
- **WHEN** imported parliamentary-amendment records match supported filters such as exercise, year-number identifier, author, amendment type, function, or object
- **THEN** the public lookup capability returns the matching amendment records from SQL
- **AND** the response reflects the dedicated amendment contract rather than generic revenue or expense text matching

### Requirement: Public aggregation supports totals, counts, and rankings for this domain
The system MUST allow aggregate queries over imported `transferencias-financeiras` data using the dedicated SQL persistence of the domain.

#### Scenario: Aggregation summarizes transfer-movement values
- **WHEN** imported transfer-movement records match an aggregation query for totals, counts, or rankings
- **THEN** the public aggregation capability computes the requested result from the persisted transfer-movement SQL data
- **AND** the result can group by supported movement dimensions such as receiving unit or movement type when those fields are requested

#### Scenario: Aggregation summarizes parliamentary-amendment values
- **WHEN** imported parliamentary-amendment records match an aggregation query for totals, counts, or rankings
- **THEN** the public aggregation capability computes the requested result from the persisted amendment SQL data
- **AND** the result can group by supported dimensions such as author, function, or amendment type when those fields are requested

### Requirement: The citizen-facing agent uses the dedicated `transferencias-financeiras` tool path for structured questions
The chatbot MUST treat structured questions about municipal financial transfers and parliamentary amendments as an in-scope SQL transparency domain and answer them through the dedicated public tools of this domain.

#### Scenario: User asks about transfers to the Câmara
- **WHEN** a user asks a structured question about transferências, repasses, recebimentos, or devoluções between public units such as Prefeitura and Câmara
- **THEN** the agent keeps the request inside the supported public-data scope
- **AND** it answers through the dedicated `transferencias-financeiras` SQL tool path instead of generic reasoning or unrelated revenue tools

#### Scenario: User asks about parliamentary amendments
- **WHEN** a user asks a structured question about emendas parlamentares received by the municipality
- **THEN** the agent keeps the request inside the supported public-data scope
- **AND** it answers through the dedicated `transferencias-financeiras` SQL tool path instead of generic revenue, planning, or expense fallbacks

### Requirement: Dedicated `transferencias-financeiras` tools remain auditable within the public registry
The public tool registry, prompt contracts, and compatible routing layer MUST keep the supported `transferencias-financeiras` capabilities discoverable to the citizen-facing agent.

#### Scenario: Public tool set includes the dedicated domain capabilities
- **WHEN** the citizen-facing agent is initialized with the public tool registry
- **THEN** the supported lookup and aggregation capabilities for `transferencias-financeiras` are available in the public tool set
- **AND** they remain tagged and documented as part of the public transparency domain

#### Scenario: Structured transfer questions prefer the dedicated domain over generic neighbors
- **WHEN** the user asks a question that clearly targets transfers, repasses, or parliamentary amendments
- **THEN** the routing and prompt contracts prefer the dedicated `transferencias-financeiras` tool path
- **AND** the answer does not depend solely on adjacent `receitas`, `despesas`, or `planejamento` capabilities when the domain-specific tools are available

