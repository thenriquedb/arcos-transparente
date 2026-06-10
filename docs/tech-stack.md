# Tech Stack

| Camada | Tecnologia | Finalidade |
|--------|-----------|-----------|
| Linguagem | Python 3.13+ | Runtime principal |
| Gerenciador de pacotes | uv | Resolução de dependências e ambiente virtual isolado |
| CLI | Typer + Rich | Interface de linha de comando para ingestão e operação do banco |
| ORM | SQLAlchemy 2.x | Mapeamento objeto-relacional e execução de queries |
| Migrations | Alembic | Versionamento e aplicação de schema no banco |
| Banco de dados | SQLite | Persistência relacional local dos dados públicos |
| Validação de dados | Pydantic 2.x | Schemas de entrada e saída das tools e do pipeline de ingestão |
| Logging | Loguru | Logging estruturado com rastreabilidade de erros de ingestão |
| Agente de IA | LangChain + LangGraph | Orquestração do agente ReAct, registro de tools e streaming de respostas |
| LLM | OpenAI API (`gpt-4.1-mini` padrão) | Modelo de linguagem principal para compreensão e resposta |
| Embedding | `langchain-openai` (embeddings OpenAI) | Geração de vetores para o índice RAG |
| Vetor store | Chroma (`langchain-chroma`) | Armazenamento e recuperação semântica de documentos markdown e PDF |
| RAG | LangChain text splitters + Chroma | Indexação e retrieval do acervo municipal curado em `data/rag/` |
| Observabilidade | LangSmith (opcional) | Rastreamento de execuções do agente; desabilitado por padrão (`noop`) |
| Interface web | Streamlit | App de chat cidadão exposto via navegador |
| Containerização | Docker + Docker Compose | Build, deploy e persistência de volume stateful |
| Parsing XML | BeautifulSoup4 | Leitura e extração dos XMLs do portal da transparência |
| Testes | pytest | Testes unitários e de integração |
| Linting / formatação | Ruff | Análise estática e formatação de código |
