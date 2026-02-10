from types import SimpleNamespace

import pytest

from nanobot.providers.openai_codex_provider import OpenAICodexProvider


@pytest.mark.asyncio
async def test_codex_chat_keeps_tls_verification_without_opt_in(monkeypatch) -> None:
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

    provider = OpenAICodexProvider(allow_insecure_tls_fallback=False)
    response = await provider.chat(messages=[{"role": "user", "content": "hi"}])

    assert calls == [True]
    assert response.finish_reason == "error"
    assert "CERTIFICATE_VERIFY_FAILED" in response.content


@pytest.mark.asyncio
async def test_codex_chat_retries_without_tls_verification_with_opt_in(
    monkeypatch,
) -> None:
    calls: list[bool] = []
    warnings: list[str] = []

    async def _fake_request_codex(
        url: str, headers: dict[str, str], body: dict[str, object], verify: bool
    ):
        calls.append(verify)
        if verify:
            raise RuntimeError("CERTIFICATE_VERIFY_FAILED")
        return "ok", [], "stop"

    monkeypatch.setattr(
        "nanobot.providers.openai_codex_provider.get_codex_token",
        lambda: SimpleNamespace(account_id="acc", access="tok"),
    )
    monkeypatch.setattr(
        "nanobot.providers.openai_codex_provider._request_codex", _fake_request_codex
    )
    monkeypatch.setattr(
        "nanobot.providers.openai_codex_provider.logger.warning",
        lambda msg: warnings.append(msg),
    )

    provider = OpenAICodexProvider(allow_insecure_tls_fallback=True)
    response = await provider.chat(messages=[{"role": "user", "content": "hi"}])

    assert calls == [True, False]
    assert response.finish_reason == "stop"
    assert response.content == "ok"
    assert any("allow_insecure_tls_fallback" in msg for msg in warnings)
