# public-despesas-por-funcao-agent-access Specification

## Purpose
TBD - created by archiving change extend-despesas-por-funcao-ingestion-and-agent-tools. Update Purpose after archive.
## Requirements
### Requirement: Public `despesas-por-funcao` tools expose imported function-report records from SQL
The system MUST expose imported `despesas-por-funcao` data through dedicated public SQL tools for lookup and aggregation, using the dedicated SQL table of this domain as the source of truth.

#### Scenario: Lookup tool returns function-report rows with supported filters
- **WHEN** imported `despesas-por-funcao` records match supported lookup filters such as year, report period, unit, function, or supported value ranges
- **THEN** the public lookup capability returns the matching function-report rows from SQL
- **AND** the response includes only the supported source-backed fields exposed by the public contract

#### Scenario: Aggregation tool summarizes imported `despesas-por-funcao` data
- **WHEN** imported `despesas-por-funcao` records match an aggregation query for totals, counts, comparisons, or rankings
- **THEN** the public aggregation capability computes the requested result from the persisted SQL data
- **AND** the result can group by supported dimensions such as `funcao`, `origem`, or `unidade_gestora` when those fields are requested

### Requirement: The citizen-facing agent uses the dedicated `despesas-por-funcao` tool path for structured function-report questions
The chatbot MUST treat structured questions about the `despesas-por-funcao` report as an in-scope SQL transparency domain and answer them through the dedicated public tools of this domain.

#### Scenario: User asks for individual function-report rows
- **WHEN** a user asks for specific `despesas-por-funcao` entries or report slices such as the values for a function, unit, or period
- **THEN** the agent keeps the request inside the supported public-data scope
- **AND** it answers through the dedicated lookup capability instead of generic free-form reasoning

#### Scenario: User asks for totals or rankings over functions
- **WHEN** a user asks for total paid, total budget, comparisons, or rankings across functions in the `despesas-por-funcao` report
- **THEN** the agent keeps the request inside the supported public-data scope
- **AND** it answers through the dedicated aggregation capability as the SQL source of truth

### Requirement: Dedicated `despesas-por-funcao` tools remain auditable within the public registry
The public tool registry, prompt contracts, and compatible routing layer MUST keep the supported `despesas-por-funcao` capabilities discoverable to the citizen-facing agent.

#### Scenario: Public tool set includes the dedicated domain capabilities
- **WHEN** the citizen-facing agent is initialized with the public tool registry
- **THEN** the supported lookup and aggregation capabilities for `despesas-por-funcao` are available in the public tool set
- **AND** they remain tagged and documented as part of the public transparency domain

#### Scenario: Explicit function-report questions prefer the dedicated domain over generic neighbors
- **WHEN** the user asks a structured question that clearly targets the `despesas-por-funcao` report or its function-level metrics
- **THEN** the routing and prompt contracts prefer the dedicated `despesas-por-funcao` tool path
- **AND** the answer does not depend solely on adjacent `planejamento` or generic `despesas` capabilities when the domain-specific tools are available

