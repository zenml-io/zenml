"""ZenML Pipeline for lagent ReAct Agent.

This pipeline demonstrates how to integrate lagent with ZenML
for orchestration and artifact management.
"""

import os
from typing import Annotated, Any, Dict

from lagent.schema import AgentMessage
from lagent_agent import agent

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
def run_lagent_agent(
    query: str,
) -> Annotated[Dict[str, Any], "agent_results"]:
    """Execute the lagent ReAct agent with the given query."""
    try:
        # Create user message
        user_msg = AgentMessage(sender="user", content=query)

        # Run the agent
        response = agent(user_msg)

        # Extract response content
        if hasattr(response, "content"):
            result_content = response.content
        else:
            result_content = str(response)

        return {
            "query": query,
            "response": result_content,
            "status": "success",
        }
    except Exception as e:
        return {
            "query": query,
            "response": f"Agent error: {str(e)}",
            "status": "error",
        }


@step
def format_lagent_response(
    agent_data: Dict[str, Any],
) -> Annotated[str, "formatted_response"]:
    """Format the lagent results into a readable summary."""
    query = agent_data["query"]
    response = agent_data["response"]
    status = agent_data["status"]

    if status == "error":
        formatted = f"""❌ LAGENT AGENT ERROR
{"=" * 40}

Query: {query}
Error: {response}
"""
    else:
        formatted = f"""🤖 LAGENT REACT AGENT RESPONSE
{"=" * 40}

Query: {query}

Response:
{response}

🧠 Powered by lagent (InternLM)
"""

    return formatted.strip()


@pipeline(settings={"docker": docker_settings}, enable_cache=False)
def lagent_agent_pipeline() -> str:
    """ZenML pipeline that orchestrates the lagent ReAct agent.

    Returns:
        Formatted agent response
    """
    # External artifact for the query
    user_query = ExternalArtifact(
        value="Write a Python function to calculate the factorial of a number, then calculate factorial of 5."
    )

    # Run the lagent agent
    agent_results = run_lagent_agent(user_query)

    # Format the results
    summary = format_lagent_response(agent_results)

    return summary


if __name__ == "__main__":
    print("🚀 Running lagent ReAct agent pipeline...")
    run_result = lagent_agent_pipeline()
    print("Pipeline completed successfully!")
    print("Check the ZenML dashboard for detailed results and artifacts.")
