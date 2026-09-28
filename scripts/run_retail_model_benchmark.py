#!/usr/bin/env python3
"""Run real model architecture comparisons for the Retail BA Agent.

No provider result is fabricated. A provider is runnable only when its API key,
model and (where required) endpoint are configured.
"""

from __future__ import annotations

import argparse
import json
import os
from collections.abc import Callable
from pathlib import Path

from eiw.retail.data import RetailDataEngine
from eiw.retail.model_benchmark import ArchitectureMode, ModelArchitectureBenchmark
from eiw.retail.model_client import (
    AnthropicChatClient,
    ChatClient,
    GeminiChatClient,
    ModelPricing,
    OpenAICompatibleChatClient,
)


def required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(f"missing required environment variable: {name}")
    return value


def pricing(prefix: str) -> ModelPricing:
    return ModelPricing(
        input_per_million_usd=float(
            os.getenv(f"{prefix}_INPUT_USD_PER_MTOK", "0") or 0
        ),
        output_per_million_usd=float(
            os.getenv(f"{prefix}_OUTPUT_USD_PER_MTOK", "0") or 0
        ),
    )


def provider_factory(provider: str) -> tuple[str, Callable[[], ChatClient], bool]:
    if provider == "openai":
        model = required("OPENAI_MODEL")
        key = required("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").strip()
        price = pricing("OPENAI")
        return (
            model,
            lambda: OpenAICompatibleChatClient(
                base_url=base_url,
                model=model,
                api_key=key,
                pricing=price,
            ),
            bool(price.input_per_million_usd or price.output_per_million_usd),
        )
    if provider == "qwen":
        model = required("QWEN_MODEL")
        key = os.getenv("QWEN_API_KEY", "").strip() or required("DASHSCOPE_API_KEY")
        base_url = required("QWEN_BASE_URL")
        price = pricing("QWEN")
        return (
            model,
            lambda: OpenAICompatibleChatClient(
                base_url=base_url,
                model=model,
                api_key=key,
                pricing=price,
            ),
            bool(price.input_per_million_usd or price.output_per_million_usd),
        )
    if provider == "anthropic":
        model = required("ANTHROPIC_MODEL")
        key = required("ANTHROPIC_API_KEY")
        base_url = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1")
        price = pricing("ANTHROPIC")
        return (
            model,
            lambda: AnthropicChatClient(
                base_url=base_url,
                model=model,
                api_key=key,
                pricing=price,
            ),
            bool(price.input_per_million_usd or price.output_per_million_usd),
        )
    if provider == "gemini":
        model = required("GEMINI_MODEL")
        key = required("GEMINI_API_KEY")
        base_url = os.getenv(
            "GEMINI_BASE_URL",
            "https://generativelanguage.googleapis.com/v1beta",
        )
        price = pricing("GEMINI")
        return (
            model,
            lambda: GeminiChatClient(
                base_url=base_url,
                model=model,
                api_key=key,
                pricing=price,
            ),
            bool(price.input_per_million_usd or price.output_per_million_usd),
        )
    raise SystemExit(f"unsupported provider: {provider}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--provider",
        required=True,
        choices=("openai", "qwen", "anthropic", "gemini"),
    )
    parser.add_argument("--cases", type=int, default=10)
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--architectures",
        default="deterministic,single-agent,supervisor,supervisor+specialists",
    )
    args = parser.parse_args()

    model, factory, pricing_configured = provider_factory(args.provider)
    engine = (
        RetailDataEngine.from_complete_journey(args.data_dir)
        if args.data_dir is not None
        else RetailDataEngine.demo()
    )
    requested = tuple(
        ArchitectureMode(value.strip())
        for value in args.architectures.split(",")
        if value.strip()
    )
    result = ModelArchitectureBenchmark(
        engine,
        provider=args.provider,
        model=model,
        client_factory=factory,
    ).run(case_limit=args.cases, modes=requested)
    result["pricing_configured"] = pricing_configured
    rendered = json.dumps(result, indent=2, ensure_ascii=False)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
