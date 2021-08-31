from playground.annotations.base_annotations import GenericType
from playground.artifacts.base import BaseArtifact

Input = type("Input", (GenericType,), {"VALID_TYPES": [BaseArtifact]})

Output = type("Output", (GenericType,), {"VALID_TYPES": [BaseArtifact]})

External = type("Input", (GenericType,), {"VALID_TYPES": [BaseArtifact]})
