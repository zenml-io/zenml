"""Lagent implementation with ReAct agent and custom actions.

This module demonstrates how to create a lagent ReAct agent with custom actions
for use in ZenML pipelines.
"""

from lagent.actions import ActionExecutor, PythonInterpreter
from lagent.agents import ReAct
from lagent.llms import GPTAPI


class WeatherAction:
    """A simple weather lookup action for demonstration."""

    def __init__(self):
        self.name = "get_weather"
        self.description = "Get the current weather for a given city"

    def __call__(self, city: str) -> str:
        """Get weather information for a city."""
        # This is a mock implementation - in production you'd call a real API
        weather_data = {
            "beijing": "Sunny, 22°C",
            "shanghai": "Cloudy, 18°C",
            "shenzhen": "Rainy, 25°C",
            "hangzhou": "Partly cloudy, 20°C",
        }
        city_lower = city.lower()
        if city_lower in weather_data:
            return f"Weather in {city}: {weather_data[city_lower]}"
        return f"Weather data not available for {city}"


# Initialize the LLM - using OpenAI API
# You can also use other models like InternLM2
llm = GPTAPI(
    model_type="gpt-4o-mini",
    key="",  # Will be read from OPENAI_API_KEY environment variable
)

# Create Python interpreter action
python_interpreter = PythonInterpreter()

# Create action executor with available actions
action_executor = ActionExecutor(
    actions=[python_interpreter],
)

# Create the ReAct agent
agent = ReAct(
    llm=llm,
    action_executor=action_executor,
    max_turn=5,  # Maximum number of reasoning steps
)
