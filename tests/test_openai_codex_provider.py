import ssl
from types import SimpleNamespace

import httpx
import pytest

from nanobot.cli.commands import _make_provider
from nanobot.config.schema import Config
from nanobot.providers.openai_codex_provider import OpenAICodexProvider


@pytest.mark.asyncio
async def test_codex_chat_does_not_retry_with_insecure_tls(monkeypatch) -> None:
    calls: list[bool] = []

    async def _fake_request_codex(
        url: str, headers: dict[str, str], body: dict[str, object], verify: bool
    ):
        calls.append(verify)
        try:
            raise ssl.SSLCertVerificationError("certificate verify failed")
        except ssl.SSLCertVerificationError as cert_err:
            raise httpx.ConnectError("tls failure") from cert_err

    monkeypatch.setattr(
        "nanobot.providers.openai_codex_provider.get_codex_token",
        lambda: SimpleNamespace(account_id="acc", access="tok"),
    )
    monkeypatch.setattr(
        "nanobot.providers.openai_codex_provider._request_codex", _fake_request_codex
    )

    provider = OpenAICodexProvider()
    response = await provider.chat(messages=[{"role": "user", "content": "hi"}])

    assert calls == [True]
    assert response.finish_reason == "error"
    assert "TLS certificate verification failed" in response.content


@pytest.mark.asyncio
async def test_codex_chat_returns_sanitized_network_error(monkeypatch) -> None:
    calls: list[bool] = []

    async def _fake_request_codex(
        url: str, headers: dict[str, str], body: dict[str, object], verify: bool
    ):
        calls.append(verify)
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(
        "nanobot.providers.openai_codex_provider.get_codex_token",
        lambda: SimpleNamespace(account_id="acc", access="tok"),
    )
    monkeypatch.setattr(
        "nanobot.providers.openai_codex_provider._request_codex", _fake_request_codex
    )

    provider = OpenAICodexProvider()
    response = await provider.chat(messages=[{"role": "user", "content": "hi"}])

    assert calls == [True]
    assert response.finish_reason == "error"
    assert response.content == "Error calling Codex: Network error while calling Codex."


@pytest.mark.asyncio
async def test_codex_chat_sanitizes_untrusted_error_details(monkeypatch) -> None:
    async def _fake_request_codex(
        url: str, headers: dict[str, str], body: dict[str, object], verify: bool
    ):
        raise RuntimeError("upstream leaked secret_token=abc123")

    monkeypatch.setattr(
        "nanobot.providers.openai_codex_provider.get_codex_token",
        lambda: SimpleNamespace(account_id="acc", access="tok"),
    )
    monkeypatch.setattr(
        "nanobot.providers.openai_codex_provider._request_codex", _fake_request_codex
    )

    provider = OpenAICodexProvider()
    response = await provider.chat(messages=[{"role": "user", "content": "hi"}])

    assert response.finish_reason == "error"
    assert response.content == "Error calling Codex: Codex request failed."
    assert "secret_token=abc123" not in response.content


def test_make_provider_uses_codex_provider_without_api_key() -> None:
    config = Config.model_validate(
        {
            "agents": {"defaults": {"model": "openai-codex/gpt-5.1-codex"}},
            "providers": {"openai_codex": {}},
        }
    )

    provider = _make_provider(config)

    assert isinstance(provider, OpenAICodexProvider)
