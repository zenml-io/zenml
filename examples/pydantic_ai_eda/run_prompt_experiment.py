#!/usr/bin/env python3
"""Run prompt experimentation pipeline to optimize Pydantic AI agents."""

import os
from models import AgentConfig, DataSourceConfig
from pipelines.prompt_experiment_pipeline import prompt_experiment_pipeline


def main():
    """Run prompt A/B testing to find the best system prompt."""
    print("🧪 Pydantic AI Prompt Experimentation")
    print("=" * 40)
    
    # Check for API keys
    has_openai = bool(os.getenv("OPENAI_API_KEY"))
    has_anthropic = bool(os.getenv("ANTHROPIC_API_KEY"))
    
    if not (has_openai or has_anthropic):
        print("❌ No API keys found!")
        print("Set OPENAI_API_KEY or ANTHROPIC_API_KEY environment variable")
        return
    
    model_name = "gpt-4o-mini" if has_openai else "claude-3-haiku-20240307"
    print(f"🤖 Using model: {model_name}")

    # Dataset configuration
    source_config = DataSourceConfig(
        source_type="hf",
        source_path="scikit-learn/iris",
        target_column="target",
    )

    agent_config = AgentConfig(
        model_name=model_name,
        max_tool_calls=4,  # Reduce for faster testing
        timeout_seconds=30,  # Shorter timeout to avoid stalling
    )

    # Define prompt variants to test (simplified for speed)
    prompt_variants = [
        # Variant 1: Concise
        """You are a data analyst. Analyze the dataset quickly - focus on data quality score and key findings. Be concise.""",
        
        # Variant 2: Quality-focused  
        """You are a data quality specialist. Calculate data quality score, identify missing data and duplicates. Provide specific recommendations.""",
        
        # Variant 3: Business-oriented
        """You are a business analyst. Is this data ready for ML? Provide go/no-go recommendation with quality score and business impact."""
    ]

    print(f"📊 Testing {len(prompt_variants)} prompt variants on: {source_config.source_path}")
    print("This will help identify the best performing prompt for your use case.\n")

    try:
        pipeline_run = prompt_experiment_pipeline(
            source_config=source_config,
            prompt_variants=prompt_variants,
            agent_config=agent_config,
        )
        
        # Extract results from ZenML pipeline artifacts
        print("📈 EXPERIMENT RESULTS")
        print("=" * 25)
        print("✅ Pipeline completed successfully!")
        
        # Get the artifact from the pipeline run
        run_metadata = pipeline_run.dict()
        print(f"🔍 Pipeline run ID: {pipeline_run.id}")
        print(f"📊 Check ZenML dashboard for detailed experiment results")
        print(f"🏆 Results are stored as pipeline artifacts")
        
        # Try to access the step outputs
        try:
            step_names = list(pipeline_run.steps.keys())
            print(f"📋 Pipeline steps: {step_names}")
            
            if "compare_agent_prompts" in step_names:
                step_output = pipeline_run.steps["compare_agent_prompts"]
                print(f"🎯 Experiment data available in step outputs")
                
                # Try to load the actual results
                outputs = step_output.outputs
                if "prompt_comparison_results" in outputs:
                    experiment_data = outputs["prompt_comparison_results"].load()
                    summary = experiment_data["experiment_summary"]
                    
                    print(f"✅ Successful runs: {summary['successful_runs']}/{summary['total_prompts_tested']}")
                    print(f"🏆 Best prompt: {summary['best_prompt_variant']}")
                    print(f"⏱️  Average time: {summary['avg_execution_time']}s")
                    
                    print("\n💡 RECOMMENDATIONS:")
                    for rec in experiment_data["recommendations"]:
                        print(f"  • {rec}")
        
        except Exception as e:
            print(f"⚠️  Could not extract detailed results: {e}")
            print("Check ZenML dashboard for full experiment analysis")
            
        print(f"\n✅ Prompt experiment completed! Check ZenML dashboard for detailed results.")
        return pipeline_run
        
    except Exception as e:
        print(f"❌ Experiment failed: {e}")
        print("\nTroubleshooting:")
        print("- Check your API key is valid")
        print("- Ensure ZenML is initialized: zenml init") 
        print("- Install requirements: pip install -r requirements.txt")


if __name__ == "__main__":
    main()