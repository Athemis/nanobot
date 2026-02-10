from types import SimpleNamespace

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
        raise RuntimeError("CERTIFICATE_VERIFY_FAILED")

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
    assert "CERTIFICATE_VERIFY_FAILED" in response.content


def test_make_provider_uses_codex_provider_without_api_key() -> None:
    config = Config.model_validate(
        {
            "agents": {"defaults": {"model": "openai-codex/gpt-5.1-codex"}},
            "providers": {"openai_codex": {}},
        }
    )

    provider = _make_provider(config)

    assert isinstance(provider, OpenAICodexProvider)
