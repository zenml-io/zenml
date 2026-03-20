"""ZenML Pipeline for AG2 Multi-Agent Travel Assistant.

This pipeline encapsulates the AG2 multi-agent system in a ZenML pipeline,
demonstrating how to integrate the AG2 framework with ZenML for orchestration
and artifact management.

AG2 (package `ag2` on PyPI) is a community-maintained fork of AutoGen with
500K+ monthly downloads. It is distinct from Microsoft AutoGen:
- AG2 imports:    from autogen import AssistantAgent, GroupChat, GroupChatManager
- MS AutoGen imports: from autogen_core import RoutedAgent  (see ../autogen/)
"""

import asyncio
import os
from typing import Annotated, Any, Dict

from autogen import AssistantAgent, GroupChat, GroupChatManager, LLMConfig

from zenml import pipeline, step
from zenml.config import DockerSettings, PythonPackageInstaller

docker_settings = DockerSettings(
    python_package_installer=PythonPackageInstaller.UV,
    requirements="requirements.txt",  # relative to the pipeline directory
    environment={
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
    },
)


def get_weather(city: str) -> str:
    """Return simulated weather conditions for a city.

    Args:
        city: Name of the destination city.

    Returns:
        A short weather description string.
    """
    weather_data = {
        "berlin": "12°C, partly cloudy with light winds",
        "paris": "15°C, sunny with clear skies",
        "tokyo": "18°C, warm and humid",
        "new york": "10°C, cool with chance of rain",
        "san francisco": "14°C, foggy morning clearing to sunshine",
    }
    return weather_data.get(city.lower(), f"22°C, pleasant weather in {city}")


def get_attractions(city: str) -> str:
    """Return top tourist attractions for a city.

    Args:
        city: Name of the destination city.

    Returns:
        A comma-separated list of attractions.
    """
    attractions_data = {
        "berlin": "Brandenburg Gate, Museum Island, East Side Gallery, Tiergarten",
        "paris": "Eiffel Tower, Louvre Museum, Notre-Dame, Montmartre",
        "tokyo": "Senso-ji Temple, Shibuya Crossing, Meiji Shrine, Akihabara",
        "new york": "Central Park, Statue of Liberty, Times Square, Brooklyn Bridge",
        "san francisco": "Golden Gate Bridge, Alcatraz, Fisherman's Wharf, Chinatown",
    }
    return attractions_data.get(
        city.lower(),
        f"City Center, Local Markets, Historic District in {city}",
    )


@step
def run_ag2_agents(
    city: str,
) -> Annotated[Dict[str, Any], "agent_results"]:
    """Execute the AG2 GroupChat multi-agent system and return results.

    Creates three specialized agents in a GroupChat:
    - weather_agent: fetches weather via tool call
    - attractions_agent: fetches top attractions via tool call
    - travel_coordinator: synthesizes both into a travel recommendation

    The ZenML step is synchronous; AG2's async conversation is wrapped
    with asyncio.run() to satisfy ZenML's sync execution model.

    Args:
        city: Destination city for travel planning.

    Returns:
        Dictionary with city, weather summary, attractions, and coordinator
        recommendation for the formatting step.
    """
    llm_config = LLMConfig(
        {"model": "gpt-4o-mini", "api_key": os.getenv("OPENAI_API_KEY")},
    )

    weather_agent = AssistantAgent(
        name="weather_agent",
        llm_config=llm_config,
        system_message=(
            "You are a weather specialist. "
            "Use the get_weather tool to look up conditions for the requested city. "
            "Report only the tool result, without embellishment."
        ),
    )

    attractions_agent = AssistantAgent(
        name="attractions_agent",
        llm_config=llm_config,
        system_message=(
            "You are a tourism expert. "
            "Use the get_attractions tool to find top attractions for the requested city. "
            "Report only the tool result, without embellishment."
        ),
    )

    coordinator = AssistantAgent(
        name="travel_coordinator",
        llm_config=llm_config,
        system_message=(
            "You are a travel coordinator. "
            "Once weather_agent and attractions_agent have reported, "
            "write a concise two-sentence travel recommendation that combines both. "
            "End your message with TERMINATE."
        ),
    )

    # AG2 requires both decorators: register_for_llm exposes the JSON schema to
    # the model; register_for_execution binds the Python callable that runs it.
    @weather_agent.register_for_llm(
        description="Get current weather for a city"
    )
    @weather_agent.register_for_execution()
    def weather_tool(
        city: Annotated[str, "The city to check weather for"],
    ) -> str:
        return get_weather(city)

    @attractions_agent.register_for_llm(
        description="Get top tourist attractions for a city"
    )
    @attractions_agent.register_for_execution()
    def attractions_tool(
        city: Annotated[str, "The city to find attractions in"],
    ) -> str:
        return get_attractions(city)

    group_chat = GroupChat(
        agents=[weather_agent, attractions_agent, coordinator],
        messages=[],
        max_round=8,
    )

    manager = GroupChatManager(
        groupchat=group_chat,
        llm_config=llm_config,
    )

    chat_result = asyncio.run(
        weather_agent.a_initiate_chat(
            manager,
            message=(
                f"Plan a trip to {city}. "
                "weather_agent: check the weather. "
                "attractions_agent: find the top attractions. "
                "travel_coordinator: give a final recommendation."
            ),
        )
    )

    # Walk the chat history in reverse to find the coordinator's recommendation,
    # stripping the TERMINATE sentinel before storing as an artifact.
    recommendation = f"Travel plan for {city} could not be generated."
    for msg in reversed(chat_result.chat_history):
        content = msg.get("content", "") or ""
        if content.strip() and content.strip() != "TERMINATE":
            recommendation = content.replace("TERMINATE", "").strip()
            break

    return {
        "city": city,
        "weather": get_weather(city),
        "attractions": get_attractions(city),
        "recommendation": recommendation,
        "status": "success",
    }


@step
def format_travel_plan(
    plan_data: Dict[str, Any],
) -> Annotated[str, "formatted_plan"]:
    """Format the AG2 agent results into a readable travel summary.

    Args:
        plan_data: Dictionary produced by run_ag2_agents.

    Returns:
        Formatted travel plan string.
    """
    city = plan_data["city"]
    status = plan_data["status"]

    if status == "error":
        return f"TRAVEL PLANNING ERROR FOR {city.upper()}\n{'=' * 50}\n\n{plan_data['recommendation']}"

    summary = f"""✈️ TRAVEL PLAN FOR {city.upper()}
{"=" * 50}

🌤️ Weather:
   {plan_data["weather"]}

🏛️ Top Attractions:
   {plan_data["attractions"]}

📋 Coordinator Recommendation:
   {plan_data["recommendation"]}

🤖 Generated by AG2 Multi-Agent System (GroupChat)
"""
    return summary.strip()


@pipeline(settings={"docker": docker_settings}, enable_cache=False)
def agent_pipeline(city: str = "Berlin") -> str:
    """ZenML pipeline that orchestrates the AG2 multi-agent travel system.

    Args:
        city: Destination city for travel planning. Defaults to Berlin.

    Returns:
        Formatted travel plan summary.
    """
    plan_data = run_ag2_agents(city=city)
    summary = format_travel_plan(plan_data)
    return summary


if __name__ == "__main__":
    print("🚀 Running AG2 travel pipeline...")
    run_result = agent_pipeline()
    print("Pipeline completed successfully!")
    print("Check the ZenML dashboard for detailed results and artifacts.")
