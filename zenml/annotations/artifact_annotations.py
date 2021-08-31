from zenml.annotations.base_annotations import GenericType
from zenml.artifacts.base import BaseArtifact

Input = type("Input", (GenericType,), {"VALID_TYPES": [BaseArtifact]})

Output = type("Output", (GenericType,), {"VALID_TYPES": [BaseArtifact]})

External = type("Input", (GenericType,), {"VALID_TYPES": [BaseArtifact]})
