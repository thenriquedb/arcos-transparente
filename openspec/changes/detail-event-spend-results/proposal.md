## Why

Hoje perguntas sobre gastos podem ser respondidas apenas com um somatório agregado, mesmo quando o cidadão precisa enxergar os registros que sustentam esse valor. Em casos mais confusos, a resposta ainda pode misturar conceitos diferentes como valor estimado de licitação, valor contratado, despesa executada, diária ou passagem sem deixar clara a diferença entre essas fontes.

## What Changes

- Fazer com que perguntas sobre gasto/custo priorizem uma resposta detalhada em lista, em vez de retornar apenas um total agregado por padrão.
- Garantir que o agente escolha tools de consulta detalhada para domínios de gasto sempre que a pergunta não pedir explicitamente só total, ranking ou comparação agregada.
- Para perguntas de gasto que cruzem mais de uma fonte, como licitações, contratos e despesas, exigir que a resposta combine as fontes relevantes e explique o papel de cada uma.
- Exigir que a resposta explique em linguagem simples a diferença entre valor estimado de licitação, valor contratado, despesa paga/executada e outros registros de gasto quando aplicável.
- Evitar que registros textuais indiretos, acessórios ou preparatórios sejam apresentados sozinhos como se fossem o gasto consolidado do objeto perguntado.
- Adicionar cobertura de comportamento para perguntas de gasto em múltiplos domínios, incluindo despesas gerais, diárias, passagens e cenários de evento/objeto com fontes mistas.

## Capabilities

### New Capabilities
- `public-spend-breakdowns`: Responde perguntas sobre gasto com uma lista auditável de registros relevantes por domínio e por fonte, diferenciando claramente o papel e o significado de licitações, contratos, despesas e outros registros de execução.

### Modified Capabilities
- None.

## Impact

- Affected code: `agents/chatbot/*`, `agents/tools/sql_tools/despesas/*`, `agents/tools/sql_tools/diarias/*`, `agents/tools/sql_tools/passagens/*`, `agents/tools/sql_tools/licitacoes/*`, `agents/tools/sql_tools/contratos/*`, `agents/tools/registry.py` e testes do chatbot/seleção.
- Affected behavior: perguntas sobre gastos deixam de favorecer apenas somatórios e passam a apresentar listas detalhadas por padrão, com totais apenas como apoio e com distinção explícita entre os tipos de valor.
- Affected contracts: instruções do prompt do agente, heurísticas/seleção de tools para perguntas de gasto e contratos de resposta esperados para consultas auditáveis em múltiplos domínios.
- Risk areas: ainda confundir quando uma pergunta quer total agregado versus lista detalhada, cruzar fontes erradas em perguntas mistas, ou produzir respostas extensas demais sem priorizar os registros mais úteis.
