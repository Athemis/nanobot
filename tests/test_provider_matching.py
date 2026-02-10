from nanobot.config.schema import Config


def test_fallback_prefers_key_based_provider_over_oauth_default() -> None:
    cfg = Config.model_validate(
        {
            "agents": {"defaults": {"model": "custom-model"}},
            "providers": {
                "deepseek": {"api_key": "deepseek-key"},
            },
        }
    )

    assert cfg.get_provider_name("custom-model") == "deepseek"
    assert cfg.get_api_key("custom-model") == "deepseek-key"


def test_oauth_provider_still_matches_by_keyword_without_api_key() -> None:
    cfg = Config.model_validate(
        {
            "agents": {"defaults": {"model": "openai-codex/gpt-5.1-codex"}},
            "providers": {},
        }
    )

    assert cfg.get_provider_name("openai-codex/gpt-5.1-codex") == "openai_codex"


def test_oauth_provider_can_be_generic_fallback_if_explicitly_configured() -> None:
    cfg = Config.model_validate(
        {
            "agents": {"defaults": {"model": "custom-model"}},
            "providers": {
                "openai_codex": {"api_base": "https://chatgpt.com/backend-api"},
            },
        }
    )

    assert cfg.get_provider_name("custom-model") == "openai_codex"


def test_fallback_respects_provider_order_between_key_and_oauth() -> None:
    cfg = Config.model_validate(
        {
            "agents": {"defaults": {"model": "custom-model"}},
            "providers": {
                "gemini": {"api_key": "gemini-key"},
                "openai_codex": {"api_base": "https://chatgpt.com/backend-api"},
            },
        }
    )

    assert cfg.get_provider_name("custom-model") == "openai_codex"
