#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

"""Class to run steps."""

import inspect
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
)

from zenml.artifacts.base_artifact import BaseArtifact
from zenml.client import Client
from zenml.config.step_configurations import StepConfiguration
from zenml.config.step_run_info import StepRunInfo
from zenml.enums import StackComponentType
from zenml.exceptions import StepInterfaceError
from zenml.logger import get_logger
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.materializers.unmaterialized_artifact import UnmaterializedArtifact
from zenml.models.artifact_models import (
    ArtifactRequestModel,
    ArtifactResponseModel,
)
from zenml.orchestrators.publish_utils import (
    publish_output_artifact_metadata,
    publish_output_artifacts,
    publish_step_run_metadata,
    publish_successful_step_run,
)
from zenml.orchestrators.utils import is_setting_enabled
from zenml.steps.step_context import StepContext
from zenml.steps.step_environment import StepEnvironment
from zenml.steps.utils import (
    parse_return_type_annotations,
    resolve_type_annotation,
)
from zenml.utils import source_utils

if TYPE_CHECKING:
    from zenml.config.step_configurations import Step
    from zenml.metadata.metadata_types import MetadataType
    from zenml.stack import Stack


logger = get_logger(__name__)


class StepRunner:
    """Class to run steps."""

    def __init__(self, step: "Step", stack: "Stack"):
        """Initializes the step runner.

        Args:
            step: The step to run.
            stack: The stack on which the step should run.
        """
        self._step = step
        self._stack = stack

    @property
    def configuration(self) -> StepConfiguration:
        """Configuration of the step to run.

        Returns:
            The step configuration.
        """
        return self._step.config

    def run(
        self,
        input_artifacts: Dict[str, "ArtifactResponseModel"],
        output_artifact_uris: Dict[str, str],
        step_run_info: StepRunInfo,
    ) -> None:
        """Runs the step.

        Args:
            input_artifacts: The input artifacts of the step.
            output_artifact_uris: The URIs of the output artifacts of the step.
            step_run_info: The step run info.

        Raises:
            BaseException: A general exception if the step fails.
        """
        step_entrypoint = self._load_step_entrypoint()
        output_materializers = self._load_output_materializers()
        spec = inspect.getfullargspec(inspect.unwrap(step_entrypoint))

        # Parse the inputs for the entrypoint function.
        function_params = self._parse_inputs(
            args=spec.args,
            annotations=spec.annotations,
            input_artifacts=input_artifacts,
            output_artifact_uris=output_artifact_uris,
            output_materializers=output_materializers,
        )

        # Wrap the execution of the step function in a step environment
        # that the step function code can access to retrieve information about
        # the pipeline runtime, such as the current step name and the current
        # pipeline run ID
        cache_enabled = is_setting_enabled(
            is_enabled_on_step=step_run_info.config.enable_cache,
            is_enabled_on_pipeline=step_run_info.pipeline.enable_cache,
        )
        with StepEnvironment(
            step_run_info=step_run_info,
            cache_enabled=cache_enabled,
        ):
            self._stack.prepare_step_run(info=step_run_info)
            step_failed = False
            try:
                return_values = step_entrypoint(**function_params)
            except BaseException as step_exception:  # noqa: E722
                step_failed = True
                failure_hook_source = self.configuration.failure_hook_source
                if failure_hook_source:
                    logger.info("Detected failure hook. Running...")
                    self.load_and_run_hook(
                        failure_hook_source,
                        step_exception=step_exception,
                        output_artifact_uris=output_artifact_uris,
                        output_materializers=output_materializers,
                    )
                raise
            finally:
                step_run_metadata = self._stack.get_step_run_metadata(
                    info=step_run_info,
                )
                publish_step_run_metadata(
                    step_run_id=step_run_info.step_run_id,
                    step_run_metadata=step_run_metadata,
                )
                self._stack.cleanup_step_run(
                    info=step_run_info, step_failed=step_failed
                )
                if not step_failed:
                    success_hook_source = (
                        self.configuration.success_hook_source
                    )
                    if success_hook_source:
                        logger.info("Detected success hook. Running...")
                        self.load_and_run_hook(
                            success_hook_source,
                            step_exception=None,
                            output_artifact_uris=output_artifact_uris,
                            output_materializers=output_materializers,
                        )

            # Store and publish the output artifacts of the step function.
            output_annotations = parse_return_type_annotations(
                spec.annotations
            )
            output_data = self._validate_outputs(
                return_values, output_annotations
            )
            artifact_metadata_enabled = is_setting_enabled(
                is_enabled_on_step=step_run_info.config.enable_artifact_metadata,
                is_enabled_on_pipeline=step_run_info.pipeline.enable_artifact_metadata,
            )
            output_artifacts, artifact_metadata = self._store_output_artifacts(
                output_data=output_data,
                output_artifact_uris=output_artifact_uris,
                output_materializers=output_materializers,
                artifact_metadata_enabled=artifact_metadata_enabled,
            )

        output_artifact_ids = publish_output_artifacts(
            output_artifacts=output_artifacts,
        )
        publish_output_artifact_metadata(
            output_artifact_ids=output_artifact_ids,
            output_artifact_metadata=artifact_metadata,
        )

        # Update the status and output artifacts of the step run.
        publish_successful_step_run(
            step_run_id=step_run_info.step_run_id,
            output_artifact_ids=output_artifact_ids,
        )

    def _load_step_entrypoint(self) -> Callable[..., Any]:
        """Load the step entrypoint function.

        Returns:
            The step entrypoint function.
        """
        from zenml.steps import BaseStep

        step_instance = BaseStep.load_from_source(self._step.spec.source)
        step_instance._configuration = self._step.config
        return step_instance.entrypoint

    def _load_output_materializers(self) -> Dict[str, Type[BaseMaterializer]]:
        """Loads the output materializers for the step.

        Returns:
            The step output materializers.
        """
        materializers = {}
        for name, output in self.configuration.outputs.items():
            materializer_class: Type[
                BaseMaterializer
            ] = source_utils.load_and_validate_class(
                output.materializer_source, expected_class=BaseMaterializer
            )
            materializers[name] = materializer_class
        return materializers

    def _parse_inputs(
        self,
        args: List[str],
        annotations: Dict[str, Any],
        input_artifacts: Dict[str, "ArtifactResponseModel"],
        output_artifact_uris: Dict[str, str],
        output_materializers: Dict[str, Type[BaseMaterializer]],
    ) -> Dict[str, Any]:
        """Parses the inputs for a step entrypoint function.

        Args:
            args: The arguments of the step entrypoint function.
            annotations: The annotations of the step entrypoint function.
            input_artifacts: The input artifacts of the step.
            output_artifact_uris: The URIs of the output artifacts of the step.
            output_materializers: The output materializers of the step.

        Returns:
            The parsed inputs for the step entrypoint function.
        """
        from zenml.steps import BaseParameters

        function_params: Dict[str, Any] = {}

        if args and args[0] == "self":
            args.pop(0)

        for arg in args:
            arg_type = annotations.get(arg, None)
            arg_type = resolve_type_annotation(arg_type)

            # Parse the parameters
            if issubclass(arg_type, BaseParameters):
                step_params = arg_type.parse_obj(self.configuration.parameters)
                function_params[arg] = step_params

            # Parse the step context
            elif issubclass(arg_type, StepContext):
                step_name = self.configuration.name
                context = arg_type(
                    step_name=step_name,
                    output_materializers=output_materializers,
                    output_artifact_uris=output_artifact_uris,
                )
                function_params[arg] = context

            # Parse the input artifacts
            else:
                # At this point, it has to be an artifact, so we resolve
                function_params[arg] = self._load_input_artifact(
                    input_artifacts[arg], arg_type
                )

        return function_params

    def _parse_hook_inputs(
        self,
        args: List[str],
        annotations: Dict[str, Any],
        step_exception: Optional[BaseException],
        output_artifact_uris: Dict[str, str],
        output_materializers: Dict[str, Type[BaseMaterializer]],
    ) -> Dict[str, Any]:
        """Parses the inputs for a step entrypoint function.

        Args:
            args: The arguments of the step entrypoint function.
            annotations: The annotations of the step entrypoint function.
            step_exception: The exception of the original step.
            output_artifact_uris: The URIs of the output artifacts of the step.
            output_materializers: The output materializers of the step.

        Returns:
            The parsed inputs for the step entrypoint function.

        Raises:
            TypeError: If hook function is passed a wrong parameter type.
        """
        from zenml.steps import BaseParameters

        function_params: Dict[str, Any] = {}

        if args and args[0] == "self":
            args.pop(0)

        for arg in args:
            arg_type = annotations.get(arg, None)
            arg_type = resolve_type_annotation(arg_type)

            # Parse the parameters
            if issubclass(arg_type, BaseParameters):
                step_params = arg_type.parse_obj(self.configuration.parameters)
                function_params[arg] = step_params

            # Parse the step context
            elif issubclass(arg_type, StepContext):
                step_name = self.configuration.name
                context = arg_type(
                    step_name=step_name,
                    output_materializers=output_materializers,
                    output_artifact_uris=output_artifact_uris,
                )
                function_params[arg] = context

            elif issubclass(arg_type, BaseException):
                function_params[arg] = step_exception

            else:
                # It should not be of any other type
                raise TypeError(
                    "Hook functions can only take parameters of type `StepContext`,"
                    f"`BaseParameters`, or `BaseException`, not {arg_type}"
                )

        return function_params

    def _load_input_artifact(
        self, artifact: "ArtifactResponseModel", data_type: Type[Any]
    ) -> Any:
        """Loads an input artifact.

        Args:
            artifact: The artifact to load.
            data_type: The data type of the artifact value.

        Returns:
            The artifact value.
        """
        # Skip materialization for `UnmaterializedArtifact`.
        if data_type == UnmaterializedArtifact:
            return UnmaterializedArtifact.parse_obj(artifact)

        # Skip materialization for `BaseArtifact` and its subtypes.
        if issubclass(data_type, BaseArtifact):
            logger.warning(
                "Skipping materialization by specifying a subclass of "
                "`zenml.artifacts.BaseArtifact` as input data type is "
                "deprecated and will be removed in a future release. Please "
                "type your input as "
                "`zenml.materializers.UnmaterializedArtifact` instead."
            )
            return artifact

        materializer_class: Type[
            BaseMaterializer
        ] = source_utils.load_and_validate_class(
            artifact.materializer, expected_class=BaseMaterializer
        )
        materializer = materializer_class(artifact.uri)
        return materializer.load(data_type=data_type)

    def _validate_outputs(
        self,
        return_values: Any,
        output_annotations: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Validates the step function outputs.

        Args:
            return_values: The return values of the step function.
            output_annotations: The output annotations of the step function.

        Returns:
            The validated output, mapping output names to return values.

        Raises:
            StepInterfaceError: If the step function return values do not
                match the output annotations.
        """
        step_name = self.configuration.name

        # if there are no outputs, the return value must be `None`.
        if len(output_annotations) == 0:
            if return_values is not None:
                raise StepInterfaceError(
                    f"Wrong step function output type for step '{step_name}': "
                    f"Expected no outputs but the function returned something: "
                    f"{return_values}."
                )
            return {}

        # if there is only one output annotation (either directly specified
        # or contained in an `Output` tuple) we treat the step function
        # return value as the return for that output.
        if len(output_annotations) == 1:
            return_values = [return_values]

        # if the user defined multiple outputs, the return value must be a list
        # or tuple.
        if not isinstance(return_values, (list, tuple)):
            raise StepInterfaceError(
                f"Wrong step function output type for step '{step_name}': "
                f"Expected multiple outputs ({output_annotations}) but "
                f"the function did not return a list or tuple "
                f"(actual return value: {return_values})."
            )

        # The amount of actual outputs must be the same as the amount of
        # expected outputs.
        if len(output_annotations) != len(return_values):
            raise StepInterfaceError(
                f"Wrong amount of step function outputs for step "
                f"'{step_name}: Expected {len(output_annotations)} outputs "
                f"but the function returned {len(return_values)} outputs"
                f"(return values: {return_values})."
            )

        # Validate the output types.
        validated_outputs: Dict[str, Any] = {}
        for return_value, (output_name, output_type) in zip(
            return_values, output_annotations.items()
        ):
            # The actual output type must be the same as the expected output
            # type.
            if not isinstance(return_value, output_type):
                raise StepInterfaceError(
                    f"Wrong type for output '{output_name}' of step "
                    f"'{step_name}' (expected type: {output_type}, "
                    f"actual type: {type(return_value)})."
                )
            validated_outputs[output_name] = return_value
        return validated_outputs

    def _store_output_artifacts(
        self,
        output_data: Dict[str, Any],
        output_materializers: Dict[str, Type[BaseMaterializer]],
        output_artifact_uris: Dict[str, str],
        artifact_metadata_enabled: bool,
    ) -> Tuple[
        Dict[str, ArtifactRequestModel], Dict[str, Dict[str, "MetadataType"]]
    ]:
        """Stores the output artifacts of the step.

        Args:
            output_data: The output data of the step function, mapping output
                names to return values.
            output_materializers: The output materializers of the step.
            output_artifact_uris: The output artifact URIs of the step.
            artifact_metadata_enabled: Whether artifact metadata collection is
                enabled.

        Returns:
            An `ArtifactRequestModel` for each output artifact that was saved,
            and the metadata of each output artifact.
        """
        client = Client()
        active_user_id = client.active_user.id
        active_workspace_id = client.active_workspace.id
        artifact_stores = client.active_stack_model.components.get(
            StackComponentType.ARTIFACT_STORE
        )
        assert artifact_stores  # Every stack has an artifact store.
        artifact_store_id = artifact_stores[0].id
        output_artifacts: Dict[str, ArtifactRequestModel] = {}
        output_artifact_metadata: Dict[str, Dict[str, "MetadataType"]] = {}
        for output_name, return_value in output_data.items():
            materializer_class = output_materializers[output_name]
            materializer_source = self.configuration.outputs[
                output_name
            ].materializer_source
            uri = output_artifact_uris[output_name]
            materializer = materializer_class(uri)
            materializer.save(return_value)
            if artifact_metadata_enabled:
                try:
                    artifact_metadata = materializer.extract_metadata(
                        return_value
                    )
                    output_artifact_metadata[output_name] = artifact_metadata
                except Exception as e:
                    logger.warning(
                        f"Failed to extract metadata for output artifact "
                        f"'{output_name}' of step '{self.configuration.name}': "
                        f"{e}"
                    )
            output_artifact = ArtifactRequestModel(
                name=output_name,
                type=materializer_class.ASSOCIATED_ARTIFACT_TYPE,
                uri=uri,
                materializer=materializer_source,
                data_type=source_utils.resolve_class(type(return_value)),
                user=active_user_id,
                workspace=active_workspace_id,
                artifact_store_id=artifact_store_id,
            )
            output_artifacts[output_name] = output_artifact
        return output_artifacts, output_artifact_metadata

    def load_and_run_hook(
        self,
        hook_source: str,
        step_exception: Optional[BaseException],
        output_artifact_uris: Dict[str, str],
        output_materializers: Dict[str, Type[BaseMaterializer]],
    ) -> None:
        """Loads hook source and runs the hook.

        Args:
            hook_source: The source of the hook function.
            step_exception: The exception of the original step.
            output_artifact_uris: The URIs of the output artifacts of the step.
            output_materializers: The output materializers of the step.
        """
        try:
            hook = source_utils.load_source_path(hook_source)
            hook_spec = inspect.getfullargspec(inspect.unwrap(hook))

            function_params = self._parse_hook_inputs(
                args=hook_spec.args,
                annotations=hook_spec.annotations,
                step_exception=step_exception,
                output_artifact_uris=output_artifact_uris,
                output_materializers=output_materializers,
            )
            logger.debug(f"Running hook {hook} with params: {function_params}")
            hook(**function_params)
        except Exception as e:
            logger.error(
                f"Failed to load hook source with exception: '{hook_source}': {e}"
            )
