"""Le réseau réel est interdit en test : un appel externe non remplacé échoue bruyamment."""
import httpx
import pytest


def test_real_http_call_is_blocked():
    with pytest.raises(RuntimeError, match="Réseau interdit"):
        httpx.get("http://example.invalid")


async def _async_get():
    async with httpx.AsyncClient() as client:
        await client.get("http://example.invalid")


def test_real_async_http_call_is_blocked():
    import asyncio

    with pytest.raises(RuntimeError, match="Réseau interdit"):
        asyncio.run(_async_get())


def test_mock_transport_still_works():
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200)))
    assert client.get("http://example.invalid").status_code == 200
