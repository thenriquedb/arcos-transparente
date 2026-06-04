## 1. Descoberta e parsing das fontes

- [x] 1.1 Identificar o contrato suportado dos arquivos `recebimentos-YYYY.xml` e `emendas-parlamentares-YYYY.csv`, incluindo encoding, cabeçalhos, campos obrigatórios e regras de descoberta no pipeline.
- [x] 1.2 Implementar parsers específicos para XML de transferências financeiras e CSV de emendas parlamentares, com normalização de datas, textos e valores monetários.
- [x] 1.3 Adicionar fixtures e testes de parser para layouts válidos e para arquivos inválidos ou não suportados do domínio.

## 2. Persistência SQL dedicada

- [x] 2.1 Criar modelos SQL e migrations para tabelas próprias do domínio, separando movimentos de transferências financeiras e emendas parlamentares.
- [x] 2.2 Integrar o novo tipo `transferencias-financeiras` ao pipeline de ingestão com regras de upsert e idempotência adequadas a cada família de fonte.
- [x] 2.3 Adicionar testes de pipeline e banco provando persistência correta, rastreabilidade e estabilidade em reimportações.

## 3. Tools públicas do domínio

- [x] 3.1 Implementar tools públicas de consulta para `transferencias-financeiras`, cobrindo filtros suportados para movimentos e emendas parlamentares.
- [x] 3.2 Implementar tools públicas de agregação para totais, contagens e rankings do domínio, incluindo agrupamentos úteis para unidades, tipos de movimento, autores e funções.
- [x] 3.3 Registrar as novas tools na superfície pública e adicionar testes unitários para comportamento SQL-backed e contratos de resposta.

## 4. Integração com o agente

- [x] 4.1 Atualizar prompt, descrições de tools e roteamento compatível para que perguntas sobre repasses, transferências, recebimentos e emendas usem o novo domínio.
- [x] 4.2 Adicionar testes de router/chatbot cobrindo perguntas estruturadas sobre transferências para a Câmara, emendas parlamentares, totais e rankings.
- [x] 4.3 Atualizar a documentação relevante de banco, importação e arquitetura para descrever o novo domínio `transferencias-financeiras`.
