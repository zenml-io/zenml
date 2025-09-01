"""ZenML Pipeline for Semantic Kernel.

This pipeline demonstrates how to integrate Semantic Kernel with ZenML
for orchestration and artifact management.
"""

import asyncio
import os
from typing import Annotated, Any, Dict

from semantic_kernel_agent import kernel

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
def run_semantic_kernel_agent(
    query: str,
) -> Annotated[Dict[str, Any], "agent_results"]:
    """Execute the Semantic Kernel agent and return results."""
    try:

        async def run_kernel_async():
            from semantic_kernel.connectors.ai.function_choice_behavior import (
                FunctionChoiceBehavior,
            )
            from semantic_kernel.connectors.ai.open_ai.prompt_execution_settings.open_ai_prompt_execution_settings import (
                OpenAIChatPromptExecutionSettings,
            )
            from semantic_kernel.contents.chat_history import ChatHistory

            # Get the chat service
            chat_service = kernel.get_service("openai-chat")

            # Create chat history with user message
            history = ChatHistory()
            history.add_user_message(query)

            # Configure settings to enable function calling
            settings = OpenAIChatPromptExecutionSettings()
            settings.function_choice_behavior = FunctionChoiceBehavior.Auto()

            # Execute the chat with the kernel
            response = await chat_service.get_chat_message_content(
                chat_history=history,
                settings=settings,
                kernel=kernel,
            )

            return response.content

        # Run the async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            response = loop.run_until_complete(run_kernel_async())
        finally:
            loop.close()

        return {"query": query, "response": response, "status": "success"}
    except Exception as e:
        return {
            "query": query,
            "response": f"Agent error: {str(e)}",
            "status": "error",
        }


@step
def format_semantic_kernel_response(
    agent_data: Dict[str, Any],
) -> Annotated[str, "formatted_response"]:
    """Format the Semantic Kernel results into a readable summary."""
    query = agent_data["query"]
    response = agent_data["response"]
    status = agent_data["status"]

    if status == "error":
        formatted = f"""❌ SEMANTIC KERNEL AGENT ERROR
{"=" * 40}

Query: {query}
Error: {response}
"""
    else:
        formatted = f"""🧠 SEMANTIC KERNEL RESPONSE
{"=" * 40}

Query: {query}

Response:
{response}

🔧 Powered by Microsoft Semantic Kernel (AI Orchestration)
"""

    return formatted.strip()


@pipeline(settings={"docker": docker_settings}, enable_cache=False)
def semantic_kernel_agent_pipeline() -> str:
    """ZenML pipeline that orchestrates the Semantic Kernel agent.

    Returns:
        Formatted agent response
    """
    # External artifact for agent query
    agent_query = ExternalArtifact(value="What is the weather in Tokyo?")

    # Run the Semantic Kernel agent
    agent_results = run_semantic_kernel_agent(agent_query)

    # Format the results
    summary = format_semantic_kernel_response(agent_results)

    return summary


if __name__ == "__main__":
    print("🚀 Running Semantic Kernel pipeline...")
    run_result = semantic_kernel_agent_pipeline()
    print("Pipeline completed successfully!")
    print("Check the ZenML dashboard for detailed results and artifacts.")
