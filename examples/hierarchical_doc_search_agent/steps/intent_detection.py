"""Intent detection step using Pydantic AI to classify queries."""

import json
from typing import Dict, Any, List, Annotated

from pydantic import BaseModel
from pydantic_ai import Agent
from zenml import step, ArtifactConfig
from zenml.logger import get_logger

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from materializers import SearchIntentMaterializer

logger = get_logger(__name__)


class IntentAnalysis(BaseModel):
    """Analysis result from intent detection."""

    search_type: str  # "simple" or "deep"
    confidence: float  # 0.0 to 1.0
    reasoning: str
    key_concepts: List[str]
    complexity_indicators: List[str]


class SearchIntent(BaseModel):
    """Intent detection response."""

    query: str
    search_type: str
    confidence: float
    reasoning: str
    key_concepts: List[str]
    requires_traversal: bool


def get_intent_agent():
    """Get the AI agent for intent detection (lazy-loaded)."""
    return Agent(
        "openai:gpt-4",  # Will use LiteLLM routing
        output_type=IntentAnalysis,
        system_prompt="""
        You are an expert at analyzing search queries to determine the appropriate search strategy.

        Classify queries as either:
        - "simple": Direct lookup queries that can be answered with a single document
        - "deep": Complex queries requiring exploration of multiple related documents

        Simple queries typically:
        - Ask for definitions or basic explanations
        - Use phrases like "what is", "define", "introduction to"
        - Focus on a single, specific topic

        Deep queries typically:
        - Ask about relationships between concepts
        - Request comprehensive overviews spanning multiple topics
        - Use phrases like "how do X relate to Y", "latest developments", "comprehensive overview"
        - Require synthesis of information from multiple sources

        Analyze the query carefully and provide your classification with confidence and reasoning.
        """,
    )


@step
def detect_intent(
    query: str,
    simple_indicators: List[str] = None,
    complex_indicators: List[str] = None,
    complexity_threshold: float = 0.6,
) -> Annotated[SearchIntent, ArtifactConfig(name="search_intent", materializer=SearchIntentMaterializer)]:
    """Detect the intent of a search query to determine search strategy.

    Args:
        query: The user's search query
        simple_indicators: Keywords that suggest simple queries
        complex_indicators: Keywords that suggest complex queries
        complexity_threshold: Threshold for classifying as complex

    Returns:
        SearchIntent with classification and reasoning
    """
    logger.info(f"Analyzing query intent: {query}")

    # Default indicators if not provided
    if simple_indicators is None:
        simple_indicators = [
            "what is", "define", "introduction to", "basics of",
            "overview of", "explain", "meaning of"
        ]

    if complex_indicators is None:
        complex_indicators = [
            "relationship between", "how do", "compare", "comprehensive",
            "latest developments", "applications", "connect", "relate",
            "evolution of", "impact of"
        ]

    # First, do a simple keyword-based check
    query_lower = query.lower()
    simple_matches = sum(1 for indicator in simple_indicators if indicator in query_lower)
    complex_matches = sum(1 for indicator in complex_indicators if indicator in query_lower)

    # Use AI agent for more sophisticated analysis
    try:
        analysis_prompt = f"""
        Analyze this search query: "{query}"

        Consider:
        - Keyword indicators for simple queries: {simple_indicators}
        - Keyword indicators for complex queries: {complex_indicators}
        - Overall complexity and scope of the question
        - Whether it requires connecting multiple domains/concepts

        Simple keyword matches found: {simple_matches}
        Complex keyword matches found: {complex_matches}
        """

        analysis = get_intent_agent().run_sync(analysis_prompt)

        # Create the final intent result
        search_intent = SearchIntent(
            query=query,
            search_type=analysis.output.search_type,
            confidence=analysis.output.confidence,
            reasoning=analysis.output.reasoning,
            key_concepts=analysis.output.key_concepts,
            requires_traversal=analysis.output.search_type == "deep"
        )

    except Exception as e:
        logger.warning(f"AI analysis failed, falling back to keyword-based classification: {e}")

        # Fallback to simple keyword-based classification
        if simple_matches > complex_matches and simple_matches > 0:
            search_type = "simple"
            confidence = 0.7
        elif complex_matches > 0 or len(query.split()) > 8:
            search_type = "deep"
            confidence = 0.6
        else:
            search_type = "simple"
            confidence = 0.5

        search_intent = SearchIntent(
            query=query,
            search_type=search_type,
            confidence=confidence,
            reasoning=f"Keyword-based classification: {simple_matches} simple, {complex_matches} complex indicators",
            key_concepts=query.split(),
            requires_traversal=search_type == "deep"
        )

    logger.info(f"Intent detection result: {search_intent.search_type} (confidence: {search_intent.confidence:.2f})")
    logger.info(f"Reasoning: {search_intent.reasoning}")

    return search_intent