from collections import namedtuple
from typing import TYPE_CHECKING, Dict, Optional, Type

from zenml.exceptions import StepInterfaceError

if TYPE_CHECKING:
    from zenml.artifacts.base_artifact import BaseArtifact
    from zenml.materializers.base_materializer import BaseMaterializer


StepContextOutput = namedtuple(
    "StepContextOutput", ["materializer_class", "artifact"]
)


class StepContext:
    def __init__(
        self,
        output_materializers: Dict[str, Type["BaseMaterializer"]],
        output_artifacts: Dict[str, "BaseArtifact"],
    ):
        if output_materializers.keys() != output_artifacts.keys():
            raise StepInterfaceError()

        self._outputs = {
            key: StepContextOutput(
                output_materializers[key], output_artifacts[key]
            )
            for key in output_materializers.keys()
        }

    def _get_output(
        self, output_name: Optional[str] = None
    ) -> StepContextOutput:
        output_count = len(self._outputs)
        if output_count == 0:
            raise StepInterfaceError()

        if not output_name and output_count > 1:
            raise StepInterfaceError()

        if output_name:
            return self._outputs[output_name]
        else:
            return next(iter(self._outputs.values()))

    def get_output_materializer(
        self,
        output_name: Optional[str] = None,
        custom_materializer_class: Optional[Type["BaseMaterializer"]] = None,
    ) -> "BaseMaterializer":
        materializer_class, artifact = self._get_output(output_name)
        # use custom materializer class if provided or fallback to default
        # materializer for output
        materializer_class = custom_materializer_class or materializer_class
        return materializer_class(artifact)

    def get_output_artifact_uri(self, output_name: Optional[str] = None) -> str:
        return self._get_output(output_name).artifact.uri
