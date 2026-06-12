"""Camada de compreensão de linguagem natural (NLU) do chatbot cidadão.

Concentra a leitura estruturada de perguntas (`reading`), os extractors de
entidades, a normalização conversacional, os detectores determinísticos de
domínio e os predicados de intenção usados pela seleção híbrida de tools e pelos
guardrails. Substitui o antigo pacote `agents/routing` após a remoção do router
legado.
"""

from __future__ import annotations
