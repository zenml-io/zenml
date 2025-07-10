"""Agent Architecture Comparison Pipeline.

This pipeline implements the README example for comparing different agent architectures
on customer service queries. It demonstrates how to use ZenML to evaluate and compare
different AI approaches in a reproducible way.
"""

from steps import (
    evaluate_and_decide,
    load_prompts,
    load_real_conversations,
    run_architecture_comparison,
    train_intent_classifier,
)

from zenml import pipeline


@pipeline(enable_cache=False)
def compare_agent_architectures() -> None:
    """Compare different agent architectures on customer service queries."""
    # Load test data
    queries = load_real_conversations()

    # Load prompts as individual ZenML artifacts (visualization handled by materializer)
    (
        single_agent_prompt,
        specialist_returns_prompt,
        specialist_billing_prompt,
        specialist_technical_prompt,
        specialist_general_prompt,
        langgraph_workflow_prompt,
    ) = load_prompts()

    # Train intent classifier on the loaded data
    intent_classifier = train_intent_classifier(queries)

    # Run all architectures on the same data (returns metrics and architectural diagrams)
    (
        results,
        single_agent_diagram,
        multi_specialist_diagram,
        langgraph_diagram,
    ) = run_architecture_comparison(
        queries,
        intent_classifier,
        single_agent_prompt,
        specialist_returns_prompt,
        specialist_billing_prompt,
        specialist_technical_prompt,
        specialist_general_prompt,
        langgraph_workflow_prompt,
    )

    # Evaluate and generate report (HTML format)
    _ = evaluate_and_decide(queries, results)
