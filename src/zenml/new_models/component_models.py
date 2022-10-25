from typing import Any, Dict

from pydantic import Field

from zenml.enums import StackComponentType
from zenml.models.constants import MODEL_NAME_FIELD_MAX_LENGTH
from zenml.new_models.base_models import (
    ShareableRequestModel,
    ShareableResponseModel,
)
from zenml.utils.analytics_utils import AnalyticsTrackedModelMixin

# TODO: Add example schemas and analytics fields

# -------- #
# RESPONSE #
# -------- #


class ComponentResponseModel(
    ShareableResponseModel, AnalyticsTrackedModelMixin
):
    """Model describing the Component."""

    name: str = Field(
        title="The name of the stack component.",
        max_length=MODEL_NAME_FIELD_MAX_LENGTH,
    )
    type: StackComponentType = Field(
        title="The type of the stack component.",
    )

    flavor: str = Field(
        title="The flavor of the stack component.",
    )

    configuration: Dict[str, Any] = Field(
        title="The stack component configuration.",
    )


# ------- #
# REQUEST #
# ------- #


class ComponentRequestModel(ShareableRequestModel, AnalyticsTrackedModelMixin):
    name: str = Field(
        title="The name of the stack component.",
        max_length=MODEL_NAME_FIELD_MAX_LENGTH,
    )
    type: StackComponentType = Field(
        title="The type of the stack component.",
    )

    flavor: str = Field(
        title="The flavor of the stack component.",
    )

    configuration: Dict[str, Any] = Field(
        title="The stack component configuration.",
    )
