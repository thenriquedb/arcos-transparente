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


def buscar_servidores_por_secretaria(
    secretaria: str, limite: int = 10
) -> dict[str, Any]:
    """
    Busca servidores por secretaria.

    Examples:
      'quais servidores trabalham na Secretaria de Educação',
      'me mostre os servidores da Secretaria de Saúde'.

    Args:
        secretaria (str): O nome ou parte do nome da secretaria a ser buscada.
        limite (int): O número máximo de resultados a serem retornados.
    Returns:
        list[Servidor]: Uma lista de objetos Servidor que correspondem ao critério de busca
    """
    with get_session() as session:
        servidores = (
            session.query(Servidor)
            .filter(func.lower(Servidor.secretaria).like(f"%{secretaria.lower()}%"))
            .order_by(Servidor.nome.asc())
            .limit(limite)
            .all()
        )

        return [
            {k: v for k, v in s.__dict__.items() if not k.startswith("_")}
            for s in servidores
        ]


def buscar_servidores_por_cargo(cargo: str, limite: int = 10) -> dict[str, Any]:
    """
    Busca servidores por cargo.

    Examples:
        'quais servidores ocupam o cargo de Professor',
        'me mostre os servidores que são Médicos'.

    Args:
        cargo (str): O nome ou parte do nome do cargo a ser buscado.
        limite (int): O número máximo de resultados a serem retornados.
    Returns:
        list[Servidor]: Uma lista de objetos Servidor que correspondem ao critério de busca
    """
    with get_session() as session:
        servidores = (
            session.query(Servidor)
            .filter(func.lower(Servidor.cargo).like(f"%{cargo.lower()}%"))
            .order_by(Servidor.nome.asc())
            .limit(limite)
            .all()
        )

        return [
            {k: v for k, v in s.__dict__.items() if not k.startswith("_")}
            for s in servidores
        ]


def buscar_servidores_admitidos_no_periodo(
    data_inicio: str, data_fim: str, limite: int = 10
) -> dict[str, Any]:
    """
    Busca servidores admitidos em um período específico.

    Examples:
        'quais servidores foram admitidos entre 01/01/2020 e 31/12/2020',
        'me mostre os servidores admitidos no ano de 2021'.

    Args:
        data_inicio (str): A data de início do período no formato 'DD/MM/YYYY'.
        data_fim (str): A data de fim do período no formato 'DD/MM/YYYY'.
        limite (int): O número máximo de resultados a serem retornados.
    Returns:
        list[Servidor]: Uma lista de objetos Servidor que correspondem ao critério de busca
    """
    with get_session() as session:
        servidores = (
            session.query(Servidor)
            .filter(Servidor.data_admissao.between(data_inicio, data_fim))
            .order_by(Servidor.data_admissao.asc())
            .limit(limite)
            .all()
        )

        return [
            {k: v for k, v in s.__dict__.items() if not k.startswith("_")}
            for s in servidores
        ]
