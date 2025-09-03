"""Data loading steps for the agent comparison pipeline."""

import json
from pathlib import Path
from typing import Tuple

import pandas as pd
from materializers.prompt import Prompt
from materializers.prompt_materializer import PromptMaterializer
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


@step(output_materializers=PromptMaterializer)
def load_prompts() -> Tuple[
    Annotated[Prompt, "single_agent_prompt"],
    Annotated[Prompt, "specialist_returns_prompt"],
    Annotated[Prompt, "specialist_billing_prompt"],
    Annotated[Prompt, "specialist_technical_prompt"],
    Annotated[Prompt, "specialist_general_prompt"],
    Annotated[Prompt, "langgraph_workflow_prompt"],
]:
    """Load prompts from files as individual ZenML artifacts.

    Returns:
        Tuple of individual Prompt objects for different agent types
    """
    prompts_dir = Path(__file__).parent.parent / "prompts"

    # Load single agent RAG prompt
    single_agent_content = (prompts_dir / "single_agent_rag.txt").read_text()
    single_agent_prompt = Prompt(
        name="single_agent_rag",
        content=single_agent_content,
        version="1.0.0",
        description="Single agent RAG prompt for customer service queries",
        variables={
            "knowledge_context": "Formatted knowledge base context",
            "query": "Customer query text",
        },
        author="ZenML Agent Comparison Example",
        tags={"type": "rag", "domain": "customer_service"},
    )

    # Load specialist prompts
    specialist_prompts_data = json.loads(
        (prompts_dir / "specialist_prompts.json").read_text()
    )

    specialist_prompts = []
    for specialist_type, content in specialist_prompts_data.items():
        specialist_prompt = Prompt(
            name=f"specialist_{specialist_type}",
            content=content,
            version="1.0.0",
            description=f"Specialist prompt for {specialist_type} queries",
            variables={"query": "Customer query text"},
            author="ZenML Agent Comparison Example",
            tags={
                "type": "specialist",
                "domain": "customer_service",
                "specialist_type": specialist_type,
            },
        )
        specialist_prompts.append(specialist_prompt)

    # Load LangGraph workflow prompt
    langgraph_content = (prompts_dir / "langgraph_workflow.txt").read_text()
    langgraph_prompt = Prompt(
        name="langgraph_workflow",
        content=langgraph_content,
        version="1.0.0",
        description="LangGraph workflow prompt for structured customer service processing",
        variables={
            "query_type": "Classified query type",
            "knowledge_context": "Relevant knowledge context",
            "query": "Customer query text",
        },
        author="ZenML Agent Comparison Example",
        tags={
            "type": "workflow",
            "domain": "customer_service",
            "framework": "langgraph",
        },
    )

    logger.info(
        f"Loaded {1 + len(specialist_prompts) + 1} prompt templates as individual ZenML artifacts"
    )
    return (
        single_agent_prompt,
        specialist_prompts[0],  # returns
        specialist_prompts[1],  # billing
        specialist_prompts[2],  # technical
        specialist_prompts[3],  # general
        langgraph_prompt,
    )
