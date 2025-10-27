"""Qwen-Agent implementation with custom tools.

This module demonstrates how to create a Qwen-Agent with custom tools
for use in ZenML pipelines.
"""

import os

import json5
from qwen_agent.agents import Assistant
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

    def call(self, params: str, **kwargs) -> str:
        """Call the calculator tool."""
        data = json5.loads(params)
        operation = data.get("operation")
        a = float(data.get("a", 0))
        b = float(data.get("b", 0))

        if operation == "divide" and b == 0:
            return "Error: Division by zero"

        ops = {
            "add": lambda x, y: x + y,
            "subtract": lambda x, y: x - y,
            "multiply": lambda x, y: x * y,
            "divide": lambda x, y: x / y,
        }
        if operation not in ops:
            return f"Error: Unknown operation '{operation}'"

        result = ops[operation](a, b)
        return str(result)


# Initialize the LLM - uses OpenAI API by default
llm_cfg = {
    "model": "gpt-4o-mini",
    # Explicit OpenAI base URL ensures consistent behavior across environments
    "model_server": "https://api.openai.com/v1",
    "api_key": os.environ.get("OPENAI_API_KEY"),
    "generate_cfg": {
        # You can add generation params here, e.g., "top_p": 0.8
    },
}

system_instruction = (
    "You are a helpful math assistant. Use the 'calculator' tool to perform arithmetic. "
    "Respond with only the final numeric result unless the user requests detailed steps."
)

agent = Assistant(
    llm=llm_cfg,
    system_message=system_instruction,
    function_list=["calculator"],
)
