"""ZenML Pipeline for Google ADK (Gemini) Agent.

This module encapsulates a Google ADK agent within a ZenML pipeline to provide
production-grade orchestration and artifact management. The core agent and its
tools live in this file so it can be executed standalone, while the ZenML
pipeline enables reproducibility and observability when running as part of a
larger workflow.

Design notes:
- The agent exposes simple Python functions as tools; this keeps the toolchain
  easy to test and reason about.
- We expose the environment variable GOOGLE_API_KEY to the containerized steps,
  as required by the Google Gemini API.
- The agent invocation is wrapped in a defensive call pattern to support both
  callable agents and explicit `.run(...)` dispatch depending on the ADK version.
"""

import datetime
import os
from typing import Annotated, Any, Dict
from zoneinfo import ZoneInfo

from google.adk.agents import Agent

from zenml import pipeline, step
from zenml.config import DockerSettings, PythonPackageInstaller


def get_weather(city: str) -> dict:
    """Retrieve a simple weather report for a specified city.

    This mock is intentionally deterministic to make the example reproducible
    and to keep the focus on the pipeline orchestration and tool usage patterns,
    rather than on external API behavior or variability.
    """
    return {
        "status": "success",
        "report": f"The weather in {city} is sunny with a temperature of 22°C.",
        "timestamp": datetime.datetime.now().isoformat(),
    }


def get_current_time(timezone: str = "UTC") -> dict:
    """Return the current time in the specified timezone.

    Handles invalid timezones gracefully and encodes the error into the result
    instead of raising, so downstream steps don't fail on user input issues.
    """
    try:
        tz = ZoneInfo(timezone)
        current_time = datetime.datetime.now(tz)
        return {
            "status": "success",
            "time": current_time.strftime("%Y-%m-%d %H:%M:%S %Z"),
            "timezone": timezone,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Invalid timezone: {timezone}",
            "error": str(e),
        }


# PanAgent will discover this 'root_agent' variable
root_agent = Agent(
    name="weather_time_agent",
    model="gemini-2.0-flash",
    description="Agent to answer questions about the weather in a city and provide current time.",
    instruction=(
        "You are a helpful agent who can answer user questions about the weather and "
        "current time. Use the available tools to provide accurate information. "
        "When asked, call the weather tool for city-specific weather and the time tool "
        "for timezone-specific time."
    ),
    tools=[get_weather, get_current_time],
)


# Docker/step settings ensure consistent, hermetic execution across environments.
docker_settings = DockerSettings(
    python_package_installer=PythonPackageInstaller.UV,
    requirements="requirements.txt",  # resolved relative to this directory
    environment={
        # Expose credentials in the execution environment only; no hard-coding.
        "GOOGLE_API_KEY": os.getenv("GOOGLE_API_KEY"),
    },
)


@step
def run_google_adk_agent(
    query: str,
) -> Annotated[Dict[str, Any], "agent_results"]:
    """Execute the Google ADK agent and normalize the response.

    The agent library may expose different invocation styles across versions.
    We attempt a callable interface first and fall back to an explicit .run() call.
    """
    try:
        result: Any
        try:
            # Prefer a callable interface if the Agent implements __call__.
            result = root_agent(query)
        except Exception:
            # Fall back to an explicit method in case __call__ isn't supported.
            result = root_agent.run(query)  # type: ignore[attr-defined]

        response_text = str(result)
        return {"query": query, "response": response_text, "status": "success"}
    except Exception as e:
        return {
            "query": query,
            "response": f"Agent error: {str(e)}",
            "status": "error",
        }


@step
def format_google_adk_response(
    agent_data: Dict[str, Any],
) -> Annotated[str, "formatted_response"]:
    """Format agent output into a concise, human-readable summary.

    Keeping formatting separate simplifies evolution of the agent logic without
    impacting presentation, and makes it easy to replace with richer renderers later.
    """
    query = agent_data.get("query", "")
    response = agent_data.get("response", "")
    status = agent_data.get("status", "unknown")

    if status != "success":
        formatted = f"""❌ GOOGLE ADK AGENT ERROR
{"=" * 40}

Query: {query}
Error: {response}
"""
    else:
        formatted = f"""🧠 GOOGLE ADK (GEMINI) AGENT RESPONSE
{"=" * 40}

Query:
{query}

Response:
{response}

⚙️ Powered by Google ADK (Gemini)
"""

    return formatted.strip()


@pipeline(settings={"docker": docker_settings}, enable_cache=False)
def agent_pipeline(
    query: str = "What's the weather in Paris and the current time in Europe/Paris?",
) -> str:
    """ZenML pipeline orchestrating the Google ADK agent end-to-end.

    Returns:
        A formatted string summarizing the agent response.
    """
    results = run_google_adk_agent(query=query)
    summary = format_google_adk_response(results)
    return summary


if __name__ == "__main__":
    print("🚀 Running Google ADK (Gemini) agent pipeline...")
    _ = agent_pipeline()
    print("Pipeline completed successfully!")
    print("Check the ZenML dashboard for detailed results and artifacts.")
