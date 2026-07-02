from __future__ import annotations

import re

from fastapi.testclient import TestClient

import ui.server as server


client = TestClient(server.app)


def test_landing_renderiza_hero_e_link_para_chat() -> None:
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.text
    assert "As contas públicas de Arcos, explicadas numa conversa" in body
    # CTA aponta para o chat montado na mesma origem.
    assert 'href="/chat"' in body


def test_landing_tem_og_image() -> None:
    body = client.get("/").text
    assert 'property="og:image"' in body
    assert "/static/og-image.svg" in body


def test_og_image_servido() -> None:
    resp = client.get("/static/og-image.svg")
    assert resp.status_code == 200
    assert "image/svg+xml" in resp.headers["content-type"]


def test_landing_mockup_rotulado_e_disclaimer_ia() -> None:
    # Normaliza espacos: o formatter pode quebrar textos em varias linhas.
    body = re.sub(r"\s+", " ", client.get("/").text)
    # Mockup deve deixar claro que e ilustrativo (sem dados reais de pessoa).
    assert "Exemplo ilustrativo" in body
    # Disclaimer honesto sobre IA na propria landing.
    assert "geradas por IA" in body
    # Rotulo de bot em vez de "online" (que sugeriria atendente humano).
    assert "Assistente automático" in body


def test_privacidade_pagina() -> None:
    resp = client.get("/privacidade")
    assert resp.status_code == 200
    body = resp.text
    assert "Privacidade" in body
    assert "OpenAI" in body
    assert "LGPD" in body


def test_landing_linka_privacidade() -> None:
    assert 'href="/privacidade"' in client.get("/").text


def test_chat_welcome_tem_disclaimer_e_privacidade() -> None:
    md = client.get("/chat/project/settings").json().get("markdown") or ""
    assert "IA" in md
    assert "/privacidade" in md
    assert "não substitui" in md


def test_chat_header_links_para_site_e_privacidade() -> None:
    ui = client.get("/chat/project/settings").json().get("ui", {})
    urls = {link.get("url") for link in (ui.get("header_links") or [])}
    assert "/" in urls
    assert "/privacidade" in urls
    assert "/cobertura" in urls


def test_cobertura_pagina() -> None:
    resp = client.get("/cobertura")
    assert resp.status_code == 200
    body = resp.text
    # Grupos fieis aos dominios de tools do agente.
    for termo in ["Gastos e despesas", "Contratos e licitações", "Câmara Municipal", "Frota"]:
        assert termo in body
    # Periodo dos dados (fonte unica).
    assert server.DATA_RANGE in body
    # Disclaimer honesto de IA.
    assert "podem conter erros" in body


def test_cobertura_deixa_claro_somente_leitura_e_publico() -> None:
    body = re.sub(r"\s+", " ", client.get("/cobertura").text)
    assert "Apenas consulta" in body
    assert "nunca altera, apaga ou insere" in body
    assert "Todas as informações são públicas" in body
    # Codigo aberto como sinal de confianca (auditavel).
    assert "Código aberto" in body
    assert "qualquer pessoa pode inspecionar" in body


def test_cobertura_estrutura_de_documentacao() -> None:
    body = re.sub(r"\s+", " ", client.get("/cobertura").text)
    # Responde as perguntas-chave do usuario.
    assert "O que você pode perguntar ao Arcos Transparente" in body
    assert "Você pode perguntar" in body
    assert "Dados utilizados" in body
    # Secoes por tipo.
    for secao in ["Dinheiro público", "Pessoas e remuneração", "Patrimônio e operação", "Cidade e representação"]:
        assert secao in body
    # Reduz expectativas + FAQ.
    assert "O que ainda não está disponível" in body
    assert "Perguntas frequentes" in body
    assert "Como a IA usa os dados" in body


def test_landing_linka_cobertura() -> None:
    assert 'href="/cobertura"' in client.get("/").text


def test_sitemap_inclui_paginas() -> None:
    body = client.get("/sitemap.xml").text
    assert "/cobertura" in body
    assert "/privacidade" in body


def test_data_range_consistente_entre_paginas() -> None:
    # Fonte unica: landing, privacidade e welcome do chat exibem o mesmo periodo.
    dr = server.DATA_RANGE
    assert dr in client.get("/").text
    assert dr in client.get("/privacidade").text
    welcome = client.get("/chat/project/settings").json().get("markdown") or ""
    assert dr in welcome


def test_static_css_servido() -> None:
    resp = client.get("/static/app.css")
    assert resp.status_code == 200
    assert "--color-primary" in resp.text


def test_robots_aponta_para_sitemap() -> None:
    resp = client.get("/robots.txt")
    assert resp.status_code == 200
    assert "Sitemap:" in resp.text
    assert "/sitemap.xml" in resp.text


def test_sitemap_xml() -> None:
    resp = client.get("/sitemap.xml")
    assert resp.status_code == 200
    assert "<urlset" in resp.text


def test_landing_tem_cabecalhos_de_seguranca() -> None:
    resp = client.get("/")
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert resp.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    csp = resp.headers["Content-Security-Policy"]
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    # script-src restrito a 'self' (sem unsafe-inline/eval).
    assert "script-src 'self'" in csp


def test_landing_nao_usa_cdn_de_terceiros() -> None:
    body = client.get("/").text
    assert "cdn.tailwindcss.com" not in body
    assert "unpkg.com" not in body
    assert "/static/tailwind.css" in body
    assert "/static/vendor/lucide.min.js" in body


def test_chat_nao_recebe_csp() -> None:
    # A SPA do Chainlit quebraria sob CSP estrita; deve ficar de fora.
    resp = client.get("/chat/")
    assert "Content-Security-Policy" not in resp.headers


def test_base_url_usa_origem_da_requisicao_sem_env() -> None:
    # Sem PUBLIC_BASE_URL, canonical/sitemap usam a origem da requisicao.
    resp = client.get("/sitemap.xml")
    assert "http://testserver/" in resp.text
