from zenml.annotations.base_annotations import BaseAnnotation

# Parameter annotation for the steps
Param = type("Param", (BaseAnnotation,), {"VALID_TYPES": [int, float, str, bool]})
