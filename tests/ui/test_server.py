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
