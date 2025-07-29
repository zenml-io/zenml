"""Steps for creating and managing prompt variants."""

from typing import Any, Dict, List

from zenml import step
from zenml.logger import get_logger
from zenml.prompts import Prompt

logger = get_logger(__name__)


@step
def create_prompt_variant(
    base_prompt: Prompt,
    variant_name: str,
    template: str = None,
    variables: Dict[str, Any] = None,
    prompt_type: str = None,
) -> Prompt:
    """Create a variant of a prompt with specified changes.

    Args:
        base_prompt: The base prompt to create a variant from
        variant_name: Name/description for the variant
        template: New template (if changing)
        variables: New variables (if changing)
        prompt_type: New prompt type (if changing)

    Returns:
        New Prompt instance as a variant
    """
    # Start with base prompt data
    variant_data = base_prompt.model_dump(exclude_none=True)

    # Apply changes
    if template:
        variant_data["template"] = template
    if variables:
        variant_data["variables"] = variables
    if prompt_type:
        variant_data["prompt_type"] = prompt_type

    # Create new prompt
    variant = Prompt(**variant_data)

    logger.info(f"Created variant '{variant_name}' from base prompt")
    return variant


@step
def create_multiple_variants(
    base_prompt: Prompt,
    variant_configs: List[Dict[str, Any]],
) -> List[Prompt]:
    """Create multiple variants of a prompt.

    Args:
        base_prompt: The base prompt to create variants from
        variant_configs: List of variant configurations

    Returns:
        List of prompt variants
    """
    variants = []

    for config in variant_configs:
        variant_name = config.pop("name", f"variant_{len(variants) + 1}")
        variant = create_prompt_variant(
            base_prompt=base_prompt, variant_name=variant_name, **config
        )
        variants.append(variant)

    logger.info(f"Created {len(variants)} prompt variants")
    return variants
