import os

from llama_index.core.agent.workflow import FunctionAgent
from llama_index.llms.openai import OpenAI


# Define simple tools
def get_weather(city: str) -> str:
    """Get weather for a given city."""
    return f"It's always sunny in {city}!"


def calculate_tip(bill_amount: float, tip_percentage: float = 15.0) -> str:
    """Calculate tip amount for a restaurant bill."""
    tip = bill_amount * (tip_percentage / 100)
    total = bill_amount + tip
    return f"Tip: ${tip:.2f}, Total: ${total:.2f}"


# Create the agent
agent = FunctionAgent(
    tools=[get_weather, calculate_tip],
    llm=OpenAI(model="gpt-5-nano", api_key=os.getenv("OPENAI_API_KEY")),
    system_prompt=(
        "You are a helpful assistant that can check weather for any city "
        "and calculate restaurant tips on demand."
    ),
)
