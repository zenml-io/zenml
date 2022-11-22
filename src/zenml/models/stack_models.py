import json
from typing import Any, Dict, List
from uuid import UUID

from pydantic import BaseModel, Field

from zenml.enums import StackComponentType
from zenml.models.base_models import (
    ShareableRequestModel,
    ShareableResponseModel,
    update,
)
from zenml.models.component_models import ComponentResponseModel
from zenml.models.constants import (
    MODEL_DESCRIPTIVE_FIELD_MAX_LENGTH,
    MODEL_NAME_FIELD_MAX_LENGTH,
)

# TODO: Add example schemas and analytics fields


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
    """Stack model with Components, User and Workspace fully hydrated."""

    components: Dict[StackComponentType, List[ComponentResponseModel]] = Field(
        title="A mapping of stack component types to the actual"
        "instances of components of this type."
    )

    @property
    def is_valid(self) -> bool:
        """Check if the stack is valid.
        Returns:
            True if the stack is valid, False otherwise.
        """
        if (
            StackComponentType.ARTIFACT_STORE
            and StackComponentType.ORCHESTRATOR in self.components.keys()
        ):
            return True
        else:
            return False

    def to_yaml(self) -> Dict[str, Any]:
        """Create yaml representation of the Stack Model.

        Returns:
            The yaml representation of the Stack Model.
        """
        component_data = {}
        for component_type, components_list in self.components.items():
            component_dict = json.loads(components_list[0].json())
            component_dict.pop("workspace")  # Not needed in the yaml repr
            component_dict.pop("created")  # Not needed in the yaml repr
            component_dict.pop("updated")  # Not needed in the yaml repr
            component_data[component_type.value] = component_dict

        # write zenml version and stack dict to YAML
        yaml_data = {
            "stack_name": self.name,
            "components": component_data,
        }

        return yaml_data


# ------- #
# REQUEST #
# ------- #


class StackRequestModel(StackBaseModel, ShareableRequestModel):
    components: Dict[StackComponentType, List[UUID]] = Field(
        title="A mapping of stack component types to the actual"
        "instances of components of this type."
    )

    @property
    def is_valid(self) -> bool:
        """Check if the stack is valid.
        Returns:
            True if the stack is valid, False otherwise.
        """
        if (
            StackComponentType.ARTIFACT_STORE
            and StackComponentType.ORCHESTRATOR in self.components.keys()
        ):
            return True
        else:
            return False


# ------ #
# UPDATE #
# ------ #


@update
class StackUpdateModel(StackRequestModel):
    """beautiful."""
