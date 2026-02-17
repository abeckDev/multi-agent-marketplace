"""Integration tests for Azure OpenAI LLM client."""

import os
from unittest.mock import MagicMock, patch

import pytest
from openai.types.chat import ChatCompletionUserMessageParam
from pydantic import BaseModel

from magentic_marketplace.marketplace.llm.clients.azure_openai import (
    AzureOpenAIClient,
    AzureOpenAIConfig,
)

pytestmark = pytest.mark.skip_ci


class ResponseModel(BaseModel):
    """Test response model for structured output."""

    answer: str
    confidence: float


class TestAzureOpenAIConfig:
    """Test AzureOpenAIConfig creation and validation."""

    def test_config_from_env(self):
        """Test creating config from environment variables."""
        env = {
            "LLM_PROVIDER": "azure_openai",
            "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/",
            "AZURE_OPENAI_API_VERSION": "2025-04-01-preview",
            "AZURE_OPENAI_DEPLOYMENT_NAME": "gpt-4o",
            "AZURE_OPENAI_USE_ENTRA_ID": "true",
            "LLM_TEMPERATURE": "0.1",
            "LLM_MAX_TOKENS": "100",
        }
        with patch.dict(os.environ, env, clear=True):
            config = AzureOpenAIConfig()
            assert config.provider == "azure_openai"
            assert config.azure_endpoint == env["AZURE_OPENAI_ENDPOINT"]
            assert config.api_version == env["AZURE_OPENAI_API_VERSION"]
            assert config.model == env["AZURE_OPENAI_DEPLOYMENT_NAME"]
            assert config.use_entra_id is True
            assert str(config.temperature) == env["LLM_TEMPERATURE"]
            assert str(config.max_tokens) == env["LLM_MAX_TOKENS"]

    def test_config_defaults(self):
        """Test config with defaults."""
        with patch.dict(
            os.environ,
            {"AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/"},
            clear=True,
        ):
            config = AzureOpenAIConfig()
            assert config.provider == "azure_openai"
            assert config.azure_endpoint == "https://test.openai.azure.com/"
            assert config.api_version == "2025-04-01-preview"
            assert config.api_key is None
            assert config.use_entra_id is True
            assert config.model is None
            assert config.temperature is None
            assert config.max_tokens == 2000
            assert config.reasoning_effort == "minimal"
            assert config.max_concurrency == 64

    def test_config_with_api_key_auth(self):
        """Test config with API key authentication."""
        env = {
            "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/",
            "AZURE_OPENAI_USE_ENTRA_ID": "false",
            "AZURE_OPENAI_API_KEY": "test-key-12345",
        }
        with patch.dict(os.environ, env, clear=True):
            config = AzureOpenAIConfig()
            assert config.use_entra_id is False
            assert config.api_key == "test-key-12345"

    def test_config_entra_id_no_api_key(self):
        """Test that Entra ID mode doesn't require API key."""
        env = {
            "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/",
            "AZURE_OPENAI_USE_ENTRA_ID": "true",
        }
        with patch.dict(os.environ, env, clear=True):
            config = AzureOpenAIConfig()
            assert config.use_entra_id is True
            assert config.api_key is None


class TestAzureOpenAIClient:
    """Test AzureOpenAIClient functionality."""

    def test_client_initialization_with_entra_id(self):
        """Test client initialization with Entra ID auth."""
        with patch.dict(
            os.environ,
            {
                "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/",
                "AZURE_OPENAI_USE_ENTRA_ID": "true",
            },
            clear=True,
        ):
            with patch(
                "magentic_marketplace.marketplace.llm.clients.azure_openai.DefaultAzureCredential"
            ) as mock_credential:
                with patch(
                    "magentic_marketplace.marketplace.llm.clients.azure_openai.get_bearer_token_provider"
                ) as mock_token_provider:
                    mock_credential.return_value = MagicMock()
                    mock_token_provider.return_value = MagicMock()

                    config = AzureOpenAIConfig()
                    client = AzureOpenAIClient(config)

                    assert client.config == config
                    assert client.provider == "azure_openai"
                    assert mock_credential.called
                    assert mock_token_provider.called
                    # Verify the token provider was called with correct scope
                    mock_token_provider.assert_called_once()
                    args = mock_token_provider.call_args
                    assert "https://cognitiveservices.azure.com/.default" in args[0]

    def test_client_initialization_with_api_key(self):
        """Test client initialization with API key auth."""
        with patch.dict(
            os.environ,
            {
                "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/",
                "AZURE_OPENAI_USE_ENTRA_ID": "false",
                "AZURE_OPENAI_API_KEY": "test-key",
            },
            clear=True,
        ):
            config = AzureOpenAIConfig()
            client = AzureOpenAIClient(config)

            assert client.config == config
            assert client.provider == "azure_openai"
            # Verify the client was created (we can't directly check AsyncAzureOpenAI internals)
            assert client.client is not None

    def test_client_initialization_no_api_key_without_entra_id(self):
        """Test client initialization fails without API key when Entra ID is disabled."""
        with patch.dict(
            os.environ,
            {
                "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/",
                "AZURE_OPENAI_USE_ENTRA_ID": "false",
            },
            clear=True,
        ):
            with pytest.raises(ValueError, match="API key not found"):
                AzureOpenAIClient()

    def test_cache_key_generation(self):
        """Test that cache keys are generated correctly."""
        with patch.dict(
            os.environ,
            {
                "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/",
                "AZURE_OPENAI_API_KEY": "test-key",
            },
            clear=True,
        ):
            config1 = AzureOpenAIConfig()
            config2 = AzureOpenAIConfig()

            key1 = AzureOpenAIClient._get_cache_key(config1)
            key2 = AzureOpenAIClient._get_cache_key(config2)

            # Same config should produce same key
            assert key1 == key2

            # Different endpoint should produce different key
            config3 = AzureOpenAIConfig(
                azure_endpoint="https://different.openai.azure.com/"
            )
            key3 = AzureOpenAIClient._get_cache_key(config3)
            assert key1 != key3

    def test_from_cache(self):
        """Test client caching mechanism."""
        with patch.dict(
            os.environ,
            {
                "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/",
                "AZURE_OPENAI_API_KEY": "test-key",
                "AZURE_OPENAI_USE_ENTRA_ID": "false",
            },
            clear=True,
        ):
            # Clear cache before test
            AzureOpenAIClient._client_cache.clear()

            config = AzureOpenAIConfig()
            client1 = AzureOpenAIClient.from_cache(config)
            client2 = AzureOpenAIClient.from_cache(config)

            # Should return the same instance
            assert client1 is client2
            assert len(AzureOpenAIClient._client_cache) == 1


@pytest.mark.skipif(
    not os.environ.get("AZURE_OPENAI_ENDPOINT")
    or not (
        os.environ.get("AZURE_OPENAI_API_KEY")
        or os.environ.get("AZURE_OPENAI_USE_ENTRA_ID") == "true"
    ),
    reason="Azure OpenAI credentials not configured",
)
class TestAzureOpenAIClientIntegration:
    """Test AzureOpenAIClient with real API calls (requires credentials)."""

    @pytest.fixture
    def config(self) -> AzureOpenAIConfig:
        """Test configuration from environment."""
        return AzureOpenAIConfig()

    @pytest.mark.asyncio
    async def test_generate_string_response(self, config: AzureOpenAIConfig) -> None:
        """Test creating a string response."""
        client = AzureOpenAIClient(config)
        messages = [
            ChatCompletionUserMessageParam(
                role="user", content="Say 'Hello World' and nothing else."
            )
        ]

        response, usage = await client.generate(
            messages, model=config.model or "gpt-4o-mini"
        )

        assert isinstance(response, str)
        assert "Hello World" in response
        assert usage.token_count > 0
        assert usage.provider == "azure_openai"

    @pytest.mark.asyncio
    async def test_generate_structured_response(
        self, config: AzureOpenAIConfig
    ) -> None:
        """Test creating a structured response."""
        client = AzureOpenAIClient(config)
        messages = [
            ChatCompletionUserMessageParam(
                role="user", content="Answer '42' with confidence 0.95"
            )
        ]

        response, usage = await client.generate(
            messages,
            model=config.model or "gpt-4o-mini",
            response_format=ResponseModel,
        )

        assert isinstance(response, ResponseModel)
        assert response.answer == "42"
        assert response.confidence == 0.95
        assert usage.token_count > 0
        assert usage.provider == "azure_openai"
