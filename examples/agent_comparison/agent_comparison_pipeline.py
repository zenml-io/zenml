"""Agent Architecture Comparison Pipeline.

This pipeline implements the README example for comparing different agent architectures
on customer service queries. It demonstrates how to use ZenML to evaluate and compare
different AI approaches in a reproducible way.

This is the main entry point that imports from the modular structure.
"""

from pipelines import compare_agent_architectures

if __name__ == "__main__":
    # Run the comparison pipeline
    print("🚀 Starting Agent Architecture Comparison Pipeline...")
    print(
        "This will compare three different agent architectures on customer service queries."
    )
    print("📊 Now featuring LangGraph workflow visualization!")
    print()

    # Execute the pipeline
    result = compare_agent_architectures()

    print("✅ Pipeline completed successfully!")
    print("\n" + "=" * 60)
    print("📊 EVALUATION REPORT")
    print("=" * 60)
    print(
        "Check the ZenML Dashboard for the detailed evaluation report and LangGraph workflow visualization!"
    )
