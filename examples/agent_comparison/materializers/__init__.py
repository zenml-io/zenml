"""Materializers package for the agent comparison example."""

from .prompt import Prompt
from .prompt_materializer import PromptMaterializer
from .prompt_visualizer import visualize_prompt_data

# Register the materializers with ZenML
from zenml.materializers.materializer_registry import materializer_registry

materializer_registry.register_and_overwrite_type(
    key=Prompt, 
    type_=PromptMaterializer
)

# Register BaseAgent materializer separately to avoid circular import
def register_agent_materializer() -> None:
    """Register the BaseAgent materializer to avoid circular imports."""
    from agents import BaseAgent
    from .agent_materializer import AgentMaterializer
    materializer_registry.register_and_overwrite_type(
        key=BaseAgent,
        type_=AgentMaterializer
    )

# Note: Agent materializer registration deferred to avoid circular import
# It will be registered when the pipeline imports materializers

__all__ = [
    "Prompt",
    "PromptMaterializer", 
    "visualize_prompt_data",
]