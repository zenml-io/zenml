"""Utility functions for prompt operations."""

import json
import os
from pathlib import Path
from typing import Any, Dict, List

from zenml.logger import get_logger
from zenml.prompts import Prompt

logger = get_logger(__name__)


def load_prompt_from_file(file_path: str) -> Prompt:
    """Load a prompt from a JSON file.

    Args:
        file_path: Path to the JSON file

    Returns:
        Loaded Prompt instance

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file format is invalid
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Prompt file not found: {file_path}")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return Prompt(**data)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format in {file_path}: {e}")
    except Exception as e:
        raise ValueError(f"Failed to load prompt from {file_path}: {e}")


def save_prompt_to_file(
    prompt: Prompt, file_path: str, indent: int = 2
) -> None:
    """Save a prompt to a JSON file.

    Args:
        prompt: Prompt to save
        file_path: Path where to save the file
        indent: JSON indentation level
    """
    # Ensure directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    prompt_dict = prompt.model_dump(exclude_none=True)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(prompt_dict, f, indent=indent, default=str)

    logger.info(f"Saved prompt to {file_path}")


def load_prompts_from_directory(directory_path: str) -> List[Prompt]:
    """Load all prompts from JSON files in a directory.

    Args:
        directory_path: Path to directory containing prompt files

    Returns:
        List of loaded Prompt instances
    """
    prompts = []
    directory = Path(directory_path)

    if not directory.exists():
        raise FileNotFoundError(f"Directory not found: {directory_path}")

    for file_path in directory.glob("*.json"):
        try:
            prompt = load_prompt_from_file(str(file_path))
            prompts.append(prompt)
            logger.info(f"Loaded prompt from {file_path}")
        except Exception as e:
            logger.warning(f"Failed to load prompt from {file_path}: {e}")

    return prompts


def format_prompt_with_examples(
    prompt: Prompt, examples: List[Dict[str, Any]], **variables: Any
) -> str:
    """Format a prompt with examples and variables.

    Args:
        prompt: The prompt to format
        examples: Examples to include in the prompt
        **variables: Variables for template substitution

    Returns:
        Formatted prompt string with examples
    """
    # Format examples
    examples_text = ""
    if examples:
        examples_text = "\n\nExamples:\n"
        for i, example in enumerate(examples, 1):
            examples_text += f"Example {i}:\n"
            for key, value in example.items():
                examples_text += f"  {key}: {value}\n"

    # Add examples to variables
    format_vars = {**variables, "examples": examples_text}

    # Format the prompt
    if "{examples}" in prompt.template:
        return prompt.format(**format_vars)
    else:
        # Append examples if not in template
        base_formatted = prompt.format(**variables)
        return base_formatted + examples_text


def create_prompt_from_template(
    template: str,
    variables: Dict[str, Any] = None,
    prompt_type: str = "user",
    **kwargs: Any,
) -> Prompt:
    """Create a prompt from a template string.

    Args:
        template: The prompt template
        variables: Default variables
        prompt_type: Type of prompt
        **kwargs: Additional prompt parameters

    Returns:
        New Prompt instance
    """
    return Prompt(
        template=template,
        variables=variables or {},
        prompt_type=prompt_type,
        **kwargs,
    )


def validate_prompt_template(template: str) -> Dict[str, Any]:
    """Validate a prompt template.

    Args:
        template: The template to validate

    Returns:
        Validation results
    """
    import re

    # Find all variables
    variables = re.findall(r"\{([^}]+)\}", template)

    # Check for issues
    issues = []

    # Check for unclosed braces
    if template.count("{") != template.count("}"):
        issues.append("Unmatched braces in template")

    # Check for empty variables
    if any(not var.strip() for var in variables):
        issues.append("Empty variable names found")

    # Check for duplicate variables
    if len(variables) != len(set(variables)):
        issues.append("Duplicate variable names found")

    return {
        "is_valid": len(issues) == 0,
        "issues": issues,
        "variables": list(set(variables)),
        "variable_count": len(set(variables)),
    }
