"""Testing steps for the agent comparison pipeline."""

from typing import Dict, List, Tuple

import pandas as pd
from agents import (
    LangGraphCustomerServiceAgent,
    MultiSpecialistAgents,
    SingleAgentRAG,
)
from sklearn.base import BaseEstimator
from typing_extensions import Annotated

from zenml import step
from zenml.logger import get_logger
from zenml.types import HTMLString

logger = get_logger(__name__)


@step
def run_architecture_comparison(
    queries: pd.DataFrame,
    intent_classifier: BaseEstimator,
) -> Tuple[
    Annotated[
        Dict[str, Dict[str, List[float]]], "architecture_performance_metrics"
    ],
    Annotated[HTMLString, "langgraph_workflow_diagram"],
]:
    """Test three different agent architectures on the same data.

    Args:
        queries: DataFrame containing customer service queries to test
        intent_classifier: Trained intent classifier model

    Returns:
        Tuple containing performance metrics dict and LangGraph Mermaid diagram HTML
    """
    architectures = {
        "single_agent": SingleAgentRAG(),
        "multi_specialist": MultiSpecialistAgents(),
        "langgraph_workflow": LangGraphCustomerServiceAgent(),
    }

    results = {}

    for name, agent in architectures.items():
        logger.info(f"Testing {name} architecture...")

        # Store response metrics in separate lists for ZenML compatibility
        latencies = []
        confidences = []
        tokens_used = []
        response_texts = []

        for _, row in queries.iterrows():
            query = row["query_text"]
            response = agent.process_query(query)

            latencies.append(response.latency_ms)
            confidences.append(response.confidence)
            tokens_used.append(float(response.tokens_used))
            response_texts.append(response.text)

        results[name] = {
            "latencies": latencies,
            "confidences": confidences,
            "tokens_used": tokens_used,
        }

        logger.info(f"Completed {name} with {len(response_texts)} responses")

    # Generate predictions with the intent classifier for comparison
    sample_predictions = intent_classifier.predict(
        queries["query_text"].head(5).tolist()
    )
    logger.info(
        f"Intent classifier predictions for first 5 queries: {sample_predictions}"
    )

    # Generate LangGraph workflow diagram
    langgraph_agent = LangGraphCustomerServiceAgent()
    mermaid_diagram = HTMLString(langgraph_agent.get_mermaid_diagram())

    return results, mermaid_diagram
