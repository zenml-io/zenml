"""ZenML Pipeline for LlamaIndex Function Agent.

This pipeline demonstrates how to integrate LlamaIndex agents with ZenML
for orchestration and artifact management.
"""

import os
from typing import Annotated, Any, Dict

from agent import agent

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
def run_llamaindex_agent(
    query: str,
) -> Annotated[Dict[str, Any], "agent_results"]:
    """Execute the LlamaIndex Function Agent and return results.

    Args:
        query: Question for the agent.

    Returns:
        The query and generated response.
    """

    async def run_agent_async() -> Any:
        return await agent.run(query)

    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        response = loop.run_until_complete(run_agent_async())
    finally:
        loop.close()

    if hasattr(response, "response"):
        result = str(response.response)
    else:
        result = str(response)

    return {"query": query, "response": result}


@step
def format_llamaindex_response(
    agent_data: Dict[str, Any],
) -> Annotated[str, "formatted_response"]:
    """Format the LlamaIndex agent results into a readable summary.

    Args:
        agent_data: Query and generated response.

    Returns:
        The formatted agent response.
    """
    query = agent_data["query"]
    response = agent_data["response"]
    formatted = f"""🦙 LLAMAINDEX FUNCTION AGENT RESPONSE
{"=" * 40}

Query: {query}

Response:
{response}

🔧 Powered by LlamaIndex (Function Agent + Tools)
"""

    return formatted.strip()


@pipeline(settings={"docker": docker_settings}, enable_cache=False)
def agent_pipeline(
    query: str = "What's the weather in New York and calculate a tip for a $50 bill?",
) -> str:
    """ZenML pipeline that orchestrates the LlamaIndex Function Agent.

    Returns:
        Formatted agent response
    """
    # Run the LlamaIndex agent
    agent_results = run_llamaindex_agent(query=query)

    # Format the results
    summary = format_llamaindex_response(agent_results)

    return summary


if __name__ == "__main__":
    print("🚀 Running LlamaIndex Function Agent pipeline...")
    run_result = agent_pipeline()
    print("Pipeline completed successfully!")
    print("Check the ZenML dashboard for detailed results and artifacts.")
