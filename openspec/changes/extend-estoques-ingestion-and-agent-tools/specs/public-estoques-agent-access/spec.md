## ADDED Requirements

### Requirement: Public `estoques` tools expose imported material-balance records from SQL
The system MUST expose imported `estoques` material summaries through dedicated public SQL tools for lookup and aggregation, using the persisted stock-material table as the source of truth for saldo, entradas and saidas.

#### Scenario: Lookup tool returns material balances with supported filters
- **WHEN** imported `estoques` material records in the local SQL database match supported lookup filters such as origin, year, material description, unit of measure, report period, or supported summary value ranges
- **THEN** the public lookup capability returns the matching material-balance records from SQL
- **AND** the response includes only the supported source-backed summary fields exposed by the public contract

#### Scenario: Aggregation tool summarizes imported stock balances
- **WHEN** imported `estoques` material records in the local SQL database match an aggregation query for totals, counts, or rankings
- **THEN** the public aggregation capability computes the requested result from the persisted SQL data
- **AND** the result uses supported summary metrics such as `entrada_valor`, `saida_valor`, `saldo_quantidade`, or `saldo_valor`

### Requirement: Public `estoques` movement lookup exposes imported daily movement history from SQL
The system MUST expose imported daily stock movements through a dedicated public lookup capability, rather than forcing users to infer movement history only from summarized material balances.

#### Scenario: Movement lookup returns imported daily movements with supported filters
- **WHEN** imported `estoques` movement records in the local SQL database match supported filters such as material, date range, movement type, unidade gestora, almoxarifado, localizacao, or classificacao
- **THEN** the public movement capability returns the matching daily movement rows from SQL
- **AND** each result remains limited to the supported source-backed movement fields exposed by the public contract

### Requirement: The citizen-facing agent uses the dedicated `estoques` tool path for structured stock questions
The chatbot MUST treat structured questions about municipal stock, warehouse balances, or stock movement history as an in-scope SQL transparency domain and answer them through the dedicated public `estoques` tools.

#### Scenario: User asks for material balances or stock availability
- **WHEN** a user asks for saldo, entradas, saidas, disponibilidade ou ranking de materiais em estoque
- **THEN** the agent keeps the request inside the supported public-data scope
- **AND** it answers through the dedicated `estoques` lookup or aggregation capability instead of generic free-form reasoning

#### Scenario: User asks for stock movement history
- **WHEN** a user asks for requisicoes, compras, aplicacoes imediatas ou outras movimentacoes de um material ou almoxarifado
- **THEN** the agent keeps the request inside the supported public-data scope
- **AND** it answers through the dedicated `estoques` movement capability as the SQL source of truth

### Requirement: Dedicated `estoques` tools remain auditable within the public tool registry
The public tool registry, routing layer, and prompt contracts MUST keep the supported `estoques` tools discoverable to the citizen-facing agent so structured stock answers come from local SQL data.

#### Scenario: Public tool set includes the dedicated `estoques` capabilities
- **WHEN** the citizen-facing agent is initialized with the public tool registry
- **THEN** the supported `estoques` lookup, aggregation, and movement capabilities are available in the public tool set
- **AND** they remain tagged and documented as part of the public transparency domain

#### Scenario: Explicit stock questions prefer dedicated tools over adjacent domains
- **WHEN** the user asks a structured question that clearly targets `estoques`, `almoxarifado`, `saldo de material`, or `movimentacao de estoque`
- **THEN** the routing and prompt contracts prefer the dedicated `estoques` tool path
- **AND** the answer does not depend solely on adjacent `patrimonios`, `despesas`, or procurement-domain capabilities when the domain-specific tools are available
