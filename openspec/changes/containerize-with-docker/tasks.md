## 1. Container Runtime Artifacts

- [x] 1.1 Criar um `Dockerfile` oficial para o projeto com dependências Python, código da aplicação e comando padrão para subir `agents/chatbot/web.py` via Streamlit.
- [x] 1.2 Adicionar `.dockerignore` para excluir cache local, ambientes virtuais, artefatos transitórios e diretórios de runtime que não devem entrar na imagem.
- [x] 1.3 Adicionar um `compose.yaml` canônico com serviço principal, mapeamento de porta, leitura de `.env` e volume persistente para o diretório de runtime.

## 2. Runtime State And Operational Commands

- [x] 2.1 Configurar o fluxo Docker para usar caminhos persistentes explícitos para `DATABASE_URL` e `RAG_PERSIST_DIRECTORY`, sem depender de escrita dentro da árvore versionada.
- [x] 2.2 Garantir que a mesma imagem possa executar `uv run python cli.py db init`, `uv run python cli.py importar` e `uv run python cli.py rag index` por override de comando no fluxo Docker documentado.
- [x] 2.3 Validar que a interface web sobe com o comando padrão e que banco SQLite e índice vetorial sobrevivem à recriação do container quando o mesmo volume é reutilizado.

## 3. Documentation And Verification

- [x] 3.1 Atualizar `README.md` com uma nova seção de uso via Docker cobrindo build, subida da interface e aviso sobre a operação stateful de instância única.
- [x] 3.2 Atualizar `INSTRUCTIONS.md` com o fluxo operacional em Docker para inicialização do banco, importação dos dados e geração do índice RAG.
- [x] 3.3 Executar uma verificação focada do fluxo Docker proposto e ajustar a documentação para que os comandos publicados reflitam exatamente o comportamento suportado pela implementação.
