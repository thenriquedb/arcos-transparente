# public-spend-breakdowns Specification

## Purpose
TBD - created by archiving change detail-event-spend-results. Update Purpose after archive.

## Requirements

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

### Requirement: Aggregated totals do not replace detailed evidence when records exist
If the system includes a total in a spend answer, that total MUST remain subordinate to the detailed evidence and MUST NOT be the only substance of the answer when matching detailed records exist.

#### Scenario: Total appears with supporting list
- **WHEN** the system computes or reports a total for a spend question and matching detailed records exist
- **THEN** the response presents the detailed records first or alongside the total in an audit-friendly way
- **AND** the total is identified as a summary rather than the only answer content

### Requirement: Multi-source spend questions consult every relevant spend source
For spend questions whose object spans more than one public-spend source, the system MUST consult each relevant source before concluding what structured evidence exists in the local base.

#### Scenario: Event-like object spans licitações, contratos, and despesas
- **WHEN** the user asks about gastos of an event, service, or object that may appear in licitações, contratos, and despesas
- **THEN** the system considers findings from all relevant structured sources in the response flow
- **AND** it does not rely on only one of those sources when the others may also contain matching records

#### Scenario: One relevant source is empty but another has records
- **WHEN** a multi-source spend question has direct records in one relevant source but none in another
- **THEN** the system reports the source that has matching records
- **AND** it explicitly indicates that the other relevant source did not return direct records for that same query

### Requirement: Spend answers distinguish the meaning of each value source
The system MUST explain in plain language the difference between the value meanings returned by different spend sources whenever those sources are used in the same answer.

#### Scenario: Mixed-source response clarifies value semantics
- **WHEN** a spend answer includes values from licitações, contratos, despesas, diárias, or passagens
- **THEN** the response states what each source represents in practical terms for the citizen
- **AND** it distinguishes estimated procurement value, signed contracted value, and effectively paid or executed value when those meanings differ

### Requirement: Indirect textual mentions do not become the consolidated spend by themselves
The system MUST NOT present indirect, accessory, or preparatory records that merely mention the queried object as if they were, by themselves, the consolidated spend for that object.

#### Scenario: Only indirect related records exist
- **WHEN** the requested spend question has no direct structured records proving the consolidated spend, but does have related records whose text only mentions support activity such as travel, divulgação, reunião, pedágio, diária, or similar preparation
- **THEN** the system may list those records as related evidence
- **AND** it does not assert that their sum is the total spend of the queried object
- **AND** it explains that the local base only shows related records, not enough evidence to confirm the consolidated spend
