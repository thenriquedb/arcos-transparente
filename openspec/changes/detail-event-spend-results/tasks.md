## 1. Seleção e orquestração de perguntas de gasto

- [x] 1.1 Ajustar a seleção do chatbot para que perguntas amplas sobre gasto/custo priorizem tools de consulta detalhada do domínio correto, em vez de cair direto em agregação simples.
- [x] 1.2 Garantir que perguntas multi-fonte de gasto consultem todas as fontes estruturadas relevantes, como `licitacoes`, `contratos` e `despesas`, antes de concluir o que existe na base local.
- [x] 1.3 Definir o comportamento para registros indiretos ou acessórios, separando evidência relacionada de gasto consolidado do objeto perguntado.

## 2. Contrato de resposta cidadã

- [x] 2.1 Atualizar o prompt do agente para que perguntas amplas sobre `gastos` retornem lista detalhada por padrão, com totais apenas como apoio.
- [x] 2.2 Tornar obrigatória na resposta a distinção entre valor estimado, valor contratado e valor efetivamente pago/executado quando a resposta cruzar múltiplas fontes.
- [x] 2.3 Refinar o guidance das tools de consulta e agregação de gasto para que agregados não substituam a lista detalhada por padrão.

## 3. Cobertura e validação

- [x] 3.1 Adicionar testes de seleção e prompt cobrindo perguntas de gasto em domínios diferentes, como despesas, diárias, passagens e cenários multi-fonte.
- [x] 3.2 Adicionar testes conversacionais para casos com lista detalhada disponível e para casos em que só existam registros indiretos relacionados ao objeto perguntado.
- [x] 3.3 Validar com a base local que perguntas amplas de gasto não retornam apenas somatório enganoso e deixam clara a diferença entre as fontes quando ela existir.
