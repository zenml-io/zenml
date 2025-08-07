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
"""Prompt response artifact for capturing LLM outputs linked to prompts."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from zenml.metadata.metadata_types import MetadataType


class PromptResponse(BaseModel):
    """Artifact representing an LLM response generated from a prompt.

    This class captures the complete response from an LLM, including metadata
    about generation parameters, costs, and quality metrics. It's designed to
    be linked to the source Prompt artifact for full traceability.

    The PromptResponse enables tracking of:
    - Raw LLM responses and parsed structured outputs
    - Generation metadata (model, parameters, timestamps)
    - Cost and performance metrics
    - Quality scores and validation results
    - Links back to source prompts for provenance

    Examples:
        # Basic response capture
        response = PromptResponse(
            content="The capital of France is Paris.",
            prompt_id="prompt_abc123"
        )

        # Structured response with metadata
        response = PromptResponse(
            content='{"city": "Paris", "country": "France"}',
            parsed_output={"city": "Paris", "country": "France"},
            model_name="gpt-4",
            prompt_tokens=50,
            completion_tokens=20,
            total_cost=0.001,
            prompt_id="prompt_abc123"
        )

        # Response with quality metrics
        response = PromptResponse(
            content="Paris",
            quality_score=0.95,
            validation_passed=True,
            prompt_id="prompt_abc123"
        )
    """

    model_config = {"protected_namespaces": ()}

    # Response content
    content: str = Field(..., description="Raw text response from the LLM")

    parsed_output: Optional[Any] = Field(
        default=None,
        description="Structured output parsed from content (e.g., JSON, Pydantic model)",
    )

    # Generation metadata
    model_name: Optional[str] = Field(
        default=None,
        description="Name of the LLM model used for generation",
    )

    temperature: Optional[float] = Field(
        default=None,
        description="Temperature parameter used for generation",
    )

    max_tokens: Optional[int] = Field(
        default=None,
        description="Maximum tokens parameter used for generation",
    )

    # Usage and cost tracking
    prompt_tokens: Optional[int] = Field(
        default=None,
        description="Number of tokens in the input prompt",
    )

    completion_tokens: Optional[int] = Field(
        default=None,
        description="Number of tokens in the generated completion",
    )

    total_tokens: Optional[int] = Field(
        default=None,
        description="Total tokens used (prompt + completion)",
    )

    total_cost: Optional[float] = Field(
        default=None,
        description="Total cost in USD for this generation",
    )

    # Quality and validation
    quality_score: Optional[float] = Field(
        default=None,
        description="Quality score for the response (0.0 to 1.0)",
    )

    validation_passed: Optional[bool] = Field(
        default=None,
        description="Whether the response passed schema validation",
    )

    validation_errors: List[str] = Field(
        default_factory=list,
        description="List of validation error messages if validation failed",
    )

    # Provenance and linking
    prompt_id: Optional[str] = Field(
        default=None,
        description="ID of the source prompt artifact",
    )

    prompt_version: Optional[str] = Field(
        default=None,
        description="Version of the source prompt artifact",
    )

    parent_response_ids: List[str] = Field(
        default_factory=list,
        description="IDs of parent responses if this is part of a multi-turn conversation",
    )

    # Timestamps
    created_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when the response was generated",
    )

    response_time_ms: Optional[float] = Field(
        default=None,
        description="Response time in milliseconds",
    )

    # Additional metadata
    metadata: Dict[str, MetadataType] = Field(
        default_factory=dict,
        description="Additional metadata for the response",
    )

    def get_token_efficiency(self) -> Optional[float]:
        """Calculate token efficiency (completion tokens / total tokens).

        Returns:
            Token efficiency ratio or None if token counts unavailable
        """
        if self.completion_tokens is None or self.total_tokens is None:
            return None
        if self.total_tokens == 0:
            return 0.0
        return self.completion_tokens / self.total_tokens

    def get_cost_per_token(self) -> Optional[float]:
        """Calculate cost per token.

        Returns:
            Cost per token or None if cost/token data unavailable
        """
        if self.total_cost is None or self.total_tokens is None:
            return None
        if self.total_tokens == 0:
            return 0.0
        return self.total_cost / self.total_tokens

    def is_valid_response(self) -> bool:
        """Check if the response is considered valid.

        Returns:
            True if response has content and passed validation (if applicable)
        """
        has_content = bool(self.content and self.content.strip())
        passed_validation = self.validation_passed is not False
        return has_content and passed_validation

    def add_validation_error(self, error: str) -> None:
        """Add a validation error message.

        Args:
            error: Error message to add
        """
        if error not in self.validation_errors:
            self.validation_errors.append(error)
        self.validation_passed = False

    def link_to_prompt(
        self, prompt_id: str, prompt_version: Optional[str] = None
    ) -> None:
        """Link this response to a source prompt.

        Args:
            prompt_id: ID of the source prompt artifact
            prompt_version: Version of the source prompt artifact
        """
        self.prompt_id = prompt_id
        self.prompt_version = prompt_version

    def __str__(self) -> str:
        """String representation of the prompt response.

        Returns:
            String representation of the response
        """
        content_preview = (
            self.content[:100] + "..."
            if len(self.content) > 100
            else self.content
        )
        return (
            f"PromptResponse(model={self.model_name}, "
            f"tokens={self.total_tokens}, "
            f"cost=${self.total_cost or 0:.4f}, "
            f"content='{content_preview}')"
        )

    def __repr__(self) -> str:
        """Detailed representation of the prompt response.

        Returns:
            Detailed representation of the response
        """
        return (
            f"PromptResponse(content_length={len(self.content)}, "
            f"model='{self.model_name}', "
            f"tokens={self.total_tokens}, "
            f"cost=${self.total_cost or 0:.4f}, "
            f"quality={self.quality_score}, "
            f"valid={self.validation_passed})"
        )
