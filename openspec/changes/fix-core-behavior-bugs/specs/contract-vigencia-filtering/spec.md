## ADDED Requirements

### Requirement: Contract queries can filter by vigência (date range)
The public contract filter contract MUST expose a way to filter contracts by their vigência interval, not only by start date. The contract filter schema SHALL accept `data_fim` bounds (or an equivalent in-force-on-date filter) in addition to the existing `data_inicio` bounds, so that callers can express "contracts whose validity interval contains a given date".

#### Scenario: Filter schema accepts data_fim bounds
- **WHEN** a contract query is built with a `data_fim` bound (or an in-force-on-date parameter)
- **THEN** the contract filter schema accepts it and applies it to the query
- **AND** the field is exposed publicly, consistent with the underlying contract model that already stores `data_fim`

### Requirement: "Contracts active today" selects in-force contracts
When a citizen asks which contracts are active, current, or in force on a date (`ativos`, `atuais`, `atualmente`, `hoje`), the system MUST select contracts whose vigência interval contains that date — `data_inicio ≤ data` and (`data_fim ≥ data` or `data_fim` is null) — instead of contracts that merely started during the current year.

#### Scenario: Multi-year contract still in force counts as active today
- **WHEN** a contract started in 2024 with end date 2027 is evaluated for "contratos ativos hoje"
- **THEN** it is counted as active today

#### Scenario: Already-finished contract started this year is excluded
- **WHEN** a contract started in January 2026 and ended in March 2026 is evaluated for "contratos ativos hoje" (with today after March 2026)
- **THEN** it is not counted as active today

#### Scenario: Supplier ranking of active contracts uses the in-force population
- **WHEN** a user asks "Qual fornecedor tem mais contratos ativos com a prefeitura hoje?"
- **THEN** the ranking is computed over contracts in force on the current date, not over contracts started in the current year
