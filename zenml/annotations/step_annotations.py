from zenml.annotations.base_annotations import GenericType
from zenml.steps.base_step import BaseStep

Step = type("Step", (GenericType,), {"VALID_TYPES": [BaseStep]})
