import os  # Added for env var lookup

from strands import Agent, tool
from strands.models.openai import OpenAIModel


@tool
def get_weather(city: str) -> str:
    """
    Very naive weather lookup that *always* returns a sunny forecast.

    Args:
        city: Name of the city.

    Returns:
        A short weather blurb.
    """
    return f"It\u2019s always sunny in {city}!"


# Initialize the OpenAI model, pulling the key from the environment rather than
# hard-coding credentials.
model = OpenAIModel(
    client_args={
        "api_key": os.getenv("OPENAI_API_KEY", ""),
    },
    model_id="gpt-5-nano",
    params={"temperature": 0.7},
)


# --------------------------------------------------------------------------- #
# Global agent                                                                #
# --------------------------------------------------------------------------- #
agent: Agent = Agent(
    model=model,
    tools=[get_weather],
    system_prompt="You are a helpful assistant that can check weather for cities.",
)

# NOTE: PanAgent discovers the `agent` variable at runtime; do **not**
# execute the agent from within this module.
