#!/usr/bin/env python3
"""Two-Stage Prompt Optimization Example with ZenML."""

import os
from typing import Optional

import click

from models import AgentConfig, DataSourceConfig
from pipelines.production_eda_pipeline import production_eda_pipeline
from pipelines.prompt_optimization_pipeline import prompt_optimization_pipeline


@click.command(help="Run prompt optimization and/or production EDA pipelines (both by default)")
@click.option("--optimization-pipeline", is_flag=True, help="Run prompt optimization")
@click.option("--production-pipeline", is_flag=True, help="Run production EDA")
@click.option("--data-source", default="hf:scikit-learn/iris", help="Data source (type:path)")
@click.option("--target-column", default="target", help="Target column name")
@click.option("--model-name", help="Model name (auto-detected if not specified)")
@click.option("--max-tool-calls", default=6, type=int, help="Max tool calls")
@click.option("--timeout-seconds", default=60, type=int, help="Timeout seconds")
@click.option("--no-cache", is_flag=True, help="Disable caching")
def main(
    optimization_pipeline: bool = False,
    production_pipeline: bool = False,
    data_source: str = "hf:scikit-learn/iris",
    target_column: str = "target",
    model_name: Optional[str] = None,
    max_tool_calls: int = 6,
    timeout_seconds: int = 60,
    no_cache: bool = False,
):
    """Run prompt optimization and/or production EDA pipelines."""
    # Default: run both pipelines if no flags specified
    if not optimization_pipeline and not production_pipeline:
        optimization_pipeline = True
        production_pipeline = True

    # Check API keys
    has_openai = bool(os.getenv("OPENAI_API_KEY"))
    has_anthropic = bool(os.getenv("ANTHROPIC_API_KEY"))

    if not (has_openai or has_anthropic):
        click.echo("❌ Set OPENAI_API_KEY or ANTHROPIC_API_KEY")
        return

    # Auto-detect model
    if model_name is None:
        model_name = "gpt-4o-mini" if has_openai else "claude-3-haiku-20240307"
    
    # Parse data source
    try:
        source_type, source_path = data_source.split(":", 1)
    except ValueError:
        click.echo(f"❌ Invalid data source: {data_source}")
        return
    
    # Create configs
    source_config = DataSourceConfig(
        source_type=source_type,
        source_path=source_path,
        target_column=target_column,
    )

    agent_config = AgentConfig(
        model_name=model_name,
        max_tool_calls=max_tool_calls,
        timeout_seconds=timeout_seconds,
    )
    
    pipeline_options = {"enable_cache": not no_cache}
    
    # Stage 1: Prompt optimization
    if optimization_pipeline:
        click.echo("🧪 Running prompt optimization...")
        
        prompt_variants = [
            "You are a data analyst. Quickly assess data quality (0-100 score) and identify key patterns. Be concise.",
            "You are a data quality specialist. Calculate quality score (0-100), find missing data, duplicates, and correlations. Provide specific recommendations.",
            "You are a business analyst. Assess ML readiness with quality score. Focus on business impact and actionable insights."
        ]
        
        try:
            prompt_optimization_pipeline.with_options(**pipeline_options)(
                source_config=source_config,
                prompt_variants=prompt_variants,
                agent_config=agent_config,
            )
            click.echo("✅ Optimization completed - best prompt tagged")
            
        except Exception as e:
            click.echo(f"❌ Optimization failed: {e}")
    
    # Stage 2: Production analysis  
    if production_pipeline:
        click.echo("🏭 Running production analysis...")
        
        try:
            production_eda_pipeline.with_options(**pipeline_options)(
                source_config=source_config,
                agent_config=agent_config,
            )
            click.echo("✅ Production analysis completed")
            
        except Exception as e:
            click.echo(f"❌ Production analysis failed: {e}")


if __name__ == "__main__":
    main()