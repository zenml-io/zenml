"""ZenML Pipeline for AWS Strands Weather Agent.

This pipeline encapsulates the AWS Strands agent system in a ZenML pipeline,
demonstrating how to integrate the Strands framework with ZenML for orchestration
and artifact management.
"""

import os
from typing import Annotated

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
def run_strands_agent(query: str) -> Annotated[str, "agent_response"]:
    """Execute the Strands agent and return the response."""
    try:
        response = agent(query)
        return str(response)
    except Exception as e:
        return f"Agent error: {str(e)}"


@step
def format_weather_response(
    response: str,
) -> Annotated[str, "formatted_response"]:
    """Format the agent response into a readable summary."""
    formatted = f"""🌤️ WEATHER REPORT
{"=" * 30}

{response}

Powered by AWS Strands Agent
"""
    return formatted.strip()


@pipeline(settings={"docker": docker_settings}, enable_cache=False)
def strands_weather_pipeline() -> str:
    """ZenML pipeline that orchestrates the AWS Strands weather agent.

    Returns:
        Formatted weather response
    """
    # External artifact for weather query
    weather_query = ExternalArtifact(value="What's the weather like in Tokyo?")

    # Run the agent
    response = run_strands_agent(weather_query)

    # Format the results
    summary = format_weather_response(response)

    return summary


if __name__ == "__main__":
    print("🚀 Running AWS Strands weather pipeline...")
    run_result = strands_weather_pipeline()
    print("Pipeline completed successfully!")
    print("Check the ZenML dashboard for detailed results and artifacts.")
