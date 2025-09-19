"""Pipeline for evaluating agent performance across different modes."""

import os
from typing import Any

from steps.evaluate import evaluate_agent_performance, generate_test_dataset

from zenml import pipeline
from zenml.config import DockerSettings


@pipeline(
    enable_cache=False,
    settings={
        "docker": DockerSettings(
            requirements="requirements.txt",
            parent_image="zenmldocker/zenml:0.85.0-py3.12",
            environment={
                "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
            },
        )
    }
)
def agent_evaluation_pipeline() -> Any:
    """Compare LLM-only vs Hybrid agent performance."""
    # Generate test dataset
    test_texts, test_labels = generate_test_dataset()

    # Run comprehensive evaluation
    evaluation_results, confusion_matrices_html = evaluate_agent_performance(test_texts, test_labels)

    return evaluation_results, confusion_matrices_html