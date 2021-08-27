from playground.annotations.base_annotations import GenericType
from playground.steps.base_step import BaseStep

Step = type("Step", (GenericType,), {"VALID_TYPES": [BaseStep]})
