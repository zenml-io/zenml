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
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PromptType(str, Enum):
    """Enum for different types of prompts."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


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
            prompt_type=PromptType.SYSTEM
        )

        # Versioned prompt for tracking changes
        prompt = Prompt(
            template="Answer: {question}",
            version="2.0.0"  # Track iterations
        )

        # Prompt with structured output schema
        from pydantic import BaseModel
        class InvoiceData(BaseModel):
            total: float
            vendor: str
            date: str

        prompt = Prompt(
            template="Extract invoice data: {document_text}",
            output_schema=InvoiceData,
            examples=[
                {
                    "input": {"document_text": "Invoice from ACME Corp. Total: $100"},
                    "output": {"total": 100.0, "vendor": "ACME Corp", "date": "2024-01-01"}
                }
            ]
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
    prompt_type: PromptType = Field(
        default=PromptType.USER,
        description="Type of prompt: system, user, or assistant",
    )

    # Enhanced fields for structured output and examples
    output_schema: Optional[Dict[str, Any]] = Field(
        default=None,
        description="JSON schema dict defining expected LLM response structure",
    )

    examples: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of input-output examples to guide LLM behavior and improve response quality",
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

    def get_schema_dict(self) -> Optional[Dict[str, Any]]:
        """Get the output schema as a dictionary.

        Returns:
            Schema dictionary or None if no schema is defined
        """
        return self.output_schema

    def validate_example(self, example: Dict[str, Any]) -> bool:
        """Validate that an example has the correct structure.

        Args:
            example: Example to validate

        Returns:
            True if example is valid, False otherwise
        """
        if not isinstance(example, dict):
            return False

        required_keys = {"input", "output"}
        return required_keys.issubset(example.keys())

    def add_example(
        self, input_vars: Dict[str, Any], expected_output: Any
    ) -> None:
        """Add a new example to the prompt.

        Args:
            input_vars: Input variables for the example
            expected_output: Expected output for the example
        """
        example = {"input": input_vars, "output": expected_output}
        if self.validate_example(example):
            self.examples.append(example)
        else:
            raise ValueError(
                "Invalid example format. Must have 'input' and 'output' keys."
            )

    def format_with_examples(self, **kwargs: Any) -> str:
        """Format the prompt template with examples included.

        Args:
            **kwargs: Variables to substitute in the template

        Returns:
            Formatted prompt string with examples
        """
        formatted_prompt = self.format(**kwargs)

        if not self.examples:
            return formatted_prompt

        examples_text = "\n\nExamples:\n"
        for i, example in enumerate(self.examples, 1):
            examples_text += f"\nExample {i}:\n"
            examples_text += f"Input: {example['input']}\n"
            examples_text += f"Output: {example['output']}\n"

        return formatted_prompt + examples_text

    def diff(
        self, other: "Prompt", name1: str = "Current", name2: str = "Other"
    ) -> Dict[str, Any]:
        """Compare this prompt with another prompt using GitHub-style diff.

        Args:
            other: The other prompt to compare with
            name1: Name for this prompt in the diff (default: "Current")
            name2: Name for the other prompt in the diff (default: "Other")

        Returns:
            Comprehensive diff analysis including template, variables, and metadata changes

        Example:
            ```python
            prompt1 = Prompt(template="Hello {name}")
            prompt2 = Prompt(template="Hi {name}!")

            diff_result = prompt1.diff(prompt2)
            print(diff_result["template_diff"]["unified_diff"])
            ```
        """
        from zenml.prompts.diff_utils import compare_prompts

        return compare_prompts(self, other, name1, name2)

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
