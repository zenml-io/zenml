#!/usr/bin/env python3
"""Two-Stage Prompt Optimization Example with ZenML."""

import argparse
import os
import sys
from typing import Optional

from models import AgentConfig, DataSourceConfig
from pipelines.production_eda_pipeline import production_eda_pipeline
from pipelines.prompt_optimization_pipeline import prompt_optimization_pipeline


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser.

    Rationale:
    - Uses only the Python standard library to avoid extra dependencies.
    - Mirrors the original Click-based flag and option semantics to keep the
      README usage and user experience unchanged.
    """
    parser = argparse.ArgumentParser(
        description="Run prompt optimization and/or production EDA pipelines (both by default)"
    )
    parser.add_argument(
        "--optimization-pipeline",
        action="store_true",
        help="Run prompt optimization",
    )
    parser.add_argument(
        "--production-pipeline",
        action="store_true",
        help="Run production EDA",
    )
    parser.add_argument(
        "--data-source",
        default="hf:scikit-learn/iris",
        help="Data source (type:path)",
    )
    parser.add_argument(
        "--target-column",
        default="target",
        help="Target column name",
    )
    parser.add_argument(
        "--model-name",
        help="Model name (auto-detected if not specified)",
    )
    parser.add_argument(
        "--max-tool-calls",
        default=6,
        type=int,
        help="Max tool calls",
    )
    parser.add_argument(
        "--timeout-seconds",
        default=60,
        type=int,
        help="Timeout seconds",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable caching",
    )
    return parser


def main() -> int:
    """Run prompt optimization and/or production EDA pipelines."""
    parser = build_parser()
    args = parser.parse_args()

    # Default: run both pipelines if no flags specified
    optimization_pipeline = args.optimization_pipeline
    production_pipeline = args.production_pipeline
    if not optimization_pipeline and not production_pipeline:
        optimization_pipeline = True
        production_pipeline = True

    # Check API keys. We support either OpenAI or Anthropic; at least one is required.
    has_openai = bool(os.getenv("OPENAI_API_KEY"))
    has_anthropic = bool(os.getenv("ANTHROPIC_API_KEY"))

    if not (has_openai or has_anthropic):
        print("❌ Set OPENAI_API_KEY or ANTHROPIC_API_KEY", file=sys.stderr)
        return 1

    # Auto-detect model if not explicitly provided. This keeps a sensible default
    # that aligns with whichever provider the user configured.
    model_name: Optional[str] = args.model_name
    if model_name is None:
        model_name = "gpt-4o-mini" if has_openai else "claude-3-haiku-20240307"

    # Parse data source "type:path" into its components early so we can fail-fast
    # with a helpful error if the format is invalid.
    try:
        source_type, source_path = args.data_source.split(":", 1)
    except ValueError:
        print(f"❌ Invalid data source: {args.data_source}", file=sys.stderr)
        return 2

    # Create configs passed to the pipelines
    source_config = DataSourceConfig(
        source_type=source_type,
        source_path=source_path,
        target_column=args.target_column,
    )

    agent_config = AgentConfig(
        model_name=model_name,
        max_tool_calls=args.max_tool_calls,
        timeout_seconds=args.timeout_seconds,
    )

    # ZenML run options: keep parity with the original example
    pipeline_options = {"enable_cache": not args.no_cache}

    # Stage 1: Prompt optimization
    if optimization_pipeline:
        print("🧪 Running prompt optimization...")

        prompt_variants = [
            "You are a data analyst. Quickly assess data quality (0-100 score) and identify key patterns. Be concise.",
            "You are a data quality specialist. Calculate quality score (0-100), find missing data, duplicates, and correlations. Provide specific recommendations.",
            "You are a business analyst. Assess ML readiness with quality score. Focus on business impact and actionable insights.",
        ]

        try:
            prompt_optimization_pipeline.with_options(**pipeline_options)(
                source_config=source_config,
                prompt_variants=prompt_variants,
                agent_config=agent_config,
            )
            print("✅ Optimization completed - best prompt tagged")
        except Exception as e:
            # Best-effort behavior: log the error and continue to the next stage
            print(f"❌ Optimization failed: {e}", file=sys.stderr)

    # Stage 2: Production analysis
    if production_pipeline:
        print("🏭 Running production analysis...")
        try:
            production_eda_pipeline.with_options(**pipeline_options)(
                source_config=source_config,
                agent_config=agent_config,
            )
            print("✅ Production analysis completed")
        except Exception as e:
            print(f"❌ Production analysis failed: {e}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
