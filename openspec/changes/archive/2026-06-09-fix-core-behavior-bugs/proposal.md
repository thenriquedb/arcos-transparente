## Why

The behavior audit (`docs/auditoria-comportamento-core.md`) found six semantic/product defects where what the citizen asks, what the prompt says, what the tool means, and what the router does disagree. Several produce visibly wrong answers to seed questions (a contracts question answered as "no such employee", contract "active today" computed as "started this year", broad spend collapsed to a single paid value). These erode trust in a transparency assistant, so they are worth fixing before adding new capabilities.

## What Changes

- **Generic search verbs stop routing to salary history.** "Busque os contratos da saúde" / "Pesquise as licitações abertas" no longer extract a false employee name and lock selection onto the payroll history tool. Name extraction requires a real salary/payment cue.
- **"Contracts active today" means in-force, not started-this-year.** Contract queries gain a vigência (date-range) filter so "ativos hoje" selects `data_inicio ≤ hoje ≤ data_fim`, including multi-year contracts and excluding already-finished ones.
- **Event/show spend routes consistently.** "gasto com eventos" / "gasto com shows" trigger the same cross-source (licitações + contratos + despesas) path as "shows e eventos", instead of falling silently into the generic selector.
- **Generic "viagens" spend covers diárias + passagens.** A bare "gastos com viagens" no longer answers with passagens only while diárias (which advertises "viagem" as a hint) are dropped.
- **Broad "total gasto com [função]" keeps the four-stage breakdown.** The presence of "total" no longer silently collapses execution stages to a single `valor_pago`; empenhado / em liquidação / liquidado / pago are all presented.
- **Named festivals are preserved.** "festival de música em 2024" keeps the specific phrase and the user-supplied year instead of being overwritten by the default "festival gastronômico de 2025" assumption.

## Capabilities

### New Capabilities
- `contract-vigencia-filtering`: Citizen queries about contracts that are active/in-force on a given date are answered by date-range (vigência) filtering on the contract tool, not by start-year filtering.

### Modified Capabilities
- `hybrid-tool-selection`: Candidate narrowing changes for generic search verbs (no forced payroll route), event/show spend (cross-source path), travel spend (diárias + passagens), and named-festival object preservation.
- `public-spend-breakdowns`: Broad spend over a government function returns the four execution stages even when the query says "total", instead of a single aggregated paid value.

## Impact

- **Routing / extraction:** `agents/routing/extractors.py` (`_extract_nome_para_historico`, `_extract_contratos_active_year_filters`, `_GENERIC_PUBLIC_OBJECT_TOKENS`, `_extract_licitacoes_objeto`, `_extract_public_object_candidate`, `_query_establishes_public_context`).
- **Hybrid selection:** `agents/routing/hybrid_selection.py` (`_select_salary_history_with_router`, `_select_event_spend_query`, `_select_travel_spend_query`, `_select_direct_spend_candidate_names`, `_select_broad_spend_query`, `_is_explicit_aggregate_spend_request`).
- **Tool contracts / schemas:** `contracts/shared/filters.py` (`ContratosFiltroSchema` — add `data_fim` / vigência filter); `despesas_por_funcao.py` aggregation default.
- **System prompt:** `docs/agent-system-prompt.md` rules for "ativos hoje", four-stage spend, and festival ambiguity.
- **Tests:** `tests/agents/test_router.py`, `tests/agents/test_hybrid_selection.py`, plus contract vigência fixtures.
