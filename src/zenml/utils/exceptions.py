class StepInterfaceError(Exception):
    """Raises exception when interacting with the Step interface
    in an unsupported way."""


class PipelineInterfaceError(Exception):
    """Raises exception when interacting with the Pipeline interface
    in an unsupported way."""


class ArtifactInterfaceError(Exception):
    """Raises exception when interacting with the Artifact interface
    in an unsupported way."""
