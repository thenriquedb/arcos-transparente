## Context

Hoje `ingestion/pipeline.py` registra o dominio `servidores` com `ServidoresParser()` e a model `Servidor`, descobrindo `*servidores*.xml` e, na falta deles, reutilizando `*folha-pagamento*.xml`. Essa ingestao gera rows com `nome`, `cargo`, `secretaria`, `salario_base` e `competencia_referencia`, que alimentam `consultar_servidores`, `agregar_servidores` e parte dos enriquecimentos usados nas respostas de folha.

Em paralelo, `folha_servidores` hoje e apenas uma dimensao por nome, com foreign key opcional `servidor_id` apontando para `servidores`. A reconciliacao acontece por nome, cargo e secretaria em helpers como `_find_servidor_canonico`, e as respostas de folha dependem de `FolhaServidor.servidor_canonico` para recuperar secretaria e mes de referencia do snapshot.

O novo arquivo `data/xml/servidores/relacao-servidores/relacao-servidores.json` muda completamente o contrato: ele traz `id`, `Competencia`, `Nome`, `CPF`, `Matricula`, `CargoFuncao`, `FundamentoLegal`, `Lotacao`, `SituacaoFuncional`, `FormaContratacaoInvestidura`, `DataAdmissao`, `DataDesligamento`, `HorarioTrabalho`, `CargaHoraria`, `LocalOrigemCedencia`, `LocalDestinoCedencia`, `OnusPagamentoCedencia`, `DataInicioCessao`, `DataFimCessao`, `RegimeAposentadoria` e `VinculoEmpregaticio`. Essa fonte nao substitui o contrato usado hoje para salario/folha; ela representa um cadastro separado, sem chave confiavel de relacionamento com as tabelas atuais.

## Goals / Non-Goals

**Goals:**
- Separar de forma explicita o contrato legado de snapshot de folha do novo cadastro JSON de servidores.
- Preservar a consultabilidade dos dados hoje usados por `consultar_servidores`, `agregar_servidores` e pelas respostas de historico de folha.
- Remover o relacionamento entre `folha_servidores` e `servidores` na camada SQL, ORM e pipeline.
- Mapear todos os campos suportados do JSON para a nova tabela `servidores`, com normalizacao previsivel de textos, datas e campos vazios.
- Tornar a reimportacao da fonte JSON idempotente.

**Non-Goals:**
- Criar, nesta mesma mudanca, uma nova superficie publica de perguntas cidadas sobre os campos exclusivos do cadastro JSON.
- Introduzir relacionamento entre a nova tabela `servidores` e outras tabelas do dominio.
- Preservar o antigo parser XML de `servidores` como segunda fonte paralela para a mesma tabela.
- Resolver enriquecimentos futuros entre folha e cadastro JSON sem uma chave oficial entre as fontes.

## Decisions

### 1. `folha_servidores` passa a ser a casa do contrato legado de snapshot

`folha_servidores` deve absorver os campos hoje persistidos em `servidores` para o contrato legado de consultas publicas: `nome`, `cargo`, `secretaria`, `salario_base` e `competencia_referencia`. A tabela deixa de ser uma dimensao apenas por nome e passa a armazenar os snapshots que hoje alimentam perguntas sobre salarios e lotacao.

Rationale:
- O usuario quer que o conteudo atual de `servidores` seja movido para `folha_servidores`.
- Preservar o contrato legado em `folha_servidores` evita que a nova tabela `servidores` fique sobrecarregada com dois significados.
- Manter os nomes dos campos do contrato legado reduz o impacto sobre as tools publicas.

Alternatives considered:
- Fazer apenas uma copia historica unica para `folha_servidores` e nunca mais atualiza-la: rejeitado porque a base ficaria desatualizada na proxima carga de folha.
- Manter os snapshots na tabela `servidores` e criar uma tabela nova para o JSON: rejeitado porque o pedido explicito e que a nova fonte ocupe `servidores`.

### 2. A associacao de folha deve deixar de depender de um servidor canonico

O campo `folha_servidores.servidor_id`, a foreign key correspondente, os relacionamentos ORM e a logica `_find_servidor_canonico` devem ser removidos. Qualquer enriquecimento de folha deve passar a ler os campos suportados diretamente de `folha_servidores` e, quando necessario, complementar com `FolhaPagamentoRegistro`.

Rationale:
- A nova tabela `servidores` nao tera relacionamento com outras tabelas por enquanto.
- O relacionamento atual nao tem chave de negocio robusta; ele depende de matching textual e ficaria ainda mais fragil ao trocar a semantica de `servidores`.
- Eliminar a reconciliacao reduz risco de vinculos errados entre folha e cadastro JSON.

Alternatives considered:
- Manter uma foreign key opcional e preenchida por matching de nome/matricula: rejeitado porque a fonte JSON nao garante unicidade por nome e a matricula aparece repetida para alguns registros.
- Trocar a foreign key por um relacionamento logico sem constraint: rejeitado porque manteria o mesmo acoplamento informal, apenas mais dificil de auditar.

### 3. O novo `servidores` deve ser reconstruido ao redor do contrato JSON

A tabela `servidores` deve passar a refletir somente o arquivo `relacao-servidores.json`. O schema SQL deve usar nomes internos estaveis em snake_case, mantendo um `id` interno do banco e persistindo o `id` do arquivo como `source_id` unico para garantir reimportacao idempotente. O campo `Competencia` deve ser normalizado para uma data mensal (`competencia_referencia`), enquanto os demais campos devem ser mapeados para colunas como `cpf`, `matricula`, `cargo_funcao`, `fundamento_legal`, `lotacao`, `situacao_funcional`, `forma_contratacao_investidura`, `data_admissao`, `data_desligamento`, `horario_trabalho`, `carga_horaria`, `local_origem_cedencia`, `local_destino_cedencia`, `onus_pagamento_cedencia`, `data_inicio_cessao`, `data_fim_cessao`, `regime_aposentadoria` e `vinculo_empregaticio`.

Rationale:
- O JSON traz um contrato novo e mais amplo, que nao cabe na model atual baseada em salario/cargo/secretaria.
- Guardar `source_id` separado do PK interno evita acoplamento rigido ao identificador da fonte e facilita futuras evolucoes.
- Normalizar datas e strings vazias durante a ingestao reduz ambiguidade nas consultas futuras.
- Matricula deve ter a constraint unique para evitar duplicatas

Alternatives considered:
- NÃ0 se deve usar o `id` do JSON como primary key da tabela, porque mistura identidade interna e identidade da fonte, dificultando evolucoes futuras.
- Guardar apenas um blob bruto de JSON na tabela: rejeitado porque o pedido e mapear todos os campos para colunas utilizaveis.

### 4. A carga de folha passa a manter `folha_servidores`

Como `ServidoresParser` deixara de ler o XML de folha e passara a ler JSON, a manutencao corrente de `folha_servidores` deve sair da antiga carga de `servidores` e passar a acontecer na carga de `folha_pagamento`. Cada registro mensal de folha deve resolver ou criar o snapshot correspondente em `folha_servidores`, e `folha_pagamentos.servidor_id` deve continuar apontando para esse snapshot.

Rationale:
- O arquivo de folha continua sendo a fonte que contem os dados salariais necessarios para o contrato legado.
- Essa estrategia elimina a duplicidade de dois parsers concorrendo pelo mesmo snapshot de folha.
- Ela preserva a utilidade das consultas publicas de salarios apos a repurposicao da tabela `servidores`.

Alternatives considered:
- Continuar usando `ServidoresParser` para ler folha XML e tambem um parser JSON para o mesmo dominio: rejeitado porque criaria duas fontes com semanticas diferentes para `servidores`.
- Parar de atualizar `folha_servidores` depois da migracao inicial: rejeitado porque congelaria a base historica e quebraria a expectativa de novas importacoes de folha.

### 5. As tools publicas de `servidores` continuam respondendo sobre o contrato legado

`consultar_servidores`, `agregar_servidores` e os enriquecimentos de `buscar_historico_de_pagamentos_do_servidor` devem passar a ler `folha_servidores` como fonte do contrato legado de snapshot, e nao a nova tabela `servidores`. O cadastro JSON sera persistido e validado nesta change, mas sua exposicao cidada pode ser feita em uma mudanca futura com filtros e respostas proprias.

Rationale:
- As tools publicas atuais foram desenhadas para perguntas sobre salario, cargo, secretaria e mes de referencia, nao para o cadastro funcional completo do JSON.
- Reaproveitar os mesmos nomes de tools com a nova tabela JSON mudaria radicalmente o comportamento publico e quebraria testes existentes.
- Separar persistencia nova de exposicao publica reduz risco de regressao.

Alternatives considered:
- Apontar imediatamente `consultar_servidores` para a nova tabela JSON: rejeitado porque isso eliminaria ordenacoes por salario e consultas por snapshot mensal.
- Desabilitar temporariamente as tools publicas de servidores: rejeitado porque degradaria uma superficie ja existente sem necessidade.

## Risks / Trade-offs

- [Risk] O backfill de `folha_pagamentos.servidor_id` pode ficar ambiguo quando houver mais de um snapshot compativel. -> Mitigation: usar `nome`, `cargo`, `secretaria/lotacao` e `competencia` como chave de remapeamento e falhar explicitamente quando ainda houver colisao.
- [Risk] O JSON contem varios campos vazios e CPFs mascarados, e a normalizacao pode apagar informacao util. -> Mitigation: converter apenas strings em branco para `null` e preservar mascaras e textos publicos como vierem da fonte saneada.
- [Risk] A refatoracao vai deslocar muitas referencias de `Servidor` para `FolhaServidor`. -> Mitigation: concentrar o acesso em helpers compartilhados e atualizar os testes de tool junto com a mudanca de modelo.
- [Risk] Trocar o parser de pasta XML para um parser JSON pode gerar imports quebrados ou nomenclatura confusa. -> Mitigation: manter a classe `ServidoresParser` como contrato estavel, ainda que o modulo fisico mude para um pacote JSON.

## Migration Plan

1. Criar uma migration Alembic que expanda `folha_servidores` com o contrato legado de snapshot, backfille os dados atuais de `servidores`, remapeie `folha_pagamentos.servidor_id`, remova a foreign key canonica e recrie `servidores` com o schema JSON.
2. Atualizar as models SQLAlchemy e os exports de `database.models` para refletir a nova semantica das duas tabelas.
3. Alterar a descoberta de arquivos, o parser `ServidoresParser`, o schema de ingestao e a logica de carga para persistir o JSON em `servidores` e manter `folha_servidores` pela carga de folha.
4. Migrar as tools publicas e os serializadores de folha para ler `folha_servidores` no contrato legado.
5. Executar testes de parser, schema, pipeline, tools publicas e migracoes; depois validar localmente a reimportacao do JSON e uma consulta representativa de folha.

Rollback strategy:
- Reverter a migration apenas com backup previo do banco, porque a mudanca envolve copia de dados, remapeamento de foreign key e recriacao estrutural da tabela `servidores`.

## Open Questions

- A nova tabela `servidores` precisa ganhar tools publicas dedicadas ainda nesta iniciativa, ou a exposicao do cadastro JSON pode ficar para um follow-up depois que o contrato de consulta for definido?
