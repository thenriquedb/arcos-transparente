# Auditoria de Comportamento Core — Arcos Transparente

> Foco: falhas semânticas e de produto em tool descriptions, docstrings, routing
> hints/examples, system prompt, selection prompts, guardrails e mismatches entre
> "o que o prompt diz", "para que a tool serve", "o que o router faz" e "o que o
> cidadão espera". **Não** cobre arquitetura, estilo, refatoração ou convenções.
>
> Achados ordenados por impacto visível ao usuário.

---

## 1. Verbos de busca genéricos ("pesquise/busque/procure …") são interpretados como consulta de salário individual

**Severidade: Alta** (tool errada + resposta errada)

**Prompts que disparam**
- "Busque os contratos da saúde"
- "Pesquise as licitações abertas"
- "Procure as despesas com educação"
- "Quanto a prefeitura recebe de repasse?" (mesma classe)

**Comportamento incorreto atual**
`_extract_nome_para_historico` (`agents/nlu/extractors.py`) tem o padrão catch‑all
`(?:pesquise|busque|procure|pesquisar|buscar|procurar)\s+(?:por\s+)?([a-z\s]+?)(?:\?|$)`.
Para "busque os contratos da saúde" retorna o falso "nome" `os contratos da saude`.
`_try_route_historico` é o primeiro item de `ROUTE_PRIORITY_CHAIN`, então retorna rota
confiante para `buscar_historico_de_pagamentos_do_servidor`. Na seleção híbrida,
`_select_salary_history_with_router` restringe o conjunto candidato a **apenas** a tool de
folha. O agente busca um servidor chamado "os contratos da saude", não encontra, e responde
que não há servidor — para uma pergunta sobre contratos.

Também corrompe o guardrail de escopo: `_query_establishes_public_context` usa o mesmo
extractor, então entradas fora de domínio "pesquise X" são admitidas e roteadas para folha.

Obs.: o padrão só é evitado quando a query contém um ano de 4 dígitos (a classe `[a-z\s]`
não atravessa dígitos), ou seja, o bug dispara justamente na formulação comum sem ano.

**Por que está errado**
"Pesquisar/buscar/procurar" são verbos agnósticos de domínio, não pistas de salário. O padrão
assume que o objeto do verbo é o nome de uma pessoa.

**Comportamento esperado**
Esses verbos, por si só, não devem gerar rota de histórico de folha. A extração de nome deve
exigir uma pista real de salário/pagamento (salário, recebe, ganha, pagamentos) — já coberta
pelos outros padrões.

**Provável origem:** heurística de seleção (regex do extractor), amplificada pelo contrato
semântico da tool (rota de folha é a primeira da cadeia).

**Direção de correção mínima:** routing heuristic — remover o padrão `pesquise|busque|procure`
de `_extract_nome_para_historico`, ou exigir termo de salário/pagamento concomitante e rejeitar
candidatos que comecem com substantivos de domínio (contrato, licitação, despesa, diária etc.).

**Regressões a adicionar (tests/agents/test_hybrid_selection.py, test_intents.py):**
- "Busque os contratos da saúde" → não roteia para `buscar_historico_de_pagamentos_do_servidor`.
- "Pesquise as licitações abertas" → domínio de licitações, não folha.
- "Salário do João Silva" → ainda roteia para folha (proteção contra overcorreção).

---

## 2. "Contratos ativos hoje" é calculado como "iniciados neste ano", não "em vigência"

**Severidade: Alta** (resposta errada a uma pergunta-semente principal)

**Prompts que disparam**
- "Qual fornecedor tem mais contratos ativos com a prefeitura hoje?"
- "Quais contratos estão ativos atualmente?"

**Comportamento incorreto atual**
Tanto o prompt (`docs/agent-system-prompt.md:58`) quanto `_extract_contratos_active_year_filters`
(`extractors.py:586`) traduzem "ativos/atuais/atualmente/hoje" em `data_inicio` entre
1º jan e 31 dez do ano corrente. A resposta conta apenas contratos **iniciados em 2026**.
O schema público `ContratosFiltroSchema` (`contratos/shared/filters.py`) expõe somente
`data_inicio*` — **não há filtro `data_fim`**, embora `data_fim` exista no modelo
(`ALLOWED_CONTRACT_FIELDS`).

**Por que está errado**
"Contrato ativo/vigente hoje" significa `data_inicio ≤ hoje ≤ data_fim`. Um contrato plurianual
assinado em 2024 e vigente hoje é excluído; um contrato iniciado em jan/2026 mas já encerrado é
contado indevidamente. O ranking por fornecedor fica contra a população errada, e a tool nem
consegue expressar a vigência real.

**Comportamento esperado**
"Ativo hoje" deve selecionar contratos cujo intervalo de vigência contém a data atual
(início ≤ hoje e fim ≥ hoje / fim nulo).

**Provável origem:** contrato semântico da tool (sem filtro `data_fim`) + system prompt
codificando a regra errada + heurística de routing.

**Direção de correção mínima:** tool semantic change — adicionar filtros `data_fim` / vigência
ao `ContratosFiltroSchema`; depois corrigir `_extract_contratos_active_year_filters` e a regra do
prompt para usar o intervalo, não o ano de início.

**Regressões a adicionar:**
- Fixture: contrato iniciado 2024, fim 2027 → contado como ativo "hoje".
- Contrato iniciado jan/2026, encerrado mar/2026 → não contado como ativo "hoje".

---

## 3. "Eventos"/"shows" sozinhos são rejeitados como "genéricos demais", mas "shows e eventos" tem caso especial — roteamento de gasto-com-evento inconsistente

**Severidade: Média** (seleção de tool inconsistente / fallback)

**Prompts que disparam**
- "Quanto foi gasto com eventos em 2025?"
- "Quanto foi gasto com shows em 2025?"
- vs. a semente "Quanto foi gasto com shows e eventos em 2025?" (funciona)

**Comportamento incorreto atual**
`_GENERIC_PUBLIC_OBJECT_TOKENS` (`extractors.py:73`) lista `evento(s)`, `show(s)`,
`festival(is)` como genéricos demais, então `_is_too_generic_public_object` os rejeita — exceto
`"shows e eventos"`, hard-coded para passar, e `"festival"`, que tem fallback próprio. Resultado:
`_extract_licitacoes_objeto` retorna objeto (e `_select_event_spend_query` dispara o fan-out
licitações+contratos+despesas) para "shows e eventos" e "festival", mas retorna `None` para
"eventos"/"shows" no singular/plural isolado, que então caem no seletor model-based genérico sem
orientação de gasto-com-evento.

**Por que está errado**
Um cidadão que pergunta "gasto com eventos" expressa a mesma intenção de "shows e eventos". O
comportamento depende de um match de frase exata arbitrário.

**Comportamento esperado**
"eventos"/"shows"/"evento"/"show" com sinal de gasto devem disparar o mesmo caminho cross-source
(ou uma clarificação consistente), não cair silenciosamente no fallback.

**Provável origem:** heurística de seleção (`_GENERIC_PUBLIC_OBJECT_TOKENS` + caso especial
`"shows e eventos"`).

**Direção de correção mínima:** routing heuristic — dar a `evento(s)`/`show(s)` o mesmo
tratamento de fallback de `festival`, ou removê-los do conjunto de rejeição genérica quando há
sinal de gasto.

**Regressões a adicionar (tests/agents/test_hybrid_selection.py):**
- "Quanto foi gasto com eventos em 2025?" → conjunto candidato inclui `consultar_licitacoes`,
  `consultar_contratos`, `consultar_despesas`.
- Idem para "shows".

---

## 4. "Viagem/viagens" roteia apenas para passagens, contradizendo o hint de diárias

**Severidade: Média** (responde métrica mais estreita que a pretendida)

**Prompts que disparam**
- "Quanto a prefeitura gastou com viagens em 2025?"
- "Gastos com viagens da prefeitura"

**Comportamento incorreto atual**
`consultar_diarias` declara `"viagem"` como hint de routing, mas `DIARIAS_DOMAIN_KEYWORDS` contém
apenas `diaria/diarias/adiantamento de viagem`. `PASSAGENS_DOMAIN_KEYWORDS` é dona de
`viagem/viagens`. Então `_select_direct_spend_candidate_names` (`hybrid_selection.py:556`) checa
passagens e retorna só `["consultar_passagens"]`. O combinado `_select_travel_spend_query` exige
**ambos** os conjuntos de keywords, então "viagens" sozinho nunca chega lá. O "custo de viagem" do
cidadão é respondido só com passagens, omitindo diárias.

**Por que está errado**
"Viagem" é exatamente a palavra que a tool de diárias anuncia, e custo de viagem para o cidadão
normalmente inclui diárias + passagens. O mapa determinístico de keywords contradiz o hint
publicado.

**Comportamento esperado**
Um "gastos com viagens" genérico deve combinar diárias e passagens, ou fazer uma pergunta de
clarificação — não escolher passagens silenciosamente.

**Provável origem:** tool description/hint vs. constants de domínio (mismatch prompt + routing).

**Direção de correção mínima:** prompt + routing — ou remover `"viagem"` do hint de diárias (para
não implicar cobertura) ou tratar "viagem/viagens + gasto" como o caminho combinado
diárias+passagens.

**Regressões a adicionar:**
- "Quanto a prefeitura gastou com viagens em 2025?" → candidatos incluem diárias e passagens (ou
  uma única clarificação), não passagens isolado.

---

## 5. "Total gasto com [função]" colapsa a política de 4 estágios em um único valor pago

**Severidade: Média** (responde silenciosamente um único estágio financeiro)

**Prompts que disparam**
- "Qual o total gasto com saúde em 2025?"
- "Quanto no total foi gasto com educação?"

**Comportamento incorreto atual**
Para gasto amplo por função, a política (`agent-system-prompt.md:52,149`) exige mostrar
`valor_empenhado`, `valor_em_liquidacao`, `valor_liquidado`, `valor_pago`. Mas quando há "total",
`_is_explicit_aggregate_spend_request` faz `_select_broad_spend_query` desistir (retorna None) e o
caminho de tool agregada é preferido. `agregar_despesas_por_funcao` retorna uma **única** métrica,
default `soma_valor_pago` (`despesas_por_funcao.py:176`). O usuário recebe só "pago", com
empenhado/liquidado descartados — exatamente a falha que a semente alerta.

**Por que está errado**
"Total gasto" nesse domínio continua sendo o "gasto" ambíguo que a política manda expandir em
quatro estágios; a presença de "total" não deveria escolher silenciosamente apenas o pago.

**Comportamento esperado**
"gasto/custo" amplo sobre uma função de governo — mesmo com "total" — deve apresentar os quatro
estágios de execução (ou usar `consultar_despesas_por_funcao`), não um único agregado
`valor_pago`.

**Provável origem:** prompt vs. contrato semântico da tool; heurística
(`_is_explicit_aggregate_spend_request` tratando "total" como override) + métrica default do
agregador.

**Direção de correção mínima:** prompt + routing — no domínio despesas-por-função, não deixar
"total" sozinho forçar agregado de estágio único; manter a regra de exibição dos quatro estágios
dominante, ou fazer `agregar_despesas_por_funcao` retornar a soma dos quatro estágios para "gasto"
amplo.

**Regressões a adicionar:**
- "Qual o total gasto com saúde em 2025?" → resposta contém empenhado, em liquidação, liquidado e
  pago (não só pago).

---

## 6. "Festival" vira filtro-objeto a qualquer menção, com default "festival gastronômico 2025"

**Severidade: Baixa** (interpretação ocasionalmente errada)

**Prompts que disparam**
- "Houve licitação para o festival de música em 2024?"
- "Gastos com o festival de inverno"

**Comportamento incorreto atual**
`_extract_public_object_candidate` termina com `if "festival" in normalized_text: return
"festival"`, e a política de ambiguidade do prompt (`agent-system-prompt.md:182,188`) manda assumir
"festival gastronômico de 2025". Para qualquer outro festival, o filtro-objeto degrada para o token
"festival" e a narrativa pode afirmar a interpretação gastronômico/2025.

**Por que está errado**
Faz overfit em um evento. Um festival nomeado diferente, ou um ano explicitado pelo usuário, pode
ser sobrescrito pela suposição default.

**Comportamento esperado**
Preservar a frase específica do festival e o ano informado pelo usuário; só recorrer à suposição
gastronômica para um "festival" cru, sem qualificação.

**Provável origem:** heurística de seleção + exemplo de ambiguidade do system prompt.

**Direção de correção mínima:** prompt + routing — quando "festival" for seguido de palavras
qualificadoras, manter a frase completa como objeto e não sobrescrever o ano informado.

**Regressões a adicionar:**
- "licitação para o festival de música em 2024" → objeto preserva "festival de música" e ano 2024,
  sem override gastronômico/2025.

---

## Casos-semente verificados como CORRETOS (sem defeito)

- **"Liste os 10 maiores contratos de 2025."** → roteia para `consultar_contratos` ordenado por
  `valor` desc (ranking de contratos individuais, não agregação por fornecedor).
- **"Quanto o prefeito recebe?"** → mantido fora do extractor de nome (via
  `REFERENTIAL_NAME_TOKENS`) de propósito, fluindo pelo caminho cargo→nome→pagamento em vez de uma
  busca literal de folha por "prefeito".
