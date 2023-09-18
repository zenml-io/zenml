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

import copy
import inspect
from contextlib import nullcontext
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
)

from pydantic.typing import get_origin, is_union

from zenml.client import Client
from zenml.config.step_configurations import StepConfiguration
from zenml.config.step_run_info import StepRunInfo
from zenml.constants import (
    ENV_ZENML_DISABLE_STEP_LOGS_STORAGE,
    handle_bool_env_var,
)
from zenml.enums import StackComponentType
from zenml.exceptions import StepInterfaceError
from zenml.logger import get_logger
from zenml.logging.step_logging import StepLogsStorageContext, redirected
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.materializers.unmaterialized_artifact import UnmaterializedArtifact
from zenml.new.steps.step_context import StepContext, get_step_context
from zenml.orchestrators.publish_utils import (
    publish_step_run_metadata,
    publish_successful_step_run,
)
from zenml.orchestrators.utils import is_setting_enabled
from zenml.steps.step_environment import StepEnvironment
from zenml.steps.utils import (
    parse_return_type_annotations,
    resolve_type_annotation,
)
from zenml.utils import artifact_utils, materializer_utils, source_utils

if TYPE_CHECKING:
    from uuid import UUID

    from zenml.config.source import Source
    from zenml.config.step_configurations import Step
    from zenml.models.artifact_models import ArtifactResponseModel
    from zenml.models.pipeline_run_models import PipelineRunResponseModel
    from zenml.models.step_run_models import StepRunResponseModel
    from zenml.stack import Stack
    from zenml.steps import BaseStep


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
        pipeline_run: "PipelineRunResponseModel",
        step_run: "StepRunResponseModel",
        input_artifacts: Dict[str, "ArtifactResponseModel"],
        output_artifact_uris: Dict[str, str],
        step_run_info: StepRunInfo,
    ) -> None:
        """Runs the step.

        Args:
            pipeline_run: The model of the current pipeline run.
            step_run: The model of the current step run.
            input_artifacts: The input artifacts of the step.
            output_artifact_uris: The URIs of the output artifacts of the step.
            step_run_info: The step run info.

        Raises:
            BaseException: A general exception if the step fails.
        """
        if handle_bool_env_var(ENV_ZENML_DISABLE_STEP_LOGS_STORAGE, False):
            step_logging_enabled = False
        else:
            enabled_on_step = step_run.config.enable_step_logs

            enabled_on_pipeline = None
            if pipeline_run.deployment:
                enabled_on_pipeline = (
                    pipeline_run.deployment.pipeline_configuration.enable_step_logs
                )

            step_logging_enabled = is_setting_enabled(
                is_enabled_on_step=enabled_on_step,
                is_enabled_on_pipeline=enabled_on_pipeline,
            )

        logs_context = nullcontext()
        if step_logging_enabled and not redirected.get():
            if step_run.logs:
                logs_context = StepLogsStorageContext(  # type: ignore[assignment]
                    logs_uri=step_run.logs.uri
                )
            else:
                logger.debug(
                    "There is no LogsResponseModel prepared for the step. The"
                    "step logging storage is disabled."
                )

        with logs_context:
            step_instance = self._load_step()
            output_materializers = self._load_output_materializers()
            spec = inspect.getfullargspec(
                inspect.unwrap(step_instance.entrypoint)
            )

            # (Deprecated) Wrap the execution of the step function in a step
            # environment that the step function code can access to retrieve
            # information about the pipeline runtime, such as the current step
            # name and the current pipeline run ID
            cache_enabled = is_setting_enabled(
                is_enabled_on_step=step_run_info.config.enable_cache,
                is_enabled_on_pipeline=step_run_info.pipeline.enable_cache,
            )
            with StepEnvironment(
                step_run_info=step_run_info,
                cache_enabled=cache_enabled,
            ):
                self._stack.prepare_step_run(info=step_run_info)

                # Initialize the step context singleton
                StepContext._clear()
                StepContext(
                    pipeline_run=pipeline_run,
                    step_run=step_run,
                    output_materializers=output_materializers,
                    output_artifact_uris=output_artifact_uris,
                    step_run_info=step_run_info,
                    cache_enabled=cache_enabled,
                )

                # Parse the inputs for the entrypoint function.
                function_params = self._parse_inputs(
                    args=spec.args,
                    annotations=spec.annotations,
                    input_artifacts=input_artifacts,
                )

                step_failed = False
                try:
                    return_values = step_instance.call_entrypoint(
                        **function_params
                    )
                except BaseException as step_exception:  # noqa: E722
                    step_failed = True
                    failure_hook_source = (
                        self.configuration.failure_hook_source
                    )
                    if failure_hook_source:
                        logger.info("Detected failure hook. Running...")
                        self.load_and_run_hook(
                            failure_hook_source,
                            step_exception=step_exception,
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
                            )

                        # Store and publish the output artifacts of the step function.
                        output_annotations = parse_return_type_annotations(
                            func=step_instance.entrypoint
                        )
                        output_data = self._validate_outputs(
                            return_values, output_annotations
                        )
                        artifact_metadata_enabled = is_setting_enabled(
                            is_enabled_on_step=step_run_info.config.enable_artifact_metadata,
                            is_enabled_on_pipeline=step_run_info.pipeline.enable_artifact_metadata,
                        )
                        artifact_visualization_enabled = is_setting_enabled(
                            is_enabled_on_step=step_run_info.config.enable_artifact_visualization,
                            is_enabled_on_pipeline=step_run_info.pipeline.enable_artifact_visualization,
                        )
                        output_artifact_ids = self._store_output_artifacts(
                            output_data=output_data,
                            output_artifact_uris=output_artifact_uris,
                            output_materializers=output_materializers,
                            artifact_metadata_enabled=artifact_metadata_enabled,
                            artifact_visualization_enabled=artifact_visualization_enabled,
                        )
                    StepContext._clear()  # Remove the step context singleton

            # Update the status and output artifacts of the step run.
            publish_successful_step_run(
                step_run_id=step_run_info.step_run_id,
                output_artifact_ids=output_artifact_ids,
            )

    def _load_step(self) -> "BaseStep":
        """Load the step instance.

        Returns:
            The step instance.
        """
        from zenml.steps import BaseStep

        step_instance = BaseStep.load_from_source(self._step.spec.source)
        step_instance = copy.deepcopy(step_instance)
        step_instance._configuration = self._step.config
        return step_instance

    def _load_output_materializers(
        self,
    ) -> Dict[str, Tuple[Type[BaseMaterializer], ...]]:
        """Loads the output materializers for the step.

        Returns:
            The step output materializers.
        """
        materializers = {}
        for name, output in self.configuration.outputs.items():
            output_materializers = []

            for source in output.materializer_source:
                materializer_class: Type[
                    BaseMaterializer
                ] = source_utils.load_and_validate_class(
                    source, expected_class=BaseMaterializer
                )
                output_materializers.append(materializer_class)

            materializers[name] = tuple(output_materializers)

        return materializers

    def _parse_inputs(
        self,
        args: List[str],
        annotations: Dict[str, Any],
        input_artifacts: Dict[str, "ArtifactResponseModel"],
    ) -> Dict[str, Any]:
        """Parses the inputs for a step entrypoint function.

        Args:
            args: The arguments of the step entrypoint function.
            annotations: The annotations of the step entrypoint function.
            input_artifacts: The input artifacts of the step.

        Returns:
            The parsed inputs for the step entrypoint function.

        Raises:
            RuntimeError: If a function argument value is missing.
        """
        function_params: Dict[str, Any] = {}

        if args and args[0] == "self":
            args.pop(0)

        for arg in args:
            arg_type = annotations.get(arg, None)
            arg_type = resolve_type_annotation(arg_type)

            if inspect.isclass(arg_type) and issubclass(arg_type, StepContext):
                step_name = self.configuration.name
                logger.warning(
                    "Passing a `StepContext` as an argument to a step function "
                    "is deprecated and will be removed in a future release. "
                    f"Please adjust your '{step_name}' step to instead import "
                    "the `StepContext` inside your step, as shown here: "
                    "https://docs.zenml.io/user-guide/advanced-guide/pipelining-features/fetch-metadata-within-steps"
                )
                function_params[arg] = get_step_context()
            elif arg in input_artifacts:
                function_params[arg] = self._load_input_artifact(
                    input_artifacts[arg], arg_type
                )
            elif arg in self.configuration.parameters:
                function_params[arg] = self.configuration.parameters[arg]
            else:
                raise RuntimeError(
                    f"Unable to find value for step function argument `{arg}`."
                )

        return function_params

    def _parse_hook_inputs(
        self,
        args: List[str],
        annotations: Dict[str, Any],
        step_exception: Optional[BaseException],
    ) -> Dict[str, Any]:
        """Parses the inputs for a hook function.

        Args:
            args: The arguments of the hook function.
            annotations: The annotations of the hook function.
            step_exception: The exception of the original step.

        Returns:
            The parsed inputs for the hook function.

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
                step_params = arg_type.parse_obj(
                    self.configuration.parameters[arg]
                )
                function_params[arg] = step_params

            # Parse the step context
            elif issubclass(arg_type, StepContext):
                step_name = self.configuration.name
                logger.warning(
                    "Passing a `StepContext` as an argument to a hook function "
                    "is deprecated and will be removed in a future release. "
                    f"Please adjust your '{step_name}' hook to instead import "
                    "the `StepContext` inside your hook, as shown here: "
                    "https://docs.zenml.io/user-guide/advanced-guide/pipelining-features/fetch-metadata-within-steps"
                )
                function_params[arg] = get_step_context()

            elif issubclass(arg_type, BaseException):
                function_params[arg] = step_exception

            else:
                # It should not be of any other type
                raise TypeError(
                    "Hook functions can only take arguments of type "
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

        if data_type is Any or is_union(get_origin(data_type)):
            # Entrypoint function does not define a specific type for the input,
            # we use the datatype of the stored artifact
            data_type = source_utils.load(artifact.data_type)

        materializer_class: Type[
            BaseMaterializer
        ] = source_utils.load_and_validate_class(
            artifact.materializer, expected_class=BaseMaterializer
        )
        materializer: BaseMaterializer = materializer_class(artifact.uri)
        materializer.validate_type_compatibility(data_type)
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
        step_name = self._step.spec.pipeline_parameter_name

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

        from pydantic.typing import get_origin, is_union

        from zenml.steps.utils import get_args

        validated_outputs: Dict[str, Any] = {}
        for return_value, (output_name, output_annotation) in zip(
            return_values, output_annotations.items()
        ):
            if output_annotation is Any:
                pass
            else:
                if is_union(get_origin(output_annotation)):
                    output_annotation = get_args(output_annotation)

                if not isinstance(return_value, output_annotation):
                    raise StepInterfaceError(
                        f"Wrong type for output '{output_name}' of step "
                        f"'{step_name}' (expected type: {output_annotation}, "
                        f"actual type: {type(return_value)})."
                    )
            validated_outputs[output_name] = return_value
        return validated_outputs

    def _store_output_artifacts(
        self,
        output_data: Dict[str, Any],
        output_materializers: Dict[str, Tuple[Type[BaseMaterializer], ...]],
        output_artifact_uris: Dict[str, str],
        artifact_metadata_enabled: bool,
        artifact_visualization_enabled: bool,
    ) -> Dict[str, "UUID"]:
        """Stores the output artifacts of the step.

        Args:
            output_data: The output data of the step function, mapping output
                names to return values.
            output_materializers: The output materializers of the step.
            output_artifact_uris: The output artifact URIs of the step.
            artifact_metadata_enabled: Whether artifact metadata collection is
                enabled.
            artifact_visualization_enabled: Whether artifact visualization is
                enabled.

        Returns:
            The IDs of the published output artifacts.
        """
        client = Client()
        artifact_stores = client.active_stack_model.components.get(
            StackComponentType.ARTIFACT_STORE
        )
        assert artifact_stores  # Every stack has an artifact store.
        artifact_store_id = artifact_stores[0].id
        output_artifacts: Dict[str, "UUID"] = {}

        for output_name, return_value in output_data.items():
            data_type = type(return_value)
            materializer_classes = output_materializers[output_name]
            if materializer_classes:
                materializer_class = materializer_utils.select_materializer(
                    data_type=data_type,
                    materializer_classes=materializer_classes,
                )
            else:
                # If no materializer classes are stored in the IR, that means
                # there was no/an `Any` type annotation for the output and
                # we try to find a materializer for it at runtime
                from zenml.materializers.materializer_registry import (
                    materializer_registry,
                )

                default_materializer_source = self._step.config.outputs[
                    output_name
                ].default_materializer_source

                if default_materializer_source:
                    default_materializer_class: Type[
                        BaseMaterializer
                    ] = source_utils.load_and_validate_class(
                        default_materializer_source,
                        expected_class=BaseMaterializer,
                    )
                    materializer_registry.default_materializer = (
                        default_materializer_class
                    )

                materializer_class = materializer_registry[data_type]

            uri = output_artifact_uris[output_name]
            materializer = materializer_class(uri)

            artifact_id = artifact_utils.upload_artifact(
                name=output_name,
                data=return_value,
                materializer=materializer,
                artifact_store_id=artifact_store_id,
                extract_metadata=artifact_metadata_enabled,
                include_visualizations=artifact_visualization_enabled,
            )
            output_artifacts[output_name] = artifact_id

        return output_artifacts

    def load_and_run_hook(
        self,
        hook_source: "Source",
        step_exception: Optional[BaseException],
    ) -> None:
        """Loads hook source and runs the hook.

        Args:
            hook_source: The source of the hook function.
            step_exception: The exception of the original step.
        """
        try:
            hook = source_utils.load(hook_source)
            hook_spec = inspect.getfullargspec(inspect.unwrap(hook))

            function_params = self._parse_hook_inputs(
                args=hook_spec.args,
                annotations=hook_spec.annotations,
                step_exception=step_exception,
            )
            logger.debug(f"Running hook {hook} with params: {function_params}")
            hook(**function_params)
        except Exception as e:
            logger.error(
                f"Failed to load hook source with exception: '{hook_source}': {e}"
            )
