"""Models for comprehensive prompt management."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field

from zenml.models.v2.base.base import (
    BaseRequest,
    BaseResponse,
    BaseResponseBody,
    BaseResponseMetadata,
    BaseResponseResources,
    BaseUpdate,
)
from zenml.models.v2.base.scoped import (
    ProjectScopedFilter,
    ProjectScopedRequest,
    ProjectScopedResponse,
    ProjectScopedResponseBody,
    ProjectScopedResponseMetadata,
    ProjectScopedResponseResources,
    TaggableFilter,
)


class PromptStatus(str, Enum):
    """Status of a prompt."""

    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class ExperimentStatus(str, Enum):
    """Status of a prompt experiment."""

    DRAFT = "draft"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class EvaluationType(str, Enum):
    """Type of prompt evaluation."""

    LLM_JUDGE = "llm_judge"
    HUMAN = "human"
    CUSTOM = "custom"
    AUTOMATED = "automated"


class DeploymentEnvironment(str, Enum):
    """Deployment environment for prompts."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


# ------------------ Enhanced Prompt Template Models ------------------


class PromptTemplateRequest(ProjectScopedRequest):
    """Request model for creating/updating prompt templates."""

    name: str = Field(..., description="Name of the prompt template")
    content: str = Field(..., description="The prompt template content")
    description: Optional[str] = Field(None, description="Description of the prompt")
    category: Optional[str] = Field(None, description="Category for organization")
    variables: Optional[List[str]] = Field(
        default_factory=list, description="List of variable names in the template"
    )
    tags: Optional[List[str]] = Field(
        default_factory=list, description="Tags for categorization"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional metadata"
    )
    status: PromptStatus = Field(default=PromptStatus.DRAFT, description="Prompt status")


class PromptTemplateUpdate(BaseUpdate):
    """Model for updating prompt templates."""

    name: Optional[str] = None
    content: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    variables: Optional[List[str]] = None
    status: Optional[PromptStatus] = None
    add_tags: Optional[List[str]] = None
    remove_tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class PromptTemplateResponseBody(ProjectScopedResponseBody):
    """Response body for prompt templates."""

    name: str = Field(..., description="Name of the prompt template")
    content: str = Field(..., description="The prompt template content")
    description: Optional[str] = Field(None, description="Description of the prompt")
    category: Optional[str] = Field(None, description="Category for organization")
    variables: List[str] = Field(
        default_factory=list, description="List of variable names in the template"
    )
    status: PromptStatus = Field(description="Prompt status")
    version_count: int = Field(default=0, description="Number of versions")
    latest_version: Optional[str] = Field(None, description="Latest version identifier")


class PromptTemplateResponseMetadata(ProjectScopedResponseMetadata):
    """Response metadata for prompt templates."""

    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )
    usage_stats: Optional[Dict[str, Any]] = Field(
        None, description="Usage statistics"
    )
    performance_metrics: Optional[Dict[str, Any]] = Field(
        None, description="Performance metrics"
    )


class PromptTemplateResponseResources(ProjectScopedResponseResources):
    """Response resources for prompt templates."""

    tags: List[str] = Field(default_factory=list, description="Associated tags")


class PromptTemplateResponse(
    ProjectScopedResponse[
        PromptTemplateResponseBody,
        PromptTemplateResponseMetadata,
        PromptTemplateResponseResources,
    ]
):
    """Response model for prompt templates."""

    @property
    def name(self) -> str:
        """Get prompt template name."""
        return self.get_body().name

    @property
    def content(self) -> str:
        """Get prompt template content."""
        return self.get_body().content

    @property
    def status(self) -> PromptStatus:
        """Get prompt template status."""
        return self.get_body().status

    @property
    def tags(self) -> List[str]:
        """Get prompt template tags."""
        return self.get_resources().tags


class PromptTemplateFilter(ProjectScopedFilter, TaggableFilter):
    """Filter model for prompt templates."""

    name: Optional[str] = Field(None, description="Filter by name")
    content: Optional[str] = Field(None, description="Filter by content")
    category: Optional[str] = Field(None, description="Filter by category")
    status: Optional[PromptStatus] = Field(None, description="Filter by status")


# ------------------ Prompt Experiment Models ------------------


class PromptVariant(BaseModel):
    """A variant in a prompt experiment."""

    name: str = Field(..., description="Name of the variant")
    prompt_template_id: UUID = Field(..., description="ID of the prompt template")
    prompt_version: Optional[str] = Field(None, description="Specific version")
    variables: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Variable values for this variant"
    )
    weight: float = Field(default=1.0, description="Traffic weight for A/B testing")


class PromptExperimentRequest(ProjectScopedRequest):
    """Request model for prompt experiments."""

    name: str = Field(..., description="Name of the experiment")
    description: Optional[str] = Field(None, description="Description")
    variants: List[PromptVariant] = Field(
        ..., description="List of prompt variants to test"
    )
    evaluation_criteria: List[str] = Field(
        default_factory=list, description="Criteria for evaluation"
    )
    test_dataset: Optional[str] = Field(None, description="Test dataset identifier")
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional metadata"
    )


class PromptExperimentUpdate(BaseUpdate):
    """Model for updating prompt experiments."""

    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[ExperimentStatus] = None
    variants: Optional[List[PromptVariant]] = None
    evaluation_criteria: Optional[List[str]] = None
    results: Optional[Dict[str, Any]] = None


class PromptExperimentResponseBody(ProjectScopedResponseBody):
    """Response body for prompt experiments."""

    name: str = Field(..., description="Name of the experiment")
    description: Optional[str] = Field(None, description="Description")
    status: ExperimentStatus = Field(description="Experiment status")
    variants: List[PromptVariant] = Field(description="Experiment variants")
    evaluation_criteria: List[str] = Field(description="Evaluation criteria")
    test_dataset: Optional[str] = Field(None, description="Test dataset")
    results: Optional[Dict[str, Any]] = Field(None, description="Experiment results")


class PromptExperimentResponseMetadata(ProjectScopedResponseMetadata):
    """Response metadata for prompt experiments."""

    metadata: Dict[str, Any] = Field(default_factory=dict)
    metrics: Optional[Dict[str, Any]] = Field(None, description="Performance metrics")


class PromptExperimentResponseResources(ProjectScopedResponseResources):
    """Response resources for prompt experiments."""

    pass


class PromptExperimentResponse(
    ProjectScopedResponse[
        PromptExperimentResponseBody,
        PromptExperimentResponseMetadata,
        PromptExperimentResponseResources,
    ]
):
    """Response model for prompt experiments."""

    @property
    def name(self) -> str:
        """Get experiment name."""
        return self.get_body().name

    @property
    def status(self) -> ExperimentStatus:
        """Get experiment status."""
        return self.get_body().status

    @property
    def variants(self) -> List[PromptVariant]:
        """Get experiment variants."""
        return self.get_body().variants


# ------------------ Prompt Evaluation Models ------------------


class PromptEvaluationRequest(ProjectScopedRequest):
    """Request model for prompt evaluations."""

    prompt_template_id: UUID = Field(..., description="ID of prompt template")
    prompt_version: Optional[str] = Field(None, description="Specific version")
    evaluation_type: EvaluationType = Field(..., description="Type of evaluation")
    evaluator_config: Dict[str, Any] = Field(
        default_factory=dict, description="Evaluator configuration"
    )
    test_cases: List[Dict[str, Any]] = Field(
        default_factory=list, description="Test cases for evaluation"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional metadata"
    )


class PromptEvaluationUpdate(BaseUpdate):
    """Model for updating prompt evaluations."""

    score: Optional[float] = None
    feedback: Optional[str] = None
    results: Optional[Dict[str, Any]] = None
    status: Optional[str] = None


class PromptEvaluationResponseBody(ProjectScopedResponseBody):
    """Response body for prompt evaluations."""

    prompt_template_id: UUID = Field(description="ID of evaluated prompt template")
    prompt_version: Optional[str] = Field(None, description="Evaluated version")
    evaluation_type: EvaluationType = Field(description="Type of evaluation")
    score: Optional[float] = Field(None, description="Evaluation score")
    feedback: Optional[str] = Field(None, description="Evaluation feedback")
    test_cases: List[Dict[str, Any]] = Field(description="Test cases used")
    results: Optional[Dict[str, Any]] = Field(None, description="Detailed results")
    status: str = Field(default="pending", description="Evaluation status")


class PromptEvaluationResponseMetadata(ProjectScopedResponseMetadata):
    """Response metadata for prompt evaluations."""

    metadata: Dict[str, Any] = Field(default_factory=dict)
    evaluator_config: Dict[str, Any] = Field(description="Evaluator configuration")


class PromptEvaluationResponseResources(ProjectScopedResponseResources):
    """Response resources for prompt evaluations."""

    pass


class PromptEvaluationResponse(
    ProjectScopedResponse[
        PromptEvaluationResponseBody,
        PromptEvaluationResponseMetadata,
        PromptEvaluationResponseResources,
    ]
):
    """Response model for prompt evaluations."""

    @property
    def score(self) -> Optional[float]:
        """Get evaluation score."""
        return self.get_body().score

    @property
    def feedback(self) -> Optional[str]:
        """Get evaluation feedback."""
        return self.get_body().feedback

    @property
    def evaluation_type(self) -> EvaluationType:
        """Get evaluation type."""
        return self.get_body().evaluation_type


# ------------------ Prompt Deployment Models ------------------


class PromptDeploymentRequest(ProjectScopedRequest):
    """Request model for prompt deployments."""

    prompt_template_id: UUID = Field(..., description="ID of prompt template")
    prompt_version: str = Field(..., description="Version to deploy")
    environment: DeploymentEnvironment = Field(..., description="Target environment")
    description: Optional[str] = Field(None, description="Deployment description")
    rollback_version: Optional[str] = Field(None, description="Rollback version")
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional metadata"
    )


class PromptDeploymentUpdate(BaseUpdate):
    """Model for updating prompt deployments."""

    status: Optional[str] = None
    description: Optional[str] = None
    rollback_version: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class PromptDeploymentResponseBody(ProjectScopedResponseBody):
    """Response body for prompt deployments."""

    prompt_template_id: UUID = Field(description="ID of deployed prompt template")
    prompt_version: str = Field(description="Deployed version")
    environment: DeploymentEnvironment = Field(description="Deployment environment")
    description: Optional[str] = Field(None, description="Deployment description")
    status: str = Field(default="active", description="Deployment status")
    rollback_version: Optional[str] = Field(None, description="Rollback version")
    deployed_at: datetime = Field(description="Deployment timestamp")


class PromptDeploymentResponseMetadata(ProjectScopedResponseMetadata):
    """Response metadata for prompt deployments."""

    metadata: Dict[str, Any] = Field(default_factory=dict)
    performance_metrics: Optional[Dict[str, Any]] = Field(
        None, description="Performance metrics"
    )


class PromptDeploymentResponseResources(ProjectScopedResponseResources):
    """Response resources for prompt deployments."""

    pass


class PromptDeploymentResponse(
    ProjectScopedResponse[
        PromptDeploymentResponseBody,
        PromptDeploymentResponseMetadata,
        PromptDeploymentResponseResources,
    ]
):
    """Response model for prompt deployments."""

    @property
    def environment(self) -> DeploymentEnvironment:
        """Get deployment environment."""
        return self.get_body().environment

    @property
    def prompt_version(self) -> str:
        """Get deployed prompt version."""
        return self.get_body().prompt_version

    @property
    def status(self) -> str:
        """Get deployment status."""
        return self.get_body().status


# ------------------ Filter Models ------------------


class PromptExperimentFilter(ProjectScopedFilter):
    """Filter model for prompt experiments."""

    name: Optional[str] = Field(None, description="Filter by name")
    status: Optional[ExperimentStatus] = Field(None, description="Filter by status")
    prompt_template_id: Optional[UUID] = Field(
        None, description="Filter by prompt template"
    )


class PromptEvaluationFilter(ProjectScopedFilter):
    """Filter model for prompt evaluations."""

    prompt_template_id: Optional[UUID] = Field(
        None, description="Filter by prompt template"
    )
    evaluation_type: Optional[EvaluationType] = Field(
        None, description="Filter by evaluation type"
    )
    score_min: Optional[float] = Field(None, description="Minimum score")
    score_max: Optional[float] = Field(None, description="Maximum score")


class PromptDeploymentFilter(ProjectScopedFilter):
    """Filter model for prompt deployments."""

    prompt_template_id: Optional[UUID] = Field(
        None, description="Filter by prompt template"
    )
    environment: Optional[DeploymentEnvironment] = Field(
        None, description="Filter by environment"
    )
    status: Optional[str] = Field(None, description="Filter by status")