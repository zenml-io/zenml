"""ZenML Pipeline for LlamaIndex Function Agent.

This pipeline demonstrates how to integrate LlamaIndex agents with ZenML
for orchestration and artifact management.
"""

import os
from typing import Annotated, Any, Dict

from agent import agent

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
def run_llamaindex_agent(
    query: str,
) -> Annotated[Dict[str, Any], "agent_results"]:
    """Execute the LlamaIndex Function Agent and return results."""

    async def run_agent_async():
        return await agent.run(query)

    try:
        # LlamaIndex agent.run() is actually async and needs proper await
        import asyncio

        # Create and run in event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            response = loop.run_until_complete(run_agent_async())
        finally:
            loop.close()

        # Extract the response content
        if hasattr(response, "response"):
            result = str(response.response)
        else:
            result = str(response)

        return {"query": query, "response": result, "status": "success"}
    except Exception as e:
        return {
            "query": query,
            "response": f"Agent error: {str(e)}",
            "status": "error",
        }


@step
def format_llamaindex_response(
    agent_data: Dict[str, Any],
) -> Annotated[str, "formatted_response"]:
    """Format the LlamaIndex agent results into a readable summary."""
    query = agent_data["query"]
    response = agent_data["response"]
    status = agent_data["status"]

    if status == "error":
        formatted = f"""❌ LLAMAINDEX AGENT ERROR
{"=" * 40}

Query: {query}
Error: {response}
"""
    else:
        formatted = f"""🦙 LLAMAINDEX FUNCTION AGENT RESPONSE
{"=" * 40}

Query: {query}

Response:
{response}

🔧 Powered by LlamaIndex (Function Agent + Tools)
"""

    return formatted.strip()


@pipeline(settings={"docker": docker_settings}, enable_cache=False)
def llamaindex_agent_pipeline() -> str:
    """ZenML pipeline that orchestrates the LlamaIndex Function Agent.

    Returns:
        Formatted agent response
    """
    # External artifact for agent query
    agent_query = ExternalArtifact(
        value="What's the weather in New York and calculate a tip for a $50 bill?"
    )

    # Run the LlamaIndex agent
    agent_results = run_llamaindex_agent(agent_query)

    # Format the results
    summary = format_llamaindex_response(agent_results)

    return summary


if __name__ == "__main__":
    print("🚀 Running LlamaIndex Function Agent pipeline...")
    run_result = llamaindex_agent_pipeline()
    print("Pipeline completed successfully!")
    print("Check the ZenML dashboard for detailed results and artifacts.")
