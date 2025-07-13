"""Prompt class for versioned prompt management in ZenML."""

import re
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class Prompt(BaseModel):
    """A versioned prompt with metadata for MLOps tracking."""

    name: str = Field(..., description="Name of the prompt")
    content: str = Field(..., description="The actual prompt content")
    version: str = Field(default="1.0.0", description="Version of the prompt")
    description: Optional[str] = Field(
        None, description="Description of the prompt's purpose"
    )
    variables: Dict[str, str] = Field(
        default_factory=dict,
        description="Variables that can be substituted in the prompt",
    )
    created_at: datetime = Field(
        default_factory=datetime.now, description="When the prompt was created"
    )
    author: Optional[str] = Field(None, description="Author of the prompt")
    tags: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata tags"
    )

    class Config:
        """Pydantic configuration."""

        arbitrary_types_allowed = True

    def format(self, **kwargs: Any) -> str:
        """Format the prompt with the provided variables.

        Args:
            **kwargs: Variables to substitute in the prompt

        Returns:
            Formatted prompt string
        """
        return self.content.format(**kwargs)

    def get_variable_names(self) -> list[str]:
        """Get list of variable names that can be substituted in the prompt.

        Returns:
            List of variable names found in the prompt content
        """
        return re.findall(r"\{(\w+)\}", self.content)

    def validate_variables(self, **kwargs: Any) -> bool:
        """Validate that all required variables are provided.

        Args:
            **kwargs: Variables to validate

        Returns:
            True if all required variables are provided
        """
        required_vars = set(self.get_variable_names())
        provided_vars = set(kwargs.keys())
        return required_vars.issubset(provided_vars)

    def to_dict(self) -> Dict[str, Any]:
        """Convert prompt to dictionary for serialization.

        Returns:
            Dict[str, Any]: Dictionary representation of the prompt
        """
        return {
            "name": self.name,
            "content": self.content,
            "version": self.version,
            "description": self.description,
            "variables": self.variables,
            "created_at": self.created_at.isoformat(),
            "author": self.author,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Prompt":
        """Create prompt from dictionary.

        Args:
            data: Dictionary containing prompt data

        Returns:
            Prompt: New Prompt instance created from dictionary
        """
        if isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        return cls(**data)

    def __str__(self) -> str:
        """String representation of the prompt.

        Returns:
            str: Human-readable string representation of the prompt
        """
        return f"Prompt(name='{self.name}', version='{self.version}', variables={self.get_variable_names()})"

    def __repr__(self) -> str:
        """Detailed representation of the prompt.

        Returns:
            str: Detailed string representation of the prompt
        """
        return f"Prompt(name='{self.name}', version='{self.version}', content_length={len(self.content)})"
