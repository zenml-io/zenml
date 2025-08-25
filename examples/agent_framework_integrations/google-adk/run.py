"""ZenML Pipeline for Google ADK Agent.

This pipeline demonstrates how to integrate Google ADK agents with ZenML
for orchestration and artifact management.
"""

from typing import Annotated, Any, Dict

from adk_agent import root_agent

from zenml import ExternalArtifact, pipeline, step


@step
def run_adk_agent(query: str) -> Annotated[Dict[str, Any], "agent_results"]:
    """Execute the Google ADK agent and return results."""
    try:
        # Check what methods the agent has
        agent_response = None
        if hasattr(root_agent, "__call__"):
            agent_response = root_agent(query)
        elif hasattr(root_agent, "run"):
            agent_response = root_agent.run(query)
        elif hasattr(root_agent, "execute"):
            agent_response = root_agent.execute(query)
        else:
            # Fallback - just return info about available methods
            methods = [
                method
                for method in dir(root_agent)
                if not method.startswith("_")
            ]
            agent_response = f"Available methods: {methods}"

        return {
            "query": query,
            "result": str(agent_response),
            "status": "success",
        }
    except Exception as e:
        return {
            "query": query,
            "result": f"Agent error: {str(e)}",
            "status": "error",
        }


@step
def format_adk_response(
    agent_data: Dict[str, Any],
) -> Annotated[str, "formatted_response"]:
    """Format the Google ADK agent results into a readable summary."""
    query = agent_data["query"]
    result = agent_data["result"]
    status = agent_data["status"]

    if status == "error":
        formatted = f"""❌ GOOGLE ADK AGENT ERROR
{"=" * 40}

Query: {query}
Error: {result}
"""
    else:
        formatted = f"""🤖 GOOGLE ADK AGENT RESPONSE
{"=" * 40}

Query: {query}

Response:
{result}

🔧 Powered by Google ADK
"""

    return formatted.strip()


@pipeline
def google_adk_pipeline() -> str:
    """ZenML pipeline that orchestrates the Google ADK agent system.

    Returns:
        Formatted agent response
    """
    # External artifact for agent query
    agent_query = ExternalArtifact(value="What's the weather like in Tokyo?")

    # Run the Google ADK agent
    agent_results = run_adk_agent(agent_query)

    # Format the results
    summary = format_adk_response(agent_results)

    return summary


if __name__ == "__main__":
    print("🚀 Running Google ADK agent pipeline...")
    run_result = google_adk_pipeline()
    print("Pipeline completed successfully!")
    print("Check the ZenML dashboard for detailed results and artifacts.")
