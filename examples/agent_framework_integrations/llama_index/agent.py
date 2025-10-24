"""LlamaIndex agent example for PanAgent."""

from llama_index.core.agent import ReActAgent
from llama_index.core.tools import FunctionTool
from llama_index.llms.openai import OpenAI


def get_weather(city: str) -> str:
    """Get weather for a given city."""
    return f"It's always sunny in {city}!"


# Create the tool
weather_tool = FunctionTool.from_defaults(fn=get_weather)

# Create the agent
llm = OpenAI(model="gpt-4o-mini")
agent = ReActAgent(tools=[weather_tool], llm=llm, verbose=True)
