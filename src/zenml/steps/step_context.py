from typing import TYPE_CHECKING, Dict, NamedTuple, Optional, Type, cast

from zenml.exceptions import StepContextError
from zenml.repository import Repository

if TYPE_CHECKING:
    from zenml.artifacts.base_artifact import BaseArtifact
    from zenml.materializers.base_materializer import BaseMaterializer
    from zenml.metadata_stores.base_metadata_store import BaseMetadataStore
    from zenml.stack import Stack


class StepContextOutput(NamedTuple):
    """Tuple containing materializer class and artifact for a step output."""

    materializer_class: Type["BaseMaterializer"]
    artifact: "BaseArtifact"


class StepContext:
    """Provides additional context inside a step function.

    This class is used to access the metadata store, materializers and
    artifacts inside a step function. To use it, add a `StepContext` object
    to the signature of your step function like this:

    ```python
    @step
    def my_step(context: StepContext, ...)
        context.get_output_materializer(...)
    ```

    You do not need to create a `StepContext` object yourself and pass it
    when creating the step, as long as you specify it in the signature ZenML
    will create the `StepContext` and automatically pass it when executing your
    step.

    **Note**: When using a `StepContext` inside a step, ZenML disables caching
    for this step by default as the context provides access to external
    resources which might influence the result of your step execution. To
    enable caching anyway, explicitly enable it in the `@step` decorator or when
    initializing your custom step class.
    """

    def __init__(
        self,
        step_name: str,
        output_materializers: Dict[str, Type["BaseMaterializer"]],
        output_artifacts: Dict[str, "BaseArtifact"],
    ):
        """Initializes a StepContext instance.

        Args:
            step_name: The name of the step that this context is used in.
            output_materializers: The output materializers of the step that
                                  this context is used in.
            output_artifacts: The output artifacts of the step that this
                              context is used in.

        Raises:
             StepContextError: If the keys of the output materializers and
                               output artifacts do not match.
        """
        if output_materializers.keys() != output_artifacts.keys():
            raise StepContextError(
                f"Mismatched keys in output materializers and output "
                f"artifacts for step '{step_name}'. Output materializer "
                f"keys: {set(output_materializers)}, output artifact "
                f"keys: {set(output_artifacts)}"
            )

        self.step_name = step_name
        self._outputs = {
            key: StepContextOutput(
                output_materializers[key], output_artifacts[key]
            )
            for key in output_materializers.keys()
        }
        self._metadata_store = Repository().active_stack.metadata_store
        self._stack = Repository().active_stack

    def _get_output(
        self, output_name: Optional[str] = None
    ) -> StepContextOutput:
        """Returns the materializer and artifact URI for a given step output.

        Args:
            output_name: Optional name of the output for which to get the
                materializer and URI.

        Returns:
            Tuple containing the materializer and artifact URI for the
            given output.

        Raises:
            StepContextError: If the step has no outputs, no output for
                              the given `output_name` or if no `output_name`
                              was given but the step has multiple outputs.
        """
        output_count = len(self._outputs)
        if output_count == 0:
            raise StepContextError(
                f"Unable to get step output for step '{self.step_name}': "
                f"This step does not have any outputs."
            )

        if not output_name and output_count > 1:
            raise StepContextError(
                f"Unable to get step output for step '{self.step_name}': "
                f"This step has multiple outputs ({set(self._outputs)}), "
                f"please specify which output to return."
            )

        if output_name:
            if output_name not in self._outputs:
                raise StepContextError(
                    f"Unable to get step output '{output_name}' for "
                    f"step '{self.step_name}'. This step does not have an "
                    f"output with the given name, please specify one of the "
                    f"available outputs: {set(self._outputs)}."
                )
            return self._outputs[output_name]
        else:
            return next(iter(self._outputs.values()))

    @property
    def metadata_store(self) -> "BaseMetadataStore":
        """
        Returns an instance of the metadata store that is used to store
        metadata about the step (and the corresponding pipeline) which is
        being executed.
        """
        return self._metadata_store

    @property
    def stack(self) -> Optional["Stack"]:
        """Returns the current active stack."""
        return self._stack

    def get_output_materializer(
        self,
        output_name: Optional[str] = None,
        custom_materializer_class: Optional[Type["BaseMaterializer"]] = None,
    ) -> "BaseMaterializer":
        """Returns a materializer for a given step output.

        Args:
            output_name: Optional name of the output for which to get the
                materializer. If no name is given and the step only has a
                single output, the materializer of this output will be
                returned. If the step has multiple outputs, an exception
                will be raised.
            custom_materializer_class: If given, this `BaseMaterializer`
                subclass will be initialized with the output artifact instead
                of the materializer that was registered for this step output.

        Returns:
            A materializer initialized with the output artifact for
            the given output.

        Raises:
            StepContextError: If the step has no outputs, no output for
                              the given `output_name` or if no `output_name`
                              was given but the step has multiple outputs.
        """
        materializer_class, artifact = self._get_output(output_name)
        # use custom materializer class if provided or fallback to default
        # materializer for output
        materializer_class = custom_materializer_class or materializer_class
        return materializer_class(artifact)

    def get_output_artifact_uri(self, output_name: Optional[str] = None) -> str:
        """Returns the artifact URI for a given step output.

        Args:
            output_name: Optional name of the output for which to get the URI.
                If no name is given and the step only has a single output,
                the URI of this output will be returned. If the step has
                multiple outputs, an exception will be raised.

        Returns:
            Artifact URI for the given output.

        Raises:
            StepContextError: If the step has no outputs, no output for
                              the given `output_name` or if no `output_name`
                              was given but the step has multiple outputs.
        """
        return cast(str, self._get_output(output_name).artifact.uri)
