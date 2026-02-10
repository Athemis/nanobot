"""LiteLLM provider implementation for multi-provider support."""

import json
import os
from typing import Any

import litellm
from litellm import acompletion
from loguru import logger

from nanobot.providers.base import LLMProvider, LLMResponse, ToolCallRequest
from nanobot.providers.registry import find_by_model, find_gateway


class LiteLLMProvider(LLMProvider):
    """
    LLM provider using LiteLLM for multi-provider support.

    Supports OpenRouter, Anthropic, OpenAI, Gemini, and many other providers through
    a unified interface.  Provider-specific logic is driven by the registry
    (see providers/registry.py) — no if-elif chains needed here.
    """

    def __init__(
        self,
        api_key: str | None = None,
        api_base: str | None = None,
        default_model: str = "anthropic/claude-opus-4-5",
        extra_headers: dict[str, str] | None = None,
        provider_name: str | None = None,
    ):
        super().__init__(api_key, api_base)
        self.default_model = default_model
        self.extra_headers = extra_headers or {}

        # Detect gateway / local deployment.
        # provider_name (from config key) is the primary signal;
        # api_key / api_base are fallback for auto-detection.
        self._gateway = find_gateway(provider_name, api_key, api_base)

        # Configure environment variables
        if api_key:
            self._setup_env(api_key, api_base, default_model)

        if api_base:
            litellm.api_base = api_base

        # Disable LiteLLM logging noise
        litellm.suppress_debug_info = True
        # Drop unsupported parameters for providers (e.g., gpt-5 rejects some params)
        litellm.drop_params = True

    def _setup_env(self, api_key: str, api_base: str | None, model: str) -> None:
        """Set environment variables based on detected provider."""
        spec = self._gateway or find_by_model(model)
        if not spec:
            return

        # Gateway/local overrides existing env; standard provider doesn't
        if self._gateway:
            os.environ[spec.env_key] = api_key
        else:
            os.environ.setdefault(spec.env_key, api_key)

        # Resolve env_extras placeholders:
        #   {api_key}  → user's API key
        #   {api_base} → user's api_base, falling back to spec.default_api_base
        effective_base = api_base or spec.default_api_base
        for env_name, env_val in spec.env_extras:
            resolved = env_val.replace("{api_key}", api_key)
            resolved = resolved.replace("{api_base}", effective_base)
            os.environ.setdefault(env_name, resolved)

    def _resolve_model(self, model: str) -> str:
        """Resolve model name by applying provider/gateway prefixes."""
        if self._gateway:
            # Gateway mode: apply gateway prefix, skip provider-specific prefixes
            prefix = self._gateway.litellm_prefix
            if self._gateway.strip_model_prefix:
                model = model.split("/")[-1]
            if prefix and not model.startswith(f"{prefix}/"):
                model = f"{prefix}/{model}"
            return model

        # Standard mode: auto-prefix for known providers
        spec = find_by_model(model)
        if spec and spec.litellm_prefix:
            if not any(model.startswith(s) for s in spec.skip_prefixes):
                model = f"{spec.litellm_prefix}/{model}"

        return model

    def _apply_model_overrides(self, model: str, kwargs: dict[str, Any]) -> None:
        """Apply model-specific parameter overrides from the registry."""
        model_lower = model.lower()
        spec = find_by_model(model)
        if spec:
            for pattern, overrides in spec.model_overrides:
                if pattern in model_lower:
                    kwargs.update(overrides)
                    return

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """
        Send a chat completion request via LiteLLM.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            tools: Optional list of tool definitions in OpenAI format.
            model: Model identifier (e.g., 'anthropic/claude-sonnet-4-5').
            max_tokens: Maximum tokens in response.
            temperature: Sampling temperature.

        Returns:
            LLMResponse with content and/or tool calls.
        """
        model = self._resolve_model(model or self.default_model)
        formatted_messages = self._format_messages_for_provider(messages, model)

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": formatted_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        # Apply model-specific overrides (e.g. kimi-k2.5 temperature)
        self._apply_model_overrides(model, kwargs)

        # Pass api_key directly — more reliable than env vars alone
        if self.api_key:
            kwargs["api_key"] = self.api_key

        # Pass api_base for custom endpoints
        if self.api_base:
            kwargs["api_base"] = self.api_base

        # Pass extra headers (e.g. APP-Code for AiHubMix)
        if self.extra_headers:
            kwargs["extra_headers"] = self.extra_headers

        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        try:
            response = await acompletion(**kwargs)
            return self._parse_response(response)
        except Exception as e:
            # Return error as content for graceful handling
            return LLMResponse(
                content=f"Error calling LLM: {str(e)}",
                finish_reason="error",
            )

    def _format_messages_for_provider(
        self, messages: list[dict[str, Any]], model: str
    ) -> list[dict[str, Any]]:
        """
        Format all messages in the list for the specific provider.

        Args:
            messages: List of message dicts.
            model: Model name.

        Returns:
            Formatted messages list.
        """
        formatted = []
        for msg in messages:
            formatted_msg = {"role": msg["role"]}
            if "content" in msg:
                formatted_msg["content"] = self._format_content_for_provider(
                    msg["content"], model
                )
            if "tool_calls" in msg:
                formatted_msg["tool_calls"] = msg["tool_calls"]
            if msg.get("role") == "tool":
                formatted_msg["tool_call_id"] = msg.get("tool_call_id")
                formatted_msg["name"] = msg.get("name")
            formatted.append(formatted_msg)
        return formatted

    def _parse_response(self, response: Any) -> LLMResponse:
        """Parse LiteLLM response into our standard format."""
        choice = response.choices[0]
        message = choice.message

        tool_calls = []
        if hasattr(message, "tool_calls") and message.tool_calls:
            for tc in message.tool_calls:
                # Parse arguments from JSON string if needed
                args = tc.function.arguments
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {"raw": args}

                tool_calls.append(ToolCallRequest(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=args,
                ))

        usage = {}
        if hasattr(response, "usage") and response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
        reasoning_content = getattr(message, "reasoning_content", None)

        return LLMResponse(
            content=message.content,
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason or "stop",
            usage=usage,
            reasoning_content=reasoning_content,
        )

    def get_default_model(self) -> str:
        """Get the default model."""
        return self.default_model

    def _has_image_content(self, content: Any) -> bool:
        """Check if content contains image data."""
        if isinstance(content, str):
            return False
        if isinstance(content, list):
            return any(item.get("type") == "image_url" for item in content)
        return False

    def _format_content_for_provider(self, content: Any, model: str) -> Any:
        """
        Format message content for specific provider's multimodal format.

        Args:
            content: Message content (str or list with images)
            model: Model name to determine format

        Returns:
            Formatted content for the provider
        """
        # Handle text-only content
        if isinstance(content, str):
            return content

        # No images, return as-is
        if not self._has_image_content(content):
            return content

        # Format for specific provider
        model_lower = model.lower()
        if "claude" in model_lower or "anthropic" in model_lower:
            return self._format_for_claude(content)
        elif "gemini" in model_lower:
            return self._format_for_gemini(content)
        else:
            # Default to OpenAI format (already in image_url format)
            return content

    def _format_for_claude(self, content: list) -> list:
        """
        Format content for Claude vision API.

        Claude expects: {"type": "image", "source": {"type": "base64", "media_type": "...", "data": "..."}}
        """
        formatted = []
        for item in content:
            if item.get("type") == "image_url":
                # Parse data URL (format: data:mime/type;base64,data)
                url = item["image_url"]["url"]
                if url.startswith("data:"):
                    try:
                        # Remove "data:" prefix and split
                        mime_and_data = url[5:]
                        if ";base64," in mime_and_data:
                            mime_type, b64_data = mime_and_data.split(";base64,", 1)
                            formatted.append({
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": mime_type,
                                    "data": b64_data
                                }
                            })
                        else:
                            logger.warning(f"Invalid data URL format for Claude: {url[:50]}...")
                            continue
                    except Exception as e:
                        logger.error(f"Error formatting image for Claude: {e}")
                        continue
                else:
                    # Regular URL (not supported for Claude, need base64)
                    logger.warning("Claude vision requires base64-encoded images, not URLs")
                    continue
            elif item.get("type") == "text":
                formatted.append({"type": "text", "text": item["text"]})
        return formatted

    def _format_for_gemini(self, content: list) -> list:
        """
        Format content for Gemini vision API.

        Gemini expects: {"inline_data": {"mime_type": "...", "data": "..."}}
        """
        parts = []
        for item in content:
            if item.get("type") == "image_url":
                # Parse data URL
                url = item["image_url"]["url"]
                if url.startswith("data:"):
                    try:
                        mime_and_data = url[5:]
                        if ";base64," in mime_and_data:
                            mime_type, b64_data = mime_and_data.split(";base64,", 1)
                            parts.append({
                                "inline_data": {
                                    "mime_type": mime_type,
                                    "data": b64_data
                                }
                            })
                        else:
                            logger.warning(f"Invalid data URL format for Gemini: {url[:50]}...")
                            continue
                    except Exception as e:
                        logger.error(f"Error formatting image for Gemini: {e}")
                        continue
                else:
                    logger.warning("Gemini vision requires base64-encoded images, not URLs")
                    continue
            elif item.get("type") == "text":
                parts.append({"text": item["text"]})
        return parts
