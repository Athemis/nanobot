"""Configuration schema using Pydantic."""

from pathlib import Path

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings


class WhatsAppConfig(BaseModel):
    """WhatsApp channel configuration."""
    enabled: bool = False
    bridge_url: str = "ws://localhost:3001"
    allow_from: list[str] = Field(default_factory=list)  # Allowed phone numbers


class TelegramConfig(BaseModel):
    """Telegram channel configuration."""
    enabled: bool = False
    token: str = ""  # Bot token from @BotFather
    allow_from: list[str] = Field(default_factory=list)  # Allowed user IDs or usernames
    proxy: str | None = None  # HTTP/SOCKS5 proxy URL, e.g. "http://127.0.0.1:7890" or "socks5://127.0.0.1:1080"


class FeishuConfig(BaseModel):
    """Feishu/Lark channel configuration using WebSocket long connection."""
    enabled: bool = False
    app_id: str = ""  # App ID from Feishu Open Platform
    app_secret: str = ""  # App Secret from Feishu Open Platform
    encrypt_key: str = ""  # Encrypt Key for event subscription (optional)
    verification_token: str = ""  # Verification Token for event subscription (optional)
    allow_from: list[str] = Field(default_factory=list)  # Allowed user open_ids


class DingTalkConfig(BaseModel):
    """DingTalk channel configuration using Stream mode."""
    enabled: bool = False
    client_id: str = ""  # AppKey
    client_secret: str = ""  # AppSecret
    allow_from: list[str] = Field(default_factory=list)  # Allowed staff_ids


class DiscordConfig(BaseModel):
    """Discord channel configuration."""
    enabled: bool = False
    token: str = ""  # Bot token from Discord Developer Portal
    allow_from: list[str] = Field(default_factory=list)  # Allowed user IDs
    gateway_url: str = "wss://gateway.discord.gg/?v=10&encoding=json"
    intents: int = 37377  # GUILDS + GUILD_MESSAGES + DIRECT_MESSAGES + MESSAGE_CONTENT

class EmailConfig(BaseModel):
    """Email channel configuration (IMAP inbound + SMTP outbound)."""
    enabled: bool = False
    consent_granted: bool = False  # Explicit owner permission to access mailbox data

    # IMAP (receive)
    imap_host: str = ""
    imap_port: int = 993
    imap_username: str = ""
    imap_password: str = ""
    imap_mailbox: str = "INBOX"
    imap_use_ssl: bool = True

    # SMTP (send)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    smtp_use_ssl: bool = False
    from_address: str = ""

    # Behavior
    auto_reply_enabled: bool = True  # If false, inbound email is read but no automatic reply is sent
    poll_interval_seconds: int = 30
    mark_seen: bool = True
    max_body_chars: int = 12000
    subject_prefix: str = "Re: "
    allow_from: list[str] = Field(default_factory=list)  # Allowed sender email addresses


class MochatMentionConfig(BaseModel):
    """Mochat mention behavior configuration."""
    require_in_groups: bool = False


class MochatGroupRule(BaseModel):
    """Mochat per-group mention requirement."""
    require_mention: bool = False


class MochatConfig(BaseModel):
    """Mochat channel configuration."""
    enabled: bool = False
    base_url: str = "https://mochat.io"
    socket_url: str = ""
    socket_path: str = "/socket.io"
    socket_disable_msgpack: bool = False
    socket_reconnect_delay_ms: int = 1000
    socket_max_reconnect_delay_ms: int = 10000
    socket_connect_timeout_ms: int = 10000
    refresh_interval_ms: int = 30000
    watch_timeout_ms: int = 25000
    watch_limit: int = 100
    retry_delay_ms: int = 500
    max_retry_attempts: int = 0  # 0 means unlimited retries
    claw_token: str = ""
    agent_user_id: str = ""
    sessions: list[str] = Field(default_factory=list)
    panels: list[str] = Field(default_factory=list)
    allow_from: list[str] = Field(default_factory=list)
    mention: MochatMentionConfig = Field(default_factory=MochatMentionConfig)
    groups: dict[str, MochatGroupRule] = Field(default_factory=dict)
    reply_delay_mode: str = "non-mention"  # off | non-mention
    reply_delay_ms: int = 120000


class SlackDMConfig(BaseModel):
    """Slack DM policy configuration."""
    enabled: bool = True
    policy: str = "open"  # "open" or "allowlist"
    allow_from: list[str] = Field(default_factory=list)  # Allowed Slack user IDs


class SlackConfig(BaseModel):
    """Slack channel configuration."""
    enabled: bool = False
    mode: str = "socket"  # "socket" supported
    webhook_path: str = "/slack/events"
    bot_token: str = ""  # xoxb-...
    app_token: str = ""  # xapp-...
    user_token_read_only: bool = True
    group_policy: str = "mention"  # "mention", "open", "allowlist"
    group_allow_from: list[str] = Field(default_factory=list)  # Allowed channel IDs if allowlist
    dm: SlackDMConfig = Field(default_factory=SlackDMConfig)


class QQConfig(BaseModel):
    """QQ channel configuration using botpy SDK."""
    enabled: bool = False
    app_id: str = ""  # 机器人 ID (AppID) from q.qq.com
    secret: str = ""  # 机器人密钥 (AppSecret) from q.qq.com
    allow_from: list[str] = Field(default_factory=list)  # Allowed user openids (empty = public access)


class ChannelsConfig(BaseModel):
    """Configuration for chat channels."""
    whatsapp: WhatsAppConfig = Field(default_factory=WhatsAppConfig)
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)
    discord: DiscordConfig = Field(default_factory=DiscordConfig)
    feishu: FeishuConfig = Field(default_factory=FeishuConfig)
    mochat: MochatConfig = Field(default_factory=MochatConfig)
    dingtalk: DingTalkConfig = Field(default_factory=DingTalkConfig)
    email: EmailConfig = Field(default_factory=EmailConfig)
    slack: SlackConfig = Field(default_factory=SlackConfig)
    qq: QQConfig = Field(default_factory=QQConfig)


class AgentDefaults(BaseModel):
    """Default agent configuration."""
    workspace: str = "~/.nanobot/workspace"
    model: str = "anthropic/claude-opus-4-5"
    max_tokens: int = 8192
    temperature: float = 0.7
    max_tool_iterations: int = 20


class AgentsConfig(BaseModel):
    """Agent configuration."""
    defaults: AgentDefaults = Field(default_factory=AgentDefaults)


class ProviderConfig(BaseModel):
    """LLM provider configuration."""
    api_key: str = ""
    api_base: str | None = None
    extra_headers: dict[str, str] | None = None  # Custom headers (e.g. APP-Code for AiHubMix)


class ProvidersConfig(BaseModel):
    """Configuration for LLM providers."""
    anthropic: ProviderConfig = Field(default_factory=ProviderConfig)
    openai: ProviderConfig = Field(default_factory=ProviderConfig)
    openrouter: ProviderConfig = Field(default_factory=ProviderConfig)
    deepseek: ProviderConfig = Field(default_factory=ProviderConfig)
    groq: ProviderConfig = Field(default_factory=ProviderConfig)
    zhipu: ProviderConfig = Field(default_factory=ProviderConfig)
    dashscope: ProviderConfig = Field(default_factory=ProviderConfig)  # 阿里云通义千问
    vllm: ProviderConfig = Field(default_factory=ProviderConfig)
    gemini: ProviderConfig = Field(default_factory=ProviderConfig)
    moonshot: ProviderConfig = Field(default_factory=ProviderConfig)
    aihubmix: ProviderConfig = Field(default_factory=ProviderConfig)  # AiHubMix API gateway


class GatewayConfig(BaseModel):
    """Gateway/server configuration."""
    host: str = "0.0.0.0"
    port: int = 18790


class WebSearchConfig(BaseModel):
    """Web search tool configuration."""
    api_key: str = ""  # Brave Search API key
    max_results: int = 5


class WebToolsConfig(BaseModel):
    """Web tools configuration."""
    search: WebSearchConfig = Field(default_factory=WebSearchConfig)


class ExecToolConfig(BaseModel):
    """Shell exec tool configuration."""
    timeout: int = 60


class TTSConfig(BaseModel):
    """Text-to-speech configuration."""
    enabled: bool = False  # Enable TTS output
    provider: str = "openai"  # openai, elevenlabs
    voice: str = "alloy"  # openai: alloy, echo, fable, onyx, nova, shimmer
    api_key: str = ""  # Optional override for TTS provider
    model: str = "tts-1"  # TTS model: tts-1 (fast), tts-1-hd (high quality)
    max_text_length: int = 4000  # Maximum characters to synthesize
    timeout: float = 60.0  # HTTP request timeout in seconds

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        """Validate TTS provider is supported."""
        valid_providers = {"openai"}  # Only openai is currently implemented
        provider = v.lower()
        if provider not in valid_providers:
            raise ValueError(
                f"Invalid TTS provider: {v}. "
                f"Valid options: {', '.join(valid_providers)}"
            )
        return provider

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: str) -> str:
        """Validate TTS model is supported."""
        valid_models = {"tts-1", "tts-1-hd"}
        if v not in valid_models:
            raise ValueError(
                f"Invalid TTS model: {v}. Valid options: {', '.join(valid_models)}"
            )
        return v

    @field_validator("max_text_length")
    @classmethod
    def validate_max_text_length(cls, v: int) -> int:
        """Validate max_text_length is within reasonable bounds."""
        if v < 100:
            raise ValueError("max_text_length must be at least 100 characters")
        if v > 10000:
            raise ValueError("max_text_length cannot exceed 10000 characters")
        return v

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: float) -> float:
        """Validate timeout is within reasonable bounds."""
        if v < 5:
            raise ValueError("TTS timeout must be at least 5 seconds")
        if v > 300:
            raise ValueError("TTS timeout cannot exceed 300 seconds")
        return v


class MultimodalConfig(BaseModel):
    """Multi-modal capabilities configuration."""
    vision_enabled: bool = True  # Enable image/vision analysis
    max_image_size: int = 20 * 1024 * 1024  # 20MB default
    max_video_size: int = 100 * 1024 * 1024  # 100MB default
    max_video_frames: int = 5  # Max frames to extract from video
    video_frame_interval: float = 5.0  # Seconds between frame extractions
    video_max_frame_width: int = 640  # Max width for extracted frames (pixels)
    video_processing_timeout: int = 30  # ffmpeg timeout in seconds
    tts: TTSConfig = Field(default_factory=TTSConfig)

    @field_validator("max_image_size")
    @classmethod
    def validate_max_image_size(cls, v: int) -> int:
        """Validate max_image_size is within reasonable bounds."""
        min_size = 1024 * 1024  # 1MB minimum
        max_size = 200 * 1024 * 1024  # 200MB maximum
        if v < min_size:
            raise ValueError(f"max_image_size must be at least {min_size} bytes")
        if v > max_size:
            raise ValueError(f"max_image_size cannot exceed {max_size} bytes")
        return v

    @field_validator("max_video_size")
    @classmethod
    def validate_max_video_size(cls, v: int) -> int:
        """Validate max_video_size is within reasonable bounds."""
        min_size = 1024 * 1024  # 1MB minimum
        max_size = 500 * 1024 * 1024  # 500MB maximum
        if v < min_size:
            raise ValueError(f"max_video_size must be at least {min_size} bytes")
        if v > max_size:
            raise ValueError(f"max_video_size cannot exceed {max_size} bytes")
        return v

    @field_validator("max_video_frames")
    @classmethod
    def validate_max_video_frames(cls, v: int) -> int:
        """Validate max_video_frames is within reasonable bounds."""
        if v < 1:
            raise ValueError("max_video_frames must be at least 1")
        if v > 20:
            raise ValueError("max_video_frames cannot exceed 20")
        return v

    @field_validator("video_processing_timeout")
    @classmethod
    def validate_video_processing_timeout(cls, v: int) -> int:
        """Validate video_processing_timeout is within reasonable bounds."""
        if v < 5:
            raise ValueError("video_processing_timeout must be at least 5 seconds")
        if v > 300:  # 5 minutes
            raise ValueError("video_processing_timeout cannot exceed 300 seconds")
        return v

    @field_validator("video_frame_interval")
    @classmethod
    def validate_video_frame_interval(cls, v: float) -> float:
        """Validate video_frame_interval is within reasonable bounds."""
        if v < 0.5:
            raise ValueError("video_frame_interval must be at least 0.5 seconds")
        if v > 60:  # 1 minute
            raise ValueError("video_frame_interval cannot exceed 60 seconds")
        return v

    @field_validator("video_max_frame_width")
    @classmethod
    def validate_video_max_frame_width(cls, v: int) -> int:
        """Validate video_max_frame_width is within reasonable bounds."""
        if v < 320:
            raise ValueError("video_max_frame_width must be at least 320 pixels")
        if v > 3840:  # 4K width
            raise ValueError("video_max_frame_width cannot exceed 3840 pixels")
        return v


class ToolsConfig(BaseModel):
    """Tools configuration."""
    web: WebToolsConfig = Field(default_factory=WebToolsConfig)
    exec: ExecToolConfig = Field(default_factory=ExecToolConfig)
    multimodal: MultimodalConfig = Field(default_factory=MultimodalConfig)
    restrict_to_workspace: bool = False  # If true, restrict all tool access to workspace directory


class Config(BaseSettings):
    """Root configuration for nanobot."""
    agents: AgentsConfig = Field(default_factory=AgentsConfig)
    channels: ChannelsConfig = Field(default_factory=ChannelsConfig)
    providers: ProvidersConfig = Field(default_factory=ProvidersConfig)
    gateway: GatewayConfig = Field(default_factory=GatewayConfig)
    tools: ToolsConfig = Field(default_factory=ToolsConfig)

    @property
    def workspace_path(self) -> Path:
        """Get expanded workspace path."""
        return Path(self.agents.defaults.workspace).expanduser()

    def _match_provider(self, model: str | None = None) -> tuple["ProviderConfig | None", str | None]:
        """Match provider config and its registry name. Returns (config, spec_name)."""
        from nanobot.providers.registry import PROVIDERS
        model_lower = (model or self.agents.defaults.model).lower()

        # Match by keyword (order follows PROVIDERS registry)
        for spec in PROVIDERS:
            p = getattr(self.providers, spec.name, None)
            if p and any(kw in model_lower for kw in spec.keywords) and p.api_key:
                return p, spec.name

        # Fallback: gateways first, then others (follows registry order)
        for spec in PROVIDERS:
            p = getattr(self.providers, spec.name, None)
            if p and p.api_key:
                return p, spec.name
        return None, None

    def get_provider(self, model: str | None = None) -> ProviderConfig | None:
        """Get matched provider config (api_key, api_base, extra_headers). Falls back to first available."""
        p, _ = self._match_provider(model)
        return p

    def get_provider_name(self, model: str | None = None) -> str | None:
        """Get the registry name of the matched provider (e.g. "deepseek", "openrouter")."""
        _, name = self._match_provider(model)
        return name

    def get_api_key(self, model: str | None = None) -> str | None:
        """Get API key for the given model. Falls back to first available key."""
        p = self.get_provider(model)
        return p.api_key if p else None

    def get_api_base(self, model: str | None = None) -> str | None:
        """Get API base URL for the given model. Applies default URLs for known gateways."""
        from nanobot.providers.registry import find_by_name
        p, name = self._match_provider(model)
        if p and p.api_base:
            return p.api_base
        # Only gateways get a default api_base here. Standard providers
        # (like Moonshot) set their base URL via env vars in _setup_env
        # to avoid polluting the global litellm.api_base.
        if name:
            spec = find_by_name(name)
            if spec and spec.is_gateway and spec.default_api_base:
                return spec.default_api_base
        return None

    class Config:
        env_prefix = "NANOBOT_"
        env_nested_delimiter = "__"
