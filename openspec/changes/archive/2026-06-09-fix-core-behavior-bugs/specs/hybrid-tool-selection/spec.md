## ADDED Requirements

### Requirement: Generic search verbs do not force a payroll-history route
Generic, domain-agnostic search verbs (`pesquisar`, `buscar`, `procurar` and their inflections) MUST NOT, on their own, cause the system to extract a person name or route the query to the employee payroll-history tool. Name extraction for payroll history MUST require a real salary or payment cue (such as `salário`, `recebe`, `ganha`, `pagamentos`).

#### Scenario: Search verb over a public-object domain does not route to payroll
- **WHEN** a user submits a query such as "Busque os contratos da saúde" or "Pesquise as licitações abertas"
- **THEN** the system does not extract a person name from the verb object
- **AND** the query is not routed to the employee payroll-history tool

#### Scenario: Explicit salary cue still routes to payroll
- **WHEN** a user submits a query with a genuine salary or payment cue, such as "Salário do João Silva"
- **THEN** the system still extracts the person name and routes to the employee payroll-history tool

#### Scenario: Out-of-scope search phrase is not admitted as public context
- **WHEN** an out-of-domain "pesquise X" phrase is submitted
- **THEN** the generic search verb alone does not establish public-data context that admits the query into payroll routing

### Requirement: Event and show spend questions use the cross-source path consistently
Spend questions about events or shows MUST trigger the same cross-source candidate path (licitações, contratos, despesas) regardless of whether the public object is phrased as `evento(s)`, `show(s)`, or the compound `shows e eventos`. The system MUST NOT silently drop a singular `evento`/`show` into the generic selector while treating `shows e eventos` specially.

#### Scenario: "gasto com eventos" returns the cross-source candidate set
- **WHEN** a user asks "Quanto foi gasto com eventos em 2025?"
- **THEN** the candidate tool set includes `consultar_licitacoes`, `consultar_contratos`, and `consultar_despesas`

#### Scenario: "gasto com shows" returns the cross-source candidate set
- **WHEN** a user asks "Quanto foi gasto com shows em 2025?"
- **THEN** the candidate tool set includes `consultar_licitacoes`, `consultar_contratos`, and `consultar_despesas`

### Requirement: Generic travel spend combines diárias and passagens
A generic travel-spend question (for example "gastos com viagens") MUST consider both the diárias and passagens domains, or ask a single clarification, rather than silently answering with passagens alone. The deterministic keyword mapping MUST NOT contradict the published `consultar_diarias` routing hint that advertises "viagem".

#### Scenario: Bare "viagens" spend includes both travel domains
- **WHEN** a user asks "Quanto a prefeitura gastou com viagens em 2025?"
- **THEN** the candidate set includes both the diárias and passagens tools (or the system asks a single clarification)
- **AND** it does not return passagens as the only candidate

### Requirement: Named festivals preserve their phrase and user-supplied year
When the word "festival" is qualified by additional words or accompanied by a user-supplied year, the system MUST preserve the specific festival phrase and that year as the public-object filter. The default "festival gastronômico de 2025" assumption MUST apply only to a bare, unqualified "festival".

#### Scenario: Qualified festival keeps its phrase and year
- **WHEN** a user asks "Houve licitação para o festival de música em 2024?"
- **THEN** the public object preserves "festival de música" and the year 2024
- **AND** the system does not override it with the gastronômico/2025 default

#### Scenario: Bare festival falls back to the documented assumption
- **WHEN** a user asks about a bare, unqualified "festival" with no year
- **THEN** the system may apply the documented "festival gastronômico de 2025" assumption
