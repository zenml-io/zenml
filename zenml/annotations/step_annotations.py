from zenml.annotations.base_annotations import BaseAnnotation
from zenml.steps.base_step import BaseStep

Step = type("Step", (BaseAnnotation,), {"VALID_TYPES": [BaseStep]})
