"""ZenML Pipeline for Autogen Multi-Agent Travel Assistant.

This pipeline encapsulates the autogen multi-agent system in a ZenML pipeline,
demonstrating how to integrate agent frameworks with ZenML for orchestration
and artifact management.
"""

import asyncio
from typing import Annotated, Any, Dict

from autogen_agent import TravelQuery, setup_runtime
from autogen_core import AgentId

from zenml import ExternalArtifact, pipeline, step


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


@pipeline
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
