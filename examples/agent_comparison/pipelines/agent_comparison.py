"""Agent Architecture Comparison Pipeline.

This pipeline implements the README example for comparing different agent architectures
on customer service queries. It demonstrates how to use ZenML to evaluate and compare
different AI approaches in a reproducible way.
"""

from steps import (
    evaluate_and_decide,
    load_real_conversations,
    run_architecture_comparison,
    train_intent_classifier,
)

from zenml import pipeline


@pipeline
def compare_agent_architectures() -> None:
    """Compare different agent architectures on customer service queries."""
    # Load test data
    queries = load_real_conversations()

    # Train intent classifier on the loaded data
    intent_classifier = train_intent_classifier(queries)

    # Run all architectures on the same data (returns both metrics and mermaid diagram)
    results, _ = run_architecture_comparison(queries, intent_classifier)

    # Evaluate and generate report (HTML format)
    _ = evaluate_and_decide(queries, results)
