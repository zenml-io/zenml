"""Semantic Kernel agent example for PanAgent.

Stage 1 Semantic Kernel example for PanAgent.

Discovery contract:
    * Global ``kernel`` variable (Semantic Kernel ``Kernel`` instance)
    * Optional ``create_kernel()`` factory lets adapters rebuild kernels
      with alternative services or settings.

Safe-import rule:
    No network calls or async work is executed at module import time.
"""

from __future__ import annotations

import asyncio
from typing import Annotated

from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.function_choice_behavior import (
    FunctionChoiceBehavior,
)
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
from semantic_kernel.connectors.ai.open_ai.prompt_execution_settings.open_ai_prompt_execution_settings import (
    OpenAIChatPromptExecutionSettings,
)
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.functions import kernel_function


# --------------------------------------------------------------------------- #
# Example native plugin                                                       #
# --------------------------------------------------------------------------- #
class WeatherPlugin:
    """A very small native plugin with one callable function."""

    @kernel_function(
        name="get_weather",
        description="Return a short weather report for the specified city.",
    )
    def get_weather(
        self,
        city: Annotated[str, "The city to get weather for"],
    ) -> str:
        """Pretend to fetch weather information.

        In real scenarios you might call an external API here.
        """
        return f"It's always sunny in {city}!"


# --------------------------------------------------------------------------- #
# Kernel factory                                                              #
# --------------------------------------------------------------------------- #
def create_kernel(
    *,
    model_id: str = "gpt-5-nano",
    service_id: str = "openai-chat",
) -> Kernel:
    """Build and return a ready-to-use Semantic Kernel instance.

    Args:
        model_id:
            OpenAI model to register (default: ``gpt-5-nano``).
        service_id:
            Service identifier used when registering the chat completion service.
    """
    kernel = Kernel()

    # Register OpenAI chat completion service (no network call at import time)
    kernel.add_service(
        OpenAIChatCompletion(ai_model_id=model_id, service_id=service_id)
    )

    # Register our Weather plugin
    kernel.add_plugin(WeatherPlugin(), plugin_name="Weather")

    return kernel


# --------------------------------------------------------------------------- #
# PanAgent discovery variable                                                 #
# --------------------------------------------------------------------------- #
# IMPORTANT: PanAgent looks for this global name when framework == "semantic-kernel"
kernel: Kernel = create_kernel()

__all__ = ["kernel", "create_kernel", "WeatherPlugin"]


# --------------------------------------------------------------------------- #
# Interactive demo (run only when executed directly)                          #
# --------------------------------------------------------------------------- #
async def _demo() -> None:  # pragma: no cover – illustrative only
    """Simple interactive test of function-calling behavior."""
    chat_service = kernel.get_service(OpenAIChatCompletion)  # type: ignore[arg-type]

    # Chat history with a user request that triggers function calling
    history = ChatHistory()
    history.add_user_message("What is the weather in Paris?")

    # Enable automatic function choice so the model may call our plugin
    settings = OpenAIChatPromptExecutionSettings()
    settings.function_choice_behavior = FunctionChoiceBehavior.Auto()

    response = await chat_service.get_chat_message_content(  # type: ignore[attr-defined]
        chat_history=history,
        settings=settings,
        kernel=kernel,
    )
    print(f"Assistant: {response.content}")  # noqa: T201 – demo print


if __name__ == "__main__":  # pragma: no cover
    # Run the async demo when the script is executed directly
    asyncio.run(_demo())
