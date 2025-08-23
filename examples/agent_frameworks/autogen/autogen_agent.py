"""
Multi-Agent Travel Assistant Example for PanAgent
=================================================

This example demonstrates how to use Microsoft Autogen with PanAgent
to create a multi-agent travel planning system. Each agent specializes
in a different aspect of travel planning.
"""

import asyncio
from typing import List

from autogen_core import (
    AgentId,
    AgentRuntime,
    MessageContext,
    RoutedAgent,
    SingleThreadedAgentRuntime,
    message_handler,
)
from pydantic import BaseModel

# Message Types - Using Pydantic for better serialization support
# ================================================================


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
    await WeatherAgent.register(runtime, "weather_agent", lambda: WeatherAgent())
    await AttractionAgent.register(
        runtime, "attraction_agent", lambda: AttractionAgent()
    )
    await TravelCoordinator.register(
        runtime, "coordinator", lambda: TravelCoordinator()
    )

    return runtime
