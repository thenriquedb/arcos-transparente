# from agents.tools.sql_tools.folha_pagamento import buscar_servidores_por_nome
from agents.tools.sql_tools.servidores import buscar_servidores_por_nome
from pprint import pprint


def main():
    termo = "Ronaldo Gaspar"
    # servidores = buscar_servidores_por_nome(termo)
    # pprint(servidores)

    servidores = buscar_servidores_por_nome(termo, limite=5)
    pprint(servidores)


if __name__ == "__main__":
    main()
