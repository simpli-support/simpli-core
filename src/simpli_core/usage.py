"""Token usage tracking and cost calculation for LLM calls.

Provides models and a tracker for recording token consumption and
estimating costs across all Simpli Support services.  Works with any
LLM provider via LiteLLM's unified response format.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import structlog

from simpli_core.models import SimpliBase, _TimestampBase

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

_ZERO = Decimal("0")
_ONE_MILLION = Decimal("1_000_000")


class TokenUsage(SimpliBase):
    """Token counts for a single LLM call."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def model_post_init(self, __context: Any) -> None:
        """Auto-compute *total_tokens* when it is left at zero."""
        if self.total_tokens == 0 and (self.prompt_tokens or self.completion_tokens):
            object.__setattr__(
                self,
                "total_tokens",
                self.prompt_tokens + self.completion_tokens,
            )


class ModelPricing(SimpliBase):
    """Per-model pricing in USD per 1 million tokens."""

    model: str
    input_cost_per_million: Decimal = _ZERO
    output_cost_per_million: Decimal = _ZERO


class LLMCost(_TimestampBase):
    """Cost record for a single LLM call."""

    model: str
    usage: TokenUsage
    input_cost: Decimal = _ZERO
    output_cost: Decimal = _ZERO
    total_cost: Decimal = _ZERO


# ---------------------------------------------------------------------------
# Default pricing registry  (last verified: 2026-04-01)
# ---------------------------------------------------------------------------

DEFAULT_PRICING: dict[str, ModelPricing] = {
    # --- OpenAI ---
    "openai/gpt-5": ModelPricing(
        model="openai/gpt-5",
        input_cost_per_million=Decimal("1.25"),
        output_cost_per_million=Decimal("10.00"),
    ),
    "openai/gpt-5-mini": ModelPricing(
        model="openai/gpt-5-mini",
        input_cost_per_million=Decimal("0.125"),
        output_cost_per_million=Decimal("1.00"),
    ),
    "openai/gpt-5-nano": ModelPricing(
        model="openai/gpt-5-nano",
        input_cost_per_million=Decimal("0.05"),
        output_cost_per_million=Decimal("0.40"),
    ),
    "openai/gpt-4.1": ModelPricing(
        model="openai/gpt-4.1",
        input_cost_per_million=Decimal("2.00"),
        output_cost_per_million=Decimal("8.00"),
    ),
    "openai/gpt-4.1-mini": ModelPricing(
        model="openai/gpt-4.1-mini",
        input_cost_per_million=Decimal("0.40"),
        output_cost_per_million=Decimal("1.60"),
    ),
    # --- Anthropic ---
    "anthropic/claude-opus-4-6": ModelPricing(
        model="anthropic/claude-opus-4-6",
        input_cost_per_million=Decimal("5.00"),
        output_cost_per_million=Decimal("25.00"),
    ),
    "anthropic/claude-sonnet-4-6": ModelPricing(
        model="anthropic/claude-sonnet-4-6",
        input_cost_per_million=Decimal("3.00"),
        output_cost_per_million=Decimal("15.00"),
    ),
    "anthropic/claude-haiku-4-5": ModelPricing(
        model="anthropic/claude-haiku-4-5",
        input_cost_per_million=Decimal("1.00"),
        output_cost_per_million=Decimal("5.00"),
    ),
    # --- Google ---
    "google/gemini-2.5-pro": ModelPricing(
        model="google/gemini-2.5-pro",
        input_cost_per_million=Decimal("1.25"),
        output_cost_per_million=Decimal("10.00"),
    ),
    "google/gemini-2.5-flash": ModelPricing(
        model="google/gemini-2.5-flash",
        input_cost_per_million=Decimal("0.30"),
        output_cost_per_million=Decimal("2.50"),
    ),
    "google/gemini-3-flash-preview": ModelPricing(
        model="google/gemini-3-flash-preview",
        input_cost_per_million=Decimal("0.50"),
        output_cost_per_million=Decimal("3.00"),
    ),
    # --- xAI ---
    "xai/grok-4": ModelPricing(
        model="xai/grok-4",
        input_cost_per_million=Decimal("3.00"),
        output_cost_per_million=Decimal("15.00"),
    ),
    "xai/grok-4.1-fast": ModelPricing(
        model="xai/grok-4.1-fast",
        input_cost_per_million=Decimal("0.20"),
        output_cost_per_million=Decimal("0.50"),
    ),
    # --- DeepSeek ---
    "deepseek/deepseek-chat": ModelPricing(
        model="deepseek/deepseek-chat",
        input_cost_per_million=Decimal("0.28"),
        output_cost_per_million=Decimal("0.42"),
    ),
    "deepseek/deepseek-r1": ModelPricing(
        model="deepseek/deepseek-r1",
        input_cost_per_million=Decimal("0.70"),
        output_cost_per_million=Decimal("2.50"),
    ),
    # --- Mistral ---
    "mistral/mistral-large-latest": ModelPricing(
        model="mistral/mistral-large-latest",
        input_cost_per_million=Decimal("2.00"),
        output_cost_per_million=Decimal("6.00"),
    ),
    "mistral/mistral-medium-latest": ModelPricing(
        model="mistral/mistral-medium-latest",
        input_cost_per_million=Decimal("1.00"),
        output_cost_per_million=Decimal("3.00"),
    ),
    "mistral/mistral-small-latest": ModelPricing(
        model="mistral/mistral-small-latest",
        input_cost_per_million=Decimal("0.20"),
        output_cost_per_million=Decimal("0.60"),
    ),
    "mistral/codestral-latest": ModelPricing(
        model="mistral/codestral-latest",
        input_cost_per_million=Decimal("0.20"),
        output_cost_per_million=Decimal("0.60"),
    ),
    # --- Cohere ---
    "cohere/command-a": ModelPricing(
        model="cohere/command-a",
        input_cost_per_million=Decimal("2.50"),
        output_cost_per_million=Decimal("10.00"),
    ),
    # --- OpenRouter (pass-through pricing) ---
    "openrouter/openai/gpt-5": ModelPricing(
        model="openrouter/openai/gpt-5",
        input_cost_per_million=Decimal("1.25"),
        output_cost_per_million=Decimal("10.00"),
    ),
    "openrouter/openai/gpt-4.1-mini": ModelPricing(
        model="openrouter/openai/gpt-4.1-mini",
        input_cost_per_million=Decimal("0.40"),
        output_cost_per_million=Decimal("1.60"),
    ),
    "openrouter/anthropic/claude-sonnet-4.6": ModelPricing(
        model="openrouter/anthropic/claude-sonnet-4.6",
        input_cost_per_million=Decimal("3.00"),
        output_cost_per_million=Decimal("15.00"),
    ),
    "openrouter/anthropic/claude-haiku-4.5": ModelPricing(
        model="openrouter/anthropic/claude-haiku-4.5",
        input_cost_per_million=Decimal("1.00"),
        output_cost_per_million=Decimal("5.00"),
    ),
    "openrouter/google/gemini-2.5-pro": ModelPricing(
        model="openrouter/google/gemini-2.5-pro",
        input_cost_per_million=Decimal("1.25"),
        output_cost_per_million=Decimal("10.00"),
    ),
    "openrouter/google/gemini-2.5-flash": ModelPricing(
        model="openrouter/google/gemini-2.5-flash",
        input_cost_per_million=Decimal("0.30"),
        output_cost_per_million=Decimal("2.50"),
    ),
    "openrouter/x-ai/grok-4": ModelPricing(
        model="openrouter/x-ai/grok-4",
        input_cost_per_million=Decimal("3.00"),
        output_cost_per_million=Decimal("15.00"),
    ),
    "openrouter/deepseek/deepseek-chat": ModelPricing(
        model="openrouter/deepseek/deepseek-chat",
        input_cost_per_million=Decimal("0.32"),
        output_cost_per_million=Decimal("0.89"),
    ),
    "openrouter/deepseek/deepseek-r1": ModelPricing(
        model="openrouter/deepseek/deepseek-r1",
        input_cost_per_million=Decimal("0.70"),
        output_cost_per_million=Decimal("2.50"),
    ),
    "openrouter/meta-llama/llama-4-scout": ModelPricing(
        model="openrouter/meta-llama/llama-4-scout",
        input_cost_per_million=Decimal("0.15"),
        output_cost_per_million=Decimal("0.60"),
    ),
    "openrouter/meta-llama/llama-4-maverick": ModelPricing(
        model="openrouter/meta-llama/llama-4-maverick",
        input_cost_per_million=Decimal("0.25"),
        output_cost_per_million=Decimal("1.00"),
    ),
    "openrouter/meta-llama/llama-3.3-70b-instruct": ModelPricing(
        model="openrouter/meta-llama/llama-3.3-70b-instruct",
        input_cost_per_million=Decimal("0.10"),
        output_cost_per_million=Decimal("0.32"),
    ),
    "openrouter/google/gemma-3-27b-it": ModelPricing(
        model="openrouter/google/gemma-3-27b-it",
        input_cost_per_million=Decimal("0.10"),
        output_cost_per_million=Decimal("0.20"),
    ),
    "openrouter/mistralai/mistral-small-latest": ModelPricing(
        model="openrouter/mistralai/mistral-small-latest",
        input_cost_per_million=Decimal("0.20"),
        output_cost_per_million=Decimal("0.60"),
    ),
    "openrouter/moonshotai/kimi-k2": ModelPricing(
        model="openrouter/moonshotai/kimi-k2",
        input_cost_per_million=Decimal("0.57"),
        output_cost_per_million=Decimal("2.30"),
    ),
    # --- Local / open-source (free) ---
    "ollama/llama4": ModelPricing(model="ollama/llama4"),
    "ollama/gemma3": ModelPricing(model="ollama/gemma3"),
    "ollama/qwen3": ModelPricing(model="ollama/qwen3"),
    "ollama/qwen3.5": ModelPricing(model="ollama/qwen3.5"),
    "ollama/deepseek-r1": ModelPricing(model="ollama/deepseek-r1"),
    "ollama/phi-4": ModelPricing(model="ollama/phi-4"),
    "ollama/mistral-small": ModelPricing(model="ollama/mistral-small"),
}


def get_pricing(
    model: str,
    pricing: dict[str, ModelPricing] | None = None,
) -> ModelPricing:
    """Look up pricing for *model*, returning a zero-cost fallback for unknowns."""
    registry = pricing or DEFAULT_PRICING
    if model in registry:
        return registry[model]
    logger.warning("unknown_model_pricing", model=model)
    return ModelPricing(model=model)


# ---------------------------------------------------------------------------
# Cost tracker
# ---------------------------------------------------------------------------


def _compute_cost(tokens: int, cost_per_million: Decimal) -> Decimal:
    if tokens == 0:
        return _ZERO
    return (Decimal(tokens) * cost_per_million) / _ONE_MILLION


class CostTracker:
    """Accumulates token usage and cost across multiple LLM calls.

    Usage::

        tracker = CostTracker()
        response = await litellm.acompletion(model=model, messages=msgs)
        cost = tracker.record_from_response(model, response)
        print(tracker.total_cost)
    """

    def __init__(
        self,
        pricing: dict[str, ModelPricing] | None = None,
    ) -> None:
        self._pricing = pricing
        self._history: list[LLMCost] = []

    # -- recording ---------------------------------------------------------

    def record(self, model: str, usage: TokenUsage) -> LLMCost:
        """Calculate cost for *usage* and append to history."""
        mp = get_pricing(model, self._pricing)
        input_cost = _compute_cost(usage.prompt_tokens, mp.input_cost_per_million)
        output_cost = _compute_cost(usage.completion_tokens, mp.output_cost_per_million)
        entry = LLMCost(
            model=model,
            usage=usage,
            input_cost=input_cost,
            output_cost=output_cost,
            total_cost=input_cost + output_cost,
        )
        self._history.append(entry)
        return entry

    def record_from_response(self, model: str, response: Any) -> LLMCost:
        """Extract token counts from a LiteLLM response and record them."""
        resp_usage = response.usage
        usage = TokenUsage(
            prompt_tokens=resp_usage.prompt_tokens,
            completion_tokens=resp_usage.completion_tokens,
            total_tokens=getattr(resp_usage, "total_tokens", 0),
        )
        return self.record(model, usage)

    # -- queries -----------------------------------------------------------

    @property
    def history(self) -> list[LLMCost]:
        """Read-only view of all recorded cost events."""
        return list(self._history)

    @property
    def total_cost(self) -> Decimal:
        """Sum of all recorded costs."""
        return sum((e.total_cost for e in self._history), _ZERO)

    @property
    def total_tokens(self) -> int:
        """Sum of all recorded token counts."""
        return sum(e.usage.total_tokens for e in self._history)

    def summary(self) -> dict[str, Any]:
        """Per-model breakdown of tokens and costs."""
        by_model: dict[str, dict[str, Any]] = {}
        for entry in self._history:
            bucket = by_model.setdefault(
                entry.model,
                {
                    "calls": 0,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "total_cost": _ZERO,
                },
            )
            bucket["calls"] += 1
            bucket["prompt_tokens"] += entry.usage.prompt_tokens
            bucket["completion_tokens"] += entry.usage.completion_tokens
            bucket["total_tokens"] += entry.usage.total_tokens
            bucket["total_cost"] += entry.total_cost
        return {
            "models": by_model,
            "total_cost": self.total_cost,
            "total_tokens": self.total_tokens,
        }

    def reset(self) -> None:
        """Clear all recorded history."""
        self._history.clear()
