#!/usr/bin/env python3
"""Text Summarization Example - Real prompt usage demonstration.

This example shows:
1. Using prompts for actual work (text summarization)
2. Versioned prompts (v1.0 template)
3. Dashboard visualization of prompt artifacts
4. Evaluation of prompt effectiveness

This demonstrates prompts being used for real tasks, not just comparison.
"""

from pipelines.text_summarization import text_summarization_pipeline


def display_results(results: dict):
    """Display the pipeline results in a readable format."""
    print("📊 Text Summarization Results")
    print("=" * 40)
    print(f"Prompt Version: {results['prompt_version']}")
    print(f"Articles Processed: {results['total_articles']}")
    print()

    print("📝 Sample Formatted Prompts:")
    for i, result in enumerate(results["results"][:2]):  # Show first 2
        print(f"\n--- Article {result['article_id']} ---")
        print(f"Original: {result['original_word_count']} words")
        print(f"Formatted Prompt Preview:")
        print(result["formatted_prompt"])

    print(f"\n📈 Metrics:")
    metrics = results["metrics"]
    print(
        f"  Average original length: {metrics['average_original_length']:.1f} words"
    )
    print(
        f"  Average prompt length: {metrics['average_prompt_length']:.1f} words"
    )
    print(f"  Assessment: {metrics['template_effectiveness']}")


def main():
    """Run the text summarization pipeline."""
    print("🚀 ZenML Prompt Engineering - Text Summarization")
    print("=" * 50)
    print("This demonstrates real prompt usage for text summarization tasks.")
    print()

    # Run the pipeline
    print("Running text summarization pipeline...")
    pipeline_run = text_summarization_pipeline()

    # Get the actual results from the pipeline run
    try:
        # Access the step outputs from the pipeline run
        results = (
            pipeline_run.steps["evaluate_summaries"].outputs["return"].load()
        )

        # Display results
        print()
        display_results(results)
    except Exception as e:
        print(f"\n⚠️  Could not load results: {e}")
        print("✅ Pipeline completed successfully!")
        print("🎨 Check the ZenML dashboard to see the results and artifacts.")

    print("\n✅ Pipeline completed!")
    print("\n🎨 Check your ZenML dashboard to see:")
    print("   • Prompt artifact with syntax highlighting")
    print("   • Template structure and variables")
    print("   • Pipeline run with all steps")
    print("   • Evaluation results and metrics")
    print("\n💡 This shows prompts being used for real work:")
    print("   • Loading actual data (articles)")
    print("   • Creating versioned prompt templates")
    print("   • Applying prompts to format text for LLM processing")
    print("   • Evaluating prompt effectiveness")


if __name__ == "__main__":
    main()
