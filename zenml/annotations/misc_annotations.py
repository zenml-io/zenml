from zenml.annotations.base_annotations import GenericType

Param = type("Param", (GenericType,), {"VALID_TYPES": [int, float, str, bool]})
