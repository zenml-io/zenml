from zenml.annotations.base_annotations import GenericType
from zenml.artifacts.base_artifact import BaseArtifact

# General Artifact Annotations

Input = type("Input", (GenericType,), {"VALID_TYPES": [BaseArtifact]})

Output = type("Output", (GenericType,), {"VALID_TYPES": [BaseArtifact]})

External = type("Input", (GenericType,), {"VALID_TYPES": [BaseArtifact]})

# Specialized Artifact Annotations

BeamOutput = type("BeamOutput", (Output,), {"VALID_TYPES": [BaseArtifact]})

PandasOutput = type("PandasOutput", (Output,), {"VALID_TYPES": [BaseArtifact]})

JSONOutput = type("JSONOutput", (Output,), {"VALID_TYPES": [BaseArtifact]})
