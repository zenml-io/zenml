"""ZenML Pipeline for OpenAI Agents SDK.

This pipeline demonstrates how to integrate OpenAI Agents SDK with ZenML
for orchestration and artifact management.
"""

import os
from typing import Annotated, Any, Dict

from openai_agent import agent

from zenml import pipeline, step
from zenml.config import DockerSettings, PythonPackageInstaller

docker_settings = DockerSettings(
    python_package_installer=PythonPackageInstaller.UV,
    requirements="requirements.txt",  # relative to the pipeline directory
    environment={
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
    },
)


@step
def run_openai_agent(query: str) -> Annotated[Dict[str, Any], "agent_results"]:
    """Execute the OpenAI Agents SDK agent and return results."""
    try:
        import agents

        # Use the default agent runner to execute the agent
        runner = agents.run.DEFAULT_AGENT_RUNNER
        result = runner.run_sync(agent, query)

        # Extract the final output
        response = result.final_output

        return {"query": query, "response": response, "status": "success"}
    except Exception as e:
        return {
            "query": query,
            "response": f"Agent error: {str(e)}",
            "status": "error",
        }


@step
def format_openai_response(
    agent_data: Dict[str, Any],
) -> Annotated[str, "formatted_response"]:
    """Format the OpenAI Agents SDK results into a readable summary."""
    query = agent_data["query"]
    response = agent_data["response"]
    status = agent_data["status"]

    if status == "error":
        formatted = f"""❌ OPENAI AGENTS SDK ERROR
{"=" * 40}

Query: {query}
Error: {response}
"""
    else:
        formatted = f"""🤖 OPENAI AGENTS SDK RESPONSE
{"=" * 40}

Query: {query}

Response:
{response}

🔧 Powered by OpenAI Agents SDK (Tools + GPT)
"""

    return formatted.strip()


@pipeline(settings={"docker": docker_settings}, enable_cache=False)
def agent_pipeline(query: str = "Tell me a fun fact about Tokyo") -> str:
    """ZenML pipeline that orchestrates the OpenAI Agents SDK.

    Returns:
        Formatted agent response
    """
    # Run the OpenAI Agents SDK agent
    agent_results = run_openai_agent(query=query)

    # Format the results
    summary = format_openai_response(agent_results)

    return summary


if __name__ == "__main__":
    print("🚀 Running OpenAI Agents SDK pipeline...")
    run_result = agent_pipeline()
    print("Pipeline completed successfully!")
    print("Check the ZenML dashboard for detailed results and artifacts.")
