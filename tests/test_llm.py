from __future__ import annotations

import httpx
import pytest

from voxless.config import OllamaConfig
from voxless.llm import OllamaClient


def _client_with(handler) -> OllamaClient:
    transport = httpx.MockTransport(handler)
    http = httpx.Client(transport=transport, timeout=5.0)
    cfg = OllamaConfig(model="gemma3:1b", url="http://test")
    return OllamaClient(cfg, client=http)


def test_returns_cleaned_text() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/chat"
        body = request.read().decode()
        assert "gemma3:1b" in body
        return httpx.Response(200, json={"message": {"content": "Hola mundo."}})

    client = _client_with(handler)
    assert client.clean("eh hola mundo", "system") == "Hola mundo."


def test_falls_back_to_raw_on_http_error() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    client = _client_with(handler)
    assert client.clean("texto crudo", "system") == "texto crudo"


def test_falls_back_to_raw_on_empty_response() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"message": {"content": "   "}})

    client = _client_with(handler)
    assert client.clean("texto crudo", "system") == "texto crudo"


def test_disabled_returns_input_unchanged() -> None:
    cfg = OllamaConfig(enabled=False)
    client = OllamaClient(cfg, client=httpx.Client())
    assert client.clean("foo", "sys") == "foo"


def test_empty_input_short_circuits() -> None:
    cfg = OllamaConfig()
    client = OllamaClient(cfg, client=httpx.Client())
    assert client.clean("", "sys") == ""
