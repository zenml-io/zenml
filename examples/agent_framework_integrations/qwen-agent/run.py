"""ZenML Pipeline for Qwen-Agent.

This pipeline demonstrates how to integrate Qwen-Agent with ZenML
for orchestration and artifact management.
"""

import os
from typing import Annotated, Any, Dict

from qwen_agent_impl import agent  # Use the local agent implementation

from zenml import pipeline, step
from zenml.config import DockerSettings, PythonPackageInstaller

docker_settings = DockerSettings(
    python_package_installer=PythonPackageInstaller.UV,
    requirements="requirements.txt",  # relative to the pipeline directory
    environment={
        # Propagate API keys into the container so either OpenAI-compatible endpoints
        # or Alibaba DashScope can be used interchangeably based on the LLM config.
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
        "DASHSCOPE_API_KEY": os.getenv("DASHSCOPE_API_KEY"),
    },
)


@step
def run_qwen_agent(
    query: str,
) -> Annotated[Dict[str, Any], "agent_results"]:
    """Execute the Qwen-Agent with the given query.

    Args:
        query: Question for the agent.

    Returns:
        The query and generated response.

    Raises:
        RuntimeError: If the agent returns no response.
    """
    messages = [{"role": "user", "content": query}]
    last_batch: list[Any] = []
    for batch in agent.run(messages=messages):
        last_batch = batch

    if not last_batch:
        raise RuntimeError("Qwen-Agent returned no messages.")

    last_msg = last_batch[-1]
    if isinstance(last_msg, dict):
        role = last_msg.get("role")
        final_text = last_msg.get("content")
    else:
        role = getattr(last_msg, "role", None)
        final_text = getattr(last_msg, "content", None)

    if role != "assistant" or not isinstance(final_text, str):
        raise RuntimeError("Qwen-Agent did not return a final response.")
    if not final_text.strip():
        raise RuntimeError("Qwen-Agent returned an empty response.")

    return {"query": query, "response": final_text}


@step
def format_qwen_response(
    agent_data: Dict[str, Any],
) -> Annotated[str, "formatted_response"]:
    """Format the Qwen-Agent results into a readable summary.

    Args:
        agent_data: Query and generated response.

    Returns:
        The formatted agent response.
    """
    query = agent_data["query"]
    response = agent_data["response"]
    formatted = f"""🤖 QWEN-AGENT RESPONSE
{"=" * 40}

Query: {query}

Response:
{response}

🧠 Powered by Qwen-Agent (Alibaba Cloud)
"""

    return formatted.strip()


@pipeline(settings={"docker": docker_settings}, enable_cache=False)
def agent_pipeline(
    query: str = "Calculate the result of 15 multiplied by 7, then add 42 to it.",
) -> str:
    """ZenML pipeline that orchestrates the Qwen-Agent.

    Returns:
        Formatted agent response
    """
    # Run the Qwen-Agent with the provided query
    agent_results = run_qwen_agent(query=query)

    # Format the results
    summary = format_qwen_response(agent_results)

    return summary


if __name__ == "__main__":
    print("🚀 Running Qwen-Agent pipeline...")
    run_result = agent_pipeline()
    print("Pipeline completed successfully!")
    print("Check the ZenML dashboard for detailed results and artifacts.")
