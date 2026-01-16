"""Node traversal step for hierarchical document exploration."""

import json
from typing import Dict, Any, List, Set, Optional, Annotated
from pathlib import Path

from pydantic import BaseModel
from pydantic_ai import Agent
from zenml import step, ArtifactConfig
from zenml.logger import get_logger

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from materializers import TraversalTraceMaterializer

from .plan_seed_nodes import SeedDocument

logger = get_logger(__name__)


class TraversalDecision(BaseModel):
    """AI decision for next traversal step."""

    should_continue: bool
    next_documents: List[str]
    reasoning: str
    confidence: float
    evidence_quality: float  # How good is the evidence found so far


class DocumentEvidence(BaseModel):
    """Evidence collected from a document."""

    document_id: str
    title: str
    relevant_content: str
    relevance_score: float
    key_insights: List[str]
    relationships_followed: List[str]


class TraversalTrace(BaseModel):
    """Complete trace of an agent's traversal."""

    agent_id: str
    query: str
    seed_document: str
    visited_documents: List[str]
    evidence_collected: List[DocumentEvidence]
    traversal_path: List[Dict[str, Any]]
    total_steps: int
    budget_remaining: int
    final_reasoning: str
    completion_status: str  # "budget_exhausted", "answer_found", "no_more_paths"


def get_traversal_agent():
    """Get the AI agent for traversal decisions (lazy-loaded)."""
    return Agent(
        "openai:gpt-4",
        output_type=TraversalDecision,
        system_prompt="""
        You are an expert document explorer conducting hierarchical search.

        Your goal is to find relevant information by following document relationships.

        For each document you visit:
        1. Extract relevant information related to the query
        2. Decide if you've found sufficient evidence or should continue
        3. If continuing, choose which related documents to explore next
        4. Consider your remaining budget (number of documents you can still visit)

        Evaluation criteria:
        - Quality and completeness of evidence found
        - Likelihood that related documents will provide additional value
        - Remaining budget constraints
        - Risk of getting stuck in irrelevant paths

        Be strategic: stop early if you have strong evidence, continue if you need more context.
        """,
    )


def get_content_analysis_agent():
    """Get the AI agent for content analysis (lazy-loaded)."""
    return Agent(
        "openai:gpt-4",
        output_type=DocumentEvidence,
        system_prompt="""
        You are an expert at analyzing documents and extracting relevant information.

        Your task is to:
        1. Read the document content carefully
        2. Extract information relevant to the search query
        3. Identify key insights and important points
        4. Score the relevance (0.0-1.0) of this document to the query
        5. Summarize the most important relevant content

        Focus on content that directly answers or contributes to answering the search query.
        Be concise but comprehensive in your extraction.
        """,
    )


def load_document_graph(doc_graph_path: str) -> Dict[str, Any]:
    """Load the document graph from JSON file."""
    try:
        with open(doc_graph_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # Fallback to relative path
        current_dir = Path(__file__).parent.parent
        fallback_path = current_dir / "data" / "doc_graph.json"
        with open(fallback_path, 'r') as f:
            return json.load(f)


def get_related_documents(
    document_id: str,
    documents: Dict[str, Any],
    relationship_types: List[str] = None
) -> List[str]:
    """Get related documents following specified relationship types."""
    if relationship_types is None:
        relationship_types = ["leads_to", "references", "related", "prerequisite"]

    document = documents.get(document_id, {})
    relationships = document.get('relationships', {})

    related_docs = []
    for rel_type in relationship_types:
        if rel_type in relationships:
            related_docs.extend(relationships[rel_type])

    return list(set(related_docs))  # Remove duplicates


@step
def traverse_node(
    seed_document: SeedDocument,
    agent_id: str,
    query: str,
    max_depth: int,
    agent_budget: int,
    doc_graph_path: str = "data/doc_graph.json",
    relationship_types: List[str] = None,
) -> Annotated[TraversalTrace, ArtifactConfig(name="traversal_trace", materializer=TraversalTraceMaterializer)]:
    """Perform hierarchical traversal starting from a seed document.

    Args:
        seed_document: Starting document for traversal
        agent_id: Unique identifier for this agent
        query: Original search query
        max_depth: Maximum traversal depth
        agent_budget: Maximum number of documents to visit
        doc_graph_path: Path to document graph JSON file
        relationship_types: Types of relationships to follow

    Returns:
        TraversalTrace with complete exploration record
    """
    logger.info(f"Agent {agent_id} starting traversal from {seed_document.document_id}")
    logger.info(f"Budget: {agent_budget}, Max depth: {max_depth}")

    # Load document graph
    doc_graph = load_document_graph(doc_graph_path)
    documents = doc_graph.get('documents', {})

    if relationship_types is None:
        relationship_types = ["leads_to", "references", "related", "prerequisite"]

    # Initialize traversal state
    visited_documents: Set[str] = set()
    evidence_collected: List[DocumentEvidence] = []
    traversal_path: List[Dict[str, Any]] = []
    budget_remaining = agent_budget
    current_depth = 0

    # Start with seed document
    to_visit = [seed_document.document_id]
    completion_status = "in_progress"

    try:
        while to_visit and budget_remaining > 0 and current_depth < max_depth:
            current_doc_id = to_visit.pop(0)

            if current_doc_id in visited_documents:
                continue

            if current_doc_id not in documents:
                logger.warning(f"Document {current_doc_id} not found in graph")
                continue

            # Visit current document
            visited_documents.add(current_doc_id)
            budget_remaining -= 1
            current_doc = documents[current_doc_id]

            logger.info(f"Agent {agent_id} visiting {current_doc_id} (depth {current_depth}, budget {budget_remaining})")

            # Analyze document content
            try:
                content_prompt = f"""
                Query: "{query}"

                Document to analyze:
                Title: {current_doc.get('title', 'Untitled')}
                Content: {current_doc.get('content', 'No content')}
                Type: {current_doc.get('type', 'unknown')}
                Tags: {current_doc.get('metadata', {}).get('tags', [])}

                Extract relevant information and score relevance to the query.
                """

                evidence_result = get_content_analysis_agent().run_sync(content_prompt)
                evidence = evidence_result.output

                # Get related documents for potential next steps
                related_docs = get_related_documents(current_doc_id, documents, relationship_types)
                unvisited_related = [doc for doc in related_docs if doc not in visited_documents]

                # Record traversal step
                step_info = {
                    'document_id': current_doc_id,
                    'depth': current_depth,
                    'budget_used': agent_budget - budget_remaining,
                    'evidence_quality': evidence.relevance_score,
                    'related_documents_found': len(unvisited_related),
                    'related_documents': unvisited_related
                }
                traversal_path.append(step_info)

                # Add evidence if relevant
                if evidence.relevance_score > 0.3:  # Relevance threshold
                    evidence_collected.append(evidence)

                # Decide whether to continue traversal
                if budget_remaining > 0 and current_depth < max_depth - 1 and unvisited_related:
                    decision_prompt = f"""
                    Query: "{query}"
                    Current document: {current_doc_id} ({current_doc.get('title', 'Untitled')})

                    Evidence quality so far: {sum(e.relevance_score for e in evidence_collected) / max(len(evidence_collected), 1):.2f}
                    Evidence collected: {len(evidence_collected)} documents

                    Current evidence summary: {evidence.relevant_content[:500]}...

                    Related documents available: {unvisited_related}
                    Budget remaining: {budget_remaining}
                    Depth remaining: {max_depth - current_depth - 1}

                    Should we continue exploring? Which documents should we visit next?
                    """

                    decision_result = get_traversal_agent().run_sync(decision_prompt)
                    decision = decision_result.output

                    if decision.should_continue and decision.next_documents:
                        # Filter and add valid next documents
                        valid_next = [doc for doc in decision.next_documents if doc in unvisited_related]
                        to_visit.extend(valid_next[:min(3, budget_remaining)])  # Limit to prevent explosion

                        logger.info(f"Agent {agent_id} decision: continue with {valid_next}")
                    else:
                        completion_status = "answer_found"
                        logger.info(f"Agent {agent_id} decision: stop exploration - {decision.reasoning}")
                        break

                else:
                    # No more budget/depth or no related documents
                    if budget_remaining == 0:
                        completion_status = "budget_exhausted"
                    elif current_depth >= max_depth - 1:
                        completion_status = "depth_limit_reached"
                    else:
                        completion_status = "no_more_paths"
                    break

            except Exception as e:
                logger.error(f"Error analyzing document {current_doc_id}: {e}")
                # Continue with next document despite error
                continue

            current_depth += 1

    except Exception as e:
        logger.error(f"Agent {agent_id} traversal failed: {e}")
        completion_status = "error"

    # Create final trace
    trace = TraversalTrace(
        agent_id=agent_id,
        query=query,
        seed_document=seed_document.document_id,
        visited_documents=list(visited_documents),
        evidence_collected=evidence_collected,
        traversal_path=traversal_path,
        total_steps=len(traversal_path),
        budget_remaining=budget_remaining,
        final_reasoning=f"Completed with status: {completion_status}",
        completion_status=completion_status
    )

    logger.info(f"Agent {agent_id} completed: {len(visited_documents)} docs visited, "
                f"{len(evidence_collected)} evidence pieces, status: {completion_status}")

    return trace