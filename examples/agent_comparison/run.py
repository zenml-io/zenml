#!/usr/bin/env python3
"""Simple runner script for the Agent Architecture Comparison example.

This provides a clean entry point for users who want to run the example
without needing to understand the full pipeline implementation.
"""

from pipelines import compare_agent_architectures


def main() -> None:
    """Run the agent architecture comparison pipeline."""
    print("🚀 Starting Agent Architecture Comparison Pipeline...")
    print("This will demonstrate:")
    print("  • Training a scikit-learn intent classifier")
    print("  • Running 3 different agent architectures")
    print("  • LiteLLM integration (real LLMs if API keys detected)")
    print("  • Generating LangGraph workflow visualizations")
    print("  • Creating beautiful HTML comparison reports")
    print()

    # Check if real LLMs will be used
    from llm_utils import should_use_real_llm

    if should_use_real_llm():
        print("✨ Real LLM APIs detected! Using LiteLLM for agent responses.")
    else:
        print(
            "📝 No LLM API keys found. Using mock responses (perfect for demos)."
        )
        print("💡 Set OPENAI_API_KEY to enable real LLM integration.")
    print()

    # Execute the pipeline
    compare_agent_architectures()

    print("✅ Pipeline completed successfully!")
    print()
    print("🎯 Check the ZenML Dashboard to see:")
    print("  • Customer service queries dataset")
    print("  • Trained intent classifier model")
    print("  • Architecture performance metrics")
    print("  • Interactive Mermaid workflow diagram")
    print("  • Beautiful HTML comparison report")
    print()
    print("💡 Start the dashboard with: zenml login")


if __name__ == "__main__":
    main()
