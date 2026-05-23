from database.session import get_session
from database.models import Funcionario, FolhaPagamentoRegistro

def busca_folha_funcionario(nome: str):
    with get_session() as session:
       funcionario = session.query(Funcionario).filter_by(nome=nome).first()
        if not funcionario:
            return None
      
      folha_pagamento = session.query(FolhaPagamentoRegistro).filter_by(id=funcionario.id).all()
     
      return {
          "funcionario": funcionario.nome,
          "cargo": folha_pagamento[0].cargo.nome,
          "lotacao": folha_pagamento[0 ].lotacao.nome,
          "pagamentos": [
              {
                  "competencia": f"{registro.competencia_mes_nome} {registro.competencia_ano}",
                  "valor_liquido": registro.liquido,
                  "descontos": registro.descontos,
                  "salario_base": registro.salario_base,
                  "proventos": registro.proventos,
                  "vantagens": registro.vantagens,
              }
              for registro in folha_pagamento
          ],
      }