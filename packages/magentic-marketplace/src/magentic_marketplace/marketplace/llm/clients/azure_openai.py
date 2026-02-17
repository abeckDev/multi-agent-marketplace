"""Azure OpenAI model client implementation with Entra ID authentication."""

import threading
from collections.abc import Sequence
from hashlib import sha256
from typing import Any, Literal, cast, overload

from azure.identity.aio import DefaultAzureCredential, get_bearer_token_provider
from openai import AsyncAzureOpenAI
from openai.types.chat.chat_completion import ChatCompletion

from ..base import (
    AllowedChatCompletionMessageParams,
    ProviderClient,
    TResponseModel,
    Usage,
)
from ..config import BaseLLMConfig, EnvField


class AzureOpenAIConfig(BaseLLMConfig):
    """Configuration for Azure OpenAI provider."""

    provider: Literal["azure_openai"] = EnvField("LLM_PROVIDER", default="azure_openai")  # pyright: ignore[reportIncompatibleVariableOverride]
    azure_endpoint: str = EnvField("AZURE_OPENAI_ENDPOINT")
    api_version: str = EnvField(
        "AZURE_OPENAI_API_VERSION", default="2025-04-01-preview"
    )
    api_key: str | None = EnvField("AZURE_OPENAI_API_KEY", default=None, exclude=True)
    use_entra_id: bool = EnvField("AZURE_OPENAI_USE_ENTRA_ID", default=True)


class AzureOpenAIClient(ProviderClient[AzureOpenAIConfig]):
    """Azure OpenAI model client with Entra ID authentication support.

    This client reuses the OpenAI SDK's AsyncAzureOpenAI client, which is a subclass
    of AsyncOpenAI with the same API, so the _generate implementation is compatible.
    """

    _client_cache: dict[str, "AzureOpenAIClient"] = {}
    _cache_lock = threading.Lock()

    def __init__(self, config: AzureOpenAIConfig | None = None):
        """Initialize Azure OpenAI client.

        Args:
            config: Azure OpenAI configuration. If None, creates from environment.

        """
        if config is None:
            config = AzureOpenAIConfig()
        else:
            config = AzureOpenAIConfig.model_validate(config)

        super().__init__(config)

        self.config = config

        # Validate configuration
        if not config.use_entra_id and not config.api_key:
            raise ValueError(
                "Azure OpenAI API key not found. Set AZURE_OPENAI_API_KEY environment "
                "variable or enable Entra ID authentication (AZURE_OPENAI_USE_ENTRA_ID=true)."
            )

        # Create Azure OpenAI client with appropriate authentication
        if config.use_entra_id:
            # Use Entra ID (Azure AD) authentication
            credential = DefaultAzureCredential()
            token_provider = get_bearer_token_provider(
                credential, "https://cognitiveservices.azure.com/.default"
            )
            self.client = AsyncAzureOpenAI(
                azure_endpoint=config.azure_endpoint,
                api_version=config.api_version,
                azure_ad_token_provider=token_provider,
            )
        else:
            # Use API key authentication
            self.client = AsyncAzureOpenAI(
                api_key=config.api_key,
                azure_endpoint=config.azure_endpoint,
                api_version=config.api_version,
            )

    @staticmethod
    def _get_cache_key(config: AzureOpenAIConfig) -> str:
        """Generate cache key for a config."""
        config_json = config.model_dump_json(
            include={
                "provider",
                "azure_endpoint",
                "api_version",
                "use_entra_id",
                "api_key",
            }
        )
        return sha256(config_json.encode()).hexdigest()

    @staticmethod
    def from_cache(config: AzureOpenAIConfig) -> "AzureOpenAIClient":
        """Get or create client from cache."""
        cache_key = AzureOpenAIClient._get_cache_key(config)
        with AzureOpenAIClient._cache_lock:
            if cache_key not in AzureOpenAIClient._client_cache:
                AzureOpenAIClient._client_cache[cache_key] = AzureOpenAIClient(config)
            return AzureOpenAIClient._client_cache[cache_key]

    # The _generate implementation is copied from OpenAIClient since AsyncAzureOpenAI
    # is a subclass of AsyncOpenAI with the same API
    @overload
    async def _generate(
        self,
        *,
        model: str,
        messages: Sequence[AllowedChatCompletionMessageParams],
        temperature: float | None = None,
        max_tokens: int | None = None,
        reasoning_effort: str | int | None = None,
        response_format: None = None,
        **kwargs: Any,
    ) -> tuple[str, Usage]: ...

    @overload
    async def _generate(
        self,
        *,
        model: str,
        messages: Sequence[AllowedChatCompletionMessageParams],
        temperature: float | None = None,
        max_tokens: int | None = None,
        reasoning_effort: str | int | None = None,
        response_format: type[TResponseModel],
        **kwargs: Any,
    ) -> tuple[TResponseModel, Usage]: ...

    async def _generate(
        self,
        *,
        model: str,
        messages: Sequence[AllowedChatCompletionMessageParams],
        temperature: float | None = None,
        max_tokens: int | None = None,
        reasoning_effort: str | int | None = None,
        response_format: type[TResponseModel] | None = None,
        **kwargs: Any,
    ) -> tuple[str, Usage] | tuple[TResponseModel, Usage]:
        """Generate completion using Azure OpenAI API."""
        # Build arguments, handling reasoning models
        args: dict[str, Any] = {
            "model": model,
            "messages": messages,
        }

        # Handle reasoning vs non-reasoning models
        is_reasoning_model = any(
            reasoning_model in model for reasoning_model in ("gpt-5", "o4", "o3", "o1")
        )

        if is_reasoning_model:
            # Reasoning models use max_completion_tokens
            if max_tokens:
                args["max_completion_tokens"] = max_tokens

            if "gpt-5-chat" not in model:
                # Most reasoning models don't support temperature < 1
                if temperature and temperature < 1.0:
                    temperature = None

            # Handle reasoning effort for supported models
            if reasoning_effort is not None and "o1" not in model:
                if reasoning_effort == "minimal":
                    reasoning_effort = "low"  # o models don't support minimal
                args["reasoning_effort"] = reasoning_effort
        else:
            # Non-reasoning models
            if temperature is not None:
                args["temperature"] = temperature
            if max_tokens is not None:
                args["max_tokens"] = max_tokens

        # Add any additional kwargs
        args.update(kwargs)

        # Handle structured output
        if response_format is not None:
            # Make 3 attempts to parse the model
            exceptions: list[Exception] = []
            for _ in range(3):
                try:
                    response = await self.client.chat.completions.parse(
                        response_format=response_format, **args
                    )
                    parsed = response.choices[0].message.parsed
                    if parsed is not None:
                        usage = Usage(
                            token_count=response.usage.total_tokens
                            if response.usage
                            else 0,
                            provider="azure_openai",
                            model=model,
                        )
                        return parsed, usage
                    elif response.choices[0].message.refusal:
                        # Present information to retry
                        raise ValueError(response.choices[0].message.refusal)
                    else:
                        # Unknown failure, no info to retry on, break
                        break

                except Exception as e:
                    exceptions.append(e)
                    # Append the error message to the chat history so that the model can retry with info
                    args["messages"].append({"role": "user", "content": str(e)})
            # if we make it here, we exhausted our retries
            exc_message = "Exceeded attempts to parse response_format."
            if exceptions:
                exc_message += "Inner exceptions: " + " ".join(map(str, exceptions))
            raise RuntimeError(exc_message)

        else:
            # Regular completion
            response = cast(
                ChatCompletion, await self.client.chat.completions.create(**args)
            )
            usage = Usage(
                token_count=response.usage.total_tokens if response.usage else 0,
                provider="azure_openai",
                model=model,
            )
            if response.choices and response.choices[0].message.content:
                return response.choices[0].message.content, usage
            return "", usage
