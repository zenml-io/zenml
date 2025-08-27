"""ZenML Pipeline for PydanticAI.

This pipeline demonstrates how to integrate PydanticAI with ZenML
for orchestration and artifact management.
"""

import os
from typing import Annotated, Any, Dict

from pydanticai_agent import agent

from zenml import ExternalArtifact, pipeline, step
from zenml.config import DockerSettings, PythonPackageInstaller

docker_settings = DockerSettings(
    python_package_installer=PythonPackageInstaller.UV,
    requirements="requirements.txt",  # relative to the pipeline directory
    environment={
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
    },
)


@step
def run_pydanticai_agent(
    query: str,
) -> Annotated[Dict[str, Any], "agent_results"]:
    """Execute the PydanticAI agent and return results."""
    try:
        # Execute the PydanticAI agent
        result = agent.run_sync(query)

        return {"query": query, "response": result.output, "status": "success"}
    except Exception as e:
        return {
            "query": query,
            "response": f"Agent error: {str(e)}",
            "status": "error",
        }


@step
def format_pydanticai_response(
    agent_data: Dict[str, Any],
) -> Annotated[str, "formatted_response"]:
    """Format the PydanticAI results into a readable summary."""
    query = agent_data["query"]
    response = agent_data["response"]
    status = agent_data["status"]

    if status == "error":
        formatted = f"""❌ PYDANTICAI AGENT ERROR
{"=" * 40}

Query: {query}
Error: {response}
"""
    else:
        formatted = f"""🐍 PYDANTICAI RESPONSE
{"=" * 40}

Query: {query}

Response:
{response}

🔧 Powered by PydanticAI (Type-Safe AI Agents)
"""

    return formatted.strip()


@pipeline(settings={"docker": docker_settings}, enable_cache=False)
def pydanticai_agent_pipeline() -> str:
    """ZenML pipeline that orchestrates the PydanticAI agent.

    Returns:
        Formatted agent response
    """
    # External artifact for agent query
    agent_query = ExternalArtifact(value="What is the secret data?")

    # Run the PydanticAI agent
    agent_results = run_pydanticai_agent(agent_query)

    # Format the results
    summary = format_pydanticai_response(agent_results)

    return summary


if __name__ == "__main__":
    print("🚀 Running PydanticAI pipeline...")
    run_result = pydanticai_agent_pipeline()
    print("Pipeline completed successfully!")
    print("Check the ZenML dashboard for detailed results and artifacts.")
