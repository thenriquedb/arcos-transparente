from __future__ import annotations

from fastapi.testclient import TestClient

import ui.server as server


client = TestClient(server.app)


def test_landing_renderiza_hero_e_link_para_chat() -> None:
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.text
    assert "Dados públicos de Arcos em linguagem simples" in body
    # CTA aponta para o chat montado na mesma origem.
    assert 'href="/chat"' in body


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
