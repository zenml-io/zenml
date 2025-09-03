"""ZenML Pipeline for Autogen Multi-Agent Travel Assistant.

This pipeline encapsulates the autogen multi-agent system in a ZenML pipeline,
demonstrating how to integrate agent frameworks with ZenML for orchestration
and artifact management.
"""

import asyncio
import os
from typing import Annotated, Any, Dict, List

from autogen_core import (
    AgentId,
    AgentRuntime,
    MessageContext,
    RoutedAgent,
    SingleThreadedAgentRuntime,
    message_handler,
)
from pydantic import BaseModel

from zenml import ExternalArtifact, pipeline, step
from zenml.config import DockerSettings, PythonPackageInstaller

docker_settings = DockerSettings(
    python_package_installer=PythonPackageInstaller.UV,
    requirements="requirements.txt",  # relative to the pipeline directory
    environment={
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
    },
)


class TravelQuery(BaseModel):
    """User wants to plan a trip"""

    destination: str
    days: int


class WeatherInfo(BaseModel):
    """Weather information for a destination"""

    destination: str
    forecast: str
    temperature: str


class AttractionInfo(BaseModel):
    """Tourist attractions for a destination"""

    destination: str
    attractions: List[str]


class TravelPlan(BaseModel):
    """Complete travel plan combining all information"""

    destination: str
    days: int
    weather: WeatherInfo
    attractions: AttractionInfo


# Specialized Agents - Each one is an expert in their field
# ==========================================================


class WeatherAgent(RoutedAgent):
    """Expert in weather information"""

    def __init__(self):
        super().__init__("Weather Specialist")

    @message_handler
    async def check_weather(
        self, message: TravelQuery, ctx: MessageContext
    ) -> WeatherInfo:
        """Get weather for the destination"""
        # Simulate weather API call
        weather_data = {
            "Paris": ("Partly cloudy with chance of rain", "15°C"),
            "Tokyo": ("Clear and sunny", "22°C"),
            "New York": ("Cloudy", "18°C"),
        }

        forecast, temp = weather_data.get(
            message.destination, ("Variable conditions", "20°C")
        )

        print(
            f"🌤️  WeatherAgent: Checking weather for {message.destination}..."
        )
        await asyncio.sleep(0.5)  # Simulate API delay

        return WeatherInfo(
            destination=message.destination,
            forecast=forecast,
            temperature=temp,
        )


class AttractionAgent(RoutedAgent):
    """Expert in tourist attractions"""

    def __init__(self):
        super().__init__("Tourism Specialist")

    @message_handler
    async def find_attractions(
        self, message: TravelQuery, ctx: MessageContext
    ) -> AttractionInfo:
        """Find top attractions for the destination"""
        # Simulate attraction database
        attractions_db = {
            "Paris": [
                "Eiffel Tower",
                "Louvre Museum",
                "Notre-Dame",
                "Champs-Élysées",
            ],
            "Tokyo": [
                "Tokyo Tower",
                "Senso-ji Temple",
                "Meiji Shrine",
                "Shibuya Crossing",
            ],
            "New York": [
                "Statue of Liberty",
                "Central Park",
                "Times Square",
                "Empire State Building",
            ],
        }

        attractions = attractions_db.get(
            message.destination,
            ["City Center", "Local Markets", "Historic District"],
        )

        print(
            f"🏛️  AttractionAgent: Finding attractions in {message.destination}..."
        )
        await asyncio.sleep(0.7)  # Simulate database query

        return AttractionInfo(
            destination=message.destination,
            attractions=attractions[:3],  # Top 3 attractions
        )


class TravelCoordinator(RoutedAgent):
    """Coordinates between specialists to create a travel plan and returns it."""

    def __init__(self):
        super().__init__("Travel Coordinator")

    @message_handler
    async def coordinate_travel_plan(
        self, message: TravelQuery, _
    ) -> TravelPlan:
        """
        Receives a query, fans out to specialist agents, gathers results,
        and returns a complete travel plan. This is the main entrypoint
        for an external request.
        """
        print(f"📋 Coordinator: Planning trip to {message.destination}")

        # Send requests to specialists concurrently
        weather_task = self.send_message(
            message, AgentId("weather_agent", "default")
        )
        attraction_task = self.send_message(
            message, AgentId("attraction_agent", "default")
        )

        # Await the results
        weather_info, attraction_info = await asyncio.gather(
            weather_task, attraction_task
        )

        # Assemble the final plan
        travel_plan = TravelPlan(
            destination=message.destination,
            days=message.days,
            weather=weather_info,
            attractions=attraction_info,
        )

        print(
            f"✅ Coordinator: Complete travel plan created for {message.destination}"
        )
        return travel_plan


async def setup_runtime() -> AgentRuntime:
    """PanAgent entrypoint to configure and return the Autogen runtime."""
    runtime = SingleThreadedAgentRuntime()

    # Register all the agents that form the ensemble
    await WeatherAgent.register(
        runtime, "weather_agent", lambda: WeatherAgent()
    )
    await AttractionAgent.register(
        runtime, "attraction_agent", lambda: AttractionAgent()
    )
    await TravelCoordinator.register(
        runtime, "coordinator", lambda: TravelCoordinator()
    )

    return runtime


@step
def run_autogen_agents(
    query: str,
) -> Annotated[Dict[str, Any], "agent_results"]:
    """Execute the autogen multi-agent system and return results."""
    # Parse destination and days from query string
    # Format: "Plan a X-day trip to DESTINATION"
    parts = query.split(" to ")
    destination = parts[1] if len(parts) > 1 else "Unknown"
    days_part = [w for w in query.split() if w.endswith("-day")][0]
    days = int(days_part.replace("-day", ""))

    # Create TravelQuery for the agents
    travel_query = TravelQuery(destination=destination, days=days)

    async def _run_agents():
        # Setup the autogen runtime
        runtime = await setup_runtime()

        # Start the runtime
        runtime.start()

        try:
            # Send the query to the coordinator agent
            result = await runtime.send_message(
                travel_query, AgentId("coordinator", "default")
            )
            return result

        finally:
            # Always stop the runtime
            await runtime.stop()

    # Run the async function
    travel_plan = asyncio.run(_run_agents())

    # Convert to dict for ZenML artifact storage
    return {
        "destination": travel_plan.destination,
        "days": travel_plan.days,
        "weather": {
            "destination": travel_plan.weather.destination,
            "forecast": travel_plan.weather.forecast,
            "temperature": travel_plan.weather.temperature,
        },
        "attractions": {
            "destination": travel_plan.attractions.destination,
            "attractions": travel_plan.attractions.attractions,
        },
    }


@step
def format_travel_plan(
    plan_data: Dict[str, Any],
) -> Annotated[str, "formatted_plan"]:
    """Format the travel plan into a readable summary."""
    weather = plan_data["weather"]
    attractions = plan_data["attractions"]

    summary = f"""🏖️ TRAVEL PLAN FOR {plan_data["destination"].upper()}
{"=" * 50}

📅 Duration: {plan_data["days"]} days

🌤️ Weather Forecast:
   • Condition: {weather["forecast"]}
   • Temperature: {weather["temperature"]}

🏛️ Top Attractions:
"""

    for i, attraction in enumerate(attractions["attractions"], 1):
        summary += f"   {i}. {attraction}\n"

    return summary.strip()


@pipeline(settings={"docker": docker_settings}, enable_cache=False)
def autogen_travel_pipeline() -> str:
    """ZenML pipeline that orchestrates the autogen multi-agent travel system.

    Returns:
        Formatted travel plan summary
    """
    # External artifact for travel query
    travel_query = ExternalArtifact(value="Plan a 4-day trip to Paris")

    # Run the autogen agents
    plan_data = run_autogen_agents(travel_query)

    # Format the results
    summary = format_travel_plan(plan_data)

    return summary


if __name__ == "__main__":
    print("🚀 Running autogen travel pipeline...")
    run_result = autogen_travel_pipeline()
    print("Pipeline completed successfully!")
    print("Check the ZenML dashboard for detailed results and artifacts.")
