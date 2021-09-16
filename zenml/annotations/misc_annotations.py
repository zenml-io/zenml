from zenml.annotations.base_annotations import BaseAnnotation

Param = type("Param", (BaseAnnotation,), {"VALID_TYPES": [int, float, str, bool]})
