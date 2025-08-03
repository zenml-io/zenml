from pipelines.simple_comparison import simple_prompt_comparison
from utils.helpers import format_comparison_results


def main():
    """Run the simple prompt comparison pipeline."""
    print("🚀 ZenML Prompt Engineering - Simple Comparison")
    print("=" * 50)
    
    # Run the pipeline
    print("Running prompt comparison pipeline...")
    result = simple_prompt_comparison()
    
    # Display results
    print("\n" + format_comparison_results(result))
    
    print("\n✅ Pipeline completed!")
    print("🎨 Check your ZenML dashboard to see:")
    print("   • Prompt artifacts with rich visualizations")
    print("   • Version tracking (v1.0 vs v2.0)")
    print("   • Comparison results and metrics")
    print("   • Pipeline run details")


if __name__ == "__main__":
    main()