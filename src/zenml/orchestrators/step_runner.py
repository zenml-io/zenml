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
import os
from contextlib import nullcontext
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Tuple,
    Type,
)

from zenml.artifacts.unmaterialized_artifact import UnmaterializedArtifact
from zenml.artifacts.utils import _store_artifact_data_and_prepare_request
from zenml.client import Client
from zenml.config.step_configurations import StepConfiguration
from zenml.config.step_run_info import StepRunInfo
from zenml.constants import (
    ENV_ZENML_DISABLE_STEP_LOGS_STORAGE,
    ENV_ZENML_STEP_OPERATOR,
    handle_bool_env_var,
)
from zenml.enums import ArtifactSaveType
from zenml.exceptions import StepInterfaceError
from zenml.hooks.hook_validators import load_and_run_hook
from zenml.logger import get_logger
from zenml.logging.step_logging import PipelineLogsStorageContext, redirected
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.materializers.in_memory_materializer import InMemoryMaterializer
from zenml.models.v2.core.step_run import (
    StepRunInputResponse,
    StepRunUpdate,
)
from zenml.orchestrators.publish_utils import (
    publish_step_run_metadata,
    publish_successful_step_run,
    step_exception_info,
)
from zenml.orchestrators.utils import (
    is_setting_enabled,
)
from zenml.steps.heartbeat import (
    StepHeartBeatTerminationException,
    StepHeartbeatWorker,
)
from zenml.steps.step_context import (
    StepContext,
    get_step_context,
)
from zenml.steps.utils import (
    OutputSignature,
    parse_return_type_annotations,
    resolve_type_annotation,
)
from zenml.utils import (
    env_utils,
    exception_utils,
    materializer_utils,
    source_utils,
    string_utils,
    tag_utils,
)
from zenml.utils.typing_utils import get_args, get_origin, is_union

if TYPE_CHECKING:
    from zenml.artifact_stores import BaseArtifactStore
    from zenml.config.step_configurations import Step
    from zenml.models import (
        ArtifactVersionResponse,
        PipelineRunResponse,
        StepRunResponse,
    )
    from zenml.stack import Stack
    from zenml.steps import BaseStep


logger = get_logger(__name__)


class StepRunner:
    """Class to run steps."""

    def __init__(
        self,
        step: "Step",
        stack: "Stack",
    ):
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
        pipeline_run: "PipelineRunResponse",
        step_run: "StepRunResponse",
        input_artifacts: Dict[str, List["StepRunInputResponse"]],
        output_artifact_uris: Dict[str, str],
        step_run_info: StepRunInfo,
    ) -> None:
        """Runs the step.

        Args:
            pipeline_run: The model of the current pipeline run.
            step_run: The model of the current step run.
            input_artifacts: The input artifact versions of the step.
            output_artifact_uris: The URIs of the output artifacts of the step.
            step_run_info: The step run info.

        Raises:
            BaseException: A general exception if the step fails.
            StepHeartBeatTerminationException: if step heartbeat is enabled and the step is remotely stopped.
        """
        from zenml.deployers.server import runtime

        if handle_bool_env_var(ENV_ZENML_DISABLE_STEP_LOGS_STORAGE, False):
            step_logging_enabled = False
        else:
            enabled_on_step = step_run.config.enable_step_logs
            enabled_on_pipeline = pipeline_run.config.enable_step_logs

            step_logging_enabled = is_setting_enabled(
                is_enabled_on_step=enabled_on_step,
                is_enabled_on_pipeline=enabled_on_pipeline,
            )

        logs_context = nullcontext()
        if step_logging_enabled and not redirected.get():
            if step_run.logs:
                logs_context = PipelineLogsStorageContext(  # type: ignore[assignment]
                    logs_uri=step_run.logs.uri,
                    artifact_store=self._stack.artifact_store,
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

            output_annotations = parse_return_type_annotations(
                func=step_instance.entrypoint
            )

            self._evaluate_artifact_names_in_collections(
                step_run,
                output_annotations,
                [
                    output_artifact_uris,
                    output_materializers,
                ],
            )

            self._stack.prepare_step_run(info=step_run_info)

            step_context = StepContext(
                pipeline_run=pipeline_run,
                step_run=step_run,
                output_materializers=output_materializers,
                output_artifact_uris=output_artifact_uris,
                output_artifact_configs={
                    k: v.artifact_config for k, v in output_annotations.items()
                },
            )

            with step_context:
                function_params = self._parse_inputs(
                    args=spec.args,
                    annotations=spec.annotations,
                    input_artifacts=input_artifacts,
                )

                # Get all step environment variables. For most orchestrators, the
                # non-secret environment variables have been set before by the
                # orchestrator. But for some orchestrators, this is not possible and
                # we therefore make sure to set them here so they're at least
                # available for the user code.
                step_environment = env_utils.get_step_environment(
                    step_config=step_run.config, stack=self._stack
                )
                secret_environment = env_utils.get_step_secret_environment(
                    step_config=step_run.config, stack=self._stack
                )
                step_environment.update(secret_environment)

                step_failed = False

                # To have a cross-platform compatible handling of main thread termination
                # we use Python's interrupt_main instead of termination signals (not Windows supported).
                # Since interrupt_main raises KeyboardInterrupt we want in this context to capture it
                # and handle it as a custom exception.

                heartbeat_worker = StepHeartbeatWorker(step_id=step_run.id)

                try:
                    if self._step.spec.enable_heartbeat:
                        logger.info(
                            "Initiating heartbeat for step: %s (%s)",
                            step_run.name,
                            step_run.id,
                        )
                        heartbeat_worker.start()
                    if (
                        # TODO: do we need to disable this for dynamic pipelines?
                        pipeline_run.snapshot
                        and self._stack.orchestrator.run_init_cleanup_at_step_level
                    ):
                        self._stack.orchestrator.run_init_hook(
                            snapshot=pipeline_run.snapshot
                        )

                    with env_utils.temporary_environment(step_environment):
                        return_values = step_instance.call_entrypoint(
                            **function_params
                        )
                except BaseException as step_exception:  # noqa: E722
                    step_failed = True

                    exception_info = (
                        exception_utils.collect_exception_information(
                            step_exception, step_instance
                        )
                    )

                    if ENV_ZENML_STEP_OPERATOR in os.environ:
                        # We're running in a step operator environment, so we can't
                        # depend on the step launcher to publish the exception info
                        Client().zen_store.update_run_step(
                            step_run_id=step_run_info.step_run_id,
                            step_run_update=StepRunUpdate(
                                exception_info=exception_info,
                            ),
                        )
                    else:
                        # This will be published by the step launcher
                        step_exception_info.set(exception_info)

                    if not step_run.is_retriable:
                        if (
                            failure_hook_source
                            := self.configuration.failure_hook_source
                        ):
                            logger.info("Detected failure hook. Running...")
                            with env_utils.temporary_environment(
                                step_environment
                            ):
                                load_and_run_hook(
                                    failure_hook_source,
                                    step_exception=step_exception,
                                )
                    if (
                        isinstance(step_exception, KeyboardInterrupt)
                        and heartbeat_worker.is_terminated
                    ):
                        raise StepHeartBeatTerminationException(
                            "Remotely stopped step - terminating execution."
                        )
                    raise step_exception
                finally:
                    heartbeat_worker.stop()
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
                        if (
                            success_hook_source
                            := self.configuration.success_hook_source
                        ):
                            logger.info("Detected success hook. Running...")
                            with env_utils.temporary_environment(
                                step_environment
                            ):
                                load_and_run_hook(
                                    success_hook_source,
                                    step_exception=None,
                                )

                        # Store and publish the output artifacts of the step function.
                        output_data = self._validate_outputs(
                            return_values, output_annotations
                        )
                        # Record outputs in serving context for fast access
                        if runtime.is_active():
                            runtime.record_step_outputs(
                                step_run.name, output_data
                            )
                        artifact_metadata_enabled = is_setting_enabled(
                            is_enabled_on_step=step_run_info.config.enable_artifact_metadata,
                            is_enabled_on_pipeline=step_run_info.pipeline.enable_artifact_metadata,
                        )
                        artifact_visualization_enabled = is_setting_enabled(
                            is_enabled_on_step=step_run_info.config.enable_artifact_visualization,
                            is_enabled_on_pipeline=step_run_info.pipeline.enable_artifact_visualization,
                        )
                        output_artifacts = self._store_output_artifacts(
                            output_data=output_data,
                            output_artifact_uris=output_artifact_uris,
                            output_materializers=output_materializers,
                            output_annotations=output_annotations,
                            artifact_metadata_enabled=artifact_metadata_enabled,
                            artifact_visualization_enabled=artifact_visualization_enabled,
                        )

                        if (
                            model_version := step_run.model_version
                            or pipeline_run.model_version
                        ):
                            from zenml.orchestrators import step_run_utils

                            step_run_utils.link_output_artifacts_to_model_version(
                                artifacts={
                                    k: [v] for k, v in output_artifacts.items()
                                },
                                model_version=model_version,
                            )

                    # We run the cleanup hook at step level if we're not in an
                    # environment that supports a shared run context
                    if (
                        pipeline_run.snapshot
                        and self._stack.orchestrator.run_init_cleanup_at_step_level
                    ):
                        self._stack.orchestrator.run_cleanup_hook(
                            snapshot=pipeline_run.snapshot
                        )

            # Update the status and output artifacts of the step run.
            output_artifact_ids = {
                output_name: [
                    artifact.id,
                ]
                for output_name, artifact in output_artifacts.items()
            }
            publish_successful_step_run(
                step_run_id=step_run_info.step_run_id,
                output_artifact_ids=output_artifact_ids,
            )

    def _evaluate_artifact_names_in_collections(
        self,
        step_run: "StepRunResponse",
        output_annotations: Dict[str, OutputSignature],
        collections: List[Dict[str, Any]],
    ) -> None:
        """Evaluates the artifact names in the collections.

        Args:
            step_run: The step run.
            output_annotations: The output annotations of the step function
                (also evaluated).
            collections: The collections to evaluate.
        """
        collections.append(output_annotations)
        for k, v in list(output_annotations.items()):
            name = k
            if v.artifact_config and v.artifact_config.name:
                name = string_utils.format_name_template(
                    v.artifact_config.name,
                    substitutions=step_run.config.substitutions,
                )

            for d in collections:
                d[name] = d.pop(k)

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
                materializer_class: Type[BaseMaterializer] = (
                    source_utils.load_and_validate_class(
                        source, expected_class=BaseMaterializer
                    )
                )
                output_materializers.append(materializer_class)

            materializers[name] = tuple(output_materializers)

        return materializers

    def _parse_inputs(
        self,
        args: List[str],
        annotations: Dict[str, Any],
        input_artifacts: Dict[str, List["StepRunInputResponse"]],
    ) -> Dict[str, Any]:
        """Parses the inputs for a step entrypoint function.

        Args:
            args: The arguments of the step entrypoint function.
            annotations: The annotations of the step entrypoint function.
            input_artifacts: The input artifact versions of the step.

        Raises:
            RuntimeError: If a function argument value is missing.
            StepInterfaceError: If the function argument annotation is invalid.

        Returns:
            The parsed inputs for the step entrypoint function.
        """
        function_params: Dict[str, Any] = {}

        if args and args[0] == "self":
            args.pop(0)

        for arg in args:
            annotation = annotations.get(arg, None)
            arg_type = resolve_type_annotation(annotation)

            if arg in input_artifacts:
                artifact_list = input_artifacts[arg]

                if len(artifact_list) == 1:
                    function_params[arg] = self._load_input_artifact(
                        artifact_list[0], arg_type
                    )
                else:
                    item_arg_type = arg_type
                    collection_type = list

                    if arg_type == UnmaterializedArtifact:
                        raise StepInterfaceError(
                            "Passing multiple unmaterialized artifacts to a "
                            "step is not allowed."
                        )
                    elif arg_type in (Any, None):
                        pass
                    elif issubclass(arg_type, (list, tuple)):
                        assert annotation
                        item_arg_type = get_args(annotation)[0]
                        item_arg_type = resolve_type_annotation(item_arg_type)
                        collection_type = arg_type
                    else:
                        raise StepInterfaceError(
                            "Passing multiple artifacts to a step is only "
                            "allowed if the argument type is a list or tuple."
                        )

                    function_params[arg] = collection_type(
                        self._load_input_artifact(artifact, item_arg_type)
                        for artifact in artifact_list
                    )
            elif arg in self.configuration.parameters:
                function_params[arg] = self.configuration.parameters[arg]
            else:
                breakpoint()
                raise RuntimeError(
                    f"Unable to find value for step function argument `{arg}`."
                )

        return function_params

    def _load_input_artifact(
        self, artifact: "StepRunInputResponse", data_type: Type[Any]
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
            return UnmaterializedArtifact(
                **artifact.get_hydrated_version().model_dump()
            )

        if data_type in (None, Any) or is_union(get_origin(data_type)):
            # Entrypoint function does not define a specific type for the input,
            # we use the datatype of the stored artifact
            data_type = source_utils.load(artifact.data_type)

        from zenml.orchestrators.utils import (
            register_artifact_store_filesystem,
        )

        materializer_class: Type[BaseMaterializer] = (
            source_utils.load_and_validate_class(
                artifact.materializer, expected_class=BaseMaterializer
            )
        )

        def _load_artifact(artifact_store: "BaseArtifactStore") -> Any:
            materializer: BaseMaterializer = materializer_class(
                uri=artifact.uri, artifact_store=artifact_store
            )

            if artifact.chunk_index is not None:
                # We need to skip the type compatibility check here because
                # the annotation on the step input might not be something that
                # the materializer can load.
                return materializer.load_item(
                    data_type=data_type,
                    index=artifact.chunk_index,
                )
            else:
                materializer.validate_load_type_compatibility(data_type)
                return materializer.load(data_type=data_type)

        if artifact.artifact_store_id == self._stack.artifact_store.id:
            # Register the artifact store of the active stack here to avoid
            # unnecessary component/flavor calls when using
            # `register_artifact_store_filesystem(...)`
            self._stack.artifact_store._register()
            return _load_artifact(artifact_store=self._stack.artifact_store)
        else:
            with register_artifact_store_filesystem(
                artifact.artifact_store_id
            ) as target_artifact_store:
                return _load_artifact(artifact_store=target_artifact_store)

    def _validate_outputs(
        self,
        return_values: Any,
        output_annotations: Dict[str, OutputSignature],
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
        invocation_id = self._step.spec.invocation_id

        # if there are no outputs, the return value must be `None`.
        if len(output_annotations) == 0:
            if return_values is not None:
                raise StepInterfaceError(
                    f"Wrong step function output type for step `{invocation_id}`: "
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
                f"Wrong step function output type for step `{invocation_id}`: "
                f"Expected multiple outputs ({output_annotations}) but "
                f"the function did not return a list or tuple "
                f"(actual return value: {return_values})."
            )

        # The amount of actual outputs must be the same as the amount of
        # expected outputs.
        if len(output_annotations) != len(return_values):
            raise StepInterfaceError(
                f"Wrong amount of step function outputs for step "
                f"'{invocation_id}: Expected {len(output_annotations)} outputs "
                f"but the function returned {len(return_values)} outputs"
                f"(return values: {return_values})."
            )

        from zenml.steps.utils import get_args

        validated_outputs: Dict[str, Any] = {}
        for return_value, (output_name, output_annotation) in zip(
            return_values, output_annotations.items()
        ):
            output_type = output_annotation.resolved_annotation
            if output_type is Any:
                pass
            else:
                if is_union(get_origin(output_type)):
                    output_type = get_args(output_type)

                if not isinstance(return_value, output_type):
                    raise StepInterfaceError(
                        f"Wrong type for output '{output_name}' of step "
                        f"'{invocation_id}' (expected type: {output_type}, "
                        f"actual type: {type(return_value)})."
                    )
            validated_outputs[output_name] = return_value
        return validated_outputs

    def _store_output_artifacts(
        self,
        output_data: Dict[str, Any],
        output_materializers: Dict[str, Tuple[Type[BaseMaterializer], ...]],
        output_artifact_uris: Dict[str, str],
        output_annotations: Dict[str, OutputSignature],
        artifact_metadata_enabled: bool,
        artifact_visualization_enabled: bool,
    ) -> Dict[str, "ArtifactVersionResponse"]:
        """Stores the output artifacts of the step.

        Args:
            output_data: The output data of the step function, mapping output
                names to return values.
            output_materializers: The output materializers of the step.
            output_artifact_uris: The output artifact URIs of the step.
            output_annotations: The output annotations of the step function.
            artifact_metadata_enabled: Whether artifact metadata collection is
                enabled.
            artifact_visualization_enabled: Whether artifact visualization is
                enabled.

        Returns:
            The IDs of the published output artifacts.
        """
        from zenml.deployers.server import runtime

        step_context = get_step_context()
        artifact_requests = []

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
                    default_materializer_class: Type[BaseMaterializer] = (
                        source_utils.load_and_validate_class(
                            default_materializer_source,
                            expected_class=BaseMaterializer,
                        )
                    )
                    materializer_registry.default_materializer = (
                        default_materializer_class
                    )

                materializer_class = materializer_registry[data_type]

            uri = output_artifact_uris[output_name]
            artifact_config = output_annotations[output_name].artifact_config

            artifact_type = None
            if artifact_config is not None:
                has_custom_name = bool(artifact_config.name)
                version = artifact_config.version
                artifact_type = artifact_config.artifact_type
            else:
                has_custom_name, version = False, None

            if runtime.should_skip_artifact_materialization():
                # Use the artifact type of the original materializer...
                artifact_type = (
                    artifact_type
                    or materializer_class.ASSOCIATED_ARTIFACT_TYPE
                )
                # ... but use the in-memory materializer to store the data
                materializer_class = InMemoryMaterializer

            # Override the artifact name if it is not a custom name.
            if has_custom_name:
                artifact_name = output_name
            else:
                if step_context.pipeline_run.pipeline:
                    pipeline_name = step_context.pipeline_run.pipeline.name
                else:
                    pipeline_name = "unlisted"
                step_name = step_context.step_run.name
                artifact_name = f"{pipeline_name}::{step_name}::{output_name}"

            # Get metadata that the user logged manually
            user_metadata = step_context.get_output_metadata(output_name)

            # Get full set of tags
            tags = step_context.get_output_tags(output_name)
            if step_context.pipeline_run.config.tags is not None:
                for tag in step_context.pipeline_run.config.tags:
                    if isinstance(tag, tag_utils.Tag) and tag.cascade is True:
                        tags.append(tag.name)

            artifact_request = _store_artifact_data_and_prepare_request(
                name=artifact_name,
                data=return_value,
                materializer_class=materializer_class,
                uri=uri,
                artifact_type=artifact_type,
                store_metadata=artifact_metadata_enabled,
                store_visualizations=artifact_visualization_enabled,
                has_custom_name=has_custom_name,
                version=version,
                tags=tags,
                save_type=ArtifactSaveType.STEP_OUTPUT,
                metadata=user_metadata,
            )
            artifact_requests.append(artifact_request)

        responses = Client().zen_store.batch_create_artifact_versions(
            artifact_requests
        )
        return dict(zip(output_data.keys(), responses))
