import datetime
from zoneinfo import ZoneInfo

from google.adk.agents import Agent


def get_weather(city: str) -> dict:
    """Retrieves the current weather report for a specified city."""
    # This is a mock implementation for demonstration purposes
    # In a real agent, you would integrate with a weather API
    return {
        "status": "success",
        "report": f"The weather in {city} is sunny with a temperature of 22°C.",
        "timestamp": datetime.datetime.now().isoformat(),
    }


def get_current_time(timezone: str = "UTC") -> dict:
    """Get the current time in the specified timezone."""
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
    model="gemini-1.5-flash-latest",
    description="Agent to answer questions about the weather in a city and provide current time.",
    instruction="You are a helpful agent who can answer user questions about the weather and current time. Use the available tools to provide accurate information.",
    tools=[get_weather, get_current_time],
)
