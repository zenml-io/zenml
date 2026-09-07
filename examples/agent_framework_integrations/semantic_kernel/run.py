"""ZenML Pipeline for Semantic Kernel.

This pipeline demonstrates how to integrate Semantic Kernel with ZenML
for orchestration and artifact management.
"""

import asyncio
import os
from typing import Annotated, Any, Dict

from semantic_kernel_agent import kernel

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
def run_semantic_kernel_agent(
    query: str,
) -> Annotated[Dict[str, Any], "agent_results"]:
    """Execute the Semantic Kernel agent and return results.

    Args:
        query: Question for the agent.

    Returns:
        The query and generated response.
    """

    async def run_kernel_async() -> Any:
        from semantic_kernel.connectors.ai.function_choice_behavior import (
            FunctionChoiceBehavior,
        )
        from semantic_kernel.connectors.ai.open_ai.prompt_execution_settings.open_ai_prompt_execution_settings import (
            OpenAIChatPromptExecutionSettings,
        )
        from semantic_kernel.contents.chat_history import ChatHistory

        chat_service = kernel.get_service("openai-chat")
        history = ChatHistory()
        history.add_user_message(query)

        settings = OpenAIChatPromptExecutionSettings()
        settings.function_choice_behavior = FunctionChoiceBehavior.Auto()

        response = await chat_service.get_chat_message_content(
            chat_history=history,
            settings=settings,
            kernel=kernel,
        )
        return response.content

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        response = loop.run_until_complete(run_kernel_async())
    finally:
        loop.close()

    return {"query": query, "response": response}


@step
def format_semantic_kernel_response(
    agent_data: Dict[str, Any],
) -> Annotated[str, "formatted_response"]:
    """Format the Semantic Kernel results into a readable summary.

    Args:
        agent_data: Query and generated response.

    Returns:
        The formatted agent response.
    """
    query = agent_data["query"]
    response = agent_data["response"]
    formatted = f"""🧠 SEMANTIC KERNEL RESPONSE
{"=" * 40}

Query: {query}

Response:
{response}

🔧 Powered by Microsoft Semantic Kernel (AI Orchestration)
"""

    return formatted.strip()


@pipeline(settings={"docker": docker_settings}, enable_cache=False)
def agent_pipeline(query: str = "What is the weather in Tokyo?") -> str:
    """ZenML pipeline that orchestrates the Semantic Kernel agent.

    Returns:
        Formatted agent response
    """
    # Run the Semantic Kernel agent
    agent_results = run_semantic_kernel_agent(query=query)

    # Format the results
    summary = format_semantic_kernel_response(agent_results)

    return summary


if __name__ == "__main__":
    print("🚀 Running Semantic Kernel pipeline...")
    run_result = agent_pipeline()
    print("Pipeline completed successfully!")
    print("Check the ZenML dashboard for detailed results and artifacts.")
