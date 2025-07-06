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
"""Prompt abstraction for LLMOps workflows in ZenML."""

import json
import re
from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Union
from uuid import uuid4

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from types import FunctionType

    from zenml.config.source import Source

    HookSpecification = Union[str, Source, FunctionType, Callable[..., None]]


class Prompt(BaseModel):
    """Prompt abstraction for LLMOps workflows in ZenML.

    This is the main prompt abstraction in ZenML, designed as a simple yet
    flexible artifact that integrates seamlessly with ZenML pipelines.

    Examples:
        # Simple prompt
        prompt = Prompt(template="Hello {name}!")

        # Prompt with examples for few-shot learning
        prompt = Prompt(
            template="Answer the following question: {question}",
            prompt_type="user",
            task="question_answering",
            examples=[{"question": "What is 2+2?", "answer": "4"}]
        )

        # System prompt with instructions
        prompt = Prompt(
            template="You are a helpful assistant.",
            prompt_type="system",
            instructions="Always be concise and accurate"
        )
    """

    model_config = {"protected_namespaces": ()}

    # Core prompt content
    template: str = Field(..., description="The prompt template string")

    # Variable management
    variables: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Default variable values for template substitution",
    )

    # Prompt classification
    prompt_type: Optional[str] = Field(
        default="user",
        description="Type of prompt: 'system', 'user', 'assistant'",
    )

    task: Optional[str] = Field(
        default=None,
        description="Task this prompt is designed for: 'qa', 'summarization', 'classification', 'generation', etc.",
    )

    # Prompt engineering
    examples: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Example inputs/outputs for few-shot prompting",
    )

    instructions: Optional[str] = Field(
        default=None,
        description="Specific instructions or constraints for the prompt",
    )

    # Metadata and tracking
    description: Optional[str] = Field(
        default=None, description="Human-readable description of the prompt"
    )

    version: Optional[str] = Field(
        default=None,
        description="Semantic version of the prompt (e.g., '1.0.0', 'v2.1')",
    )

    tags: Optional[List[str]] = Field(
        default=None, description="Tags for categorization and filtering"
    )

    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional metadata for tracking and analysis",
    )

    # Timestamps
    created_at: Optional[datetime] = Field(
        default=None, description="When the prompt was created"
    )

    updated_at: Optional[datetime] = Field(
        default=None, description="When the prompt was last updated"
    )

    # Unique identifier
    prompt_id: Optional[str] = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for this prompt",
    )

    # ========================
    # Core Methods
    # ========================

    def format(self, **kwargs: Any) -> str:
        """Format the prompt template with provided variables.

        Args:
            **kwargs: Variables to substitute in the template

        Returns:
            Formatted prompt string

        Examples:
            prompt = Prompt(template="Hello {name}!", variables={"name": "World"})
            formatted = prompt.format()  # "Hello World!"
            formatted = prompt.format(name="Alice")  # "Hello Alice!"
        """
        # Merge default variables with provided kwargs
        format_vars = {}
        if self.variables:
            format_vars.update(self.variables)
        format_vars.update(kwargs)

        try:
            return self.template.format(**format_vars)
        except KeyError as e:
            missing_var = str(e).strip("'\"")
            raise ValueError(
                f"Missing required variable '{missing_var}' for prompt formatting. "
                f"Available variables: {list(format_vars.keys())}"
            )

    def format_with_context(self, context: str, **kwargs: Any) -> str:
        """Format prompt with context injection.

        Args:
            context: Context to inject into the prompt
            **kwargs: Additional variables for formatting

        Returns:
            Formatted prompt with context
        """
        # Inject context as a variable
        return self.format(context=context, **kwargs)

    def get_variable_names(self) -> List[str]:
        """Extract variable names from the template.

        Returns:
            List of variable names found in the template
        """
        pattern = r"\{([^}]+)\}"
        return list(set(re.findall(pattern, self.template)))

    def validate_variables(self) -> bool:
        """Validate that all required variables are provided.

        Returns:
            True if all variables are provided, False otherwise
        """
        template_vars = set(self.get_variable_names())
        provided_vars = set(self.variables.keys()) if self.variables else set()
        return template_vars.issubset(provided_vars)

    def get_missing_variables(self) -> List[str]:
        """Get list of missing required variables.

        Returns:
            List of variable names that are required but not provided
        """
        template_vars = set(self.get_variable_names())
        provided_vars = set(self.variables.keys()) if self.variables else set()
        return list(template_vars - provided_vars)

    # ========================
    # Prompt Engineering Methods
    # ========================

    def add_examples(self, examples: List[Dict[str, Any]]) -> "Prompt":
        """Add examples for few-shot prompting.

        Args:
            examples: List of example input/output pairs

        Returns:
            New Prompt instance with examples added
        """
        new_examples = (self.examples or []) + examples
        return self.model_copy(update={"examples": new_examples})

    def with_instructions(self, instructions: str) -> "Prompt":
        """Add or update instructions.

        Args:
            instructions: Instructions to add

        Returns:
            New Prompt instance with instructions
        """
        return self.model_copy(update={"instructions": instructions})

    def for_task(self, task: str, **task_config: Any) -> "Prompt":
        """Configure prompt for specific task.

        Args:
            task: Task type (qa, summarization, etc.)
            **task_config: Task-specific configuration

        Returns:
            New Prompt instance configured for task
        """
        updates = {"task": task}
        if task_config:
            updates["metadata"] = {**(self.metadata or {}), **task_config}
        return self.model_copy(update=updates)

    # ========================
    # Versioning and Lineage
    # ========================

    def create_variant(self, name: str = None, **changes: Any) -> "Prompt":
        """Create a variant of this prompt.

        Args:
            name: Name for the variant
            **changes: Changes to apply to create the variant

        Returns:
            New Prompt instance as a variant
        """
        updates = {
            "parent_prompt_id": self.prompt_id,
            "prompt_id": str(uuid4()),
            "created_at": datetime.now(),
            **changes,
        }

        if name:
            updates["description"] = name

        return self.model_copy(update=updates)

    def update_version(self, version: str) -> "Prompt":
        """Update prompt version.

        Args:
            version: New version string

        Returns:
            New Prompt instance with updated version
        """
        return self.model_copy(
            update={"version": version, "updated_at": datetime.now()}
        )

    # ========================
    # NEW: Enhanced Utility Methods
    # ========================

    def to_dict(self) -> Dict[str, Any]:
        """Convert prompt to dictionary representation.

        Returns:
            Dictionary representation of the prompt
        """
        return self.model_dump(exclude_none=True)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Prompt":
        """Create prompt from dictionary representation.

        Args:
            data: Dictionary representation of the prompt

        Returns:
            Prompt instance
        """
        return cls(**data)

    def to_json(self, **kwargs: Any) -> str:
        """Convert prompt to JSON string.

        Args:
            **kwargs: Additional arguments for json.dumps

        Returns:
            JSON string representation
        """
        return json.dumps(self.to_dict(), default=str, **kwargs)

    @classmethod
    def from_json(cls, json_str: str) -> "Prompt":
        """Create prompt from JSON string.

        Args:
            json_str: JSON string representation

        Returns:
            Prompt instance
        """
        return cls.from_dict(json.loads(json_str))

    def get_summary(self) -> Dict[str, Any]:
        """Get summary information about the prompt.

        Returns:
            Dictionary with summary information
        """
        return {
            "prompt_id": self.prompt_id,
            "template_length": len(self.template),
            "variable_count": len(self.variables) if self.variables else 0,
            "variable_names": self.get_variable_names(),
            "variables_complete": self.validate_variables(),
            "missing_variables": self.get_missing_variables(),
            "prompt_type": self.prompt_type,
            "task": self.task,
            "has_examples": bool(self.examples),
            "example_count": len(self.examples) if self.examples else 0,
            "has_instructions": bool(self.instructions),
            "version": self.version,
            "tags": self.tags,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def estimate_tokens(self, **format_vars: Any) -> Optional[int]:
        """Estimate token count for formatted prompt.

        Args:
            **format_vars: Variables for formatting

        Returns:
            Estimated token count or None if cannot estimate
        """
        try:
            formatted = self.format(**format_vars)
            # Simple estimation: ~4 characters per token
            return len(formatted) // 4
        except Exception:
            return None

    def get_complexity_score(self) -> float:
        """Calculate complexity score for the prompt.

        Returns:
            Complexity score from 0.0 to 1.0
        """
        score = 0.0

        # Template length contributes to complexity
        score += min(len(self.template) / 1000, 0.3)

        # Variable count
        var_count = len(self.variables) if self.variables else 0
        score += min(var_count / 10, 0.2)

        # Examples add complexity
        if self.examples:
            score += min(len(self.examples) / 5, 0.2)

        # Instructions add complexity
        if self.instructions:
            score += min(len(self.instructions) / 500, 0.1)

        return min(score, 1.0)

    def clone(self, **updates: Any) -> "Prompt":
        """Create a deep copy of the prompt with optional updates.

        Args:
            **updates: Updates to apply to the clone

        Returns:
            New Prompt instance as a clone
        """
        clone_data = self.to_dict()
        clone_data["prompt_id"] = str(uuid4())
        clone_data["created_at"] = datetime.now()
        clone_data.update(updates)
        return self.from_dict(clone_data)

    def __str__(self) -> str:
        """String representation of the prompt."""
        summary = self.get_summary()
        return (
            f"Prompt(id='{self.prompt_id[:8]}...', type='{self.prompt_type}', "
            f"task='{self.task}', variables={summary['variable_count']}, "
            f"length={summary['template_length']} chars)"
        )

    def __repr__(self) -> str:
        """Detailed representation of the prompt."""
        return (
            f"Prompt(id='{self.prompt_id}', template='{self.template[:50]}...', "
            f"type='{self.prompt_type}', task='{self.task}', "
            f"variables={self.variables})"
        )

    def __eq__(self, other: object) -> bool:
        """Check equality based on prompt_id."""
        if not isinstance(other, Prompt):
            return False
        return self.prompt_id == other.prompt_id

    def __hash__(self) -> int:
        """Hash based on prompt_id."""
        return hash(self.prompt_id)
