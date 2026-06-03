## Context

O projeto já consegue consultar `licitacoes`, `contratos`, `despesas`, `diarias` e `passagens`, mas perguntas sobre gastos ainda podem cair em um caminho ruim: o agente trata a pergunta como um pedido de total e responde só com um somatório, mesmo quando o cidadão precisa enxergar os registros que sustentam esse valor. Em casos piores, a resposta pode misturar fontes diferentes sem explicar se o número veio de valor estimado, valor contratado, despesa paga ou documento acessório.

Esse problema é cross-cutting porque depende de mais de uma camada:

- seleção das tools candidatas para perguntas de custo/gasto em diferentes domínios;
- instruções do agente para decidir entre lista detalhada e agregação simples;
- interpretação das tools de gasto quando o texto ou o objeto da pergunta apontam para relação direta ou indireta com o gasto;
- formato final da resposta cidadã, que precisa diferenciar licitação, contrato, despesa paga e demais registros executados.

O sistema já tem as fontes estruturadas necessárias para responder melhor, então o foco desta mudança não é criar novos domínios ou novos modelos SQL, e sim reorganizar a prioridade e a apresentação das fontes existentes para perguntas auditáveis sobre gastos em geral. O caso do festival gastronômico continua sendo um motivador importante, mas agora entra como exemplo de uma regra mais ampla.

## Goals / Non-Goals

**Goals:**
- Fazer perguntas de gasto/custo priorizarem listas detalhadas e auditáveis por padrão.
- Garantir que o agente prefira tools de consulta/lista para domínios de gasto quando a pergunta não pedir explicitamente só agregação.
- Usar combinações multi-fonte quando a pergunta exigir mais de um domínio de gasto, como licitações, contratos e despesas.
- Padronizar respostas que expliquem a diferença entre valor estimado, valor contratado e valor efetivamente pago/executado.
- Cobrir com testes perguntas de gasto em domínios diferentes e cenários mistos com fontes diretas e indiretas.

**Non-Goals:**
- Criar novas tabelas, migrations ou pipelines de ingestão para gastos.
- Construir um domínio SQL novo e dedicado para perguntas gerais de gasto.
- Resolver automaticamente toda e qualquer deduplicação entre contrato, licitação e despesa quando a origem pública não permitir vínculo explícito.
- Substituir perguntas agregadas legítimas quando o usuário pedir explicitamente apenas um total e não uma lista.

## Decisions

### 1. Tratar perguntas amplas de gasto como fluxo orientado a evidência detalhada

Perguntas como `quais foram os gastos com diárias em 2025`, `quais os gastos com passagens`, `quanto a prefeitura gastou com o festival gastronômico` ou `quais foram os gastos da saúde` devem seguir um fluxo deliberado:

1. identificar o domínio principal de gasto;
2. preferir tools de consulta/lista daquele domínio;
3. complementar com outras fontes apenas quando a pergunta exigir ou quando o domínio for inerentemente multi-fonte;
4. montar uma resposta final que apresente os registros encontrados antes de qualquer resumo agregado.

Rationale:
- O cidadão quer rastreabilidade, não apenas um número.
- O valor “certo” depende do que a base realmente oferece: lista de documentos, valor estimado, contratado ou pago.
- Esse fluxo reduz a chance de o agente pular direto para agregação quando a pergunta ainda pede evidência detalhada.

Alternatives considered:
- Continuar tratando perguntas de gasto como agregação simples por padrão: rejeitado porque esconde os registros que fundamentam a resposta.
- Criar uma regra única baseada só em `despesas`: rejeitado porque diferentes perguntas de gasto pertencem a domínios distintos, como diárias, passagens, contratos ou licitações.

### 2. Preferir lista detalhada por padrão quando a pergunta usar linguagem ampla de “gastos”

Quando a pergunta usa linguagem ampla como `gastos`, `custou`, `valor gasto` ou `quanto a prefeitura gastou`, a resposta padrão deve listar os registros relevantes antes de resumir totais. Totais podem aparecer como apoio, mas não devem substituir a lista auditável.

Rationale:
- A formulação em plural sugere interesse nos itens que compõem o gasto.
- Uma lista evita a falsa precisão de um número único construído a partir de fontes heterogêneas.
- Isso melhora auditabilidade e facilita follow-ups naturais do cidadão.

Alternatives considered:
- Sempre responder só com total e abrir lista apenas sob pedido adicional: rejeitado porque perpetua exatamente o problema reportado.
- Sempre responder só com lista e nunca com resumo: rejeitado porque o resumo continua útil, desde que não esconda os registros.

### 3. Tratar perguntas multi-fonte de gasto como composição explícita de domínios

Algumas perguntas de gasto exigem mais de um domínio ao mesmo tempo, especialmente quando o objeto pedido atravessa o ciclo de compra pública. Nesses casos, a resposta deve compor fontes diferentes de forma explícita, como:

- `licitacao` + `contrato` + `despesa` para evento, serviço ou objeto contratual;
- lookup detalhado do domínio específico para diárias ou passagens;
- outras combinações apenas quando houver justificativa clara no texto da pergunta.

Rationale:
- Nem toda pergunta de gasto é apenas uma pergunta de despesa executada.
- O cidadão precisa enxergar quando a resposta combina estágios diferentes do gasto.

Alternatives considered:
- Resolver tudo em uma única tool genérica de gasto: rejeitado porque apagaria as fronteiras úteis entre os domínios já existentes.

### 4. Classificar despesas textuais indiretas como evidência complementar, não como custo consolidado

As tools de `despesas` continuam úteis, mas a orquestração deve tratar despesas encontradas por texto em dois grupos:

- diretas: quando a descrição do documento claramente representa o gasto perguntado;
- indiretas/preparatórias: quando a descrição apenas menciona viagem, reunião, divulgação, diária, pedágio, ECAD ou outro apoio relacionado ao objeto da pergunta.

Se só houver despesas indiretas, a resposta não deve afirmar que aquilo é o gasto consolidado do objeto perguntado; deve dizer que são documentos relacionados ao tema, mas insuficientes para comprovar o custo consolidado.

Rationale:
- O banco atual já mostra esse caso em `2026`, com documentos ligados à preparação/divulgação do festival.
- A distinção é fundamental para evitar respostas enganosas sem exigir nova modelagem de banco.

Alternatives considered:
- Criar regra SQL rígida para excluir todas as despesas indiretas: rejeitado porque alguns cenários reais podem precisar delas como evidência complementar.
- Somar todas as despesas com menção textual: rejeitado porque produz total enganoso.

### 5. Tornar a diferença entre licitação, contrato, despesa e outros registros parte obrigatória da resposta

O formato da resposta deve sempre deixar claro:

- `licitação`: processo de compra, normalmente com valor estimado;
- `contrato`: instrumento assinado, com valor contratado;
- `despesa paga/executada`: valor efetivamente pago ou executado, quando disponível.
- `diária` ou `passagem`: registros específicos de deslocamento quando esse for o domínio perguntado.

Rationale:
- O cidadão não é obrigado a conhecer a diferença entre essas estruturas.
- A mesma pergunta pode tocar em três estágios diferentes do gasto público.
- Essa explicação reduz leituras equivocadas quando os números divergem entre as fontes.

Alternatives considered:
- Deixar a distinção implícita nos nomes dos campos: rejeitado porque isso não basta para o público geral.

### 6. Resolver a mudança no nível de seleção e prompt antes de considerar mudanças mais profundas nas tools

Esta mudança deve priorizar:

- seleção híbrida que prefira tools de consulta detalhada para perguntas amplas de gasto;
- instruções do prompt que obriguem a resposta auditável e a distinção entre fontes e significados;
- testes que fixem o comportamento esperado.

Só se isso não for suficiente devemos evoluir contracts mais profundos das tools.

Rationale:
- O bug principal é de orquestração e resposta, não de ausência das fontes.
- Isso mantém o escopo menor e reduz risco de mexer desnecessariamente nos domínios SQL já existentes.

Alternatives considered:
- Criar uma tool nova dedicada a gasto geral: rejeitado para esta etapa porque adiciona superfície pública antes de esgotar a combinação das tools atuais.

## Risks / Trade-offs

- [Risk] Respostas podem ficar longas demais ao listar registros detalhados em vários domínios de gasto. -> Mitigation: priorizar uma lista curta com campos essenciais e resumo por fonte, preservando a auditabilidade.
- [Risk] O agente ainda pode interpretar como gasto principal um registro só indiretamente relacionado ao tema. -> Mitigation: documentar a distinção entre evidência direta e indireta no prompt e cobrir cenários negativos em testes.
- [Risk] A preferência por lista detalhada pode conflitar com pedidos que realmente queriam só um total. -> Mitigation: manter o total como apoio quando útil e respeitar pedidos explicitamente agregados.
- [Risk] A ampliação de escopo pode deixar a heurística de seleção vaga demais. -> Mitigation: cobrir perguntas representativas por domínio de gasto, não apenas por evento.

## Migration Plan

1. Atualizar o prompt do agente para perguntas amplas de gasto, exigindo lista detalhada por padrão e explicação das diferenças entre fontes.
2. Ajustar a seleção híbrida para priorizar o conjunto correto de tools candidatas por domínio de gasto.
3. Refinar o guidance das tools de consulta e agregação de gasto para que agregados não substituam a lista detalhada por padrão.
4. Adicionar testes de seleção, prompt e fluxo conversacional para perguntas de gasto em domínios diferentes, incluindo casos multi-fonte.
5. Validar o comportamento com a base local em cenários com gastos diretos e indiretos.

Rollback strategy:
- Reverter a heurística específica de seleção e o guidance do prompt, voltando ao comportamento anterior de escolha mais ampla ou agregada.

## Open Questions

- Quando o usuário pedir explicitamente `qual foi o total gasto`, a resposta deve sempre incluir a lista detalhada completa ou basta resumir os registros principais e oferecer expansão?
- Há campos mínimos obrigatórios por domínio de gasto para a lista cidadã, como número, data, descrição e valor, ou isso pode variar por tipo de registro?
