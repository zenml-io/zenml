from typing import Optional

from pydantic import Field

from zenml.enums import StackComponentType
from zenml.models.constants import MODEL_CONFIG_SCHEMA_MAX_LENGTH
from zenml.new_models.base_models import (
    ProjectScopedRequestModel,
    ProjectScopedResponseModel,
)
from zenml.utils.analytics_utils import AnalyticsTrackedModelMixin

# TODO: Add example schemas and analytics fields

# -------- #
# RESPONSE #
# -------- #


class FlavorResponseModel(
    ProjectScopedResponseModel, AnalyticsTrackedModelMixin
):
    """Domain model representing the custom implementation of a flavor."""

    name: str = Field(
        title="The name of the Flavor.",
    )
    type: StackComponentType = Field(
        title="The type of the Flavor.",
    )
    config_schema: str = Field(
        title="The JSON schema of this flavor's corresponding configuration.",
        max_length=MODEL_CONFIG_SCHEMA_MAX_LENGTH,
    )
    source: str = Field(
        title="The path to the module which contains this Flavor."
    )
    integration: Optional[str] = Field(
        title="The name of the integration that the Flavor belongs to."
    )


# ------- #
# REQUEST #
# ------- #


class FlavorRequestModel(ProjectScopedRequestModel, AnalyticsTrackedModelMixin):
    """ """

    name: str = Field(
        title="The name of the Flavor.",
    )
    type: StackComponentType = Field(
        title="The type of the Flavor.",
    )
    config_schema: str = Field(
        title="The JSON schema of this flavor's corresponding configuration.",
        max_length=MODEL_CONFIG_SCHEMA_MAX_LENGTH,
    )
    source: str = Field(
        title="The path to the module which contains this Flavor."
    )
    integration: Optional[str] = Field(
        title="The name of the integration that the Flavor belongs to."
    )
