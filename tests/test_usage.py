"""Tests for the usage tracking module."""

from decimal import Decimal
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from simpli_core.usage import (
    DEFAULT_PRICING,
    CostTracker,
    LLMCost,
    ModelPricing,
    TokenUsage,
    get_pricing,
)

# ---------------------------------------------------------------------------
# TokenUsage
# ---------------------------------------------------------------------------


class TestTokenUsage:
    def test_defaults(self) -> None:
        u = TokenUsage()
        assert u.prompt_tokens == 0
        assert u.completion_tokens == 0
        assert u.total_tokens == 0

    def test_auto_computes_total(self) -> None:
        u = TokenUsage(prompt_tokens=100, completion_tokens=50)
        assert u.total_tokens == 150

    def test_explicit_total_preserved(self) -> None:
        u = TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=200)
        assert u.total_tokens == 200

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            TokenUsage(prompt_tokens=10, extra_field="bad")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# ModelPricing
# ---------------------------------------------------------------------------


class TestModelPricing:
    def test_cloud_model(self) -> None:
        mp = ModelPricing(
            model="openai/gpt-5",
            input_cost_per_million=Decimal("1.25"),
            output_cost_per_million=Decimal("10.00"),
        )
        assert mp.input_cost_per_million == Decimal("1.25")

    def test_local_model_defaults_to_zero(self) -> None:
        mp = ModelPricing(model="ollama/llama4")
        assert mp.input_cost_per_million == Decimal("0")
        assert mp.output_cost_per_million == Decimal("0")


# ---------------------------------------------------------------------------
# LLMCost
# ---------------------------------------------------------------------------


class TestLLMCost:
    def test_creation(self) -> None:
        cost = LLMCost(
            model="openai/gpt-5",
            usage=TokenUsage(prompt_tokens=100, completion_tokens=50),
            input_cost=Decimal("0.000125"),
            output_cost=Decimal("0.000500"),
            total_cost=Decimal("0.000625"),
        )
        assert cost.total_cost == Decimal("0.000625")
        assert cost.created_at.tzinfo is not None


# ---------------------------------------------------------------------------
# get_pricing
# ---------------------------------------------------------------------------


class TestGetPricing:
    def test_known_model(self) -> None:
        mp = get_pricing("openai/gpt-5")
        assert mp.input_cost_per_million == Decimal("1.25")

    def test_unknown_model_returns_zero_cost(self) -> None:
        mp = get_pricing("unknown/model-xyz")
        assert mp.model == "unknown/model-xyz"
        assert mp.input_cost_per_million == Decimal("0")

    def test_custom_pricing(self) -> None:
        custom = {
            "custom/model": ModelPricing(
                model="custom/model",
                input_cost_per_million=Decimal("5.00"),
                output_cost_per_million=Decimal("15.00"),
            ),
        }
        mp = get_pricing("custom/model", pricing=custom)
        assert mp.input_cost_per_million == Decimal("5.00")


# ---------------------------------------------------------------------------
# DEFAULT_PRICING
# ---------------------------------------------------------------------------


class TestDefaultPricing:
    def test_contains_cloud_models(self) -> None:
        assert "openai/gpt-5" in DEFAULT_PRICING
        assert "openai/gpt-5-mini" in DEFAULT_PRICING
        assert "openai/gpt-4.1" in DEFAULT_PRICING
        assert "anthropic/claude-sonnet-4-6" in DEFAULT_PRICING
        assert "anthropic/claude-haiku-4-5" in DEFAULT_PRICING
        assert "google/gemini-2.5-flash" in DEFAULT_PRICING
        assert "xai/grok-4" in DEFAULT_PRICING
        assert "deepseek/deepseek-chat" in DEFAULT_PRICING
        assert "mistral/mistral-large-latest" in DEFAULT_PRICING
        assert "cohere/command-a" in DEFAULT_PRICING

    def test_contains_openrouter_models(self) -> None:
        assert "openrouter/openai/gpt-5" in DEFAULT_PRICING
        assert "openrouter/anthropic/claude-sonnet-4.6" in DEFAULT_PRICING
        assert "openrouter/meta-llama/llama-4-scout" in DEFAULT_PRICING
        assert "openrouter/google/gemma-3-27b-it" in DEFAULT_PRICING
        assert "openrouter/deepseek/deepseek-r1" in DEFAULT_PRICING
        assert "openrouter/x-ai/grok-4" in DEFAULT_PRICING
        assert "openrouter/moonshotai/kimi-k2" in DEFAULT_PRICING

    def test_openrouter_models_have_pricing(self) -> None:
        for key, mp in DEFAULT_PRICING.items():
            if key.startswith("openrouter/"):
                assert mp.input_cost_per_million >= Decimal("0"), key
                assert mp.output_cost_per_million >= Decimal("0"), key

    def test_contains_local_models(self) -> None:
        assert "ollama/llama4" in DEFAULT_PRICING
        assert "ollama/gemma3" in DEFAULT_PRICING
        assert "ollama/qwen3" in DEFAULT_PRICING

    def test_local_models_are_free(self) -> None:
        for key, mp in DEFAULT_PRICING.items():
            if key.startswith("ollama/"):
                assert mp.input_cost_per_million == Decimal("0"), key
                assert mp.output_cost_per_million == Decimal("0"), key


# ---------------------------------------------------------------------------
# CostTracker
# ---------------------------------------------------------------------------


class TestCostTracker:
    def test_record_calculates_cost(self) -> None:
        tracker = CostTracker()
        usage = TokenUsage(prompt_tokens=1_000_000, completion_tokens=500_000)
        cost = tracker.record("openai/gpt-5", usage)
        assert cost.input_cost == Decimal("1.25")
        assert cost.output_cost == Decimal("5.00")
        assert cost.total_cost == Decimal("6.25")

    def test_accumulation(self) -> None:
        tracker = CostTracker()
        tracker.record(
            "openai/gpt-5",
            TokenUsage(prompt_tokens=1_000_000, completion_tokens=0),
        )
        tracker.record(
            "openai/gpt-5",
            TokenUsage(prompt_tokens=1_000_000, completion_tokens=0),
        )
        assert tracker.total_cost == Decimal("2.50")
        assert tracker.total_tokens == 2_000_000
        assert len(tracker.history) == 2

    def test_record_from_response(self) -> None:
        tracker = CostTracker()
        fake_response = SimpleNamespace(
            usage=SimpleNamespace(
                prompt_tokens=500,
                completion_tokens=200,
                total_tokens=700,
            )
        )
        cost = tracker.record_from_response("openai/gpt-5-mini", fake_response)
        assert cost.usage.prompt_tokens == 500
        assert cost.usage.completion_tokens == 200
        assert cost.usage.total_tokens == 700

    def test_unknown_model_zero_cost(self) -> None:
        tracker = CostTracker()
        cost = tracker.record(
            "unknown/model",
            TokenUsage(prompt_tokens=1000, completion_tokens=500),
        )
        assert cost.total_cost == Decimal("0")

    def test_local_model_zero_cost(self) -> None:
        tracker = CostTracker()
        cost = tracker.record(
            "ollama/gemma3",
            TokenUsage(prompt_tokens=10_000, completion_tokens=5_000),
        )
        assert cost.total_cost == Decimal("0")

    def test_summary(self) -> None:
        tracker = CostTracker()
        tracker.record(
            "openai/gpt-5",
            TokenUsage(prompt_tokens=100, completion_tokens=50),
        )
        tracker.record(
            "ollama/gemma3",
            TokenUsage(prompt_tokens=200, completion_tokens=100),
        )
        s = tracker.summary()
        assert "openai/gpt-5" in s["models"]
        assert "ollama/gemma3" in s["models"]
        assert s["models"]["openai/gpt-5"]["calls"] == 1
        assert s["total_tokens"] == 450

    def test_reset(self) -> None:
        tracker = CostTracker()
        tracker.record(
            "openai/gpt-5",
            TokenUsage(prompt_tokens=100, completion_tokens=50),
        )
        tracker.reset()
        assert tracker.total_cost == Decimal("0")
        assert tracker.total_tokens == 0
        assert tracker.history == []

    def test_custom_pricing(self) -> None:
        custom = {
            "my/model": ModelPricing(
                model="my/model",
                input_cost_per_million=Decimal("1.00"),
                output_cost_per_million=Decimal("2.00"),
            ),
        }
        tracker = CostTracker(pricing=custom)
        cost = tracker.record(
            "my/model",
            TokenUsage(prompt_tokens=1_000_000, completion_tokens=1_000_000),
        )
        assert cost.input_cost == Decimal("1.00")
        assert cost.output_cost == Decimal("2.00")
        assert cost.total_cost == Decimal("3.00")

    def test_decimal_precision(self) -> None:
        tracker = CostTracker()
        cost = tracker.record(
            "openai/gpt-5",
            TokenUsage(prompt_tokens=1, completion_tokens=1),
        )
        # 1 token at $1.25/1M = $0.00000125
        assert cost.input_cost == Decimal("1.25") / Decimal("1000000")
        assert cost.output_cost == Decimal("10.00") / Decimal("1000000")
