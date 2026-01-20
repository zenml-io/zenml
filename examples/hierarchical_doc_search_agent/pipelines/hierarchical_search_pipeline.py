"""Hierarchical Document Search Pipeline.

ZenML controls: fan-out, budget limits, step orchestration
Pydantic AI controls: agent decisions (traverse deeper or return answer?)
"""

from typing import Annotated, Any, Dict

from steps import (
    aggregate_results,
    create_report,
    detect_intent,
    plan_search,
    simple_search,
    traverse_node,
)

from zenml import pipeline
from zenml.config import DeploymentSettings

deployment_settings = DeploymentSettings(
    app_title="Hierarchical Document Search",
    app_description="ZenML orchestration + Pydantic AI agents",
)


@pipeline(
    dynamic=True,
    enable_cache=True,
    settings={"deployment": deployment_settings},
)
def hierarchical_search_pipeline(
    query: str = "How does quantum computing relate to machine learning?",
    max_agents: int = 3,
    max_depth: int = 2,
) -> Annotated[Dict[str, Any], "search_results"]:
    """Hierarchical search with ZenML orchestration + Pydantic AI agents.

    - ZenML controls: which steps run, fan-out, budget limits
    - Pydantic AI controls: agent decisions at each node
    - Each traverse_node call appears as a separate step in the DAG
    """
    search_type = detect_intent(query=query)

    if search_type.load() == "simple":
        results = simple_search(query=query, search_type=search_type)
    else:
        # Plan which documents to start from
        seed_nodes = plan_search(
            query=query, max_agents=max_agents, search_type=search_type
        )

        # Fan-out: spawn traversal agents, keep traversing until budget exhausted
        traversal_results = []

        # Tuple: (doc_id_chunk, budget, visited)
        # .chunk(idx) creates DAG edge AND provides the doc_id value
        pending = [
            (seed_nodes.chunk(idx), max_depth, [])
            for idx in range(len(seed_nodes.load()))
        ]

        # Configure traverse_node step to use query as a parameter
        traverse_node_step = traverse_node.with_options(
            parameters={"query": query}
        )

        while pending:
            doc_id_chunk, budget, visited = pending.pop(0)

            result, traverse_to = traverse_node_step(
                doc_id=doc_id_chunk,  # Artifact chunk - DAG edge + value
                budget=budget,
                visited=visited,
            )
            traversal_results.append(result)

            # If agent wants to traverse deeper and has budget, add to queue
            result_data = result.load()
            traverse_to_data = traverse_to.load()

            if (
                not result_data.get("found_answer")
                and result_data["budget"] > 0
            ):
                for idx in range(min(2, len(traverse_to_data))):
                    next_doc = traverse_to_data[idx]
                    if next_doc not in result_data["visited"]:
                        # traverse_to.chunk(idx) becomes doc_id for follow-up
                        pending.append(
                            (
                                traverse_to.chunk(idx),
                                result_data["budget"],
                                result_data["visited"],
                            )
                        )

        results = aggregate_results(
            traversal_results=[r.load() for r in traversal_results],
            query=query,
        )

    create_report(results=results)
    return results
