"""Tool publica para recuperar conhecimento municipal a partir do acervo markdown."""

from __future__ import annotations

from agents.rag.retrieval import KnowledgeRetriever
from agents.tools.registry import PUBLIC_SCOPE, register


@register(
    name="consultar_conhecimento_municipal",
    scope=PUBLIC_SCOPE,
    tags=["domain:conhecimento_municipal", "shape:retrieval"],
)
def consultar_conhecimento_municipal(
    pergunta: str,
    limite: int = 4,
) -> dict[str, object]:
    """
    Recupera trechos do acervo markdown local com conhecimento municipal curado.

    Use esta tool para perguntas documentais sobre telefones úteis, horários de
    ônibus, estrutura organizacional, competências institucionais, papel da
    Câmara, perguntas frequentes e outros conteúdos textuais já curados em
    `data/rag/**/*.md`.
    Ao responder com base nesta tool, cite explicitamente `titulo_documento`,
    `arquivo_fonte` ou `secao` para deixar a fonte auditável ao cidadão.
    Se a pergunta misturar contexto documental e dados estruturados, combine
    esta tool com as tools SQL e deixe claro qual parte veio do acervo markdown
    e qual parte veio dos dados estruturados.
    NAO use esta tool como fonte final para salarios, totais, rankings,
    licitações, contratos, despesas, receitas, patrimônio, quadro de pessoal ou
    qualquer outra consulta cujo dado estruturado da base local seja a fonte de
    verdade. Nesses casos, use primeiro as tools SQL apropriadas.

    Args:
        pergunta: Pergunta textual do cidadão sobre conhecimento municipal
            documentado no acervo markdown local.
        limite: Quantidade máxima de trechos relevantes a retornar. Inteiro
            entre 1 e 8. Use valores menores para respostas objetivas.
    """

    retriever = KnowledgeRetriever()
    return retriever.retrieve(pergunta, limit=limite).to_dict()
