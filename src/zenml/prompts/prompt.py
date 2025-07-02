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
"""Enhanced Prompt abstraction for LLMOps workflows."""

import json
import re
import time
from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple, Union
from uuid import uuid4

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from types import FunctionType

    from zenml.config.source import Source

    HookSpecification = Union[str, Source, FunctionType, Callable[..., None]]


class Prompt(BaseModel):
    """Enhanced Prompt abstraction for LLMOps workflows.

    This is the main prompt abstraction in ZenML that can handle any prompt use case
    through configuration rather than inheritance. Like ZenML's Model abstraction,
    this single class can be configured for different prompt types, tasks, and scenarios.

    Examples:
        # Simple prompt
        prompt = Prompt(template="Hello {name}!")

        # Complex prompt with rich configuration
        prompt = Prompt(
            template="You are a {role} assistant...",
            prompt_type="conversation",
            task="question_answering",
            model_config={"temperature": 0.7, "max_tokens": 100},
            prompt_strategy="few_shot",
            examples=[{"input": "Q: ...", "output": "A: ..."}]
        )

        # System prompt with instructions
        prompt = Prompt(
            template="You are an expert {domain} analyst...",
            prompt_type="system",
            instructions="Always provide detailed analysis with sources"
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

    # Prompt classification and configuration
    prompt_type: Optional[str] = Field(
        default="user",
        description="Type of prompt: 'system', 'user', 'assistant', 'function', 'tool', etc.",
    )

    task: Optional[str] = Field(
        default=None,
        description="Task this prompt is designed for: 'qa', 'summarization', 'classification', 'generation', etc.",
    )

    domain: Optional[str] = Field(
        default=None,
        description="Domain/subject area: 'medical', 'legal', 'technical', 'creative', etc.",
    )

    # Prompt engineering configuration
    prompt_strategy: Optional[str] = Field(
        default="direct",
        description="Prompting strategy: 'direct', 'few_shot', 'chain_of_thought', 'tree_of_thought', etc.",
    )

    examples: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Example inputs/outputs for few-shot prompting",
    )

    instructions: Optional[str] = Field(
        default=None,
        description="Specific instructions or constraints for the prompt",
    )

    context_template: Optional[str] = Field(
        default=None,
        description="Template for context injection: 'Context: {context}\\n\\nQuery: {query}'",
    )

    # Model and performance configuration
    model_config_params: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Model-specific parameters: temperature, max_tokens, top_p, etc.",
    )

    target_models: Optional[List[str]] = Field(
        default=None,
        description="Models this prompt is optimized for: ['gpt-4', 'claude-3', 'llama-2']",
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

    # Performance and evaluation
    performance_metrics: Optional[Dict[str, float]] = Field(
        default=None,
        description="Tracked performance metrics: accuracy, bleu_score, response_time, etc.",
    )

    # Timestamps and lineage
    created_at: Optional[datetime] = Field(
        default=None, description="When the prompt was created"
    )

    updated_at: Optional[datetime] = Field(
        default=None, description="When the prompt was last updated"
    )

    # Parent/lineage tracking
    parent_prompt_id: Optional[str] = Field(
        default=None,
        description="ID of parent prompt if this is derived from another",
    )

    # Validation and constraints
    min_tokens: Optional[int] = Field(
        default=None, description="Minimum expected tokens in response"
    )

    max_tokens: Optional[int] = Field(
        default=None, description="Maximum expected tokens in response"
    )

    expected_format: Optional[str] = Field(
        default=None,
        description="Expected response format: 'json', 'xml', 'markdown', 'code', etc.",
    )

    # NEW: Enhanced fields for better prompt management
    prompt_id: Optional[str] = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for this prompt",
    )

    author: Optional[str] = Field(
        default=None,
        description="Author or creator of the prompt",
    )

    license: Optional[str] = Field(
        default=None,
        description="License for the prompt usage",
    )

    source_url: Optional[str] = Field(
        default=None,
        description="URL source of the prompt if imported",
    )

    language: Optional[str] = Field(
        default="en",
        description="Primary language of the prompt",
    )

    # Experimental features
    use_cache: Optional[bool] = Field(
        default=True,
        description="Whether to cache responses for this prompt",
    )

    safety_checks: Optional[List[str]] = Field(
        default=None,
        description="Safety checks to apply: ['content_filter', 'bias_check', 'toxicity']",
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
        if self.context_template:
            # Use custom context template
            context_formatted = self.context_template.format(
                context=context, **kwargs
            )
            return self.format(context=context_formatted, **kwargs)
        else:
            # Default context injection
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

    def with_context_template(self, context_template: str) -> "Prompt":
        """Set context injection template.

        Args:
            context_template: Template for context injection

        Returns:
            New Prompt instance with context template
        """
        return self.model_copy(update={"context_template": context_template})

    def with_model_config(self, **config: Any) -> "Prompt":
        """Add model configuration parameters.

        Args:
            **config: Model configuration parameters

        Returns:
            New Prompt instance with model config
        """
        new_config = {**(self.model_config_params or {}), **config}
        return self.model_copy(update={"model_config_params": new_config})

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

    def for_domain(self, domain: str, **domain_config: Any) -> "Prompt":
        """Configure prompt for specific domain.

        Args:
            domain: Domain/subject area
            **domain_config: Domain-specific configuration

        Returns:
            New Prompt instance configured for domain
        """
        updates = {"domain": domain}
        if domain_config:
            updates["metadata"] = {**(self.metadata or {}), **domain_config}
        return self.model_copy(update=updates)

    # ========================
    # Evaluation and Metrics
    # ========================

    def log_performance(self, metrics: Dict[str, float]) -> "Prompt":
        """Log performance metrics.

        Args:
            metrics: Performance metrics to log

        Returns:
            New Prompt instance with updated metrics
        """
        new_metrics = {**(self.performance_metrics or {}), **metrics}
        return self.model_copy(update={"performance_metrics": new_metrics})

    def get_performance(self, metric: str) -> Optional[float]:
        """Get specific performance metric.

        Args:
            metric: Metric name to retrieve

        Returns:
            Metric value or None if not found
        """
        return (self.performance_metrics or {}).get(metric)

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
            "domain": self.domain,
            "strategy": self.prompt_strategy,
            "has_examples": bool(self.examples),
            "example_count": len(self.examples) if self.examples else 0,
            "has_instructions": bool(self.instructions),
            "target_models": self.target_models,
            "version": self.version,
            "tags": self.tags,
            "author": self.author,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def is_compatible_with_model(self, model_name: str) -> bool:
        """Check if prompt is compatible with a specific model.

        Args:
            model_name: Name of the model to check compatibility

        Returns:
            True if compatible, False otherwise
        """
        if not self.target_models:
            return True  # Compatible with all models if not specified

        return any(
            model_name.lower() in target.lower()
            for target in self.target_models
        )

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
            
        # Context template adds complexity
        if self.context_template:
            score += 0.1
            
        # Strategy complexity
        complex_strategies = ["chain_of_thought", "tree_of_thought", "role_playing"]
        if self.prompt_strategy in complex_strategies:
            score += 0.1
            
        return min(score, 1.0)

    # ========================
    # Analytics and A/B Testing Integration
    # ========================

    def execute_with_analytics(
        self,
        model_function: Callable[..., str],
        track_analytics: bool = True,
        ab_test_id: Optional[str] = None,
        user_id: Optional[str] = None,
        **format_kwargs: Any
    ) -> Tuple[str, Optional["PromptExecution"]]:
        """Execute prompt with analytics tracking.

        Args:
            model_function: Function that takes formatted prompt and returns response
            track_analytics: Whether to track execution analytics
            ab_test_id: ID of A/B test if this execution is part of one
            user_id: User ID for A/B test assignment
            **format_kwargs: Variables for prompt formatting

        Returns:
            Tuple of (response, execution_record)
        """
        from .prompt_analytics import get_analytics_manager
        
        start_time = time.time()
        execution_record = None
        
        try:
            # Format the prompt
            formatted_prompt = self.format(**format_kwargs)
            
            # For A/B testing, we might need to select a different prompt variant
            if ab_test_id:
                analytics_manager = get_analytics_manager()
                variant = analytics_manager.select_variant(ab_test_id, user_id)
                # Note: In a full implementation, this would load the variant prompt
                # For now, we'll just track the variant in analytics
            
            # Execute the model function
            response = model_function(formatted_prompt)
            execution_time_ms = (time.time() - start_time) * 1000
            
            # Track analytics if enabled
            if track_analytics:
                analytics_manager = get_analytics_manager()
                execution_record = analytics_manager.log_execution(
                    prompt_id=self.prompt_id or "unknown",
                    input_variables=format_kwargs,
                    formatted_prompt=formatted_prompt,
                    response=response,
                    execution_time_ms=execution_time_ms,
                    prompt_version=self.version,
                    user_id=user_id,
                    ab_test_id=ab_test_id,
                    ab_test_group=variant if ab_test_id else None,
                    success=True
                )
            
            return response, execution_record
            
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            
            # Track failed execution
            if track_analytics:
                analytics_manager = get_analytics_manager()
                execution_record = analytics_manager.log_execution(
                    prompt_id=self.prompt_id or "unknown",
                    input_variables=format_kwargs,
                    formatted_prompt=self.format(**format_kwargs) if format_kwargs else self.template,
                    execution_time_ms=execution_time_ms,
                    success=False,
                    error_message=str(e),
                    user_id=user_id,
                    ab_test_id=ab_test_id
                )
            
            raise

    def get_analytics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Optional["PromptAnalytics"]:
        """Get analytics for this prompt.

        Args:
            start_date: Start of analysis period
            end_date: End of analysis period

        Returns:
            Analytics summary for this prompt
        """
        from .prompt_analytics import get_analytics_manager
        
        if not self.prompt_id:
            return None
            
        analytics_manager = get_analytics_manager()
        return analytics_manager.get_analytics(
            prompt_id=self.prompt_id,
            start_date=start_date,
            end_date=end_date
        )

    def create_ab_test(
        self,
        variant_prompts: Dict[str, "Prompt"],
        test_name: str,
        traffic_allocation: Optional[Dict[str, float]] = None,
        duration_days: int = 7,
        primary_metric: str = "quality_score"
    ) -> "ABTestConfiguration":
        """Create an A/B test with this prompt as the control.

        Args:
            variant_prompts: Dictionary of variant names to Prompt objects
            test_name: Name for the A/B test
            traffic_allocation: Traffic allocation per variant
            duration_days: How long to run the test
            primary_metric: Primary metric to optimize

        Returns:
            A/B test configuration
        """
        from .prompt_analytics import get_analytics_manager
        
        # Include this prompt as the control variant
        variants = {"control": self.prompt_id or "unknown"}
        variants.update({
            name: prompt.prompt_id or "unknown" 
            for name, prompt in variant_prompts.items()
        })
        
        analytics_manager = get_analytics_manager()
        return analytics_manager.create_ab_test(
            name=test_name,
            variants=variants,
            traffic_allocation=traffic_allocation,
            duration_days=duration_days,
            primary_metric=primary_metric
        )

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