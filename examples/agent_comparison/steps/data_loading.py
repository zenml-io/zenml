"""Data loading steps for the agent comparison pipeline."""

import pandas as pd
from typing_extensions import Annotated

from zenml import step
from zenml.logger import get_logger

logger = get_logger(__name__)


@step
def load_real_conversations() -> Annotated[
    pd.DataFrame, "customer_service_queries"
]:
    """Load sample customer service queries for testing.

    Returns:
        DataFrame with sample customer service queries and metadata
    """
    # Sample customer service queries with different complexity levels
    queries = [
        "How do I return an item I bought last week?",
        "What's your refund policy?",
        "I was charged twice for my order #12345, can you help?",
        "My product isn't working after following the setup instructions",
        "I need to return this item but I lost my receipt, is that possible?",
        "Can you explain your shipping options and costs?",
        "I have a warranty claim for a product that broke after 6 months",
        "I want to cancel my subscription and get a refund",
        "The product I received is damaged and I need a replacement urgently",
        "I'm having trouble with setup and also need to know about returns policy",
        "Is there a way to expedite shipping for my order?",
        "I have multiple issues: billing error, return request, and technical support needed",
        "What are your customer service hours?",
        "Can I exchange this item for a different size?",
        "I need help with both installation and warranty information",
    ]

    df = pd.DataFrame(
        {
            "query_id": range(len(queries)),
            "query_text": queries,
            "query_type": ["support"] * len(queries),
            "complexity": [len(q.split()) for q in queries],
        }
    )

    logger.info(f"Loaded {len(df)} customer service queries for testing")
    return df
