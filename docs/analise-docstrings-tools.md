# Analise das docstrings das tools

Escopo analisado: as 17 tools publicas expostas ao LLM via `get_public_tools()`.
Ficaram de fora helpers internos, schemas e utilitarios que nao sao chamaveis pelo agente.

Notas de 1 a 5:
- `5`: muito bom
- `4`: bom, com pequenas lacunas
- `3`: funcional, mas incompleto
- `2`: fraco
- `1`: insuficiente

Observacao importante: as notas abaixo refletem o estado encontrado antes da reescrita. As docstrings novas ja foram aplicadas nos arquivos apontados em cada secao.

## Resumo

| Tool | Proposito | Delimitacao | Args | Returns | Confusao |
| --- | ---: | ---: | ---: | ---: | ---: |
| `consultar_servidores` | 4 | 2 | 1 | 1 | 2 |
| `agregar_servidores` | 4 | 2 | 1 | 1 | 2 |
| `buscar_historico_de_pagamentos_do_servidor` | 5 | 5 | 4 | 4 | 4 |
| `consultar_contratos` | 4 | 2 | 1 | 1 | 2 |
| `agregar_contratos` | 4 | 2 | 1 | 1 | 2 |
| `consultar_licitacoes` | 4 | 2 | 2 | 2 | 2 |
| `agregar_licitacoes` | 4 | 2 | 1 | 1 | 2 |
| `consultar_planejamento` | 3 | 1 | 2 | 1 | 1 |
| `agregar_planejamento` | 3 | 1 | 2 | 1 | 1 |
| `consultar_receitas` | 3 | 1 | 2 | 1 | 1 |
| `agregar_receitas` | 3 | 1 | 2 | 1 | 1 |
| `consultar_despesas` | 4 | 1 | 1 | 1 | 2 |
| `agregar_despesas` | 4 | 1 | 1 | 1 | 2 |
| `consultar_patrimonios` | 4 | 1 | 1 | 1 | 3 |
| `agregar_patrimonios` | 4 | 1 | 1 | 1 | 3 |
| `consultar_quadro_pessoal` | 2 | 1 | 1 | 1 | 1 |
| `agregar_quadro_pessoal` | 2 | 1 | 1 | 1 | 1 |

## Por tool

### `consultar_servidores`
Arquivo: [consultar_servidores_query.py](/Users/thiagohenriquedominguesbotelho/Documents/code/ai/arcos-transparente/agents/tools/sql_tools/servidores/consultar_servidores_query.py:41)

Notas: proposito `4`, delimitacao `2`, args `1`, returns `1`, confusao `2`

Problemas concretos encontrados:
- A docstring antiga dizia que era para "consultas", mas nao separava bem de `agregar_servidores`.
- Nao explicava a diferenca para `buscar_historico_de_pagamentos_do_servidor`.
- Nao listava os filtros aceitos nem o formato de `mes_de_referencia`.
- Nao descrevia `metadata.mes_de_referencia_considerado`, que muda o comportamento real da tool.

Docstring reescrita: aplicada no arquivo acima.

### `agregar_servidores`
Arquivo: [agregar_servidores_query.py](/Users/thiagohenriquedominguesbotelho/Documents/code/ai/arcos-transparente/agents/tools/sql_tools/servidores/agregar_servidores_query.py:45)

Notas: proposito `4`, delimitacao `2`, args `1`, returns `1`, confusao `2`

Problemas concretos encontrados:
- A docstring antiga indicava "totais e rankings", mas nao dizia explicitamente para nao listar pessoas por ela.
- Nao listava `agrupar_por`, `metrica`, `ordenar_por` e valores aceitos.
- Nao explicava o retorno em dois modos: com grupo e sem grupo.
- Nao ajudava a evitar troca com `consultar_servidores`.

Docstring reescrita: aplicada no arquivo acima.

### `buscar_historico_de_pagamentos_do_servidor`
Arquivo: [buscar_historico_de_pagamentos_do_servidor_query.py](/Users/thiagohenriquedominguesbotelho/Documents/code/ai/arcos-transparente/agents/tools/sql_tools/folha_pagamento/buscar_historico_de_pagamentos_do_servidor_query.py:25)

Notas: proposito `5`, delimitacao `5`, args `4`, returns `4`, confusao `4`

Problemas concretos encontrados:
- Ja era a melhor docstring do conjunto.
- O retorno estava descrito de forma resumida, sem nomear os campos principais.
- Nao diferenciava com tanta clareza do quadro de pessoal.

Docstring reescrita: aplicada no arquivo acima.

### `consultar_contratos`
Arquivo: [consultar_contratos_query.py](/Users/thiagohenriquedominguesbotelho/Documents/code/ai/arcos-transparente/agents/tools/sql_tools/contratos/consultar_contratos_query.py:246)

Notas: proposito `4`, delimitacao `2`, args `1`, returns `1`, confusao `2`

Problemas concretos encontrados:
- A docstring antiga nao separava bem contrato assinado de licitacao.
- Nao explicava `incluir_detalhes`.
- Nao listava os filtros aceitos, datas e faixa de valor.
- Nao descrevia o papel de `metadata.filtros_fallback_aplicados`.

Docstring reescrita: aplicada no arquivo acima.

### `agregar_contratos`
Arquivo: [agregar_contratos_query.py](/Users/thiagohenriquedominguesbotelho/Documents/code/ai/arcos-transparente/agents/tools/sql_tools/contratos/agregar_contratos_query.py:168)

Notas: proposito `4`, delimitacao `2`, args `1`, returns `1`, confusao `2`

Problemas concretos encontrados:
- A docstring antiga indicava bons exemplos, mas nao delimitava contra `consultar_contratos` e `agregar_licitacoes`.
- Nao listava `metrica`, `agrupar_por` e regras de `ordenar_por`.
- Nao explicava quando sai `valor_total` e quando sai `resultados`.

Docstring reescrita: aplicada no arquivo acima.

### `consultar_licitacoes`
Arquivo: [consultar_licitacoes_query.py](/Users/thiagohenriquedominguesbotelho/Documents/code/ai/arcos-transparente/agents/tools/sql_tools/licitacoes/consultar_licitacoes_query.py:44)

Notas: proposito `4`, delimitacao `2`, args `2`, returns `2`, confusao `2`

Problemas concretos encontrados:
- A docstring antiga era melhor que a media, mas ainda nao separava licitacao de contrato com nitidez suficiente.
- Nao listava filtros aceitos nem limites de `max_vencedores`, `max_instrumentos` e `max_itens`.
- So citava `valor_total_estimado`, sem explicar o restante do retorno.

Docstring reescrita: aplicada no arquivo acima.

### `agregar_licitacoes`
Arquivo: [agregar_licitacoes_query.py](/Users/thiagohenriquedominguesbotelho/Documents/code/ai/arcos-transparente/agents/tools/sql_tools/licitacoes/agregar_licitacoes_query.py:63)

Notas: proposito `4`, delimitacao `2`, args `1`, returns `1`, confusao `2`

Problemas concretos encontrados:
- A docstring antiga era clara no objetivo, mas nao dizia quando nao usar.
- Nao separava `valor estimado em licitacao` de `valor contratado`.
- Nao listava `metrica`, `agrupar_por` e o shape do retorno.

Docstring reescrita: aplicada no arquivo acima.

### `consultar_planejamento`
Arquivo: [consultar_planejamento_query.py](/Users/thiagohenriquedominguesbotelho/Documents/code/ai/arcos-transparente/agents/tools/sql_tools/planejamento/consultar_planejamento_query.py:30)

Notas: proposito `3`, delimitacao `1`, args `2`, returns `1`, confusao `1`

Problemas concretos encontrados:
- "Planejamento orcamentario" e uma expressao tecnica; a docstring antiga nao traduzia isso para linguagem de uso.
- A frase "valor pago" conflita com `despesas`, mas a docstring nao trazia linha de nao uso.
- O default silencioso de `origem='saude'` e importante e estava pouco contextualizado.
- Nao listava filtros aceitos, meses por nome/numero e campos de saida.

Docstring reescrita: aplicada no arquivo acima.

### `agregar_planejamento`
Arquivo: [agregar_planejamento_query.py](/Users/thiagohenriquedominguesbotelho/Documents/code/ai/arcos-transparente/agents/tools/sql_tools/planejamento/agregar_planejamento_query.py:31)

Notas: proposito `3`, delimitacao `1`, args `2`, returns `1`, confusao `1`

Problemas concretos encontrados:
- Mesma ambiguidade central de `consultar_planejamento`: "valor pago" pode levar o LLM a confundir com `agregar_despesas`.
- Nao dizia explicitamente que opera sobre planejamento, nao sobre documento de despesa.
- Nao listava metricas e agrupamentos aceitos.
- Nao explicava `valor_total` versus `resultados`.

Docstring reescrita: aplicada no arquivo acima.

### `consultar_receitas`
Arquivo: [consultar_receitas_query.py](/Users/thiagohenriquedominguesbotelho/Documents/code/ai/arcos-transparente/agents/tools/sql_tools/receitas/consultar_receitas_query.py:26)

Notas: proposito `3`, delimitacao `1`, args `2`, returns `1`, confusao `1`

Problemas concretos encontrados:
- A distincao entre `arrecadacao` e `lancamento` estava presente, mas ainda tecnica para pergunta informal.
- Nao havia linha de nao uso contra `agregar_receitas`, `consultar_planejamento` e `consultar_despesas`.
- Nao listava `tema`, filtros de faixa e meses por nome/numero.
- Nao explicava o shape de cada item retornado.

Docstring reescrita: aplicada no arquivo acima.

### `agregar_receitas`
Arquivo: [agregar_receitas_query.py](/Users/thiagohenriquedominguesbotelho/Documents/code/ai/arcos-transparente/agents/tools/sql_tools/receitas/agregar_receitas_query.py:30)

Notas: proposito `3`, delimitacao `1`, args `2`, returns `1`, confusao `1`

Problemas concretos encontrados:
- O default de `tipo_de_dado='arrecadacao'` muda bastante o sentido da tool e merecia mais destaque.
- Faltava a linha "nao use para planejamento/despesa".
- Nao listava metricas, agrupamentos e estrutura do retorno.

Docstring reescrita: aplicada no arquivo acima.

### `consultar_despesas`
Arquivo: [consultar_despesas_query.py](/Users/thiagohenriquedominguesbotelho/Documents/code/ai/arcos-transparente/agents/tools/sql_tools/despesas/consultar_despesas_query.py:175)

Notas: proposito `4`, delimitacao `1`, args `1`, returns `1`, confusao `2`

Problemas concretos encontrados:
- A docstring antiga era objetiva, mas nao fazia a separacao critica entre despesa executada e planejamento.
- Nao listava filtros aceitos, especialmente `tipo` e `descricao`.
- Nao explicava o que vem em `resultados`.
- Nao trazia linha de nao uso contra `agregar_despesas`.

Docstring reescrita: aplicada no arquivo acima.

### `agregar_despesas`
Arquivo: [agregar_despesas_query.py](/Users/thiagohenriquedominguesbotelho/Documents/code/ai/arcos-transparente/agents/tools/sql_tools/despesas/agregar_despesas_query.py:64)

Notas: proposito `4`, delimitacao `1`, args `1`, returns `1`, confusao `2`

Problemas concretos encontrados:
- A docstring antiga dava bons exemplos, mas nao delimitava contra `agregar_planejamento`.
- Nao listava `tipo`, `metrica`, `agrupar_por` e regras de ordenacao.
- Nao explicava os dois formatos de retorno.

Docstring reescrita: aplicada no arquivo acima.

### `consultar_patrimonios`
Arquivo: [consultar_patrimonios_query.py](/Users/thiagohenriquedominguesbotelho/Documents/code/ai/arcos-transparente/agents/tools/sql_tools/patrimonios/consultar_patrimonios_query.py:148)

Notas: proposito `4`, delimitacao `1`, args `1`, returns `1`, confusao `3`

Problemas concretos encontrados:
- O proposito geral era claro, mas a docstring antiga nao separava bem "bem patrimonial" de "contrato/licitacao de aquisicao".
- Nao listava filtros aceitos nem datas.
- Nao descrevia o retorno e os campos publicos.

Docstring reescrita: aplicada no arquivo acima.

### `agregar_patrimonios`
Arquivo: [agregar_patrimonios_query.py](/Users/thiagohenriquedominguesbotelho/Documents/code/ai/arcos-transparente/agents/tools/sql_tools/patrimonios/agregar_patrimonios_query.py:53)

Notas: proposito `4`, delimitacao `1`, args `1`, returns `1`, confusao `3`

Problemas concretos encontrados:
- A docstring antiga nao delimitava bem contra `consultar_patrimonios`.
- Nao listava metricas, agrupamentos e shape do retorno.
- Nao fazia a ponte com contratos/licitacoes quando a pergunta for sobre compra, nao sobre o bem.

Docstring reescrita: aplicada no arquivo acima.

### `consultar_quadro_pessoal`
Arquivo: [consultar_quadro_pessoal_query.py](/Users/thiagohenriquedominguesbotelho/Documents/code/ai/arcos-transparente/agents/tools/sql_tools/quadro_pessoal/consultar_quadro_pessoal_query.py:109)

Notas: proposito `2`, delimitacao `1`, args `1`, returns `1`, confusao `1`

Problemas concretos encontrados:
- "Quadro de pessoal" e jargao; a docstring antiga nao explicava que se trata de vagas, nao de pessoas.
- Nao trazia linha de nao uso contra `consultar_servidores` e `buscar_historico_de_pagamentos_do_servidor`.
- Nao listava filtros aceitos nem campos do retorno.
- Alto risco de o LLM usar esta tool para perguntas sobre funcionarios reais.

Docstring reescrita: aplicada no arquivo acima.

### `agregar_quadro_pessoal`
Arquivo: [agregar_quadro_pessoal_query.py](/Users/thiagohenriquedominguesbotelho/Documents/code/ai/arcos-transparente/agents/tools/sql_tools/quadro_pessoal/agregar_quadro_pessoal_query.py:48)

Notas: proposito `2`, delimitacao `1`, args `1`, returns `1`, confusao `1`

Problemas concretos encontrados:
- Mesmo problema semantico de `consultar_quadro_pessoal`: "vagas" versus "pessoas" estava subentendido demais.
- Nao delimitava contra `agregar_servidores`.
- Nao listava metricas aceitas, principalmente `saldo_vagas`.
- Nao explicava o retorno agregado.

Docstring reescrita: aplicada no arquivo acima.

## Ranking por prioridade de melhoria

Critério usado: combinacao de notas baixas com alto risco de chamada errada por um LLM que recebe perguntas de cidadaos em portugues informal.

1. `consultar_planejamento`
2. `agregar_planejamento`
3. `consultar_quadro_pessoal`
4. `agregar_quadro_pessoal`
5. `consultar_receitas`
6. `agregar_receitas`
7. `consultar_despesas`
8. `agregar_despesas`
9. `consultar_contratos`
10. `agregar_contratos`
11. `consultar_licitacoes`
12. `agregar_licitacoes`
13. `consultar_servidores`
14. `agregar_servidores`
15. `consultar_patrimonios`
16. `agregar_patrimonios`
17. `buscar_historico_de_pagamentos_do_servidor`

## Matriz de confusao entre tools parecidas

| Par de tools | Risco | Pergunta tipica que confunde | Regra de desempate que a docstring precisa explicitar |
| --- | --- | --- | --- |
| `consultar_servidores` x `agregar_servidores` | alto | "quais os maiores salarios?" x "quantos servidores ganham acima de X?" | lista/ordenacao de pessoas reais versus total/agrupamento |
| `consultar_servidores` x `buscar_historico_de_pagamentos_do_servidor` | alto | "qual o salario do Joao?" | nome de pessoa com historico mensal vai para `buscar_historico...` |
| `consultar_quadro_pessoal` x `consultar_servidores` | muito alto | "quantas vagas ha?" x "quantas pessoas trabalham?" | vagas/regimes versus pessoas reais |
| `agregar_quadro_pessoal` x `agregar_servidores` | muito alto | "quantos cargos ha por regime?" | vagas do quadro versus contagem de servidores |
| `consultar_planejamento` x `consultar_despesas` | muito alto | "quanto foi pago na saude?" | linha de planejamento/orcamento versus documento de despesa executada |
| `agregar_planejamento` x `agregar_despesas` | muito alto | "qual o total pago em 2025?" | pagar no planejamento nao e o mesmo que pagar em documento de despesa |
| `consultar_receitas` x `agregar_receitas` | alto | "quanto arrecadou de IPTU?" | lista de registros versus total agregado |
| `consultar_receitas` x `consultar_planejamento` | alto | "previsao de arrecadacao" x "orcamento previsto" | entrada de receita versus planejamento de despesa |
| `consultar_contratos` x `consultar_licitacoes` | alto | "detalhe a compra da merenda" | contrato assinado/executado versus processo licitatorio |
| `agregar_contratos` x `agregar_licitacoes` | alto | "qual o maior valor nessa area?" | valor contratado versus valor estimado da licitacao |
| `consultar_patrimonios` x `consultar_contratos` | medio | "quais computadores foram comprados?" | bem patrimonial existente versus instrumento contratual da compra |

## Perguntas comuns de cidadaos que nenhuma tool atual cobre bem

- "Qual o horario do onibus para o bairro X?"  
  Ha dado em RAG, mas nao existe tool publica dedicada para consulta estruturada de transporte.

- "Como faco um pedido pela Lei de Acesso a Informacao?"  
  Tema de orientacao civica; hoje nao ha tool publica especifica para isso.

- "Quem e o secretario da saude e qual o telefone/endereco?"  
  Falta tool de autoridades, contatos e estrutura administrativa.

- "Quais veiculos a prefeitura ou a camara possuem?"  
  Existe base de frota no repositorio, mas nao ha tool publica exposta para esse dominio.

- "Quais obras estao em andamento no meu bairro?"  
  Nao ha tool publica para obras, etapas ou geografia de execucao.

- "Quais postos, escolas ou servicos publicos existem perto de mim e quando funcionam?"  
  Nao ha tool publica de equipamentos e horarios de atendimento.

- "Qual fornecedor mais aparece somando licitacao, contrato e despesa?"  
  Falta tool transversal entre dominios para comparacoes compostas.
