#!/usr/bin/env python3
"""
Comprehensive ZenML Prompt Management Demo

This script demonstrates the complete ZenML prompt management capabilities:
- Prompt creation and versioning
- LLM-as-Judge evaluation
- A/B testing with real LLM responses
- Pipeline-driven prompt optimization
- Production-ready prompt deployment

This showcases why ZenML is superior for LLMOps compared to other platforms.
"""

import os
import click
from typing import Dict, Any

from pipelines.comprehensive_pipeline import (
    comprehensive_prompt_showcase,
    prompt_optimization_pipeline,
    production_deployment_pipeline
)

from zenml.client import Client
from zenml.logger import get_logger

logger = get_logger(__name__)


def check_requirements() -> Dict[str, bool]:
    """Check if all requirements are met."""
    requirements = {
        "zenml_connected": False,
        "llm_api_key": False,
        "stack_ready": False
    }
    
    try:
        client = Client()
        requirements["zenml_connected"] = True
        requirements["stack_ready"] = client.active_stack is not None
        logger.info(f"✓ ZenML connected - Active stack: {client.active_stack.name}")
    except Exception as e:
        logger.error(f"✗ ZenML connection failed: {e}")
        return requirements
    
    # Check for LLM API keys
    api_keys = [
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY", 
        "LITELLM_API_KEY"
    ]
    
    for key in api_keys:
        if os.getenv(key):
            requirements["llm_api_key"] = True
            logger.info(f"✓ Found API key: {key}")
            break
    
    if not requirements["llm_api_key"]:
        logger.warning("⚠ No LLM API key found. Set OPENAI_API_KEY, ANTHROPIC_API_KEY, or LITELLM_API_KEY")
        logger.info("  You can still run the demo with mock responses")
    
    return requirements


@click.command()
@click.option(
    "--demo",
    type=click.Choice(["showcase", "optimization", "production", "all"]),
    default="showcase",
    help="Which demo to run"
)
@click.option(
    "--no-cache",
    is_flag=True,
    default=False,
    help="Disable caching for the pipeline run"
)
@click.option(
    "--use-mock",
    is_flag=True,
    default=False,
    help="Use mock LLM responses instead of real API calls"
)
def main(demo: str, no_cache: bool = False, use_mock: bool = False):
    """Run comprehensive ZenML prompt management demo."""
    
    print("🚀 ZenML Comprehensive Prompt Management Demo")
    print("=" * 60)
    
    # Check requirements
    requirements = check_requirements()
    
    if not requirements["zenml_connected"]:
        logger.error("ZenML is not properly set up. Run 'zenml init' and 'zenml up'")
        return
    
    if not requirements["llm_api_key"] and not use_mock:
        logger.warning("No API key found. Enabling mock mode...")
        use_mock = True
    
    # Configure pipeline settings
    pipeline_args = {
        "enable_cache": not no_cache
    }
    
    # Set mock mode as environment variable for steps to use
    if use_mock:
        import os
        os.environ["USE_MOCK_LLM"] = "true"
    
    print(f"\n🎯 Running demo: {demo}")
    print(f"🔧 Mock mode: {'enabled' if use_mock else 'disabled'}")
    print(f"💾 Cache: {'disabled' if no_cache else 'enabled'}")
    
    try:
        if demo == "showcase" or demo == "all":
            print("\n📊 PHASE 1: Comprehensive Prompt Showcase")
            print("-" * 40)
            print("Demonstrating:")
            print("• Prompt creation with rich metadata")
            print("• LLM-as-Judge quality evaluation") 
            print("• A/B testing with statistical analysis")
            print("• Version comparison and optimization")
            print("• Real-time performance metrics")
            
            comprehensive_prompt_showcase.with_options(**pipeline_args)()
            print("✅ Showcase pipeline completed!")
        
        if demo == "optimization" or demo == "all":
            print("\n🔬 PHASE 2: Prompt Optimization Pipeline")
            print("-" * 40)
            print("Demonstrating:")
            print("• Iterative prompt refinement")
            print("• Multi-criteria evaluation")
            print("• Automated prompt generation")
            print("• Performance tracking over iterations")
            
            prompt_optimization_pipeline.with_options(**pipeline_args)()
            print("✅ Optimization pipeline completed!")
        
        if demo == "production" or demo == "all":
            print("\n🏭 PHASE 3: Production Deployment")
            print("-" * 40)
            print("Demonstrating:")
            print("• Production-ready prompt deployment")
            print("• Monitoring and alerting")
            print("• Rollback capabilities")
            print("• Continuous evaluation")
            
            production_deployment_pipeline.with_options(**pipeline_args)()
            print("✅ Production pipeline completed!")
        
        print("\n🎉 Demo completed successfully!")
        print("\n📊 What to check next:")
        print("1. 🌐 ZenML Dashboard - View rich prompt visualizations")
        print("2. 📈 Artifact Lineage - See prompt evolution over time")
        print("3. 🔄 Pipeline Runs - Compare different experiment results")
        print("4. 📋 Model Registry - View deployed prompt versions")
        print("5. 📊 Analytics - Performance metrics and trends")
        
        print("\n🏆 Why ZenML for Prompt Management:")
        print("• 🔄 Complete MLOps pipeline integration")
        print("• 📊 Built-in evaluation and A/B testing")
        print("• 🏭 Production deployment with monitoring")
        print("• 📈 Version control and lineage tracking")
        print("• 🎯 Stack-agnostic LLM integration")
        print("• 🔐 Enterprise security and compliance")
        
        client = Client()
        print(f"\n🌐 View results: {client.active_stack.name} dashboard")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        print("\n🔧 Troubleshooting:")
        print("1. Ensure ZenML server is running: 'zenml status'")
        print("2. Check API keys are set correctly")
        print("3. Verify internet connection for LLM APIs")
        print("4. Try running with --use-mock flag")


if __name__ == "__main__":
    main()