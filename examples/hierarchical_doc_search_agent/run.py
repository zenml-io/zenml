#!/usr/bin/env python3
"""
Hierarchical Document Search Agent Demo

A ZenML pipeline showcasing dynamic execution, AI-powered document exploration,
and hierarchical traversal through document relationships.

Usage:
    python run.py --query "What is Python?" --max-agents 2 --max-depth 3
    python run.py --query "How do quantum algorithms relate to machine learning?"
    python run.py --help
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Dict, Any

import yaml

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))

from pipelines.hierarchical_search_pipeline import hierarchical_search_pipeline


def setup_environment():
    """Setup environment variables for the demo."""
    # Set ZenML environment variables for cleaner demo output
    os.environ.setdefault("ZENML_ANALYTICS_OPT_IN", "false")
    os.environ.setdefault("AUTO_OPEN_DASHBOARD", "false")
    os.environ.setdefault("ZENML_LOGGING_VERBOSITY", "INFO")
    os.environ.setdefault("ZENML_DISABLE_CLIENT_SERVER_MISMATCH_WARNING", "true")

    # Check for required API keys
    if not any([
        os.getenv("OPENAI_API_KEY"),
        os.getenv("ANTHROPIC_API_KEY"),
        os.getenv("AZURE_OPENAI_API_KEY"),
    ]):
        print("⚠️  Warning: No LLM API key found. Please set one of:")
        print("   - OPENAI_API_KEY")
        print("   - ANTHROPIC_API_KEY")
        print("   - AZURE_OPENAI_API_KEY")
        print("   The pipeline may fail without a valid API key.")
        print()


def load_config(config_path: str = None) -> Dict[str, Any]:
    """Load pipeline configuration from YAML file."""
    if config_path is None:
        config_path = Path(__file__).parent / "config" / "run_config.yaml"

    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            return config
    except FileNotFoundError:
        print(f"⚠️  Config file not found: {config_path}")
        return {}


def main():
    """Main entry point for the hierarchical document search demo."""
    parser = argparse.ArgumentParser(
        description="Hierarchical Document Search Agent Demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Simple query (direct lookup)
  python run.py --query "What is Python?"

  # Complex query (hierarchical search)
  python run.py --query "How do quantum algorithms relate to machine learning?"

  # Custom parameters
  python run.py --query "Latest developments in quantum computing applications" \\
    --max-agents 4 --max-depth 5 --agent-budget 15

  # Use predefined scenario
  python run.py --query "comprehensive data science overview" --scenario full_demo
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
            print(f"📋 Using scenario: {args.scenario}")
            args.max_agents = scenario_config.get('max_agents', args.max_agents)
            args.max_depth = scenario_config.get('max_depth', args.max_depth)
            args.agent_budget = scenario_config.get('agent_budget', args.agent_budget)

    # Determine document graph path
    if args.doc_graph:
        doc_graph_path = args.doc_graph
    else:
        # Default to relative path from current location
        doc_graph_path = str(Path(__file__).parent / "data" / "doc_graph.json")

    print("=" * 60)
    print("🔍 HIERARCHICAL DOCUMENT SEARCH AGENT")
    print("=" * 60)
    print(f"📝 Query: {args.query}")
    print(f"🤖 Max Agents: {args.max_agents}")
    print(f"📊 Max Depth: {args.max_depth}")
    print(f"💰 Agent Budget: {args.agent_budget}")
    print(f"📄 Document Graph: {doc_graph_path}")
    if args.scenario:
        print(f"🎯 Scenario: {args.scenario}")
    print("=" * 60)

    try:
        # Try ZenML pipeline first
        try:
            pipeline_run = hierarchical_search_pipeline(
                query=args.query,
                max_agents=args.max_agents,
                max_depth=args.max_depth,
                agent_budget=args.agent_budget,
                doc_graph_path=doc_graph_path,
            )

            print("=" * 60)
            print("✅ ZENML PIPELINE EXECUTION COMPLETED")
            print("=" * 60)

            # Try to show dashboard info
            try:
                from zenml.client import Client
                client = Client()
                print(f"🌐 View results in ZenML Dashboard: {client.active_stack.dashboard_url}")
                print(f"🆔 Run ID: {pipeline_run.id}")
            except Exception as e:
                print("✅ Pipeline completed successfully")
                print(f"   (Dashboard info unavailable: {e})")

        except Exception as zenml_error:
            # Fall back to direct execution without ZenML orchestration
            print("⚠️  ZenML orchestration failed, running core logic directly...")
            print(f"   ZenML Error: {zenml_error}")
            print()

            run_core_logic(args.query, args.max_agents, args.max_depth, args.agent_budget, doc_graph_path)

        print("=" * 60)

    except Exception as e:
        print("=" * 60)
        print("❌ EXECUTION FAILED")
        print("=" * 60)
        print(f"Error: {e}")
        print()
        print("🔧 Troubleshooting:")
        print("1. Check your API key is set (OPENAI_API_KEY, etc.)")
        print("2. Try a simpler query first")
        print("3. Check the error details above")
        sys.exit(1)


def run_core_logic(query: str, max_agents: int, max_depth: int, agent_budget: int, doc_graph_path: str):
    """Run the core hierarchical search logic without ZenML orchestration."""
    print("🔍 HIERARCHICAL SEARCH - CORE LOGIC EXECUTION")
    print("=" * 60)

    # Import steps
    from steps.intent_detection import get_intent_agent
    from steps.plan_seed_nodes import load_document_graph, calculate_document_relevance
    from steps.traverse_node import get_content_analysis_agent, get_traversal_agent, get_related_documents
    from steps.aggregate_findings import ConsolidatedEvidence

    # Step 1: Intent Detection
    print(f"1️⃣  Analyzing query intent...")
    agent = get_intent_agent()
    result = agent.run_sync(f"""
    Query: "{query}"

    Analyze this query and classify it as either "simple" or "deep" search.
    Consider keyword indicators and complexity.
    """)

    print(f"   🧠 Intent: {result.output.search_type}")
    print(f"   📊 Confidence: {result.output.confidence:.2f}")
    print(f"   💭 Key concepts: {result.output.key_concepts}")
    print()

    if result.output.search_type == "simple":
        # Simple query path
        print("2️⃣  Performing direct document lookup...")

        import json
        with open(doc_graph_path, 'r') as f:
            doc_graph = json.load(f)

        documents = doc_graph.get('documents', {})
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
            print(f"   📄 Best match: {best_match[0]}")
            print(f"   📝 Title: {best_match[1]['title']}")
            print(f"   ⭐ Relevance: {best_score}/{len(query.split())}")
            print(f"   📖 Content: {best_match[1]['content'][:200]}...")
        else:
            print("   ❌ No matching documents found")

        print("\n✅ Simple search completed!")

    else:
        # Deep/complex query path
        print("2️⃣  Planning seed documents for deep search...")

        # Load document graph
        doc_graph = load_document_graph(doc_graph_path)
        documents = doc_graph.get('documents', {})

        # Find seed candidates
        seed_candidates = []
        for doc_id, doc_data in documents.items():
            relevance = calculate_document_relevance(query, doc_data, result.output.key_concepts)
            if relevance > 0.3:
                seed_candidates.append((doc_id, relevance, doc_data))

        # Sort and limit to max_agents
        seed_candidates.sort(key=lambda x: x[1], reverse=True)
        selected_seeds = seed_candidates[:max_agents]

        print(f"   🌱 Found {len(selected_seeds)} seed documents:")
        for doc_id, relevance, doc_data in selected_seeds:
            print(f"      • {doc_id} (relevance: {relevance:.2f}) - {doc_data['title']}")
        print()

        # Step 3: Simulate traversal for each seed
        print("3️⃣  Performing hierarchical traversal...")
        all_evidence = []

        for i, (seed_id, _, seed_doc) in enumerate(selected_seeds):
            print(f"   🤖 Agent {i+1} starting from: {seed_id}")

            # Analyze seed document
            content_agent = get_content_analysis_agent()
            evidence_result = content_agent.run_sync(f"""
            Query: "{query}"

            Document to analyze:
            Title: {seed_doc['title']}
            Content: {seed_doc['content']}
            Type: {seed_doc.get('type', 'unknown')}
            """)

            evidence = evidence_result.output
            print(f"      📊 Relevance: {evidence.relevance_score:.2f}")
            print(f"      💡 Key insights: {evidence.key_insights[:2]}")

            # Find related documents
            related_docs = get_related_documents(seed_id, documents)
            print(f"      🔗 Found {len(related_docs)} related documents")

            # Add to evidence collection
            consolidated_evidence = ConsolidatedEvidence(
                document_id=seed_id,
                title=seed_doc['title'],
                combined_content=evidence.relevant_content,
                max_relevance_score=evidence.relevance_score,
                agent_count=1,
                key_insights=evidence.key_insights,
                source_agents=[f"agent_{i}"]
            )
            all_evidence.append(consolidated_evidence)
            print()

        # Step 4: Show aggregated results
        print("4️⃣  Aggregated Results:")
        print(f"   📈 Total evidence items: {len(all_evidence)}")
        print(f"   🎯 Average relevance: {sum(e.max_relevance_score for e in all_evidence) / len(all_evidence):.2f}")

        # Sort by relevance and show top findings
        all_evidence.sort(key=lambda x: x.max_relevance_score, reverse=True)

        print("\n   🏆 Top Findings:")
        for i, evidence in enumerate(all_evidence[:3], 1):
            print(f"   {i}. {evidence.title} (score: {evidence.max_relevance_score:.2f})")
            for insight in evidence.key_insights[:2]:
                print(f"      • {insight}")

        print("\n✅ Hierarchical search completed!")

    print("\n" + "=" * 60)
    print("🎉 EXECUTION SUCCESSFUL")
    print("=" * 60)
    print("💡 This demonstrates the core AI-powered search logic.")
    print("   In a full ZenML environment, this would include:")
    print("   • Dynamic pipeline DAG generation")
    print("   • Parallel agent execution with .map()")
    print("   • Artifact lineage and caching")
    print("   • Dashboard visualization")
    print("=" * 60)


if __name__ == "__main__":
    main()