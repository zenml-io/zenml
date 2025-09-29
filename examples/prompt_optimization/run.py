#!/usr/bin/env python3
"""Two-Stage Prompt Optimization Example with ZenML."""

import argparse
import os
import sys
from typing import List, Optional

from models import AgentConfig, DataSourceConfig, ScoringConfig
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

    # Instantiate defaults from ScoringConfig so CLI flags reflect canonical values
    scoring_defaults = ScoringConfig()

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
        help="Data source in 'type:path' format, e.g., 'hf:scikit-learn/iris' or 'local:./data.csv'",
    )
    parser.add_argument(
        "--target-column",
        default="target",
        help="Target column name",
    )
    parser.add_argument(
        "--model-name",
        help="Model name (auto-detected if not specified). Can be fully-qualified like 'openai:gpt-4o-mini' or 'anthropic:claude-3-haiku-20240307'.",
    )
    parser.add_argument(
        "--provider",
        choices=["auto", "openai", "anthropic"],
        default="auto",
        help="Model provider to use. 'auto' infers from model/name/environment.",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        help="Optional row sample size for the dataset.",
    )
    parser.add_argument(
        "--prompts-file",
        help="Path to a newline-delimited prompts file (UTF-8). One prompt per line; blank lines are ignored.",
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

    # Scoring knobs (seeded from ScoringConfig defaults)
    parser.add_argument(
        "--weight-quality",
        type=float,
        default=scoring_defaults.weight_quality,
        help="Weight for the quality component.",
    )
    parser.add_argument(
        "--weight-speed",
        type=float,
        default=scoring_defaults.weight_speed,
        help="Weight for the speed/latency component.",
    )
    parser.add_argument(
        "--weight-findings",
        type=float,
        default=scoring_defaults.weight_findings,
        help="Weight for the findings coverage component.",
    )
    parser.add_argument(
        "--speed-penalty-per-second",
        type=float,
        default=scoring_defaults.speed_penalty_per_second,
        help="Penalty points per second applied when computing a speed score.",
    )
    parser.add_argument(
        "--findings-score-per-item",
        type=float,
        default=scoring_defaults.findings_score_per_item,
        help="Base points credited per key finding before applying weights.",
    )
    parser.add_argument(
        "--findings-cap",
        type=int,
        default=scoring_defaults.findings_cap,
        help="Maximum number of findings to credit when scoring.",
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

    # Derive raw model name from CLI or sensible defaults considering provider/env
    raw_model_name: Optional[str] = args.model_name
    if raw_model_name is None:
        if args.provider == "openai":
            raw_model_name = "gpt-4o-mini"
        elif args.provider == "anthropic":
            raw_model_name = "claude-3-haiku-20240307"
        else:
            raw_model_name = (
                "gpt-4o-mini" if has_openai else "claude-3-haiku-20240307"
            )

    # Detect and strip provider prefixes (e.g., 'openai:gpt-4o-mini'), preserving explicit provider
    explicit_provider: Optional[str] = None
    normalized_model_name = raw_model_name.strip()
    if ":" in normalized_model_name:
        maybe_provider, remainder = normalized_model_name.split(":", 1)
        maybe_provider = maybe_provider.strip().lower()
        if maybe_provider in ("openai", "anthropic"):
            explicit_provider = maybe_provider
            normalized_model_name = remainder.strip()

    # Combine with --provider to determine provider choice
    if args.provider == "auto":
        provider_choice: Optional[str] = explicit_provider or None
    else:
        provider_choice = args.provider

    # Validate that the chosen provider has its corresponding API key configured
    if provider_choice == "openai" and not has_openai:
        print(
            "❌ You selected --provider openai (or model prefix 'openai:') but OPENAI_API_KEY is not set.",
            file=sys.stderr,
        )
        return 1
    if provider_choice == "anthropic" and not has_anthropic:
        print(
            "❌ You selected --provider anthropic (or model prefix 'anthropic:') but ANTHROPIC_API_KEY is not set.",
            file=sys.stderr,
        )
        return 1

    # Parse data source "type:path" into its components
    try:
        source_type, source_path = args.data_source.split(":", 1)
    except ValueError:
        print(
            "❌ Invalid --data-source. Expected 'type:path' (e.g., 'hf:scikit-learn/iris' or 'local:./data.csv').",
            file=sys.stderr,
        )
        print(
            f"Provided value: {args.data_source}. Update the flag or use one of the examples above.",
            file=sys.stderr,
        )
        return 2

    # Prepare prompt variants: file-based if provided; otherwise use baked-in defaults
    prompt_variants: List[str]
    if args.prompts_file:
        try:
            with open(args.prompts_file, "r", encoding="utf-8") as f:
                prompt_variants = [
                    line.strip()
                    for line in f.read().splitlines()
                    if line.strip()
                ]
            if not prompt_variants:
                print(
                    f"❌ Prompts file is empty after removing blank lines: {args.prompts_file}",
                    file=sys.stderr,
                )
                print(
                    "Add one prompt per line, or omit --prompts-file to use the built-in defaults.",
                    file=sys.stderr,
                )
                return 4
        except OSError:
            print(
                f"❌ Unable to read prompts file: {args.prompts_file}",
                file=sys.stderr,
            )
            print(
                "Provide a valid path with --prompts-file or omit the flag to use the built-in prompts.",
                file=sys.stderr,
            )
            return 3
    else:
        prompt_variants = [
            "You are a data analyst. Quickly assess data quality (0-100 score) and identify key patterns. Be concise.",
            "You are a data quality specialist. Calculate quality score (0-100), find missing data, duplicates, and correlations. Provide specific recommendations.",
            "You are a business analyst. Assess ML readiness with quality score. Focus on business impact and actionable insights.",
        ]

    # Create configs passed to the pipelines
    source_config = DataSourceConfig(
        source_type=source_type,
        source_path=source_path,
        target_column=args.target_column,
        sample_size=args.sample_size,
    )

    agent_config = AgentConfig(
        model_name=normalized_model_name,
        provider=provider_choice,  # None => auto inference in AgentConfig
        max_tool_calls=args.max_tool_calls,
        timeout_seconds=args.timeout_seconds,
    )

    scoring_config = ScoringConfig(
        weight_quality=args.weight_quality,
        weight_speed=args.weight_speed,
        weight_findings=args.weight_findings,
        speed_penalty_per_second=args.speed_penalty_per_second,
        findings_score_per_item=args.findings_score_per_item,
        findings_cap=args.findings_cap,
    )

    # ZenML run options: keep parity with the original example
    pipeline_options = {"enable_cache": not args.no_cache}

    # Concise transparency logs
    sample_info = args.sample_size if args.sample_size is not None else "all"
    print(
        f"ℹ️  Provider: {provider_choice or 'auto'} | Model: {normalized_model_name} | Data: {source_type}:{source_path} (target={args.target_column}, sample={sample_info})"
    )
    print(
        f"ℹ️  Prompt variants: {len(prompt_variants)} | Tool calls: {args.max_tool_calls} | Timeout: {args.timeout_seconds}s"
    )

    # Stage 1: Prompt optimization
    if optimization_pipeline:
        print("🧪 Running prompt optimization...")
        try:
            optimization_result = prompt_optimization_pipeline.with_options(
                **pipeline_options
            )(
                source_config=source_config,
                prompt_variants=prompt_variants,
                agent_config=agent_config,
                scoring_config=scoring_config,
            )
            print("✅ Optimization completed")
            # Pretty-print a compact scoreboard summary if available
            if isinstance(optimization_result, dict):
                scoreboard = optimization_result.get("scoreboard") or []
                best_prompt = optimization_result.get("best_prompt")
                if isinstance(scoreboard, list) and scoreboard:
                    top = sorted(
                        scoreboard,
                        key=lambda x: x.get("score", 0.0),
                        reverse=True,
                    )[:3]
                    print("📊 Scoreboard (top 3):")
                    for entry in top:
                        pid = entry.get("prompt_id", "?")
                        sc = entry.get("score", 0.0)
                        t = entry.get("execution_time", 0.0)
                        f = entry.get("findings_count", 0)
                        ok = entry.get("success", False)
                        mark = "✅" if ok else "❌"
                        print(
                            f"- {pid} | score: {sc:.1f} | time: {t:.1f}s | findings: {f} | {mark}"
                        )
                if isinstance(best_prompt, str) and best_prompt:
                    preview = best_prompt.replace("\n", " ")[:80]
                    print(
                        f"📝 Best prompt preview: {preview}{'...' if len(best_prompt) > 80 else ''}"
                    )
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
