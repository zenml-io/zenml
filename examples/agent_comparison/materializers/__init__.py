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

__all__ = [
    "Prompt",
    "PromptMaterializer", 
    "visualize_prompt_data",
]