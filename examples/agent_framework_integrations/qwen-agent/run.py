"""ZenML Pipeline for Qwen-Agent.

This pipeline demonstrates how to integrate Qwen-Agent with ZenML
for orchestration and artifact management.
"""

import os
from typing import Annotated, Any, Dict

from qwen_agent import agent

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
def run_qwen_agent(
    query: str,
) -> Annotated[Dict[str, Any], "agent_results"]:
    """Execute the Qwen-Agent with the given query."""
    try:
        # Run the agent with the query
        response = agent.run([{"role": "user", "content": query}])

        # Extract the response content
        if isinstance(response, list) and len(response) > 0:
            result_content = response[-1].get("content", str(response))
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
def format_qwen_response(
    agent_data: Dict[str, Any],
) -> Annotated[str, "formatted_response"]:
    """Format the Qwen-Agent results into a readable summary."""
    query = agent_data["query"]
    response = agent_data["response"]
    status = agent_data["status"]

    if status == "error":
        formatted = f"""❌ QWEN-AGENT ERROR
{"=" * 40}

Query: {query}
Error: {response}
"""
    else:
        formatted = f"""🤖 QWEN-AGENT RESPONSE
{"=" * 40}

Query: {query}

Response:
{response}

🧠 Powered by Qwen-Agent (Alibaba Cloud)
"""

    return formatted.strip()


@pipeline(settings={"docker": docker_settings}, enable_cache=False)
def qwen_agent_pipeline() -> str:
    """ZenML pipeline that orchestrates the Qwen-Agent.

    Returns:
        Formatted agent response
    """
    # External artifact for the query
    user_query = ExternalArtifact(
        value="Calculate the result of 15 multiplied by 7, then add 42 to it."
    )

    # Run the Qwen-Agent
    agent_results = run_qwen_agent(user_query)

    # Format the results
    summary = format_qwen_response(agent_results)

    return summary


if __name__ == "__main__":
    print("🚀 Running Qwen-Agent pipeline...")
    run_result = qwen_agent_pipeline()
    print("Pipeline completed successfully!")
    print("Check the ZenML dashboard for detailed results and artifacts.")
