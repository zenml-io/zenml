"""OpenAI Agents SDK example for PanAgent."""

from openai import OpenAI

# Create client
client = OpenAI()


def get_weather(city: str) -> str:
    """Get weather for a given city."""
    return f"It's always sunny in {city}!"


# Define the agent
agent_config = {
    "model": "gpt-5-nano",
    "tools": [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get weather for a given city",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {
                            "type": "string",
                            "description": "The city name",
                        }
                    },
                    "required": ["city"],
                },
            },
        }
    ],
}
