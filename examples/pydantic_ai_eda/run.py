#!/usr/bin/env python3
"""Run the Pydantic AI EDA pipeline.

This script provides multiple ways to run the EDA pipeline:
- With HuggingFace datasets (default)
- With local CSV files
- With different quality thresholds
- For testing and production scenarios

Works with or without API keys (falls back to statistical analysis).
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Optional

from models import AgentConfig, DataSourceConfig
from pipelines.eda_pipeline import eda_pipeline


def create_sample_dataset():
    """Create a sample iris dataset CSV for local testing."""
    try:
        import pandas as pd
        from sklearn.datasets import load_iris

        print("📁 Creating sample dataset...")
        iris = load_iris()
        df = pd.DataFrame(iris.data, columns=iris.feature_names)
        df["target"] = iris.target

        df.to_csv("iris_sample.csv", index=False)
        print(f"✅ Created iris_sample.csv with {len(df)} rows")
        return "iris_sample.csv"
    except ImportError:
        print("❌ sklearn not available for sample dataset creation")
        return None


def check_api_keys():
    """Check for available API keys and return provider info."""
    has_openai = bool(os.getenv("OPENAI_API_KEY"))
    has_anthropic = bool(os.getenv("ANTHROPIC_API_KEY"))

    if has_openai and has_anthropic:
        print("🤖 Both OpenAI and Anthropic API keys detected")
        return "both"
    elif has_openai:
        print("🤖 OpenAI API key detected - will use GPT models")
        return "openai"
    elif has_anthropic:
        print("🤖 Anthropic API key detected - will use Claude models")
        return "anthropic"
    else:
        print("⚠️  No API keys found - will use statistical fallback analysis")
        print(
            "   Set OPENAI_API_KEY or ANTHROPIC_API_KEY for full AI features"
        )
        return None


def run_pipeline(
    source_type: str = "hf",
    source_path: str = "scikit-learn/iris",
    target_column: Optional[str] = "target",
    min_quality_score: float = 70.0,
    ai_provider: Optional[str] = None,
    timeout: int = 300,
    sample_size: Optional[int] = None,
    verbose: bool = False,
):
    """Run the EDA pipeline with specified configuration."""

    # Configure data source
    source_config = DataSourceConfig(
        source_type=source_type,
        source_path=source_path,
        target_column=target_column,
        sample_size=sample_size,
    )

    # Configure AI agent based on available providers
    if ai_provider == "anthropic":
        model_name = "claude-4"
    elif ai_provider == "openai":
        model_name = "gpt-5"
    else:
        model_name = "gpt-5"  # Default fallback

    agent_config = AgentConfig(
        model_name=model_name,
        max_tool_calls=15,  # Reduced to prevent infinite loops
        sql_guard_enabled=True,
        preview_limit=10,
        timeout_seconds=timeout,
        temperature=0.1,
    )

    print(f"📊 Analyzing dataset: {source_config.source_path}")
    if target_column:
        print(f"🎯 Target column: {target_column}")
    print(f"📏 Quality threshold: {min_quality_score}")

    try:
        print("🚀 Running EDA pipeline")
        results = eda_pipeline.with_options(enable_cache=False)(
            source_config=source_config,
            agent_config=agent_config,
            min_quality_score=min_quality_score,
            block_on_high_severity=False,  # Don't block for demo
            max_missing_data_pct=30.0,
            require_target_column=bool(target_column),
        )

        print("✅ Pipeline completed successfully!")

        # Display results summary
        print(f"\n{'=' * 60}")
        print("📋 PIPELINE RESULTS")
        print("=" * 60)

        # Show pipeline run info
        if hasattr(results, "id"):
            print(f"📝 Pipeline run ID: {results.id}")
        if hasattr(results, "status"):
            print(f"📊 Status: {results.status}")
        if hasattr(results, "name"):
            print(f"🏷️  Name: {results.name}")

        # Show artifact locations
        print(f"\n📦 Generated Artifacts:")
        print(f"  • EDA report (markdown): Available in ZenML dashboard")
        print(f"  • Analysis results (JSON): Available in ZenML dashboard")
        print(f"  • Quality assessment: Available in ZenML dashboard")
        print(f"  • SQL execution log: Available in ZenML dashboard")
        print(f"  • Analysis tables: Available in ZenML dashboard")

        # Show next steps
        print(f"\n📖 Next Steps:")
        print(f"  • View full results in ZenML dashboard")
        print(
            f"  • Access artifacts: results.steps['step_name'].outputs['artifact_name'].load()"
        )
        print(f"  • Run with different parameters using command line options")

        if not ai_provider:
            print(f"\n🔑 For AI-powered analysis:")
            print(f"  • Set: export OPENAI_API_KEY='your-key'")
            print(f"  • Or: export ANTHROPIC_API_KEY='your-key'")
            print(f"  • Then re-run for intelligent insights")

        return results

    except Exception as e:
        print(f"❌ Pipeline failed: {e}")

        if verbose:
            import traceback

            print(f"\n🔍 Full error traceback:")
            traceback.print_exc()

        print(f"\n🔧 Troubleshooting:")
        if source_type == "hf":
            print(f"  • Check internet connection for HuggingFace datasets")
            print(
                f"  • Try local mode: python run.py --source-type local --create-sample"
            )
        elif source_type == "local":
            print(f"  • Check file exists: {source_path}")
            print(f"  • Ensure file is valid CSV format")

        print(f"  • Ensure ZenML is initialized: zenml init")
        print(f"  • Check ZenML stack: zenml stack list")
        print(f"  • Install dependencies: pip install -r requirements.txt")

        return None


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(
        description="Run Pydantic AI EDA Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage with HuggingFace dataset
  python run.py
  
  # Use local CSV file
  python run.py --source-type local --source-path data.csv --target target_col
  
  # Create and use sample dataset
  python run.py --source-type local --create-sample
  
  # Custom quality threshold
  python run.py --min-quality-score 80
  
  # Custom dataset with specific settings
  python run.py --source-path username/dataset --sample-size 1000 --timeout 600
        """,
    )

    # Data source options
    parser.add_argument(
        "--source-type",
        choices=["hf", "local", "warehouse"],
        default="hf",
        help="Data source type (default: hf)",
    )
    parser.add_argument(
        "--source-path",
        default="scikit-learn/iris",
        help="Dataset path (HF dataset name or file path) (default: scikit-learn/iris)",
    )
    parser.add_argument(
        "--target-column",
        default="target",
        help="Target column name (default: target)",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        help="Limit dataset to N rows for faster processing",
    )

    # Pipeline options
    parser.add_argument(
        "--min-quality-score",
        type=float,
        default=70.0,
        help="Minimum quality score threshold (default: 70.0)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="AI agent timeout in seconds (default: 300)",
    )

    # Utility options
    parser.add_argument(
        "--create-sample",
        action="store_true",
        help="Create iris_sample.csv for local testing",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Show detailed error traces"
    )

    args = parser.parse_args()

    print("🚀 Pydantic AI EDA Pipeline")
    print("=" * 40)

    # Create sample dataset if requested
    if args.create_sample:
        sample_file = create_sample_dataset()
        if sample_file and args.source_type == "local":
            args.source_path = sample_file
            print(f"🔄 Switched to created sample: {sample_file}")

    # Check API key availability
    ai_provider = check_api_keys()

    # Validate local file exists
    if args.source_type == "local":
        if not Path(args.source_path).exists():
            print(f"❌ Local file not found: {args.source_path}")
            if not args.create_sample:
                print(
                    f"💡 Try: python run.py --source-type local --create-sample"
                )
                sys.exit(1)

    # Run the pipeline
    results = run_pipeline(
        source_type=args.source_type,
        source_path=args.source_path,
        target_column=args.target_column,
        min_quality_score=args.min_quality_score,
        ai_provider=ai_provider,
        timeout=args.timeout,
        sample_size=args.sample_size,
        verbose=args.verbose,
    )

    if results:
        print(f"\n🎉 Pipeline completed successfully!")
        sys.exit(0)
    else:
        print(f"\n💥 Pipeline failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
