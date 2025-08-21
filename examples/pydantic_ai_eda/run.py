#!/usr/bin/env python3
"""Simple Pydantic AI EDA pipeline runner."""

import os

from models import AgentConfig, DataSourceConfig
from pipelines.eda_pipeline import eda_pipeline


def main():
    """Run the EDA pipeline with simple configuration."""
    print("🔍 Pydantic AI EDA Pipeline")
    print("=" * 30)

    # Check for API keys
    has_openai = bool(os.getenv("OPENAI_API_KEY"))
    has_anthropic = bool(os.getenv("ANTHROPIC_API_KEY"))

    if not (has_openai or has_anthropic):
        print("❌ No API keys found!")
        print("Set OPENAI_API_KEY or ANTHROPIC_API_KEY environment variable")
        return

    model_name = "gpt-4o-mini" if has_openai else "claude-3-haiku-20240307"
    print(f"🤖 Using model: {model_name}")

    # Simple configuration
    source_config = DataSourceConfig(
        source_type="hf",
        source_path="scikit-learn/iris",
        target_column="target",
    )

    agent_config = AgentConfig(
        model_name=model_name,
        max_tool_calls=6,  # Keep it snappy - just the essentials
        timeout_seconds=60,  # Quick analysis
    )

    print(f"📊 Analyzing: {source_config.source_path}")

    try:
        results = eda_pipeline.with_options(enable_cache=False)(
            source_config=source_config,
            agent_config=agent_config,
            min_quality_score=70.0,
        )
        print("✅ Pipeline completed! Check ZenML dashboard for results.")
        return results
    except Exception as e:
        print(f"❌ Pipeline failed: {e}")
        print("\nTroubleshooting:")
        print("- Check your API key is valid")
        print("- Ensure ZenML is initialized: zenml init")
        print("- Install requirements: pip install -r requirements.txt")


if __name__ == "__main__":
    main()
