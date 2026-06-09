## MODIFIED Requirements

### Requirement: Broad spend questions return a detailed breakdown by default
When a citizen asks about gasto, gastos, custo, custou, or valor gasto in a supported public-spend domain, the system MUST return a detailed, auditable breakdown instead of only a single aggregated total by default. For broad spend over a government function (despesas por função), the presence of the word "total" MUST NOT collapse the answer into a single execution-stage value; the four execution stages — `valor_empenhado`, `valor_em_liquidacao`, `valor_liquidado`, and `valor_pago` — MUST all be presented.

#### Scenario: Spend question in a direct spend domain returns detailed records
- **WHEN** the user asks about gastos in a domain that already has individual public records, such as despesas, diárias, or passagens
- **THEN** the system returns a detailed list of matching records from that domain
- **AND** it does not collapse the answer into only one aggregated number when detailed records are available

#### Scenario: "total gasto com [função]" presents all four execution stages
- **WHEN** the user asks a broad function-spend question such as "Qual o total gasto com saúde em 2025?"
- **THEN** the answer presents `valor_empenhado`, `valor_em_liquidacao`, `valor_liquidado`, and `valor_pago`
- **AND** the presence of "total" does not silently reduce the answer to `valor_pago` alone
