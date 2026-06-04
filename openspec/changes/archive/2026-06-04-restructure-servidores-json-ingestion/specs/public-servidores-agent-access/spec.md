## ADDED Requirements

### Requirement: Public `servidores` tools preserve the legacy salary-snapshot contract
The system MUST keep the citizen-facing `consultar_servidores` and `agregar_servidores` capabilities backed by the legacy snapshot dataset after the table `servidores` is repurposed for JSON import.

#### Scenario: Lookup questions still return legacy snapshot fields
- **WHEN** imported legacy snapshot rows in `folha_servidores` match supported lookup filters such as nome, cargo, secretaria, salary range, or mes de referencia
- **THEN** the public lookup capability returns matching records from `folha_servidores`
- **AND** the response keeps the supported public fields such as `nome`, `cargo`, `secretaria`, `salario_base`, and `mes_de_referencia`

#### Scenario: Salary rankings and counts still use the snapshot dataset
- **WHEN** the user asks for totals, counts, rankings, or top salaries over servidores
- **THEN** the public aggregation capability computes the result from the legacy snapshot dataset persisted in `folha_servidores`
- **AND** the answer does not depend on the rebuilt JSON cadastro table for salary-based behavior

### Requirement: Folha history lookup remains usable without canonical servidor joins
The system MUST resolve `buscar_historico_de_pagamentos_do_servidor` candidates and result metadata without depending on `FolhaServidor.servidor_canonico`.

#### Scenario: Ambiguous folha matches still return usable candidate metadata
- **WHEN** more than one `folha_servidores` row matches a nome-based history lookup
- **THEN** the response still returns candidate entries with `folha_servidor_id` plus the supported identifying metadata needed for disambiguation
- **AND** that metadata is built from `folha_servidores` and linked folha payment data rather than a removed canonical `servidores` join

#### Scenario: Direct history lookup still returns folha context after decoupling
- **WHEN** a folha history lookup resolves a valid `folha_servidor_id`
- **THEN** the response still includes the supported folha context, payment timeline, and public identifying fields after the relationship to `servidores` is removed
- **AND** the lookup does not fail merely because no canonical `servidores` row exists
