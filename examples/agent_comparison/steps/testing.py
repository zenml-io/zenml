"""Testing steps for the agent comparison pipeline."""

from typing import Any, Dict, List, Tuple

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
    single_agent_prompt: Any,
    specialist_returns_prompt: Any,
    specialist_billing_prompt: Any,
    specialist_technical_prompt: Any,
    specialist_general_prompt: Any,
    langgraph_workflow_prompt: Any,
) -> Tuple[
    Annotated[
        Dict[str, Dict[str, List[float]]], "architecture_performance_metrics"
    ],
    Annotated[HTMLString, "single_agent_diagram"],
    Annotated[HTMLString, "multi_specialist_diagram"],
    Annotated[HTMLString, "langgraph_workflow_diagram"],
]:
    """Test three different agent architectures on the same data.

    Args:
        queries: DataFrame containing customer service queries to test
        intent_classifier: Trained intent classifier model
        single_agent_prompt: Single agent RAG prompt
        specialist_returns_prompt: Specialist prompt for returns
        specialist_billing_prompt: Specialist prompt for billing
        specialist_technical_prompt: Specialist prompt for technical
        specialist_general_prompt: Specialist prompt for general
        langgraph_workflow_prompt: LangGraph workflow prompt

    Returns:
        Tuple containing performance metrics dict and HTML diagrams for all three architectures
    """
    # Reconstruct the prompts list for the agents
    prompts = [
        single_agent_prompt,
        specialist_returns_prompt,
        specialist_billing_prompt,
        specialist_technical_prompt,
        specialist_general_prompt,
        langgraph_workflow_prompt,
    ]

    architectures = {
        "single_agent": SingleAgentRAG(prompts),
        "multi_specialist": MultiSpecialistAgents(prompts),
        "langgraph_workflow": LangGraphCustomerServiceAgent(prompts),
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

    # Generate architectural diagrams for all three approaches
    single_agent = SingleAgentRAG(prompts)
    multi_specialist = MultiSpecialistAgents(prompts)
    langgraph_agent = LangGraphCustomerServiceAgent(prompts)

    single_agent_diagram = HTMLString(single_agent.get_mermaid_diagram())
    multi_specialist_diagram = HTMLString(
        multi_specialist.get_mermaid_diagram()
    )
    langgraph_diagram = HTMLString(langgraph_agent.get_mermaid_diagram())

    return (
        results,
        single_agent_diagram,
        multi_specialist_diagram,
        langgraph_diagram,
    )
