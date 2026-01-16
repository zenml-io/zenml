"""Seed planning step to identify starting points for hierarchical traversal."""

import json
from typing import Dict, Any, List, Set, Annotated
from pathlib import Path

from pydantic import BaseModel
from pydantic_ai import Agent
from zenml import step, ArtifactConfig
from zenml.logger import get_logger

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from materializers import TraversalPlanMaterializer

from .intent_detection import SearchIntent

logger = get_logger(__name__)


class SeedDocument(BaseModel):
    """Information about a seed document for traversal."""

    document_id: str
    relevance_score: float
    title: str
    reasoning: str
    key_concepts: List[str]


class SeedPlan(BaseModel):
    """AI-generated plan for seed document selection."""

    selected_seeds: List[SeedDocument]
    reasoning: str
    search_strategy: str
    estimated_coverage: float


class TraversalPlan(BaseModel):
    """Complete plan for document traversal including agent allocation."""

    query: str
    seed_documents: List[SeedDocument]
    max_agents: int
    agent_allocations: List[Dict[str, Any]]
    total_estimated_documents: int
    search_strategy: str
    reasoning: str


def get_seed_planning_agent():
    """Get the AI agent for seed planning (lazy-loaded)."""
    return Agent(
        "openai:gpt-4",
        output_type=SeedPlan,
        system_prompt="""
        You are an expert at analyzing document collections and planning efficient traversal strategies.

        Your task is to identify the best starting documents (seeds) for a hierarchical search query.
        Consider:
        - Relevance to the query concepts
        - Potential for leading to related documents through relationships
        - Coverage of different aspects of the query
        - Avoiding redundant starting points

        Select 1-5 seed documents based on query complexity and available agents.
        Provide relevance scores (0.0-1.0) and reasoning for each selection.
        """,
    )


def load_document_graph(doc_graph_path: str) -> Dict[str, Any]:
    """Load the document graph from JSON file."""
    try:
        with open(doc_graph_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # Fallback to relative path for testing
        current_dir = Path(__file__).parent.parent
        fallback_path = current_dir / "data" / "doc_graph.json"
        with open(fallback_path, 'r') as f:
            return json.load(f)


def calculate_document_relevance(query: str, document: Dict[str, Any], key_concepts: List[str]) -> float:
    """Calculate relevance score between query and document."""
    query_lower = query.lower()
    doc_content = (document.get('title', '') + ' ' + document.get('content', '')).lower()
    doc_tags = [tag.lower() for tag in document.get('metadata', {}).get('tags', [])]

    # Keyword matching
    keyword_matches = sum(1 for concept in key_concepts if concept.lower() in doc_content)
    tag_matches = sum(1 for concept in key_concepts if any(concept.lower() in tag for tag in doc_tags))

    # Calculate base relevance
    total_concepts = len(key_concepts) if key_concepts else 1
    keyword_score = keyword_matches / total_concepts
    tag_score = tag_matches / len(doc_tags) if doc_tags else 0

    # Combine scores with weights
    relevance_score = (keyword_score * 0.7) + (tag_score * 0.3)

    # Boost for exact matches in title
    if any(concept.lower() in document.get('title', '').lower() for concept in key_concepts):
        relevance_score *= 1.2

    return min(relevance_score, 1.0)


def select_diverse_seeds(candidates: List[SeedDocument], max_agents: int) -> List[SeedDocument]:
    """Select diverse seed documents to maximize coverage."""
    if len(candidates) <= max_agents:
        return candidates

    # Sort by relevance first
    candidates_sorted = sorted(candidates, key=lambda x: x.relevance_score, reverse=True)

    # Select diverse seeds using greedy approach
    selected = [candidates_sorted[0]]  # Always include highest relevance
    used_concepts: Set[str] = set(candidates_sorted[0].key_concepts)

    for candidate in candidates_sorted[1:]:
        if len(selected) >= max_agents:
            break

        # Calculate concept overlap with already selected seeds
        candidate_concepts = set(candidate.key_concepts)
        overlap = len(candidate_concepts.intersection(used_concepts))
        novelty = len(candidate_concepts - used_concepts)

        # Select if it brings significant novelty or is highly relevant
        if novelty > overlap or candidate.relevance_score > 0.8:
            selected.append(candidate)
            used_concepts.update(candidate_concepts)

    return selected


@step
def plan_seed_nodes(
    search_intent: SearchIntent,
    max_agents: int,
    doc_graph_path: str = "data/doc_graph.json",
    relevance_threshold: float = 0.3,
) -> Annotated[TraversalPlan, ArtifactConfig(name="traversal_plan", materializer=TraversalPlanMaterializer)]:
    """Plan the seed documents for hierarchical traversal.

    Args:
        search_intent: Intent detection result with query and classification
        max_agents: Maximum number of agents/seeds to create
        doc_graph_path: Path to document graph JSON file
        relevance_threshold: Minimum relevance score for seed consideration

    Returns:
        TraversalPlan with seed documents and agent allocations
    """
    logger.info(f"Planning seed nodes for query: {search_intent.query}")
    logger.info(f"Max agents: {max_agents}, Search type: {search_intent.search_type}")

    # Load document graph
    doc_graph = load_document_graph(doc_graph_path)
    documents = doc_graph.get('documents', {})

    if not documents:
        logger.warning("No documents found in graph")
        return TraversalPlan(
            query=search_intent.query,
            seed_documents=[],
            max_agents=max_agents,
            agent_allocations=[],
            total_estimated_documents=0,
            search_strategy="no_documents",
            reasoning="No documents available in the graph"
        )

    # Calculate relevance scores for all documents
    seed_candidates = []
    for doc_id, doc_data in documents.items():
        relevance = calculate_document_relevance(
            search_intent.query, doc_data, search_intent.key_concepts
        )

        if relevance >= relevance_threshold:
            seed_doc = SeedDocument(
                document_id=doc_id,
                relevance_score=relevance,
                title=doc_data.get('title', doc_id),
                reasoning=f"Relevance: {relevance:.2f}, matches concepts: {search_intent.key_concepts}",
                key_concepts=search_intent.key_concepts
            )
            seed_candidates.append(seed_doc)

    # Sort by relevance
    seed_candidates.sort(key=lambda x: x.relevance_score, reverse=True)

    logger.info(f"Found {len(seed_candidates)} candidate seed documents")

    if not seed_candidates:
        logger.warning("No relevant seed documents found")
        return TraversalPlan(
            query=search_intent.query,
            seed_documents=[],
            max_agents=max_agents,
            agent_allocations=[],
            total_estimated_documents=0,
            search_strategy="no_seeds",
            reasoning="No documents met the relevance threshold"
        )

    # Use AI agent for intelligent seed selection
    try:
        candidates_info = []
        for candidate in seed_candidates[:max_agents * 2]:  # Provide more options to AI
            candidates_info.append({
                'id': candidate.document_id,
                'title': candidate.title,
                'relevance': candidate.relevance_score,
                'concepts': candidate.key_concepts
            })

        ai_prompt = f"""
        Query: "{search_intent.query}"
        Key concepts: {search_intent.key_concepts}
        Available agents: {max_agents}
        Search type: {search_intent.search_type}

        Candidate documents:
        {json.dumps(candidates_info, indent=2)}

        Select the best {min(max_agents, len(candidates_info))} seed documents that will:
        1. Cover different aspects of the query
        2. Maximize traversal potential through document relationships
        3. Minimize redundant exploration
        """

        ai_plan = get_seed_planning_agent().run_sync(ai_prompt)

        # Map AI selections back to our seed candidates
        selected_ids = {seed.document_id for seed in ai_plan.output.selected_seeds}
        ai_selected_seeds = [
            candidate for candidate in seed_candidates
            if candidate.document_id in selected_ids
        ]

        if ai_selected_seeds:
            final_seeds = ai_selected_seeds
            strategy = ai_plan.output.search_strategy
            reasoning = ai_plan.output.reasoning
        else:
            raise ValueError("AI selection didn't match any candidates")

    except Exception as e:
        logger.warning(f"AI seed selection failed, using fallback strategy: {e}")

        # Fallback to diverse selection
        final_seeds = select_diverse_seeds(seed_candidates, max_agents)
        strategy = "diverse_fallback"
        reasoning = "Used diversity-based selection due to AI agent failure"

    # Create agent allocations
    agent_allocations = []
    for i, seed in enumerate(final_seeds):
        allocation = {
            'agent_id': f"agent_{i}",
            'seed_document_id': seed.document_id,
            'priority_concepts': seed.key_concepts[:3],  # Top 3 concepts
            'estimated_documents': 3,  # Conservative estimate
        }
        agent_allocations.append(allocation)

    total_estimated = len(final_seeds) * 3  # Rough estimate

    traversal_plan = TraversalPlan(
        query=search_intent.query,
        seed_documents=final_seeds,
        max_agents=max_agents,
        agent_allocations=agent_allocations,
        total_estimated_documents=total_estimated,
        search_strategy=strategy,
        reasoning=reasoning
    )

    logger.info(f"Created traversal plan with {len(final_seeds)} seeds")
    logger.info(f"Selected seeds: {[seed.document_id for seed in final_seeds]}")

    return traversal_plan