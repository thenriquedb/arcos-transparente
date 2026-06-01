"""Parser XML para documentos de despesa."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from loguru import logger
from pydantic import ValidationError

from ingestion.parsers.xml.shared import parse_xml_root
from ingestion.schemas.despesas import (
    DespesaDocumentoComprobatorioInSchema,
    DespesaDocumentoInSchema,
    DespesaDocumentoItemInSchema,
)


class DespesasParser:
    """Converte empenhos, restos a pagar e documentos extras em registros."""

    def parse(self, filepath: str) -> list[dict[str, Any]]:
        root = parse_xml_root(filepath)
        tipo_origem = self._infer_tipo_origem(root.tag, filepath)
        origem_arquivo = self._infer_origem(filepath)
        registros: list[dict[str, Any]] = []
        invalidos = 0

        arquivo_origem = Path(filepath).name
        for sequencia, node in enumerate(root.findall("./Principal"), start=1):
            unidade_gestora = self._txt(node, "UnidadeGestora")
            origem = self._resolve_origem(origem_arquivo, unidade_gestora)
            if tipo_origem == "documento_extra":
                payload_raw = self._parse_documento_extra(
                    node,
                    origem=origem,
                    arquivo_origem=arquivo_origem,
                    sequencia_origem=sequencia,
                )
            else:
                payload_raw = self._parse_documento_orcamentario(
                    node,
                    origem=origem,
                    tipo_origem=tipo_origem,
                    arquivo_origem=arquivo_origem,
                    sequencia_origem=sequencia,
                )

            try:
                payload = DespesaDocumentoInSchema.model_validate(payload_raw)
            except ValidationError as exc:
                invalidos += 1
                logger.warning(f"Descartando documento de despesa invalido: {exc}")
                continue

            registros.append(payload.model_dump(mode="python"))

        if invalidos:
            logger.info(
                f"Descartados {invalidos} documentos de despesa invalidos em {filepath}"
            )

        return registros

    def _parse_documento_orcamentario(
        self,
        node: ET.Element,
        *,
        origem: str,
        tipo_origem: str,
        arquivo_origem: str,
        sequencia_origem: int,
    ) -> dict[str, Any]:
        return {
            "tipo_origem": tipo_origem,
            "arquivo_origem": arquivo_origem,
            "sequencia_origem": sequencia_origem,
            "origem": origem,
            "exercicio": self._txt(node, "Exercicio"),
            "unidade_gestora": self._txt(node, "UnidadeGestora"),
            "orgao": self._txt(node, "Orgao"),
            "unidade": self._txt(node, "Unidade"),
            "departamento": self._txt(node, "Departamento"),
            "funcao": self._txt(node, "Funcao"),
            "subfuncao": self._txt(node, "SubFuncao"),
            "programa": self._txt(node, "Programa"),
            "tipo_acao": self._nested_txt(node, "Acao", "Tipo"),
            "descricao_acao": self._nested_txt(node, "Acao", "Descricao"),
            "fonte_recurso_identificacao": self._nested_txt(
                node, "FonteRecurso", "Identificacao"
            ),
            "fonte_recurso_descricao": self._nested_txt(
                node, "FonteRecurso", "Descricao"
            ),
            "esfera_administrativa": self._txt(node, "EsferaAdministrativa"),
            "modalidade_aplicacao_identificacao": self._nested_txt(
                node, "ModalidadeAplicacao", "Identificacao"
            ),
            "modalidade_aplicacao_descricao": self._nested_txt(
                node, "ModalidadeAplicacao", "Descricao"
            ),
            "categoria_economica_identificacao": self._nested_txt(
                node, "CategoriaEconomica", "Identificacao"
            ),
            "categoria_economica_descricao": self._nested_txt(
                node, "CategoriaEconomica", "Descricao"
            ),
            "grupo_despesa_identificacao": self._nested_txt(
                node, "GrupoDespesa", "Identificacao"
            ),
            "grupo_despesa_descricao": self._nested_txt(
                node, "GrupoDespesa", "Descricao"
            ),
            "elemento_despesa_identificacao": self._nested_txt(
                node, "ElementoDespesa", "Identificacao"
            ),
            "elemento_despesa_descricao": self._nested_txt(
                node, "ElementoDespesa", "Descricao"
            ),
            "desdobramento_despesa_identificacao": self._nested_txt(
                node, "DesdobramentoDespesa", "Identificacao"
            ),
            "desdobramento_despesa_descricao": self._nested_txt(
                node, "DesdobramentoDespesa", "Descricao"
            ),
            "numero_documento": self._txt(node, "NumeroEmpenho"),
            "data_documento": self._txt(node, "DataEmissaoEmpenho"),
            "categoria_documento": self._txt(node, "CategoriaEmpenho"),
            "credor": self._txt(node, "Credor"),
            "cpf_cnpj": self._txt(node, "CPFCNPJ"),
            "modalidade_licitacao": self._txt(node, "ModalidadeLicitacao"),
            "numero_licitacao": self._txt(node, "NumeroLicitacao"),
            "ano_licitacao": self._txt(node, "AnoLicitacao"),
            "data_homologacao": self._txt(node, "DataHomologacao"),
            "processo_compra": self._txt(node, "ProcessoCompra"),
            "numero_contrato": self._txt(node, "NumeroContrato"),
            "numero_convenio": self._txt(node, "NumeroConvenio"),
            "valor_documento": self._txt(node, "ValorEmpenhado"),
            "valor_empenhado": self._txt(node, "ValorEmpenhado"),
            "valor_liquidacao": self._txt(node, "ValorLiquidacao"),
            "valor_liquidado": self._txt(node, "ValorLiquidado"),
            "valor_pago": self._txt(node, "ValorPago"),
            "valor_anulado": self._txt(node, "ValorAnulado"),
            "objetivo_viagem": self._txt(node, "ObjetivoViagem"),
            "legislacao_associada": self._txt(node, "LegislacaoAssociada"),
            "ato_legal": self._txt(node, "AtoLegal"),
            "destino": self._txt(node, "Destino"),
            "data_inicial_viagem": self._txt(node, "DataInicialViagem"),
            "data_final_viagem": self._txt(node, "DataFinalViagem"),
            "quantidade_dias_diarias": self._txt(node, "QuantidadeDiasDiarias"),
            "valor_diaria": self._txt(node, "ValorDiaria"),
            "valor_total": self._txt(node, "ValorTotal"),
            "itens": self._parse_itens(node),
            "documentos_comprobatorios": self._parse_comprobatorios(node),
        }

    def _parse_documento_extra(
        self,
        node: ET.Element,
        *,
        origem: str,
        arquivo_origem: str,
        sequencia_origem: int,
    ) -> dict[str, Any]:
        return {
            "tipo_origem": "documento_extra",
            "arquivo_origem": arquivo_origem,
            "sequencia_origem": sequencia_origem,
            "origem": origem,
            "exercicio": self._txt(node, "Exercicio"),
            "unidade_gestora": self._txt(node, "UnidadeGestora"),
            "conta_extra_identificacao": self._nested_txt(
                node, "ContaExtraorcamentaria", "Identificacao"
            ),
            "conta_extra_descricao": self._nested_txt(
                node, "ContaExtraorcamentaria", "Descricao"
            ),
            "numero_documento": self._txt(node, "NumeroDocumento"),
            "data_documento": self._txt(node, "DataEmissaoDocumento"),
            "credor": self._txt(node, "Credor"),
            "cpf_cnpj": self._txt(node, "CPFCNPJ"),
            "modalidade_licitacao": self._txt(node, "ModalidadeLicitacao"),
            "numero_licitacao": self._txt(node, "NumeroLicitacao"),
            "ano_licitacao": self._txt(node, "AnoLicitacao"),
            "data_homologacao": self._txt(node, "DataHomologacao"),
            "processo_compra": self._txt(node, "ProcessoCompra"),
            "numero_contrato": self._txt(node, "NumeroContrato"),
            "valor_documento": self._txt(node, "ValorDocumenro")
            or self._txt(node, "ValorDocumento"),
            "valor_pago": self._txt(node, "ValorPago"),
            "valor_anulado": self._txt(node, "ValorAnulado"),
            "itens": self._parse_itens(node),
        }

    def _parse_itens(self, node: ET.Element) -> list[dict[str, Any]]:
        itens: list[dict[str, Any]] = []
        for ordem, item_node in enumerate(node.findall("./Itens/Item"), start=1):
            payload_raw = {
                "ordem": ordem,
                "numero_item": self._txt(item_node, "Numero"),
                "descricao_item": self._txt(item_node, "Item"),
                "quantidade": self._txt(item_node, "Quantidade"),
                "valor_unitario": self._txt(item_node, "ValorUnitario"),
                "valor_total": self._txt(item_node, "ValorTotal"),
            }
            try:
                item = DespesaDocumentoItemInSchema.model_validate(payload_raw)
            except ValidationError:
                continue
            itens.append(item.model_dump(mode="python"))
        return itens

    def _parse_comprobatorios(self, node: ET.Element) -> list[dict[str, Any]]:
        documentos: list[dict[str, Any]] = []
        path = "./documentosComprobatorios/DocumentosComprobatorios"
        for ordem, doc_node in enumerate(node.findall(path), start=1):
            payload_raw = {
                "ordem": ordem,
                "data_liquidacao": self._txt(doc_node, "dt_liquidacao"),
                "codigo_tipo_documento": self._txt(doc_node, "cod_tipo_documento"),
                "descricao_tipo_documento": self._txt(doc_node, "desc_tipo_documento"),
                "numero_documento": self._txt(doc_node, "num_documento"),
                "serie_modelo_nota_fiscal": self._txt(
                    doc_node, "serie_modelo_nota_fiscal"
                ),
                "descricao_serie": self._txt(doc_node, "desc_serie"),
                "chave_acesso": self._txt(doc_node, "chave_acesso"),
                "data_emissao_documento": self._txt(doc_node, "dt_emissao_documento"),
                "valor_documento": self._txt(doc_node, "valor_documento"),
                "numero_empenho": self._txt(doc_node, "nr_empenho"),
                "codigo_unidade_gestora": self._txt(doc_node, "cdUnidadeGestora"),
                "numero_sequencia": self._txt(doc_node, "nrSequencia"),
            }
            try:
                documento = DespesaDocumentoComprobatorioInSchema.model_validate(
                    payload_raw
                )
            except ValidationError:
                continue
            documentos.append(documento.model_dump(mode="python"))
        return documentos

    @staticmethod
    def _infer_tipo_origem(root_tag: str, filepath: str) -> str:
        root_normalized = root_tag.lower()
        nome = Path(filepath).name.lower()
        if root_normalized == "documentosextras" or "documentos-extras" in nome:
            return "documento_extra"
        if root_normalized == "restospagar" or "restos-a-pagar" in nome:
            return "restos_a_pagar"
        return "empenho"

    @staticmethod
    def _infer_origem(filepath: str) -> str:
        nome = Path(filepath).name.lower()
        if "saude" in nome or "saúde" in nome:
            return "saude"
        if "prefeitura" in nome:
            return "prefeitura"
        if "camara" in nome or "câmara" in nome:
            return "camara"
        return "nao_informado"

    @staticmethod
    def _resolve_origem(origem_arquivo: str, unidade_gestora: str | None) -> str:
        if origem_arquivo != "nao_informado":
            return origem_arquivo
        unidade = (unidade_gestora or "").lower()
        if "camara" in unidade or "câmara" in unidade:
            return "camara"
        if "saude" in unidade or "saúde" in unidade or "fundação" in unidade:
            return "saude"
        if "prefeitura" in unidade:
            return "prefeitura"
        return "nao_informado"

    @staticmethod
    def _txt(node: ET.Element, tag: str) -> str | None:
        child = node.find(tag)
        if child is None or child.text is None:
            return None
        value = child.text.strip()
        return value or None

    def _nested_txt(
        self,
        node: ET.Element,
        parent_tag: str,
        child_tag: str,
    ) -> str | None:
        parent = node.find(parent_tag)
        if parent is None:
            return None
        return self._txt(parent, child_tag)
