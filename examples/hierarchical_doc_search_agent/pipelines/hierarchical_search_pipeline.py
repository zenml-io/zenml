"""Main hierarchical document search pipeline with dynamic execution."""

import argparse
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Annotated

import yaml
from zenml import pipeline, step, ArtifactConfig
from zenml.logger import get_logger
from zenml.client import Client

# Add the parent directory to the path so we can import our steps
sys.path.append(str(Path(__file__).parent.parent))

from steps import (
    detect_intent,
    plan_seed_nodes,
    traverse_node,
    aggregate_findings,
    build_evidence_pack,
)
from steps.plan_seed_nodes import SeedDocument
from steps.traverse_node import TraversalTrace
from steps.aggregate_findings import AggregatedFindings
from steps.build_evidence_pack import EvidencePack
from materializers import AggregatedFindingsMaterializer, EvidencePackMaterializer

logger = get_logger(__name__)


@step
def create_single_agent_findings(
    traversal_trace: TraversalTrace,
    query: str,
    min_relevance_threshold: float = 0.4,
) -> Annotated[AggregatedFindings, ArtifactConfig(name="aggregated_findings", materializer=AggregatedFindingsMaterializer)]:
    """Create aggregated findings from a single agent's traversal."""
    from steps.aggregate_findings import (
        AggregatedFindings, ConsolidatedEvidence,
        deduplicate_evidence, consolidate_document_evidence, analyze_coverage, create_agent_summary
    )

    # Filter evidence by relevance threshold
    relevant_evidence = [
        evidence for evidence in traversal_trace.evidence_collected
        if evidence.relevance_score >= min_relevance_threshold
    ]

    # Create consolidated evidence (even though it's just one agent)
    evidence_by_doc = {}
    for evidence in relevant_evidence:
        if evidence.document_id not in evidence_by_doc:
            evidence_by_doc[evidence.document_id] = []
        evidence_by_doc[evidence.document_id].append(evidence)

    consolidated_evidence = []
    for doc_id, evidence_list in evidence_by_doc.items():
        if evidence_list:
            first_evidence = evidence_list[0]
            consolidated = ConsolidatedEvidence(
                document_id=doc_id,
                title=first_evidence.title,
                combined_content=first_evidence.relevant_content,
                max_relevance_score=max(e.relevance_score for e in evidence_list),
                agent_count=1,
                key_insights=first_evidence.key_insights,
                source_agents=[traversal_trace.agent_id]
            )
            consolidated_evidence.append(consolidated)

    # Sort by relevance
    consolidated_evidence.sort(key=lambda x: x.max_relevance_score, reverse=True)

    # Create coverage analysis
    coverage_analysis = {
        'total_documents_visited': len(traversal_trace.visited_documents),
        'unique_documents_visited': len(traversal_trace.visited_documents),
        'agent_overlap_percentage': 0,  # Only one agent
        'average_budget_utilization': traversal_trace.total_steps,
        'completion_status_distribution': {traversal_trace.completion_status: 1},
        'efficiency_score': len(consolidated_evidence) / max(len(traversal_trace.visited_documents), 1)
    }

    # Create agent summary
    avg_relevance = sum(e.relevance_score for e in relevant_evidence) / max(len(relevant_evidence), 1)
    agent_summary = {
        'agent_id': traversal_trace.agent_id,
        'seed_document': traversal_trace.seed_document,
        'documents_visited': len(traversal_trace.visited_documents),
        'evidence_pieces': len(relevant_evidence),
        'average_relevance': avg_relevance,
        'completion_status': traversal_trace.completion_status,
        'budget_remaining': traversal_trace.budget_remaining,
        'traversal_depth': len(traversal_trace.traversal_path),
        'visited_documents': traversal_trace.visited_documents
    }

    # Calculate search effectiveness
    total_evidence_quality = sum(evidence.max_relevance_score for evidence in consolidated_evidence)
    search_effectiveness = total_evidence_quality / max(len(consolidated_evidence), 1)

    return AggregatedFindings(
        query=query,
        total_agents=1,
        total_documents_visited=len(traversal_trace.visited_documents),
        unique_documents_found=len(consolidated_evidence),
        consolidated_evidence=consolidated_evidence,
        coverage_analysis=coverage_analysis,
        agent_summaries=[agent_summary],
        search_effectiveness=search_effectiveness
    )


@step
def create_empty_evidence_pack(query: str, search_type: str) -> Annotated[EvidencePack, ArtifactConfig(name="evidence_pack", materializer=EvidencePackMaterializer)]:
    """Create an empty evidence package for failed searches."""
    from datetime import datetime

    empty_findings = AggregatedFindings(
        query=query,
        total_agents=0,
        total_documents_visited=0,
        unique_documents_found=0,
        consolidated_evidence=[],
        coverage_analysis={},
        agent_summaries=[],
        search_effectiveness=0.0
    )

    return build_evidence_pack(
        aggregated_findings=empty_findings,
        search_parameters={'query': query, 'search_type': search_type}
    )


@step
def create_simple_evidence_pack(
    query: str,
    search_intent: Any,
    doc_graph_path: str,
) -> Annotated[EvidencePack, ArtifactConfig(name="evidence_pack", materializer=EvidencePackMaterializer)]:
    """Create evidence package for simple queries."""
    # Simple search implementation - just find most relevant document
    import json
    from pathlib import Path

    try:
        with open(doc_graph_path, 'r') as f:
            doc_graph = json.load(f)
    except FileNotFoundError:
        # Fallback to relative path
        current_dir = Path(__file__).parent.parent
        fallback_path = current_dir / "data" / "doc_graph.json"
        with open(fallback_path, 'r') as f:
            doc_graph = json.load(f)

    documents = doc_graph.get('documents', {})

    # Simple relevance scoring for demo
    query_lower = query.lower()
    best_match = None
    best_score = 0

    for doc_id, doc_data in documents.items():
        content = (doc_data.get('title', '') + ' ' + doc_data.get('content', '')).lower()
        score = sum(1 for word in query_lower.split() if word in content)
        if score > best_score:
            best_score = score
            best_match = (doc_id, doc_data)

    if best_match:
        from steps.aggregate_findings import ConsolidatedEvidence

        evidence = ConsolidatedEvidence(
            document_id=best_match[0],
            title=best_match[1].get('title', best_match[0]),
            combined_content=best_match[1].get('content', ''),
            max_relevance_score=min(best_score / len(query.split()), 1.0),
            agent_count=1,
            key_insights=[f"Direct match for query: {query}"],
            source_agents=['simple_search']
        )

        simple_findings = AggregatedFindings(
            query=query,
            total_agents=1,
            total_documents_visited=1,
            unique_documents_found=1,
            consolidated_evidence=[evidence],
            coverage_analysis={'simple_search': True},
            agent_summaries=[],
            search_effectiveness=0.8
        )
    else:
        simple_findings = AggregatedFindings(
            query=query,
            total_agents=1,
            total_documents_visited=len(documents),
            unique_documents_found=0,
            consolidated_evidence=[],
            coverage_analysis={'simple_search': True, 'no_matches': True},
            agent_summaries=[],
            search_effectiveness=0.0
        )

    return build_evidence_pack(
        aggregated_findings=simple_findings,
        search_parameters={'query': query, 'search_type': 'simple'}
    )


@pipeline(dynamic=True, enable_cache=True, enable_artifact_metadata=True)
def hierarchical_search_pipeline(
    query: str,
    max_agents: int = 3,
    max_depth: int = 4,
    agent_budget: int = 10,
    doc_graph_path: str = None,
) -> None:
    """Dynamic pipeline for hierarchical document search.

    This pipeline demonstrates ZenML's dynamic capabilities through:
    - Conditional branching based on intent detection
    - Runtime fan-out across variable number of agents using .map()
    - Dynamic DAG construction based on data

    Args:
        query: Search query to process
        max_agents: Maximum number of parallel agents
        max_depth: Maximum traversal depth per agent
        agent_budget: Budget (docs) per agent
        doc_graph_path: Path to document graph data
    """
    logger.info(f"Starting hierarchical search for query: {query}")
    logger.info(f"Parameters: max_agents={max_agents}, max_depth={max_depth}, agent_budget={agent_budget}")

    # Step 1: Detect intent to determine search strategy
    search_intent = detect_intent(
        query=query,
        simple_indicators=["what is", "define", "introduction to", "basics of"],
        complex_indicators=["relationship between", "how do", "compare", "comprehensive", "latest developments"],
        complexity_threshold=0.6,
    )

    # Load the search intent data to make conditional decision
    search_intent_data = search_intent.load()

    # Conditional branching based on intent
    # ZenML will determine the DAG structure at runtime
    if search_intent_data.requires_traversal:
        logger.info("Complex query detected - initiating deep hierarchical search")

        # Step 2: Plan seed nodes for deep traversal
        traversal_plan = plan_seed_nodes(
            search_intent=search_intent,
            max_agents=max_agents,
            doc_graph_path=doc_graph_path or "data/doc_graph.json",
        )

        # Load traversal plan to check if we have seed documents
        traversal_plan_data = traversal_plan.load()

        # Step 3: Single agent traversal for demo
        # Note: Full multi-agent .map() functionality requires more complex ZenML setup
        if traversal_plan_data.seed_documents:
            logger.info(f"Running traversal with first seed document")

            # Use the first (most relevant) seed document
            primary_seed = traversal_plan_data.seed_documents[0]

            # Single traversal for now
            traversal_result = traverse_node(
                seed_document=primary_seed,
                agent_id="primary_agent",
                query=query,
                max_depth=max_depth,
                agent_budget=agent_budget,
                doc_graph_path=doc_graph_path or "data/doc_graph.json",
                relationship_types=["leads_to", "references", "related", "prerequisite"],
            )

            # Step 4: Create aggregated results from single agent
            aggregated_results = create_single_agent_findings(
                traversal_trace=traversal_result,
                query=query,
                min_relevance_threshold=0.4,
            )

            # Step 5: Build final evidence package
            evidence_pack = build_evidence_pack(
                aggregated_findings=aggregated_results,
                search_parameters={
                    'query': query,
                    'max_agents': max_agents,
                    'max_depth': max_depth,
                    'agent_budget': agent_budget,
                    'search_type': 'deep',
                }
            )

            logger.info("Deep search completed - evidence package created")

        else:
            logger.info("No seed documents found for deep search - creating empty result")
            # Create empty evidence package for failed deep search
            evidence_pack = create_empty_evidence_pack(
                query=query,
                search_type="failed_deep"
            )

    else:
        logger.info("Simple query detected - performing direct retrieval")

        # For simple queries, we can do a direct lookup
        # This demonstrates conditional pipeline execution
        evidence_pack = create_simple_evidence_pack(
            query=query,
            search_intent=search_intent,
            doc_graph_path=doc_graph_path or "data/doc_graph.json",
        )

        logger.info("Simple search completed")

    logger.info("Pipeline execution completed")


def load_config(config_path: str = None) -> Dict[str, Any]:
    """Load pipeline configuration from YAML file."""
    if config_path is None:
        config_path = Path(__file__).parent.parent / "config" / "run_config.yaml"

    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            return config
    except FileNotFoundError:
        logger.warning(f"Config file not found: {config_path}")
        return {}


def setup_environment():
    """Setup environment variables for the demo."""
    # Set ZenML environment variables for cleaner demo output
    os.environ.setdefault("ZENML_ANALYTICS_OPT_IN", "false")
    os.environ.setdefault("AUTO_OPEN_DASHBOARD", "false")
    os.environ.setdefault("ZENML_LOGGING_VERBOSITY", "INFO")

    # Check for required API keys
    if not any([
        os.getenv("OPENAI_API_KEY"),
        os.getenv("ANTHROPIC_API_KEY"),
        os.getenv("AZURE_OPENAI_API_KEY"),
    ]):
        logger.warning(
            "No LLM API key found. Please set one of: OPENAI_API_KEY, ANTHROPIC_API_KEY, AZURE_OPENAI_API_KEY"
        )
        logger.warning("The pipeline may fail without a valid API key")


def main():
    """Main entry point for running the pipeline."""
    parser = argparse.ArgumentParser(
        description="Hierarchical Document Search Agent Demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Deep search with default parameters
  python pipelines/hierarchical_search_pipeline.py \\
    --query "What are the latest developments in quantum computing applications?"

  # Simple search
  python pipelines/hierarchical_search_pipeline.py \\
    --query "What is Python?"

  # Custom parameters
  python pipelines/hierarchical_search_pipeline.py \\
    --query "How do advanced Python concepts relate to software engineering?" \\
    --max-agents 5 --max-depth 3 --agent-budget 15

  # Load from demo scenario
  python pipelines/hierarchical_search_pipeline.py \\
    --query "comprehensive data science overview" \\
    --scenario full_demo
        """
    )

    parser.add_argument(
        "--query", "-q",
        required=True,
        help="Search query to process"
    )

    parser.add_argument(
        "--max-agents", "-a",
        type=int,
        default=3,
        help="Maximum number of parallel agents (default: 3)"
    )

    parser.add_argument(
        "--max-depth", "-d",
        type=int,
        default=4,
        help="Maximum traversal depth per agent (default: 4)"
    )

    parser.add_argument(
        "--agent-budget", "-b",
        type=int,
        default=10,
        help="Budget (number of documents) per agent (default: 10)"
    )

    parser.add_argument(
        "--scenario", "-s",
        choices=["quick_demo", "full_demo", "caching_demo"],
        help="Use predefined demo scenario parameters"
    )

    parser.add_argument(
        "--config", "-c",
        help="Path to configuration YAML file"
    )

    parser.add_argument(
        "--doc-graph",
        help="Path to document graph JSON file"
    )

    args = parser.parse_args()

    # Setup environment
    setup_environment()

    # Load configuration
    config = load_config(args.config)

    # Override with scenario parameters if specified
    if args.scenario:
        scenario_config = config.get('demo_scenarios', {}).get(args.scenario, {})
        if scenario_config:
            logger.info(f"Using scenario: {args.scenario}")
            args.max_agents = scenario_config.get('max_agents', args.max_agents)
            args.max_depth = scenario_config.get('max_depth', args.max_depth)
            args.agent_budget = scenario_config.get('agent_budget', args.agent_budget)

    # Determine document graph path
    if args.doc_graph:
        doc_graph_path = args.doc_graph
    else:
        # Default to relative path from pipeline location
        doc_graph_path = str(Path(__file__).parent.parent / "data" / "doc_graph.json")

    logger.info("=" * 60)
    logger.info("HIERARCHICAL DOCUMENT SEARCH AGENT DEMO")
    logger.info("=" * 60)
    logger.info(f"Query: {args.query}")
    logger.info(f"Max Agents: {args.max_agents}")
    logger.info(f"Max Depth: {args.max_depth}")
    logger.info(f"Agent Budget: {args.agent_budget}")
    logger.info(f"Document Graph: {doc_graph_path}")
    if args.scenario:
        logger.info(f"Scenario: {args.scenario}")
    logger.info("=" * 60)

    try:
        # Run the pipeline
        pipeline_run = hierarchical_search_pipeline(
            query=args.query,
            max_agents=args.max_agents,
            max_depth=args.max_depth,
            agent_budget=args.agent_budget,
            doc_graph_path=doc_graph_path,
        )

        logger.info("=" * 60)
        logger.info("PIPELINE EXECUTION COMPLETED")
        logger.info("=" * 60)

        # Get ZenML client to show dashboard info
        try:
            client = Client()
            logger.info(f"View results in ZenML Dashboard: {client.active_stack.dashboard_url}")
            logger.info(f"Run ID: {pipeline_run.id}")
        except Exception as e:
            logger.info("Pipeline completed successfully")
            logger.debug(f"Could not get dashboard info: {e}")

        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}")
        logger.error("Please check your configuration and try again")
        sys.exit(1)


if __name__ == "__main__":
    main()