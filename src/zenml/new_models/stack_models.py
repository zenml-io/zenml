from typing import Dict, List
from uuid import UUID

from pydantic import BaseModel, Field

from zenml.enums import StackComponentType
from zenml.models.constants import (
    MODEL_DESCRIPTIVE_FIELD_MAX_LENGTH,
    MODEL_NAME_FIELD_MAX_LENGTH,
)
from zenml.new_models.base_models import (
    ShareableRequestModel,
    ShareableResponseModel,
)
from zenml.new_models.component_models import ComponentResponseModel

# TODO: Add example schemas and analytics fields
# TODO: Add base models

# ---- #
# BASE #
# ---- #


class StackBaseModel(BaseModel):
    name: str = Field(
        title="The name of the stack.", max_length=MODEL_NAME_FIELD_MAX_LENGTH
    )
    description: str = Field(
        default="",
        title="The description of the stack",
        max_length=MODEL_DESCRIPTIVE_FIELD_MAX_LENGTH,
    )


# -------- #
# RESPONSE #
# -------- #


class StackResponseModel(StackBaseModel, ShareableResponseModel):
    """Stack model with Components, User and Project fully hydrated."""

    components: Dict[StackComponentType, List[ComponentResponseModel]] = Field(
        title="A mapping of stack component types to the actual"
        "instances of components of this type."
    )


# ------- #
# REQUEST #
# ------- #


class StackRequestModel(StackBaseModel, ShareableRequestModel):
    components: Dict[StackComponentType, List[UUID]] = Field(
        title="A mapping of stack component types to the actual"
        "instances of components of this type."
    )
