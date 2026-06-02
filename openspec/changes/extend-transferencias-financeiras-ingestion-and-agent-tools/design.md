## Context

O diretório `data/xml/transferencias-financeiras/` já contém pelo menos duas famílias de arquivos públicos com formatos muito diferentes:

- XMLs de `recebimentos-YYYY.xml`, com movimentos de transferências financeiras entre unidades gestoras, incluindo programação inicial, data, tipo de movimento e valor.
- CSVs de `emendas-parlamentares-YYYY.csv`, com autor, objeto, tipo, função e valor de emendas parlamentares destinadas ao município.

Hoje esse conteúdo não entra na base SQLite nem na superfície pública do agente. O projeto já possui domínios maduros para `receitas`, `despesas` e `planejamento`, mas nenhum deles representa corretamente essas duas fontes. Reaproveitar tabelas já existentes faria perder semântica, dificultaria filtros e confundiria o agente na hora de responder perguntas sobre repasses à Câmara ou emendas parlamentares.

Além disso, a arquitetura atual favorece tools públicas amplas por domínio, com forte rastreabilidade em SQL, idempotência em reimportações e integração explícita com prompt, router compatível e testes. A nova solução precisa seguir esse padrão sem diluir duas estruturas de fonte heterogêneas em uma modelagem genérica demais.

## Goals / Non-Goals

**Goals:**
- Incluir os arquivos de `transferencias-financeiras` no fluxo padrão de importação para SQLite.
- Persistir os dados em tabelas próprias do domínio, preservando campos relevantes de cada família de fonte.
- Garantir reimportação idempotente e rastreável para XMLs de movimentos e CSVs de emendas.
- Expor o domínio ao agente por meio de tools públicas SQL e integração com prompt/roteamento.
- Permitir perguntas estruturadas sobre transferências para a Câmara, tipos de movimento, autores de emenda, funções e totais por período.

**Non-Goals:**
- Reaproveitar `receitas` ou `despesas` como destino principal desse domínio.
- Unificar XML de recebimentos e CSV de emendas em uma única tabela esparsa só por conveniência.
- Cobrir fontes externas além dos arquivos já existentes no diretório local.
- Resolver visualizações, dashboards ou páginas dedicadas nesta mudança.

## Decisions

### 1. Criar duas tabelas top-level dedicadas dentro do domínio

A persistência deve criar tabelas próprias para as duas famílias de fonte, em vez de reaproveitar `receita_arrecadacoes` ou misturar tudo em uma tabela única. Em termos de design, isso significa uma tabela para movimentos de transferências financeiras e outra para emendas parlamentares.

Rationale:
- Os XMLs de recebimentos descrevem movimentos financeiros entre unidades, com `tipo_movimento`, `data_movimento`, `programacao_inicial` e `valor_movimento`.
- O CSV de emendas descreve atos políticos e finalidades de repasse, com `autor`, `ano/numero`, `objeto`, `tipo`, `funcao` e `valor`.
- Uma única tabela ampla produziria muitos campos nulos, filtros confusos e semântica pior para tools e testes.

Alternatives considered:
- Reusar tabelas de `receitas`: rejeitado porque transferências e emendas não seguem o contrato de arrecadação/lançamento tributário.
- Reusar `despesa_documentos`: rejeitado porque os arquivos não representam documentos de despesa executada.
- Criar uma tabela única com discriminador: rejeitado porque a estrutura ficaria esparsa demais para um primeiro contrato público sólido.

### 2. Tratar `transferencias-financeiras` como um tipo de ingestão próprio no pipeline

O pipeline deve ganhar um domínio explícito de ingestão para `transferencias-financeiras`, capaz de descobrir tanto XMLs quanto CSVs no mesmo diretório e acionar parsers específicos por extensão e padrão de arquivo.

Rationale:
- O operador pensa nesse conteúdo como um conjunto único de fontes relacionadas.
- A pasta já está consolidada no repositório e deve continuar sendo a âncora operacional desse domínio.
- Um tipo próprio no pipeline evita acoplamento artificial com `receitas` ou `despesas`.

Alternatives considered:
- Embutir os XMLs em `receitas` e o CSV em outro tipo já existente: rejeitado porque fragmenta manutenção e dificulta operação.
- Manter importadores manuais fora do pipeline: rejeitado porque quebra consistência com o restante do projeto.

### 3. Expor o domínio com tools públicas dedicadas, mas orientadas ao domínio unificado

O agente deve enxergar `transferencias-financeiras` como um domínio público novo, por meio de tools dedicadas de consulta e agregação. Internamente, essas tools podem coordenar as duas tabelas específicas e expor filtros compatíveis com cada subtipo de dado.

Rationale:
- A interface cidadã deve responder perguntas como “quanto a prefeitura transferiu para a Câmara?” e “quais emendas parlamentares foram recebidas?” sem obrigar o usuário a conhecer a separação física entre tabelas.
- O padrão atual do projeto favorece tools amplas por domínio, não dezenas de ferramentas estreitas.

Alternatives considered:
- Criar um conjunto de tools totalmente separado para emendas e outro para transferências: possível, mas rejeitado para v1 porque aumenta a superfície pública e a complexidade do prompt sem necessidade imediata.
- Não criar tools e depender de SQL genérico: rejeitado porque enfraquece o contrato público do agente.

### 4. Preservar idempotência por linhagem de origem em cada família

Cada família de fonte deve ter sua própria estratégia de unicidade e reimportação: XMLs por identidade/movimento normalizado e CSVs de emendas por chaves de origem como exercício, ano/número, autor e demais campos estáveis do relatório.

Rationale:
- Os arquivos podem ser reprocessados mais de uma vez no ciclo local.
- O projeto já prioriza consistência e reimportação segura em outros domínios.

Alternatives considered:
- Apagar tudo e reinserir sempre sem chave estável: rejeitado porque perde rastreabilidade e aumenta risco de drift entre execuções.

### 5. Atualizar prompt e roteamento compatível com vocabulário cidadão

O domínio deve ser acessível por expressões comuns como `transferência para câmara`, `repasse`, `recebimento`, `emenda parlamentar`, `autor da emenda`, `função da emenda` e `valor da emenda`.

Rationale:
- O usuário não vai formular perguntas em linguagem de schema.
- O domínio pode competir semanticamente com `receitas`, `planejamento` e `despesas`, então os contratos precisam deixar clara a fonte de verdade.

Alternatives considered:
- Confiar só no LLM sem ajuste de prompt ou tags de domínio: rejeitado porque aumenta ambiguidade e reduz previsibilidade.

## Risks / Trade-offs

- [Risk] As duas fontes podem parecer próximas demais de `receitas` e induzir modelagem errada. -> Mitigation: separar o domínio em tabelas próprias e explicitar a fronteira em docs, prompt e tools.
- [Risk] Um único domínio público pode ficar complexo demais se os filtros não forem bem desenhados. -> Mitigation: limitar o contrato público a filtros realmente suportados e usar discriminação clara por subtipo de registro quando necessário.
- [Risk] O CSV de emendas aparenta conter ruído visual de exportação e encoding irregular. -> Mitigation: tratar parsing e normalização como contrato explícito, com fixtures representativas e falha previsível para layouts não suportados.
- [Risk] Perguntas cidadãs sobre “investimento”, “repasse” ou “emenda” podem competir com planejamento e receitas. -> Mitigation: documentar fronteiras de uso e adicionar testes de roteamento/chatbot com termos reais.

## Migration Plan

1. Adicionar os novos modelos SQL e migrations para as tabelas dedicadas do domínio.
2. Implementar descoberta de arquivos e parsers específicos para XMLs de recebimentos e CSVs de emendas parlamentares.
3. Integrar o novo tipo ao pipeline e adicionar testes de persistência/reimportação.
4. Criar tools públicas de consulta e agregação do domínio e registrá-las na superfície do agente.
5. Atualizar prompt, roteamento compatível e testes do chatbot para o novo domínio.
6. Atualizar documentação de banco, importação e arquitetura conforme necessário.

Rollback strategy:
- Remover o novo tipo do pipeline e o registro das tools públicas.
- Reverter as migrations e os novos modelos caso a modelagem se mostre inadequada.

## Open Questions

- A tool pública v1 deve expor um par único de consulta/agregação para todo o domínio ou vale separar lookup de emendas e lookup de transferências já na primeira versão?
- O CSV de emendas deve manter linhas históricas de exercícios anteriores presentes no arquivo de 2026 como parte do mesmo contrato, ou o import deve filtrar apenas pelo exercício do nome do arquivo?
- Perguntas sobre “investimento via emenda” devem ser tratadas diretamente nesse domínio ou apenas quando citarem explicitamente emenda/transferência?
