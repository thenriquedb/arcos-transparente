## Context

O projeto hoje roda como uma stack Python local baseada em `uv`, com interface
em Streamlit, banco SQLite em `database/transparencia.db`, índice vetorial local
em `vector_store/knowledge_markdown` e comandos operacionais expostos por
`cli.py`. Esse desenho funciona bem para desenvolvimento local, mas ainda não
define uma forma oficial e reproduzível de empacotar dependências, subir a
interface web e preservar o estado necessário para consultas reais.

A mudança é transversal porque toca onboarding, deploy, diretórios de runtime,
fluxos operacionais do banco e do índice RAG, e a documentação principal do
repositório. Ao mesmo tempo, a arquitetura atual impõe uma restrição relevante:
o sistema ainda é stateful e depende de SQLite em modo WAL, além de reimportar a
base inteira no fluxo `importar`. Isso favorece uma primeira solução em
container único com persistência explícita, em vez de escalonamento horizontal ou
quebra precoce em múltiplos serviços.

## Goals / Non-Goals

**Goals:**
- Definir um caminho oficial para build e execução do projeto em Docker sem
  exigir Python e `uv` instalados na máquina hospedeira.
- Preservar o comportamento atual do projeto, incluindo Streamlit, CLI,
  `.env`, SQLite local e Chroma local, dentro de uma imagem reproduzível.
- Tornar explícitos os diretórios que precisam de volume persistente para banco
  e índice vetorial.
- Documentar os comandos canônicos para subir a interface, inicializar banco,
  importar dados e gerar o índice RAG usando Docker.
- Manter o fluxo local sem Docker funcional como alternativa, sem forçar
  reescrita da aplicação.

**Non-Goals:**
- Migrar SQLite para Postgres, MySQL ou outro banco cliente-servidor.
- Transformar o projeto em arquitetura multi-serviço com workers, filas ou API
  HTTP dedicada nesta mudança.
- Introduzir orquestração específica de nuvem, como Kubernetes, ECS ou manifests
  de um provedor particular.
- Resolver escalabilidade horizontal do chat ou paralelismo de importações além
  do que o desenho atual com SQLite já suporta.

## Decisions

### 1. Adotar uma imagem Docker única e um serviço principal único como runtime oficial

A mudança será desenhada em torno de uma imagem oficial do projeto e de um
serviço principal único para operação padrão da aplicação.

Direção escolhida:
- Um `Dockerfile` oficial empacota código, dependências Python e entrypoint
  principal da interface web.
- Um arquivo de orquestração simples, como `compose.yaml`, será o fluxo
  canônico de execução local com Docker.
- O mesmo artefato de imagem também servirá para comandos operacionais do CLI,
  sobrescrevendo o comando padrão quando necessário.

Por quê:
- A aplicação atual é um único processo web em Streamlit com dependências locais
  compartilhadas pelo CLI.
- Uma imagem única reduz divergência entre execução do chat e execução de
  tarefas como `db init`, `importar` e `rag index`.
- `docker compose` oferece o caminho mais curto para explicar porta, volume e
  `.env` sem exigir que toda pessoa usuária monte `docker run` manualmente.

Alternativas consideradas:
- Expor apenas `docker run`: rejeitado porque aumenta a carga cognitiva para
  variáveis de ambiente, volume e comandos operacionais recorrentes.
- Criar containers separados para web e jobs desde o início: rejeitado porque a
  mudança ainda precisa respeitar o mesmo diretório stateful e não ganha
  simplicidade real nesta fase.

### 2. Separar código imutável de dados mutáveis em um diretório de runtime montável

O container não deve escrever o banco SQLite nem o índice vetorial dentro do
tree de código versionado. Em vez disso, a execução oficial usará um diretório
de runtime montado por volume, por exemplo `/app/runtime`.

Direção escolhida:
- `DATABASE_URL` apontará para um caminho dentro do volume persistente, como
  `sqlite:////app/runtime/database/transparencia.db`.
- `RAG_PERSIST_DIRECTORY` apontará para um caminho dentro do mesmo volume, como
  `/app/runtime/vector_store/knowledge_markdown`.
- O conteúdo versionado necessário para leitura, como código-fonte,
  `data/rag/**` e os arquivos de dados públicos já presentes no repositório no
  momento do build, será empacotado na imagem.

Por quê:
- O código atual já trata o banco e o índice como arquivos locais; a principal
  melhoria é tornar o local desses arquivos explícito e preservável entre
  reinícios.
- Separar runtime de código evita gravar WAL, banco e artefatos do Chroma dentro
  da árvore do repositório montada no container.
- Empacotar os dados versionados mantém a primeira versão da solução
  autocontida, sem depender de mounts adicionais só para conseguir importar.

Alternativas consideradas:
- Continuar escrevendo em `database/` e `vector_store/` dentro do diretório do
  app: rejeitado porque mistura artefatos mutáveis de runtime com código
  versionado e atrapalha deploys reproduzíveis.
- Exigir mounts separados também para `data/xml` e `data/rag`: rejeitado nesta
  fase porque aumenta o setup e reduz a portabilidade do primeiro fluxo Docker.

### 3. Usar a interface Streamlit como comando padrão do container e o CLI como comando sobrescrevível

O comando padrão do container deve subir a interface web da aplicação, enquanto
os comandos de manutenção continuarão acessíveis pela mesma imagem com override
de comando.

Direção escolhida:
- O comando padrão executa `streamlit run agents/chatbot/web.py` escutando em
  `0.0.0.0` e porta configurável por variável de ambiente.
- Operações como `db init`, `importar` e `rag index` serão executadas pela mesma
  imagem via `docker compose run --rm app ...` ou equivalente.

Por quê:
- A interface Streamlit é a superfície pública principal do projeto.
- Reutilizar a mesma imagem para web e CLI evita drift entre ambientes.
- O modelo atual já concentra as rotinas operacionais em `cli.py`, então não é
  necessário criar um segundo runtime só para tarefas de manutenção.

Alternativas consideradas:
- Criar uma imagem só para o web e outra para jobs: rejeitado porque duplicaria
  dependências e tornaria a manutenção mais cara sem necessidade imediata.
- Esconder o CLI atrás de scripts shell opacos: rejeitado porque os comandos
  atuais em Python já são a interface operacional estabelecida do projeto.

### 4. Formalizar o modo Docker atual como operação stateful de instância única

A especificação precisa assumir explicitamente que a primeira versão
containerizada será operada como uma instância única com volume persistente.

Por quê:
- `database/session.py` ativa SQLite com WAL e `check_same_thread=False`, o que
  é compatível com o desenho local atual, mas não transforma a aplicação em algo
  seguro para múltiplas réplicas concorrendo pelo mesmo volume.
- `cli.py importar` recria toda a base antes da carga, então importações e uso
  do chat compartilham um mesmo recurso stateful e precisam de coordenação
  simples.
- Explicitar essa limitação evita que a documentação dê a entender que bastaria
  “escalar replicas” sem mudanças arquiteturais adicionais.

Alternativas consideradas:
- Permitir múltiplas instâncias desde já: rejeitado porque criaria uma promessa
  operacional que o banco atual não sustenta de forma confiável.
- Aproveitar a mudança para migrar o banco para Postgres: rejeitado porque muda
  demais o escopo da entrega pedida.

### 5. Atualizar README e INSTRUCTIONS com um fluxo Docker canônico e honesto

A documentação principal do repositório passará a incluir uma seção dedicada ao
uso com Docker.

Direção escolhida:
- `README.md` recebe um guia curto de entrada com build e execução.
- `INSTRUCTIONS.md` recebe a versão operacional mais completa, incluindo
  inicialização do banco, importação e indexação via container.
- Enquanto a implementação ainda não existir, a documentação adicionada deve
  deixar claro que o fluxo Docker está sendo proposto nesta mudança, evitando
  instruções apresentadas como já suportadas se o código ainda não as entrega.

Por quê:
- O README é a primeira porta de entrada; `INSTRUCTIONS.md` é o manual de
  operação mais detalhado do projeto.
- A solicitação do usuário inclui explicitamente documentação sobre como rodar
  com Docker.
- O repositório já sofreu com deriva entre código e docs em outros pontos; a
  mudança precisa evitar repetir esse problema.

## Risks / Trade-offs

- [Risk] Empacotar `data/xml` na imagem aumenta o tamanho do build. -> Mitigation:
  começar com a solução autocontida por simplicidade e revisar a estratégia se o
  custo de imagem se tornar relevante na prática.
- [Risk] Pessoas podem interpretar a presença de Docker como sinal de suporte a
  múltiplas instâncias. -> Mitigation: documentar de forma explícita a operação
  stateful de instância única e cobrir isso na spec.
- [Risk] Permissões de escrita no volume podem falhar em alguns ambientes. ->
  Mitigation: padronizar o diretório de runtime e validar criação de banco e
  índice em testes ou verificação manual do container.
- [Risk] Documentação pode prometer comandos antes da implementação real. ->
  Mitigation: enquanto a mudança estiver só em proposta, marcar a seção como
  fluxo planejado e apontar para a própria OpenSpec change.

## Migration Plan

1. Adicionar os artefatos de containerização, como `Dockerfile`,
   `.dockerignore` e `compose.yaml`, apontando runtime stateful para um volume
   persistente.
2. Configurar o serviço principal para subir a interface Streamlit no endereço e
   porta esperados por ambientes Docker.
3. Garantir que os comandos `db init`, `importar` e `rag index` possam ser
   executados pela mesma imagem com override de comando.
4. Atualizar `README.md` e `INSTRUCTIONS.md` com o fluxo canônico de build e
   operação em Docker.
5. Validar build, subida da interface e persistência do volume antes de
   considerar a mudança pronta.

Rollback:
- Remover os artefatos Docker e as seções de documentação associadas, mantendo o
  fluxo local com `uv` como caminho suportado.

## Open Questions

- O fluxo oficial deve publicar apenas `compose.yaml`, ou também vale expor
  exemplos equivalentes de `docker run` no README?
- Vale introduzir um pequeno script/target de conveniência para comandos
  frequentes do container, ou a primeira versão deve depender apenas de `docker
  compose` puro para manter o contrato enxuto?
