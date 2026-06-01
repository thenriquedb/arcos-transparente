# Guia Curto Para Novas Regras Do Router

## Objetivo

Este guia existe para ajudar a manter heurísticas de compatibilidade no router
sem transformá-lo novamente na autoridade principal de comportamento do agente.

## Estrutura Atual

- Fachada pública: `agents/router.py`
- Constantes e palavras-chave: `agents/routing/constants.py`
- Normalização e extração: `agents/routing/extractors.py`
- Tipos compartilhados: `agents/routing/models.py`

Regras por domínio:

- `agents/routing/routes/folha_pagamento.py`
- `agents/routing/routes/servidores.py`
- `agents/routing/routes/licitacoes.py`
- `agents/routing/routes/planejamento.py`

## Regra Prática

Antes de criar uma regra nova, decida em qual camada ela pertence:

- Se for guardrail hard-coded de bloqueio, mantenha na camada compartilhada de guardrails
- Se for interpretação conversacional geral, prefira o system prompt e o runtime do chatbot
- Se for regra local de um domínio específico, prefira a descrição/contrato da tool correspondente
- Se for palavra-chave compartilhada ou pattern global, coloque em `constants.py`
- Se for extração de nome, ano, entidade, secretaria ou filtros, coloque em `extractors.py`
- Se for heurística de compatibilidade de um domínio, coloque no arquivo de `routes/` desse domínio
- Se for apenas ordem de precedência entre regras, ajuste `ROUTE_PRIORITY_CHAIN` em `agents/router.py`

## Como Adicionar Uma Nova Regra

1. Identifique o domínio da pergunta.
2. Reaproveite extractors existentes antes de criar novos.
3. Crie ou ajuste uma função `_try_route_*` no módulo do domínio.
4. Faça a função retornar `RouteDecision` quando houver match claro e `None` quando não houver.
5. Posicione a função na `ROUTE_PRIORITY_CHAIN` com cuidado.
6. Adicione testes de roteamento e guardrail.

## Como Não Quebrar A Prioridade

Use esta ordem mental:

- Regras mais específicas vêm antes
- Regras que exigem payload especial vêm antes
- Regras agregadas amplas vêm antes de listas amplas apenas quando isso evita ambiguidade real
- Fallback sempre fica por último

Exemplos:

- Histórico individual deve vir antes de rankings, porque `salario do joao` não pode cair em listagem ampla
- Detalhe de licitação por número deve vencer uma regra genérica de lista
- Perguntas amplas de planejamento e licitações devem continuar separadas por domínio antes do fallback

## Checklist Antes De Subir

- A regra nova está no domínio correto
- Não duplicou lógica que deveria estar em `extractors.py`
- A ordem em `ROUTE_PRIORITY_CHAIN` continua explícita
- Existe teste do caso feliz
- Existe teste de um caso parecido que deve retornar `None`
- Guardrails continuam permitindo apenas perguntas dentro do escopo

## Quando Não Criar Regra Nova

Evite criar regra nova quando o caso puder ser absorvido por:

- uma regra já documentada no prompt ou no contrato da tool
- um filtro extra na tool pública
- um extractor mais genérico
- um alias novo em entidade, secretaria ou objeto

Se a pergunta só varia os parâmetros da mesma capacidade, prefira evoluir filtros e extractors em vez de adicionar mais uma heurística isolada.
