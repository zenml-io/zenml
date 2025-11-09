"""Comparison steps for the weather agent pipeline."""

from typing import Annotated

from zenml import step
from zenml.steps import get_step_context


@step
def compare_city_trends(analysis: str) -> Annotated[str, "city_comparison"]:
    """Return how the current city compares to the previous turn.

    Args:
        analysis: The analysis of the current city.

    Returns:
        A string comparing the current city to the previous city.
    """
    session_state = get_step_context().session_state
    history = session_state.get("history", [])
    if len(history) < 2:
        return "Not enough history to compare cities yet."

    current = history[-1]
    previous = history[-2]
    delta_temp = current["temperature"] - previous["temperature"]
    delta_humidity = current["humidity"] - previous["humidity"]
    delta_wind = current["wind_speed"] - previous["wind_speed"]

    return (
        f"Comparing {current['city']} to {previous['city']}:\n"
        f"• Temperature change: {delta_temp:+.1f}°C\n"
        f"• Humidity change: {delta_humidity:+.0f}%\n"
        f"• Wind speed change: {delta_wind:+.1f} km/h"
    )
