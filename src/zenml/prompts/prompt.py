#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Simple prompt abstraction for LLMOps workflows in ZenML."""

import re
from typing import Any, Dict, List

from pydantic import BaseModel, Field


class Prompt(BaseModel):
    """Simple prompt artifact for ZenML pipelines.

    This is a lightweight prompt abstraction designed to work seamlessly
    with ZenML's artifact system. Complex operations are implemented as
    pipeline steps rather than built into this class.

    Prompts are versioned artifacts that can be tracked through pipeline
    runs and compared in the dashboard.

    Examples:
        # Simple prompt
        prompt = Prompt(template="Hello {name}!")
        formatted = prompt.format(name="Alice")

        # Prompt with default variables
        prompt = Prompt(
            template="Translate '{text}' to {language}",
            variables={"language": "French"}
        )
        formatted = prompt.format(text="Hello world")

        # System prompt
        prompt = Prompt(
            template="You are a helpful assistant.",
            prompt_type="system"
        )

        # Versioned prompt for tracking changes
        prompt = Prompt(
            template="Answer: {question}",
            version="2.0.0"  # Track iterations
        )
    """

    model_config = {"protected_namespaces": ()}

    # Core prompt content
    template: str = Field(..., description="The prompt template string")

    # Default variable values
    variables: Dict[str, Any] = Field(
        default_factory=dict,
        description="Default variable values for template substitution",
    )

    # Basic classification
    prompt_type: str = Field(
        default="user",
        description="Type of prompt: 'system', 'user', 'assistant'",
    )

    def format(self, **kwargs: Any) -> str:
        """Format the prompt template with provided variables.

        Args:
            **kwargs: Variables to substitute in the template.
                     These override any default variables.

        Returns:
            Formatted prompt string

        Raises:
            ValueError: If required variables are missing
        """
        # Merge default variables with provided kwargs
        format_vars = {**self.variables, **kwargs}

        try:
            return self.template.format(**format_vars)
        except KeyError as e:
            missing_var = str(e).strip("'\"")
            raise ValueError(
                f"Missing required variable '{missing_var}' for prompt formatting. "
                f"Available variables: {list(format_vars.keys())}"
            )

    def get_variable_names(self) -> List[str]:
        """Extract variable names from the template.

        Returns:
            List of variable names found in the template
        """
        pattern = r"\{([^}]+)\}"
        return list(set(re.findall(pattern, self.template)))

    def validate_variables(self) -> bool:
        """Check if all required variables are provided.

        Returns:
            True if all template variables have default values
        """
        template_vars = set(self.get_variable_names())
        provided_vars = set(self.variables.keys())
        return template_vars.issubset(provided_vars)

    def get_missing_variables(self) -> List[str]:
        """Get list of missing required variables.

        Returns:
            List of variable names that are required but not provided
        """
        template_vars = set(self.get_variable_names())
        provided_vars = set(self.variables.keys())
        return list(template_vars - provided_vars)

    def __str__(self) -> str:
        """String representation of the prompt.

        Returns:
            String representation of the prompt
        """
        var_count = len(self.variables)
        return (
            f"Prompt(type='{self.prompt_type}', "
            f"template_length={len(self.template)}, "
            f"variables={var_count})"
        )

    def __repr__(self) -> str:
        """Detailed representation of the prompt.

        Returns:
            Detailed representation of the prompt
        """
        template_preview = (
            self.template[:50] + "..."
            if len(self.template) > 50
            else self.template
        )
        return (
            f"Prompt(template='{template_preview}', "
            f"type='{self.prompt_type}', "
            f"variables={self.variables})"
        )
