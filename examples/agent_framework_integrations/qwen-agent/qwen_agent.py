"""Qwen-Agent implementation with custom tools.

This module demonstrates how to create a Qwen-Agent with custom tools
for use in ZenML pipelines.
"""

from qwen_agent.agents import Agent
from qwen_agent.llm import get_chat_model
from qwen_agent.tools.base import BaseTool, register_tool


@register_tool("calculator")
class Calculator(BaseTool):
    """A simple calculator tool for basic arithmetic operations."""

    name = "calculator"
    description = "Performs basic arithmetic operations (add, subtract, multiply, divide)"
    parameters = [
        {
            "name": "operation",
            "type": "string",
            "description": "The operation to perform: 'add', 'subtract', 'multiply', or 'divide'",
            "required": True,
        },
        {
            "name": "a",
            "type": "number",
            "description": "The first number",
            "required": True,
        },
        {
            "name": "b",
            "type": "number",
            "description": "The second number",
            "required": True,
        },
    ]

    def call(self, params: dict, **kwargs) -> str:
        """Execute the calculator operation."""
        operation = params.get("operation")
        a = float(params.get("a", 0))
        b = float(params.get("b", 0))

        operations = {
            "add": lambda x, y: x + y,
            "subtract": lambda x, y: x - y,
            "multiply": lambda x, y: x * y,
            "divide": lambda x, y: x / y
            if y != 0
            else "Error: Division by zero",
        }

        if operation not in operations:
            return f"Error: Unknown operation '{operation}'"

        result = operations[operation](a, b)
        return f"Result: {result}"


# Initialize the LLM - uses OpenAI API by default
# You can also use DashScope or other compatible endpoints
llm = get_chat_model(
    {
        "model": "gpt-4o-mini",  # Using OpenAI model
        "model_server": "openai",  # Or "dashscope" for Qwen models
    }
)

# Create the agent with the calculator tool
agent = Agent(
    llm=llm,
    name="MathAssistant",
    description="An agent that can perform mathematical calculations",
    function_list=["calculator"],
)
