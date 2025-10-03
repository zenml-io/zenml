from pydantic_ai import Agent


def get_secret_data() -> str:
    return "something_secret"


agent = Agent(
    "openai:gpt-5-nano",
    system_prompt="Be concise, reply with one sentence.",
    tools=[get_secret_data],
)

# Test code removed - agent will be invoked via FastAPI
# result = agent.run_sync("What is the secret data?")
# print(result)
