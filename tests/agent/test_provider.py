"""Tests for Agent Provider."""

import pytest

from eiw.agent.provider import (
    ProviderConfig, ProviderType, DeterministicProvider,
    create_provider, TokenUsage
)


class TestProviderConfig:
    """Tests for ProviderConfig."""

    def test_default_config(self):
        """Test default configuration."""
        config = ProviderConfig()
        assert config.provider_type == ProviderType.DETERMINISTIC
        assert config.timeout_seconds == 60.0
        assert config.max_retries == 3

    def test_custom_config(self):
        """Test custom configuration."""
        config = ProviderConfig(
            provider_type=ProviderType.ANTHROPIC,
            model_name="claude-opus-4-20250514",
            timeout_seconds=120.0,
        )
        assert config.provider_type == ProviderType.ANTHROPIC
        assert config.model_name == "claude-opus-4-20250514"
        assert config.timeout_seconds == 120.0


class TestDeterministicProvider:
    """Tests for DeterministicProvider."""

    @pytest.fixture
    def provider(self):
        """Create provider."""
        return DeterministicProvider()

    @pytest.mark.asyncio
    async def test_basic_completion(self, provider):
        """Test basic completion."""
        response = await provider.complete("test prompt")
        assert response.content is not None
        assert response.model == provider.model_info.model_name

    @pytest.mark.asyncio
    async def test_deterministic_response(self, provider):
        """Test deterministic response matching."""
        provider.add_response("analysis", '{"intent": "analysis"}')
        response = await provider.complete("analysis question")
        assert "analysis" in response.content.lower()

    @pytest.mark.asyncio
    async def test_structured_complete(self, provider):
        """Test structured completion."""
        from pydantic import BaseModel

        class TestModel(BaseModel):
            value: str
            count: int

        provider.add_structured_response("test", {"value": "hello", "count": 42})

        response = await provider.structured_complete(
            "test prompt",
            TestModel,
        )

        assert response.success
        assert response.data is not None
        assert response.data.value == "hello"
        assert response.data.count == 42

    @pytest.mark.asyncio
    async def test_token_tracking(self, provider):
        """Test token usage tracking."""
        initial_usage = provider.total_usage
        initial_total = initial_usage.total_tokens

        await provider.complete("test prompt")

        assert provider.total_usage.total_tokens > initial_total


class TestProviderFactory:
    """Tests for provider factory."""

    def test_create_deterministic(self):
        """Test creating deterministic provider."""
        provider = create_provider(ProviderConfig(
            provider_type=ProviderType.DETERMINISTIC
        ))
        assert isinstance(provider, DeterministicProvider)

    def test_create_with_env(self):
        """Test creating provider from environment."""
        # This test would use env vars in real scenario
        pass


class TestTokenUsage:
    """Tests for TokenUsage."""

    def test_token_usage_str(self):
        """Test token usage string representation."""
        usage = TokenUsage(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
        )
        assert "prompt=100" in str(usage)
        assert "completion=50" in str(usage)
        assert "total=150" in str(usage)
