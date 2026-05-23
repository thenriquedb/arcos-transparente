from sqlalchemy import func, select

from typing import Any

from database.session import get_session
from database.models import Servidor


def buscar_servidores_por_nome(nome: str, limite: int = 10) -> dict[str, Any]:
    """
    Busca um servidor pelo nome ou parte do nome.

    Examples:
      'qual o salário de João Silva',
      'me mostre os dados de Maria Souza'.

    Args:
        nome (str): O nome ou parte do nome do servidor a ser buscado.
        limite (int): O número máximo de resultados a serem retornados.
    Returns:
        list[Servidor]: Uma lista de objetos Servidor que correspondem ao critério de busca
    """
    palavras = nome.lower().strip().split()
    filters = [func.lower(Servidor.nome).like(f"%{palavra}%") for palavra in palavras]

    with get_session() as session:
        servidores = (
            session.query(Servidor)
            .filter(*filters)
            .order_by(Servidor.nome.asc())
            .limit(limite)
            .all()
        )

        return [
            {k: v for k, v in s.__dict__.items() if not k.startswith("_")}
            for s in servidores
        ]
