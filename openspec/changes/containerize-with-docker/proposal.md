## Why

Hoje o projeto depende de um ambiente Python local com `uv`, caminhos locais para
SQLite e Chroma, e uma sequência manual de comandos para inicialização, importação
e subida da interface Streamlit. Isso aumenta o atrito de onboarding e torna o
deploy mais frágil, porque pequenas diferenças entre máquinas e servidores mudam
o comportamento de arquivos, dependências e persistência.

Uma estratégia oficial de containerização com Docker reduz essa variação,
transforma a aplicação em uma unidade reproduzível para desenvolvimento e deploy
e deixa explícitos os diretórios que precisam de volume persistente para banco e
índice vetorial.

## What Changes

- Definir um runtime oficial em Docker para a aplicação, cobrindo build da
  imagem, inicialização da interface web em Streamlit e execução dos comandos
  operacionais já existentes via CLI.
- Especificar como a aplicação deve expor porta HTTP, carregar variáveis de
  ambiente e persistir SQLite e Chroma em volumes montados no container.
- Formalizar que a operação containerizada atual será orientada a uma instância
  stateful única, compatível com SQLite em modo WAL e com o fluxo atual de
  reimportação total da base.
- Documentar o fluxo de uso com Docker, incluindo build, subida da interface,
  inicialização do banco, importação dos dados e geração do índice RAG.
- Delimitar os diretórios de dados que permanecem no repositório ou em bind
  mount e os diretórios de runtime que precisam sobreviver a reinícios do
  container.

## Capabilities

### New Capabilities
- `dockerized-runtime`: Define um modo oficial de executar o projeto em Docker,
  com imagem reproduzível, entrada principal para Streamlit, comandos
  operacionais via container e persistência explícita para banco SQLite e índice
  vetorial local.

### Modified Capabilities
- None.

## Impact

- Affected code: futuros `Dockerfile`, `.dockerignore`, possíveis arquivos de
  orquestração Docker e ajustes pontuais em scripts ou entrypoints para separar
  diretórios de código, runtime e dados.
- Affected docs: `README.md`, `INSTRUCTIONS.md` e eventuais guias operacionais
  que hoje assumem apenas execução local com `uv`.
- Affected systems: fluxo de desenvolvimento local, deploy em plataforma com
  suporte a container único e volume persistente, e operação de banco/índice via
  comandos dentro do container.
- Dependencies and constraints: Docker passa a ser dependência operacional
  suportada; a solução precisa respeitar o uso atual de `Streamlit`, `SQLite`,
  `Chroma`, `.env` e o pipeline existente em `cli.py`.
