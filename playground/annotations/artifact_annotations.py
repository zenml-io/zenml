from playground.annotations.base_annotations import GenericType
from playground.artifacts.base_artifact import BaseArtifact

Input = type("Input",
             (GenericType,),
             {"VALID_TYPES": [BaseArtifact]})

Output = type("Output",
              (GenericType,),
              {"VALID_TYPES": [BaseArtifact]})

Param = type("Param",
             (GenericType,),
             {"VALID_TYPES": [int, float, str, bytes, dict]})
