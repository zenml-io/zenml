#!/usr/bin/env python
"""Working example demonstrating prompt engineering with ZenML."""

import os

from zenml.logger import get_logger

logger = get_logger(__name__)


def main():
    """Run working examples of prompt engineering pipelines."""
    # Check environment
    if not os.getenv("AZURE_OPENAI_API_KEY"):
        logger.error("Please set AZURE_OPENAI_API_KEY environment variable")
        return

    logger.info("🚀 Running ZenML Prompt Engineering Examples")

    print("\n" + "=" * 60)
    print("1. BASIC PROMPT DEVELOPMENT PIPELINE")
    print("=" * 60)

    # Import here to avoid issues if environment isn't set up
    from pipelines import prompt_development_pipeline

    # Run basic pipeline
    pipeline_run = prompt_development_pipeline(
        template="You are an expert assistant. Provide a comprehensive answer to: {question}",
        prompt_type="user",
        task="question_answering",
        model="gpt-4.1-mini",
    )

    # Get results
    prompt = (
        pipeline_run.steps["create_prompt_step"]
        .outputs["created_prompt"][0]
        .load()
    )
    results = (
        pipeline_run.steps["test_prompt_with_llm_step"]
        .outputs["test_results"][0]
        .load()
    )
    evaluation = (
        pipeline_run.steps["evaluate_prompt_step"]
        .outputs["evaluation_metrics"][0]
        .load()
    )

    print(f"✅ Basic Pipeline Results:")
    print(f"   • Prompt ID: {prompt.prompt_id}")
    print(f"   • Success Rate: {evaluation['success_rate']:.1%}")
    print(
        f"   • Average Output Length: {evaluation['avg_output_length']:.0f} characters"
    )

    print("\n" + "=" * 60)
    print("2. PROMPT COMPARISON PIPELINE")
    print("=" * 60)

    # Import comparison pipeline
    from pipelines import prompt_comparison_pipeline

    # Run comparison pipeline
    pipeline_run = prompt_comparison_pipeline(
        base_template="Answer the question: {question}",
        variant_template_1="You are an expert. Please answer: {question}",
        variant_template_2="Think step-by-step and answer: {question}",
        model="gpt-4.1-mini",
        dataset_name="default",
    )

    # Get results
    pipeline_run.steps["create_prompt_step"].outputs["created_prompt"][
        0
    ].load()
    pipeline_run.steps["create_prompt_step_2"].outputs["created_prompt"][
        0
    ].load()
    pipeline_run.steps["create_prompt_step_3"].outputs["created_prompt"][
        0
    ].load()

    base_eval = (
        pipeline_run.steps["evaluate_prompt_step"]
        .outputs["evaluation_metrics"][0]
        .load()
    )
    variant_1_eval = (
        pipeline_run.steps["evaluate_prompt_step_2"]
        .outputs["evaluation_metrics"][0]
        .load()
    )
    variant_2_eval = (
        pipeline_run.steps["evaluate_prompt_step_3"]
        .outputs["evaluation_metrics"][0]
        .load()
    )

    print(f"✅ Comparison Pipeline Results:")
    print(f"   • Base Template: {base_eval['success_rate']:.1%} success rate")
    print(
        f"   • Expert Variant: {variant_1_eval['success_rate']:.1%} success rate"
    )
    print(
        f"   • Step-by-step Variant: {variant_2_eval['success_rate']:.1%} success rate"
    )

    # Find best performing
    comparison_results = [
        ("Base", base_eval["success_rate"]),
        ("Expert", variant_1_eval["success_rate"]),
        ("Step-by-step", variant_2_eval["success_rate"]),
    ]
    best = max(comparison_results, key=lambda x: x[1])
    print(f"   🏆 Best performing: {best[0]} template")

    print("\n" + "=" * 60)
    print("3. EXAMPLE OUTPUTS")
    print("=" * 60)

    # Show some example outputs from the basic pipeline
    print("Sample Q&A from Basic Pipeline:")
    for i, result in enumerate(results[:2]):  # Show first 2
        if result.get("success"):
            print(f"\n   Q: {result['inputs']['question']}")
            print(f"   A: {result['output'][:150]}...")

    print("\n" + "=" * 60)
    print("🎉 ALL EXAMPLES COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    print("\nNext steps:")
    print(
        "• Try: python run.py basic --template 'Your custom template: {question}'"
    )
    print("• Try: python run.py comparison --dataset qa_hard")
    print("• Check the ZenML dashboard for detailed pipeline tracking")


if __name__ == "__main__":
    main()
