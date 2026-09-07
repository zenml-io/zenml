"""ZenML Pipeline for LangGraph ReAct Agent.

This pipeline demonstrates how to integrate LangGraph agents with ZenML
for orchestration and artifact management.
"""

import os
from typing import Annotated, Any, Dict

from langgraph_agent import agent

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
def run_langgraph_agent(
    query: str,
) -> Annotated[Dict[str, Any], "agent_results"]:
    """Execute the LangGraph ReAct agent and return results.

    Args:
        query: Question for the agent.

    Returns:
        The query and generated response.
    """
    messages = [{"role": "user", "content": query}]
    result = agent.invoke({"messages": messages})

    if "messages" in result and result["messages"]:
        last_message = result["messages"][-1]
        if hasattr(last_message, "content"):
            response = last_message.content
        else:
            response = str(last_message)
    else:
        response = str(result)

    return {"query": query, "response": response}


@step
def format_langgraph_response(
    agent_data: Dict[str, Any],
) -> Annotated[str, "formatted_response"]:
    """Format the LangGraph agent results into a readable summary.

    Args:
        agent_data: Query and generated response.

    Returns:
        The formatted agent response.
    """
    query = agent_data["query"]
    response = agent_data["response"]
    formatted = f"""🤖 LANGGRAPH REACT AGENT RESPONSE
{"=" * 40}

Query: {query}

Response:
{response}

🔧 Powered by LangGraph (ReAct Agent + Tools)
"""

    return formatted.strip()


@pipeline(settings={"docker": docker_settings}, enable_cache=False)
def agent_pipeline(
    query: str = "What is the weather in San Francisco?",
) -> str:
    """ZenML pipeline that orchestrates the LangGraph ReAct agent.

    Returns:
        Formatted agent response
    """
    # Run the LangGraph agent
    agent_results = run_langgraph_agent(query)

    # Format the results
    summary = format_langgraph_response(agent_results)

    return summary


if __name__ == "__main__":
    print("🚀 Running LangGraph ReAct agent pipeline...")
    run_result = agent_pipeline()
    print("Pipeline completed successfully!")
    print("Check the ZenML dashboard for detailed results and artifacts.")
