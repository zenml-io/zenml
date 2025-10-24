"""PydanticAI agent example for PanAgent."""

from pydantic_ai import Agent


def get_secret_data() -> str:
    """Return secret data."""
    return "something_secret"


agent = Agent(
    "openai:gpt-5-nano",
    system_prompt="Be concise, reply with one sentence.",
    deps_type=str,
)


@agent.tool
def secret_data_tool(ctx) -> str:
    """Get secret data from context."""
    return ctx.deps
