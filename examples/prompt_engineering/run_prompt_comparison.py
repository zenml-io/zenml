#!/usr/bin/env python3
"""Prompt Version Comparison Example - A/B testing for the same task.

This example shows:
1. Same real task (text summarization)
2. Two different prompt versions (v1.0 vs v2.0)
3. Side-by-side comparison of effectiveness
4. Winner determination for the task

This demonstrates A/B testing on actual prompt usage, not artificial comparison.
"""

from pipelines.prompt_comparison import prompt_version_comparison


def display_comparison_results(results: dict):
    """Display the comparison results in a readable format."""
    print("🏆 Prompt Version Comparison Results")
    print("=" * 45)
    print(f"Winner: Prompt {results['winner']}")
    print(f"Conclusion: {results['conclusion']}")
    print()

    metrics = results["comparison_metrics"]
    print("📊 Comparison Metrics:")
    print(
        f"  V1.0 average prompt length: {metrics['v1_avg_prompt_length']:.1f} words"
    )
    print(
        f"  V2.0 average prompt length: {metrics['v2_avg_prompt_length']:.1f} words"
    )
    print(f"  Length difference: {metrics['length_difference']:.1f} words")
    print()

    print("📝 Template Comparison:")
    v1_template = (
        results["prompt_v1"].template[:100] + "..."
        if len(results["prompt_v1"].template) > 100
        else results["prompt_v1"].template
    )
    v2_template = (
        results["prompt_v2"].template[:100] + "..."
        if len(results["prompt_v2"].template) > 100
        else results["prompt_v2"].template
    )

    print(f"  V1.0: {v1_template}")
    print(f"  V2.0: {v2_template}")


def main():
    """Run the prompt comparison pipeline."""
    print("🚀 ZenML Prompt Engineering - Version Comparison")
    print("=" * 50)
    print(
        "This compares different prompt versions on the same summarization task."
    )
    print()

    # Run the pipeline
    print("Running prompt comparison pipeline...")
    pipeline_run = prompt_version_comparison()

    # Get the actual results from the pipeline run
    try:
        # Access the step outputs from the pipeline run
        results = (
            pipeline_run.steps["compare_prompt_versions"]
            .outputs["return"]
            .load()
        )

        # Display results
        print()
        display_comparison_results(results)
    except Exception as e:
        print(f"\n⚠️  Could not load results: {e}")
        print("✅ Pipeline completed successfully!")
        print("🎨 Check the ZenML dashboard to see the results and artifacts.")

    print("\n✅ Pipeline completed!")
    print("\n🎨 Check your ZenML dashboard to see:")
    print("   • Both prompt versions as separate artifacts")
    print("   • Rich visualizations comparing templates")
    print("   • Evaluation results for each version")
    print("   • Winner determination and metrics")
    print("\n💡 This demonstrates:")
    print("   • A/B testing on real tasks (not artificial comparison)")
    print("   • Version management for prompt iterations")
    print("   • Data-driven prompt selection")
    print("   • Production-ready comparison workflows")


if __name__ == "__main__":
    main()
