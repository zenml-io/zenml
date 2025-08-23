from my_tool import get_secret_data
from pydantic_ai import Agent

agent = Agent(
    "openai:gpt-4o-mini",
    system_prompt="Be concise, reply with one sentence.",
    tools=[get_secret_data],
)

# Test code removed - agent will be invoked via FastAPI
# result = agent.run_sync("What is the secret data?")
# print(result)
