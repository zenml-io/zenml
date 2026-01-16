"""Aggregation step to consolidate findings from multiple traversal agents."""

from typing import List, Dict, Any, Set, Annotated
from collections import defaultdict

from pydantic import BaseModel
from pydantic_ai import Agent
from zenml import step, ArtifactConfig
from zenml.logger import get_logger

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from materializers import AggregatedFindingsMaterializer

from .traverse_node import TraversalTrace, DocumentEvidence

logger = get_logger(__name__)


class ConsolidatedEvidence(BaseModel):
    """Consolidated evidence from multiple sources."""

    document_id: str
    title: str
    combined_content: str
    max_relevance_score: float
    agent_count: int  # How many agents found this document
    key_insights: List[str]
    source_agents: List[str]


class AggregatedFindings(BaseModel):
    """Complete aggregated results from all agents."""

    query: str
    total_agents: int
    total_documents_visited: int
    unique_documents_found: int
    consolidated_evidence: List[ConsolidatedEvidence]
    coverage_analysis: Dict[str, Any]
    agent_summaries: List[Dict[str, Any]]
    search_effectiveness: float


def get_consolidation_agent():
    """Get the AI agent for evidence consolidation (lazy-loaded)."""
    return Agent(
        "openai:gpt-4",
        output_type=AggregatedFindings,
        system_prompt="""
        You are an expert at synthesizing research findings from multiple sources.

        Your task is to:
        1. Consolidate evidence from multiple exploration agents
        2. Remove redundant information while preserving unique insights
        3. Rank evidence by relevance and importance
        4. Assess overall search coverage and effectiveness
        5. Identify gaps or areas that might need more exploration

        Focus on creating a coherent, comprehensive view of the findings while
        maintaining traceability to the original sources.
        """,
    )


def deduplicate_evidence(all_evidence: List[DocumentEvidence]) -> Dict[str, List[DocumentEvidence]]:
    """Group evidence by document ID to identify duplicates."""
    evidence_by_doc: Dict[str, List[DocumentEvidence]] = defaultdict(list)

    for evidence in all_evidence:
        evidence_by_doc[evidence.document_id].append(evidence)

    return evidence_by_doc


def consolidate_document_evidence(evidence_list: List[DocumentEvidence]) -> ConsolidatedEvidence:
    """Consolidate multiple evidence pieces for the same document."""
    if not evidence_list:
        raise ValueError("Cannot consolidate empty evidence list")

    first_evidence = evidence_list[0]

    # Combine insights from all agents
    all_insights = []
    for evidence in evidence_list:
        all_insights.extend(evidence.key_insights)

    # Remove duplicate insights (case-insensitive)
    unique_insights = []
    seen_insights = set()
    for insight in all_insights:
        insight_lower = insight.lower().strip()
        if insight_lower not in seen_insights:
            unique_insights.append(insight)
            seen_insights.add(insight_lower)

    # Combine content (take the most comprehensive one)
    combined_content = max(evidence_list, key=lambda x: len(x.relevant_content)).relevant_content

    # Get maximum relevance score and agent info
    max_relevance = max(evidence.relevance_score for evidence in evidence_list)
    source_agents = [f"agent_{i}" for i, _ in enumerate(evidence_list)]

    consolidated = ConsolidatedEvidence(
        document_id=first_evidence.document_id,
        title=first_evidence.title,
        combined_content=combined_content,
        max_relevance_score=max_relevance,
        agent_count=len(evidence_list),
        key_insights=unique_insights,
        source_agents=source_agents
    )

    return consolidated


def analyze_coverage(traces: List[TraversalTrace]) -> Dict[str, Any]:
    """Analyze search coverage and effectiveness."""
    total_docs_visited = sum(len(trace.visited_documents) for trace in traces)
    unique_docs_visited = len(set(doc for trace in traces for doc in trace.visited_documents))

    # Calculate overlap between agents
    agent_docs = [set(trace.visited_documents) for trace in traces]
    total_possible_pairs = len(traces) * (len(traces) - 1) // 2

    if total_possible_pairs > 0:
        overlap_count = 0
        for i in range(len(agent_docs)):
            for j in range(i + 1, len(agent_docs)):
                if agent_docs[i].intersection(agent_docs[j]):
                    overlap_count += 1
        overlap_percentage = (overlap_count / total_possible_pairs) * 100
    else:
        overlap_percentage = 0

    # Agent completion status analysis
    completion_status_counts = defaultdict(int)
    for trace in traces:
        completion_status_counts[trace.completion_status] += 1

    # Budget utilization
    total_budget_used = sum(trace.total_steps for trace in traces)
    avg_budget_used = total_budget_used / len(traces) if traces else 0

    coverage = {
        'total_documents_visited': total_docs_visited,
        'unique_documents_visited': unique_docs_visited,
        'agent_overlap_percentage': overlap_percentage,
        'average_budget_utilization': avg_budget_used,
        'completion_status_distribution': dict(completion_status_counts),
        'efficiency_score': unique_docs_visited / max(total_docs_visited, 1)  # Avoid division by zero
    }

    return coverage


def create_agent_summary(trace: TraversalTrace) -> Dict[str, Any]:
    """Create summary for individual agent performance."""
    avg_relevance = 0
    if trace.evidence_collected:
        avg_relevance = sum(e.relevance_score for e in trace.evidence_collected) / len(trace.evidence_collected)

    summary = {
        'agent_id': trace.agent_id,
        'seed_document': trace.seed_document,
        'documents_visited': len(trace.visited_documents),
        'evidence_pieces': len(trace.evidence_collected),
        'average_relevance': avg_relevance,
        'completion_status': trace.completion_status,
        'budget_remaining': trace.budget_remaining,
        'traversal_depth': len(trace.traversal_path),
        'visited_documents': trace.visited_documents
    }

    return summary


@step
def aggregate_findings(
    traversal_traces: Annotated[List[TraversalTrace], "traversal_results"],
    query: str,
    min_relevance_threshold: float = 0.4,
) -> Annotated[AggregatedFindings, ArtifactConfig(name="aggregated_findings", materializer=AggregatedFindingsMaterializer)]:
    """Aggregate and consolidate findings from multiple traversal agents.

    Args:
        traversal_traces: Results from all traversal agents
        query: Original search query
        min_relevance_threshold: Minimum relevance score for inclusion

    Returns:
        AggregatedFindings with consolidated evidence and analysis
    """
    logger.info(f"Aggregating findings from {len(traversal_traces)} agents")

    if not traversal_traces:
        logger.warning("No traversal traces to aggregate")
        return AggregatedFindings(
            query=query,
            total_agents=0,
            total_documents_visited=0,
            unique_documents_found=0,
            consolidated_evidence=[],
            coverage_analysis={},
            agent_summaries=[],
            search_effectiveness=0.0
        )

    # Collect all evidence from all agents
    all_evidence = []
    for trace in traversal_traces:
        all_evidence.extend(trace.evidence_collected)

    logger.info(f"Total evidence pieces collected: {len(all_evidence)}")

    # Filter by relevance threshold
    relevant_evidence = [
        evidence for evidence in all_evidence
        if evidence.relevance_score >= min_relevance_threshold
    ]

    logger.info(f"Evidence pieces above threshold ({min_relevance_threshold}): {len(relevant_evidence)}")

    # Deduplicate evidence by document
    evidence_by_doc = deduplicate_evidence(relevant_evidence)

    # Consolidate evidence for each document
    consolidated_evidence = []
    for doc_id, evidence_list in evidence_by_doc.items():
        try:
            consolidated = consolidate_document_evidence(evidence_list)
            consolidated_evidence.append(consolidated)
        except Exception as e:
            logger.error(f"Error consolidating evidence for document {doc_id}: {e}")

    # Sort consolidated evidence by relevance and agent count
    consolidated_evidence.sort(
        key=lambda x: (x.max_relevance_score, x.agent_count),
        reverse=True
    )

    logger.info(f"Consolidated into {len(consolidated_evidence)} unique documents")

    # Analyze coverage and effectiveness
    coverage_analysis = analyze_coverage(traversal_traces)

    # Create agent summaries
    agent_summaries = [create_agent_summary(trace) for trace in traversal_traces]

    # Calculate overall search effectiveness
    total_evidence_quality = sum(evidence.max_relevance_score for evidence in consolidated_evidence)
    search_effectiveness = total_evidence_quality / max(len(consolidated_evidence), 1)

    # Try to use AI for enhanced consolidation if possible
    try:
        # Prepare data for AI analysis
        evidence_summaries = []
        for evidence in consolidated_evidence[:10]:  # Limit for AI context
            evidence_summaries.append({
                'document': evidence.document_id,
                'title': evidence.title,
                'relevance': evidence.max_relevance_score,
                'agent_count': evidence.agent_count,
                'key_insights': evidence.key_insights[:3],  # Top 3 insights
                'content_preview': evidence.combined_content[:200]
            })

        ai_prompt = f"""
        Query: "{query}"

        Consolidated evidence from {len(traversal_traces)} exploration agents:
        {evidence_summaries}

        Coverage analysis:
        - Total documents visited: {coverage_analysis['total_documents_visited']}
        - Unique documents: {coverage_analysis['unique_documents_visited']}
        - Agent overlap: {coverage_analysis['agent_overlap_percentage']:.1f}%
        - Efficiency score: {coverage_analysis['efficiency_score']:.2f}

        Analyze the search effectiveness and provide insights about coverage quality.
        """

        # Note: AI analysis would enhance the results but isn't critical for basic functionality
        # We'll keep the manually computed results as they're already comprehensive

    except Exception as e:
        logger.warning(f"AI-enhanced analysis failed: {e}")

    aggregated_findings = AggregatedFindings(
        query=query,
        total_agents=len(traversal_traces),
        total_documents_visited=coverage_analysis['total_documents_visited'],
        unique_documents_found=coverage_analysis['unique_documents_visited'],
        consolidated_evidence=consolidated_evidence,
        coverage_analysis=coverage_analysis,
        agent_summaries=agent_summaries,
        search_effectiveness=search_effectiveness
    )

    logger.info(f"Aggregation complete: {len(consolidated_evidence)} consolidated evidence pieces")
    logger.info(f"Search effectiveness score: {search_effectiveness:.2f}")

    return aggregated_findings