## 1. Generic search verbs no longer route to payroll (finding 1)

- [x] 1.1 Remove the `pesquise|busque|procure` catch-all pattern from `_extract_nome_para_historico` in `agents/routing/extractors.py`, or require a concomitant salary/payment term and reject candidates beginning with domain nouns (contrato, licitação, despesa, diária)
- [x] 1.2 Confirm `_query_establishes_public_context` no longer admits out-of-domain "pesquise X" phrases via the shared extractor
- [x] 1.3 Add regressions in `tests/agents/test_router.py` / `test_hybrid_selection.py`: "Busque os contratos da saúde" and "Pesquise as licitações abertas" do not route to `buscar_historico_de_pagamentos_do_servidor`; "Salário do João Silva" still does

## 2. Contract vigência filtering (finding 2)

- [x] 2.1 Add `data_fim` bounds (or an in-force-on-date parameter) to `ContratosFiltroSchema` in `contracts/shared/filters.py`, exposing the already-allowed `data_fim` field
- [x] 2.2 Update `_extract_contratos_active_year_filters` in `agents/routing/extractors.py` to map "ativos/atuais/atualmente/hoje" to `data_inicio ≤ hoje` AND (`data_fim ≥ hoje` OR `data_fim` null)
- [x] 2.3 Update the "ativos hoje" rule in `docs/agent-system-prompt.md` (around line 58) to use the vigência interval, not start-year
- [x] 2.4 Add fixtures/regressions: contract 2024→2027 counts as active today; contract Jan 2026→Mar 2026 does not; supplier ranking uses the in-force population

## 3. Event/show spend cross-source routing (finding 3)

- [x] 3.1 Give `evento(s)`/`show(s)` the same fallback as `festival` in `_GENERIC_PUBLIC_OBJECT_TOKENS` handling (or exempt them from generic rejection when a spend signal is present) so `_extract_licitacoes_objeto` returns an object
- [x] 3.2 Remove the hard-coded `"shows e eventos"` special case once the general path covers it
- [x] 3.3 Add regressions in `tests/agents/test_hybrid_selection.py`: "gasto com eventos" and "gasto com shows" candidate set includes `consultar_licitacoes`, `consultar_contratos`, `consultar_despesas`

## 4. Travel spend combines diárias + passagens (finding 4)

- [x] 4.1 Make `viagem/viagens + gasto` recognized so `_select_travel_spend_query` does not require both keyword sets independently; align with the `consultar_diarias` "viagem" hint
- [x] 4.2 Add regression: "Quanto a prefeitura gastou com viagens em 2025?" returns both diárias and passagens candidates (or a single clarification), not passagens alone

## 5. Function-spend totals keep four stages (finding 5)

- [x] 5.1 In the despesas-por-função domain, stop a lone "total" from making `_is_explicit_aggregate_spend_request` force the single-metric aggregate (keep `_select_broad_spend_query` engaged, or sum the four stages)
- [x] 5.2 Update the four-stage display rule in `docs/agent-system-prompt.md` (around lines 52, 149) so "total" does not override it
- [x] 5.3 Add regression: "Qual o total gasto com saúde em 2025?" response contains empenhado, em liquidação, liquidado and pago

## 6. Named festival preservation (finding 6)

- [x] 6.1 In `_extract_public_object_candidate`, preserve the full festival phrase and user-supplied year when "festival" is qualified; only bare "festival" falls back to the gastronômico/2025 default
- [x] 6.2 Update the festival ambiguity rule in `docs/agent-system-prompt.md` (around lines 182, 188) to scope the default to unqualified "festival"
- [x] 6.3 Add regression: "licitação para o festival de música em 2024" preserves "festival de música" and year 2024 with no gastronômico/2025 override

## 7. Verification

- [x] 7.1 Run the full agent/router test suite and confirm all new regressions pass and no seed-question behavior regresses
- [x] 7.2 Spot-check the verified-correct seed cases ("Liste os 10 maiores contratos de 2025", "Quanto o prefeito recebe?") still behave correctly
