"""
Scraper - Despesas por Função
Portal: https://webapp1-arcos.cidade360.cloud/pronimtb/

Payload replicado fielmente do tráfego real capturado em 04/06/2026.
Campos variáveis: cmbUnidadeCP, cmbAno, hndAno, txtDataInicial, txtDataFinal.
Todos os demais campos são estáticos conforme captura.
"""

import requests
import csv
import time
from bs4 import BeautifulSoup
from datetime import datetime

# ──────────────────────────────────────────────
# CONFIGURAÇÃO
# ──────────────────────────────────────────────

BASE_URL = "https://webapp1-arcos.cidade360.cloud/pronimtb"

# Entidades — formato: "nome": "ANO|BANCO|"
# Extraídas dos payloads reais capturados:
#   HAR 1: Fundação Municipal de Saúde e Assistência de Arcos (2025)
#   HAR 2: Prefeitura Municipal de Arcos (2026)
ENTIDADES = {
    "Prefeitura Municipal de Arcos": "2026|DW_LC131_FC_27|",
    "Fundação Municipal de Saúde e Assistência de Arcos": "2025|DW_LC131_FC_26|",
}

# Períodos — ajuste conforme necessário
PERIODOS = [
    ("01/01/2026", "30/06/2026"),
    ("01/07/2026", "31/12/2026"),
]

# Copie os cookies do browser após uma consulta manual:
# DevTools (F12) → Application → Cookies → copie name+value de cada cookie
COOKIES = {
    # "ASPSESSIONID...": "...",
}

# ──────────────────────────────────────────────
# HEADERS — replicados do HAR
# ──────────────────────────────────────────────

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/148.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Origin": "https://webapp1-arcos.cidade360.cloud",
    "Referer": f"{BASE_URL}/index.asp?acao=3&item=7",
    "sec-ch-ua": '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "same-origin",
    "sec-fetch-user": "?1",
    "Upgrade-Insecure-Requests": "1",
}

# Valor exato dos campos hnd de selects aninhados (com \r\n\t como no browser)
_SELECIONE = "\r\n\t\t\t\t\t\tSELECIONE\r\n\t\t\t\t\t"


# ──────────────────────────────────────────────
# FUNÇÕES
# ──────────────────────────────────────────────


def criar_sessao() -> requests.Session:
    s = requests.Session()
    s.headers.update(HEADERS)
    if COOKIES:
        s.cookies.update(COOKIES)
    return s


def limpar_historicos(session: requests.Session) -> bool:
    """POST acao.asp?acao=LimparHistoricos — obrigatório antes de cada consulta."""
    r = session.post(
        f"{BASE_URL}/acao.asp?acao=LimparHistoricos",
        data="",
        headers={
            "Content-Type": "text/plain;charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
        },
    )
    ok = r.status_code == 200
    print(f"  [LimparHistoricos] {r.status_code} {'✓' if ok else '✗'}")
    return ok


def montar_payload(entidade_val: str, data_inicial: str, data_final: str) -> dict:
    """
    Payload replicado fielmente do tráfego real (04/06/2026).
    Apenas cmbUnidadeCP, cmbAno, hndAno, txtDataInicial e txtDataFinal variam.
    Os campos hndUnidadeGestoraLC, hndOrgaoLC, hndEstoqueUnidadeGestoraLC,
    hndEstoqueAlmoxarifado, hndPatrimonioUnidadeGestoraLC e hndFrotasUnidadeGestora
    contêm \r\n\t exatamente como o browser envia.
    """
    partes = entidade_val.split("|")
    ano = partes[0]
    # cmbAno segue o padrão ANO|BANCO_ANO| — o banco do ano é sempre FC_XX
    # No payload real: 2026|DW_LC131_FC_27|
    # Derivamos substituindo o banco da entidade pelo do ano (último dígito +1 não é regra,
    # mas ambos os payloads reais mostram que cmbAno usa o mesmo banco que cmbUnidadeCP)
    cmb_ano = f"{ano}|{partes[1]}|" if len(partes) > 1 else f"{ano}||"

    return {
        # ── Identificação da tela ──────────────────────────────────
        "hndAcao": "3",
        "hndItem": "7",
        "anlLicenca": "09001027662",
        "anlSistema": "TB",
        "anlCliente": "webapp1-arcos.cidade360.cloud",
        "anlOpcao": "SU_INF_0004",
        "anlLogin": "govbr",
        "anlDescr": " Despesas por Função",
        "hndvisao": "1",
        "hndflagfiltrolicitacoes": "0",
        "hndflagfiltrocontratos": "0",
        # ── Campos AP ─────────────────────────────────────────────
        "hndAPDtIni": "",
        "hndAPLotacao": "",
        "hndAPCargo": "",
        "hndAPNivel": "",
        # ── Tipo exportação ───────────────────────────────────────
        "hndTipoEsportacaoDados": "",
        "cmbTipoEsportacaoDados": "2",
        # ── Publicações ───────────────────────────────────────────
        "txtNomePublicacoes": "",
        "cmbTemaPublicacoes": "",
        "hndAnoCargasPublicacoes": "",
        "cmbAnoCargasPublicacoes": "",
        "hndPeriodoPublicacao": "",
        "txtReferenciaDePublicacoes": "",
        "txtReferenciaAtePublicacoes": "",
        "cmbReferenciaDePublicacoes": "",
        "cmbReferenciaAtePublicacoes": "",
        "hndEntidadePublicacoes": "",
        "cmbEntidadePublicacoes": "",
        "cmbUnidadeGestoraPublicacoes": "",
        "hndOrdenacao": "",
        "cmbOrdenacao": "0",
        "hndCriterioOrdenacao": "",
        # ── LC ────────────────────────────────────────────────────
        "hndDataVigenciaLC": "SELECIONE",
        "cmbDataVigenciaLC": "",
        # ── Ano / Exercício ───────────────────────────────────────
        "hndAno": ano,
        "cmbAno": cmb_ano,
        # ── Arrecadação ───────────────────────────────────────────
        "hndSituacaoDividaAtivaAR": "PENDENTE",
        "cmbSituacaoDividaAtivaAR": "1",
        "txtNomeRazaoSocialInscritoDividaAtivaAR": "",
        "txtCPFCNPJInscritoDividaAtivaAR": "",
        "txtDataInicialAR": "",
        "txtDataFinalAR": "",
        "hndUnidadeGestoraAR": "SELECIONE",
        "cmbUnidadeGestoraAR": "",
        "hndExercicio": "SELECIONE",
        "cmbExercicio": "",
        "hndTipoMovimento": "",
        "cmbTipoMovimento": "0",
        # ── UG LC / Órgão LC (com \r\n\t exato do browser) ───────
        "hndUnidadeGestoraLC": _SELECIONE,
        "cmbUnidadeGestoraLC": "",
        "hndOrgaoLC": _SELECIONE,
        "cmbOrgaoLC": "",
        # ── ENTIDADE (campos variáveis) ───────────────────────────
        "hndUnidadeCP": entidade_val.split("|")[0] if False else "",  # servidor ignora
        "cmbUnidadeCP": entidade_val,
        # ── Contrato ──────────────────────────────────────────────
        "txtNumeroContrato": "",
        "txtAnoContrato": "",
        "hndSitProcessoLicit": "SELECIONE",
        "cmbSitProcessoLicit": "",
        "txtValorPagamentoDE": "",
        "txtValorPagamentoATE": "",
        "txtDataVencimentoDE": "",
        "txtDataVencimentoATE": "",
        "hndSitOrdemCrono": "",
        "cmbSitOrdemCrono": "",
        "txtFonteRecurso": "",
        "txtCodigoAplicacao": "",
        "txtNumeroProcesso": "",
        "txtNumeroModalidade": "",
        # ── Licitação ─────────────────────────────────────────────
        "hndModoExecucaoModalidade": "TODOS",
        "cmbModoExecucaoModalidade": "1",
        "hndRegistroPrecos": "TODOS",
        "cmbRegistroPrecos": "1",
        "hndDataFiltro": "",
        "cmbDataFiltro": "1",
        # ── PERÍODO (campos variáveis) ────────────────────────────
        "txtDataInicial": data_inicial,
        "txtDataFinal": data_final,
        "hndMesInicial": "",
        "hndMesFinal": "",
        # ── Gestão de Pessoas ─────────────────────────────────────
        "hndUnidadeGP": "",
        "hndVinculoGP": "TODOS",
        "cmbVinculoGP": "0",
        "hndAnoGP": "SELECIONE",
        "cmbAnoGP": "0",
        "cmbDataGP": "",
        "hndConcursoGP": "",
        "cmbConcursoGP": "0",
        "hndMesInicialGP": "SELECIONE",
        "cmbMesInicialGP": "0",
        "hndMesFinalGP": "SELECIONE",
        "cmbMesFinalGP": "0",
        # ── UG / Função ───────────────────────────────────────────
        "hndUnidadeGestora": "CONSOLIDADA",
        "cmbUnidadeGestora": "-1",
        "txtNomeFuncionario": "",
        "txtCargoFuncionario": "",
        "txtFaixaSalarialDE": "",
        "txtFaixaSalarialATE": "",
        "txtLotacaoFuncionario": "",
        "hndApresentarPorCP": "FUNÇÃO/PROGRAMA",
        "cmbApresentarPor": "0",
        "hndFuncao": "Todos",
        "cmbFuncao": "-1",
        # ── Estoque ───────────────────────────────────────────────
        "hndEstoqueDataVigenciaLC": "SELECIONE",
        "cmbEstoqueDataVigenciaLC": "",
        "hndEstoqueUnidadeGestoraLC": _SELECIONE,
        "cmbEstoqueUnidadeGestoraLC": "",
        "hndEstoqueAlmoxarifado": _SELECIONE,
        "cmbEstoqueAlmoxarifado": "",
        "txtEstoqueLocalizacao": "",
        "txtEstoqueMaterial": "",
        "hndEstoqueMesInicial": "",
        "hndEstoqueMesFinal": "SELECIONE",
        "cmbEstoqueMesFinal": "",
        "hndEstoqueTipoMovimento": "SELECIONE",
        "cmbEstoqueTipoMovimento": "-1",
        "txtEstoqueClassificacao": "",
        # ── Patrimônio ────────────────────────────────────────────
        "hndPatrimonioUnidadeGestoraLC": _SELECIONE,
        "cmbPatrimonioUnidadeGestoraLC": "",
        "txtPatrimonioDescricaoBem": "",
        "txtPatrimonioDataInicial": "",
        "txtPatrimonioDataFinal": "",
        "txtPatrimonioClassificacao": "",
        "txtPatrimonioLocalizacao": "",
        "hndPatrimonioSituacaoBem": "SELECIONE",
        "cmbPatrimonioSituacaoBem": "-1",
        "hndPatrimonioStatus": "SELECIONE",
        "cmbPatrimonioStatus": "-1",
        "hndPatrimonioTipoIngresso": "SELECIONE",
        "cmbPatrimonioTipoIngresso": "",
        # ── Frotas ────────────────────────────────────────────────
        "cmbFrotasUnidadeAF": "",
        "hndFrotasUnidadeGestora": _SELECIONE,
        "cmbFrotasUnidadeGestora": "",
        "hndFrotasTipoVeiculo": "SELECIONE",
        "cmbFrotasTipoVeiculo": "",
        "txtFrotasDescricao": "",
        "txtFrotasDataInicial": "",
        "txtFrotasDataFinal": "",
        "txtFrotasLocalizacao": "",
        "txtFrotasPlaca": "",
        "txtFrotasAnoFabricacao": "",
        "hndFrotasSituacaoVeiculo": "SELECIONE",
        "cmbFrotasSituacaoVeiculo": "-1",
        # ── GP Apresentar ─────────────────────────────────────────
        "hndApresentarPorGP": "SELECIONE",
        "hndApresentar": "",
        "ckTipoGestaoPessoas": "-1",
        "txtLotacaoCargo": "",
        # ── Tipos de empenho ──────────────────────────────────────
        "ckEmpenhoOrcamentario": "1",
        "ckEmpenhoExtra": "4",
        "ckEmpenhoResto": "2",
        # ── Credor / Fornecedor ───────────────────────────────────
        "txtNomeFornecedor": "",
        "hndSituacaoEmergenciaContratos": "TODOS",
        "cmbSituacaoEmergenciaContratos": "0",
        "txtCPFCNPJFornecedor": "",
        "hndDiariasPassagens": "",
        "txtCargoBenificiario": "",
        # ── Transferências ────────────────────────────────────────
        "hndTipoTransferencia": "SELECIONE",
        "cmbTipoTransferencia": "",
        "hndOrigemRecurso": "SELECIONE",
        "cmbOrigemRecurso": "-1",
        # ── Emendas ───────────────────────────────────────────────
        "txtEmendaAno": "",
        "txtEmendaNumero": "",
        "txtEmendaAutor": "",
        "txtEmendaObjeto": "",
        "hndEmendaModalidade": "",
        "cmbEmendaModalidade": "-1",
        "hndEmendaTipo": "",
        "cmbEmendaTipo": "-1",
        "hndEmendaTipoOperacao": "",
        "cmbEmendaTipoOperacao": "-1",
        "hndEmendaEsferaGoverno": "",
        "cmbEmendaEsferaGoverno": "-1",
        "txtEmpenho": "",
        # ── Situação de emergência / fonte ────────────────────────
        "hndSituacaoEmergenciaReceitasDespesas": "TODOS",
        "cmbSituacaoEmergenciaReceitasDespesas": "0",
        "hndFonteRecursoCodigoAplicacaoAcaoGoverno": "TODOS",
        "cmbFonteRecursoCodigoAplicacaoAcaoGoverno": "0",
        # ── Estado / Município ────────────────────────────────────
        "hndEstado": "",
        "cmbEstado": "-1",
        "hndMunicipio": "",
        "cmbMunicipio": "-1",
        # ── Contrato (valores) ────────────────────────────────────
        "txtValorContratoInicial": "",
        "txtValorContratoFinal": "",
        "ckContrato": "1",
        "txtObjeto": "",
        # ── Licitação (flags) ─────────────────────────────────────
        "hndLeiLicitacoes": "TODOS",
        "cmbLeiLicitacoes": "0",
        "hndLicitacaoCompartilhada": "TODOS",
        "cmbLicitacaoCompartilhada": "-1",
        "hndSituacaoEmergenciaLicitacoes": "TODOS",
        "cmbSituacaoEmergenciaLicitacoes": "0",
        # ── Produto / Categoria ───────────────────────────────────
        "txtDescricaoProduto": "",
        "hndCategoria": "",
        # ── Submit ────────────────────────────────────────────────
        "confirma": "Submit",
    }


def consultar_despesas(session, entidade_val, data_inicial, data_final):
    url = f"{BASE_URL}/index.asp?acao=3&item=7"
    payload = montar_payload(entidade_val, data_inicial, data_final)
    r = session.post(url, data=payload)
    print(f"  [Consulta] {r.status_code} | {len(r.content):,} bytes")
    return r.text if r.status_code == 200 else ""


def parsear_tabela(html: str) -> list[dict]:
    """
    Extrai SOMENTE id='tbTabela'.
    Row 0 = título | Row 1 = headers | Row 2+ = dados (última = Totais).
    """
    soup = BeautifulSoup(html, "html.parser")
    tabela = soup.find("table", {"id": "tbTabela"})

    if not tabela:
        tem_recaptcha = "recaptcha" in html.lower()
        tem_form = 'name="confirma"' in html
        print("  ✗ 'tbTabela' não encontrada.")
        if tem_recaptcha:
            print(
                "    → reCAPTCHA detectado: copie os cookies do browser para COOKIES no script."
            )
        elif tem_form:
            print(
                "    → Formulário retornado sem dados: sessão inválida ou payload incorreto."
            )
        return []

    rows = tabela.find_all("tr")
    if len(rows) < 3:
        print("  ✗ Tabela sem dados.")
        return []

    headers = [td.get_text(strip=True) for td in rows[1].find_all(["th", "td"])]
    print(f"  Headers ({len(headers)}): {headers}")

    registros = []
    for row in rows[2:]:
        cols = [td.get_text(strip=True) for td in row.find_all(["th", "td"])]
        if len(cols) == len(headers) and any(cols):
            registros.append(dict(zip(headers, cols)))

    return registros


def salvar_csv(dados: list[dict], nome: str):
    if not dados:
        print("  Nenhum dado para salvar.")
        return
    with open(nome, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=dados[0].keys(), delimiter=";")
        writer.writeheader()
        writer.writerows(dados)
    print(f"  ✓ Salvo: {nome} ({len(dados)} registros)")


# ──────────────────────────────────────────────
# EXECUÇÃO
# ──────────────────────────────────────────────


def main():
    session = criar_sessao()
    todos = []

    for nome_entidade, entidade_val in ENTIDADES.items():
        for data_ini, data_fim in PERIODOS:
            print(f"\n{'=' * 58}")
            print(f"Entidade : {nome_entidade}")
            print(f"Banco    : {entidade_val}")
            print(f"Período  : {data_ini} → {data_fim}")
            print(f"{'=' * 58}")

            limpar_historicos(session)
            time.sleep(0.5)

            html = consultar_despesas(session, entidade_val, data_ini, data_fim)
            if not html:
                continue

            registros = parsear_tabela(html)
            print(f"  Registros encontrados: {len(registros)}")

            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for reg in registros:
                reg["_entidade"] = nome_entidade
                reg["_banco"] = entidade_val
                reg["_periodo_ini"] = data_ini
                reg["_periodo_fim"] = data_fim
                reg["_coletado_em"] = ts

            todos.extend(registros)
            time.sleep(1)

    salvar_csv(todos, "despesas_funcao_consolidado.csv")

    if todos:
        print(f"\n{'=' * 58}")
        print(f"TOTAL: {len(todos)} registros\n")
        for r in todos:
            desc = r.get("Descrição", "?")
            pago = r.get("No Período - Valor Pago", "?")
            ent = r.get("_entidade", "?")
            per = f"{r.get('_periodo_ini', '')} → {r.get('_periodo_fim', '')}"
            print(f"  {ent[:30]:<30} | {desc:<25} | Pago: {pago:<18} | {per}")


if __name__ == "__main__":
    main()
