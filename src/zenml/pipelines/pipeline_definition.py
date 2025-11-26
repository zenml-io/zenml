#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Definition of a ZenML pipeline."""

import copy
import hashlib
import inspect
from contextlib import contextmanager, nullcontext
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterator,
    List,
    Mapping,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
)
from uuid import UUID

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError, create_model
from typing_extensions import Self

from zenml.analytics.enums import AnalyticsEvent
from zenml.analytics.utils import track_handler
from zenml.client import Client
from zenml.config.compiler import Compiler
from zenml.config.pipeline_configurations import (
    PipelineConfiguration,
    PipelineConfigurationUpdate,
)
from zenml.config.pipeline_run_configuration import PipelineRunConfiguration
from zenml.config.pipeline_spec import PipelineSpec
from zenml.config.schedule import Schedule
from zenml.config.step_configurations import StepConfigurationUpdate
from zenml.constants import (
    ENV_ZENML_DISABLE_PIPELINE_LOGS_STORAGE,
    handle_bool_env_var,
)
from zenml.enums import StackComponentType
from zenml.exceptions import EntityExistsError
from zenml.execution.pipeline.utils import (
    should_prevent_pipeline_execution,
    submit_pipeline,
)
from zenml.hooks.hook_validators import resolve_and_validate_hook
from zenml.logger import get_logger
from zenml.logging.step_logging import (
    PipelineLogsStorageContext,
    prepare_logs_uri,
)
from zenml.models import (
    CodeReferenceRequest,
    DeploymentResponse,
    LogsRequest,
    PipelineBuildBase,
    PipelineBuildResponse,
    PipelineRequest,
    PipelineResponse,
    PipelineRunResponse,
    PipelineSnapshotBase,
    PipelineSnapshotRequest,
    PipelineSnapshotResponse,
    RunTemplateResponse,
    ScheduleRequest,
)
from zenml.pipelines import build_utils
from zenml.pipelines.compilation_context import PipelineCompilationContext
from zenml.pipelines.run_utils import (
    create_placeholder_run,
    upload_notebook_cell_code_if_necessary,
)
from zenml.stack import Stack
from zenml.steps import BaseStep
from zenml.steps.entrypoint_function_utils import StepArtifact
from zenml.steps.step_invocation import StepInvocation
from zenml.steps.utils import get_unique_step_output_names
from zenml.utils import (
    code_repository_utils,
    code_utils,
    dashboard_utils,
    dict_utils,
    env_utils,
    pydantic_utils,
    settings_utils,
    source_utils,
    yaml_utils,
)
from zenml.utils.string_utils import format_name_template
from zenml.utils.tag_utils import Tag

if TYPE_CHECKING:
    from zenml.artifacts.external_artifact import ExternalArtifact
    from zenml.client_lazy_loader import ClientLazyLoader
    from zenml.config.base_settings import SettingsOrDict
    from zenml.config.cache_policy import CachePolicyOrString
    from zenml.config.retry_config import StepRetryConfig
    from zenml.config.source import Source
    from zenml.enums import ExecutionMode
    from zenml.model.lazy_load import ModelVersionDataLazyLoader
    from zenml.model.model import Model
    from zenml.models import ArtifactVersionResponse
    from zenml.types import HookSpecification, InitHookSpecification

    StepConfigurationUpdateOrDict = Union[
        Dict[str, Any], StepConfigurationUpdate
    ]

logger = get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


class Pipeline:
    """ZenML pipeline class."""

    def __init__(
        self,
        name: str,
        entrypoint: F,
        enable_cache: Optional[bool] = None,
        enable_artifact_metadata: Optional[bool] = None,
        enable_artifact_visualization: Optional[bool] = None,
        enable_step_logs: Optional[bool] = None,
        environment: Optional[Dict[str, Any]] = None,
        secrets: Optional[List[Union[UUID, str]]] = None,
        enable_pipeline_logs: Optional[bool] = None,
        settings: Optional[Mapping[str, "SettingsOrDict"]] = None,
        tags: Optional[List[Union[str, "Tag"]]] = None,
        extra: Optional[Dict[str, Any]] = None,
        on_failure: Optional["HookSpecification"] = None,
        on_success: Optional["HookSpecification"] = None,
        on_init: Optional["InitHookSpecification"] = None,
        on_init_kwargs: Optional[Dict[str, Any]] = None,
        on_cleanup: Optional["HookSpecification"] = None,
        model: Optional["Model"] = None,
        retry: Optional["StepRetryConfig"] = None,
        substitutions: Optional[Dict[str, str]] = None,
        execution_mode: Optional["ExecutionMode"] = None,
        cache_policy: Optional["CachePolicyOrString"] = None,
        **kwargs: Any,
    ) -> None:
        """Initializes a pipeline.

        Args:
            name: The name of the pipeline.
            entrypoint: The entrypoint function of the pipeline.
            enable_cache: If caching should be enabled for this pipeline.
            enable_artifact_metadata: If artifact metadata should be enabled for
                this pipeline.
            enable_artifact_visualization: If artifact visualization should be
                enabled for this pipeline.
            enable_step_logs: If step logs should be enabled for this pipeline.
            environment: Environment variables to set when running this
                pipeline.
            secrets: Secrets to set as environment variables when running this
                pipeline.
            enable_pipeline_logs: If pipeline logs should be enabled for this pipeline.
            settings: Settings for this pipeline.
            tags: Tags to apply to runs of this pipeline.
            extra: Extra configurations for this pipeline.
            on_failure: Callback function in event of failure of the step. Can
                be a function with a single argument of type `BaseException`, or
                a source path to such a function (e.g. `module.my_function`).
            on_success: Callback function in event of success of the step. Can
                be a function with no arguments, or a source path to such a
                function (e.g. `module.my_function`).
            on_init: Callback function to run on initialization of the pipeline.
                Can be a function with no arguments, or a source path to such a
                function (e.g. `module.my_function`) if the function returns a
                value, it will be stored as the pipeline state.
            on_init_kwargs: Arguments for the init hook.
            on_cleanup: Callback function to run on cleanup of the pipeline. Can
                be a function with no arguments, or a source path to such a
                function with no arguments (e.g. `module.my_function`).
            model: configuration of the model in the Model Control Plane.
            retry: Retry configuration for the pipeline steps.
            substitutions: Extra placeholders to use in the name templates.
            execution_mode: The execution mode of the pipeline.
            cache_policy: Cache policy for this pipeline.
            **kwargs: Additional keyword arguments.
        """
        self._invocations: Dict[str, StepInvocation] = {}
        self._run_args: Dict[str, Any] = {}

        self._configuration = PipelineConfiguration(
            name=name,
        )
        self._from_config_file: Dict[str, Any] = {}
        with self.__suppress_configure_warnings__():
            self.configure(
                enable_cache=enable_cache,
                enable_artifact_metadata=enable_artifact_metadata,
                enable_artifact_visualization=enable_artifact_visualization,
                enable_step_logs=enable_step_logs,
                environment=environment,
                secrets=secrets,
                enable_pipeline_logs=enable_pipeline_logs,
                settings=settings,
                tags=tags,
                extra=extra,
                on_failure=on_failure,
                on_success=on_success,
                on_init=on_init,
                on_init_kwargs=on_init_kwargs,
                on_cleanup=on_cleanup,
                model=model,
                retry=retry,
                substitutions=substitutions,
                execution_mode=execution_mode,
                cache_policy=cache_policy,
            )
        self.entrypoint = entrypoint
        self._parameters: Dict[str, Any] = {}
        self._output_artifacts: List[StepArtifact] = []

        self.__suppress_warnings_flag__ = False

    @property
    def name(self) -> str:
        """The name of the pipeline.

        Returns:
            The name of the pipeline.
        """
        return self.configuration.name

    @property
    def is_dynamic(self) -> bool:
        """If the pipeline is dynamic.

        Returns:
            If the pipeline is dynamic.
        """
        return False

    @property
    def enable_cache(self) -> Optional[bool]:
        """If caching is enabled for the pipeline.

        Returns:
            If caching is enabled for the pipeline.
        """
        return self.configuration.enable_cache

    @property
    def configuration(self) -> PipelineConfiguration:
        """The configuration of the pipeline.

        Returns:
            The configuration of the pipeline.
        """
        return self._configuration

    @property
    def invocations(self) -> Dict[str, StepInvocation]:
        """Returns the step invocations of this pipeline.

        This dictionary will only be populated once the pipeline has been
        called.

        Returns:
            The step invocations.
        """
        return self._invocations

    def resolve(self) -> "Source":
        """Resolves the pipeline.

        Returns:
            The pipeline source.
        """
        return source_utils.resolve(self.entrypoint, skip_validation=True)

    @property
    def source_object(self) -> Any:
        """The source object of this pipeline.

        Returns:
            The source object of this pipeline.
        """
        return self.entrypoint

    @property
    def source_code(self) -> str:
        """The source code of this pipeline.

        Returns:
            The source code of this pipeline.
        """
        return inspect.getsource(self.source_object)

    @property
    def model(self) -> "PipelineResponse":
        """Gets the registered pipeline model for this instance.

        Returns:
            The registered pipeline model.

        Raises:
            RuntimeError: If the pipeline has not been registered yet.
        """
        pipelines = Client().list_pipelines(name=self.name)
        if len(pipelines) == 1:
            return pipelines.items[0]

        raise RuntimeError(
            f"Cannot get the model of pipeline '{self.name}' because it has "
            f"not been registered yet. Please ensure that the pipeline has "
            f"been run or built and try again."
        )

    @contextmanager
    def __suppress_configure_warnings__(self) -> Iterator[Any]:
        """Context manager to suppress warnings in `Pipeline.configure(...)`.

        Used to suppress warnings when called from inner code and not user-facing code.

        Yields:
            Nothing.
        """
        self.__suppress_warnings_flag__ = True
        yield
        self.__suppress_warnings_flag__ = False

    def configure(
        self,
        enable_cache: Optional[bool] = None,
        enable_artifact_metadata: Optional[bool] = None,
        enable_artifact_visualization: Optional[bool] = None,
        enable_step_logs: Optional[bool] = None,
        environment: Optional[Dict[str, Any]] = None,
        secrets: Optional[Sequence[Union[UUID, str]]] = None,
        enable_pipeline_logs: Optional[bool] = None,
        settings: Optional[Mapping[str, "SettingsOrDict"]] = None,
        tags: Optional[List[Union[str, "Tag"]]] = None,
        extra: Optional[Dict[str, Any]] = None,
        on_failure: Optional["HookSpecification"] = None,
        on_success: Optional["HookSpecification"] = None,
        on_init: Optional["InitHookSpecification"] = None,
        on_init_kwargs: Optional[Dict[str, Any]] = None,
        on_cleanup: Optional["HookSpecification"] = None,
        model: Optional["Model"] = None,
        retry: Optional["StepRetryConfig"] = None,
        parameters: Optional[Dict[str, Any]] = None,
        substitutions: Optional[Dict[str, str]] = None,
        execution_mode: Optional["ExecutionMode"] = None,
        cache_policy: Optional["CachePolicyOrString"] = None,
        merge: bool = True,
    ) -> Self:
        """Configures the pipeline.

        Configuration merging example:
        * `merge==True`:
            pipeline.configure(extra={"key1": 1})
            pipeline.configure(extra={"key2": 2}, merge=True)
            pipeline.configuration.extra # {"key1": 1, "key2": 2}
        * `merge==False`:
            pipeline.configure(extra={"key1": 1})
            pipeline.configure(extra={"key2": 2}, merge=False)
            pipeline.configuration.extra # {"key2": 2}

        Args:
            enable_cache: If caching should be enabled for this pipeline.
            enable_artifact_metadata: If artifact metadata should be enabled for
                this pipeline.
            enable_artifact_visualization: If artifact visualization should be
                enabled for this pipeline.
            enable_step_logs: If step logs should be enabled for this pipeline.
            environment: Environment variables to set when running this
                pipeline.
            secrets: Secrets to set as environment variables when running this
                pipeline.
            settings: Settings for this pipeline.
            enable_pipeline_logs: If pipeline logs should be enabled for this pipeline.
            settings: settings for this pipeline.
            tags: Tags to apply to runs of this pipeline.
            extra: Extra configurations for this pipeline.
            on_failure: Callback function in event of failure of the step. Can
                be a function with a single argument of type `BaseException`, or
                a source path to such a function (e.g. `module.my_function`).
            on_success: Callback function in event of success of the step. Can
                be a function with no arguments, or a source path to such a
                function (e.g. `module.my_function`).
            on_init: Callback function to run on initialization of the pipeline.
                Can be a function with no arguments, or a source path to such a
                function (e.g. `module.my_function`) if the function returns a
                value, it will be stored as the pipeline state.
            on_init_kwargs: Arguments for the init hook.
            on_cleanup: Callback function to run on cleanup of the pipeline. Can
                be a function with no arguments, or a source path to such a
                function with no arguments (e.g. `module.my_function`).
            model: configuration of the model version in the Model Control Plane.
            retry: Retry configuration for the pipeline steps.
            parameters: input parameters for the pipeline.
            substitutions: Extra placeholders to use in the name templates.
            execution_mode: The execution mode of the pipeline.
            cache_policy: Cache policy for this pipeline.
            merge: If `True`, will merge the given dictionary configurations
                like `extra` and `settings` with existing
                configurations. If `False` the given configurations will
                overwrite all existing ones. See the general description of this
                method for an example.

        Returns:
            The pipeline instance that this method was called on.

        Raises:
            ValueError: If on_init_kwargs is provided but on_init is not and
                the init hook source is found in the current pipeline
                configuration.
        """
        failure_hook_source = None
        if on_failure:
            # string of on_failure hook function to be used for this pipeline
            failure_hook_source, _ = resolve_and_validate_hook(
                on_failure, allow_exception_arg=True
            )

        success_hook_source = None
        if on_success:
            # string of on_success hook function to be used for this pipeline
            success_hook_source, _ = resolve_and_validate_hook(on_success)

        init_hook_kwargs = None
        init_hook_source = None
        if on_init or on_init_kwargs:
            if not on_init and self.configuration.init_hook_source:
                # load the init hook source from the existing configuration if
                # not provided; this is needed for partial updates
                on_init = source_utils.load(
                    self.configuration.init_hook_source
                )
            if not on_init:
                raise ValueError(
                    "on_init is not provided and no init hook source is found "
                    "in the existing configuration"
                )

            # string of on_init hook function and JSON-able arguments to be used
            # for this pipeline
            init_hook_source, init_hook_kwargs = resolve_and_validate_hook(
                on_init, on_init_kwargs
            )

        cleanup_hook_source = None
        if on_cleanup:
            # string of on_cleanup hook function to be used for this pipeline
            cleanup_hook_source, _ = resolve_and_validate_hook(on_cleanup)

        if merge and tags and self._configuration.tags:
            # Merge tags explicitly here as the recursive update later only
            # merges dicts
            tags = self._configuration.tags + tags

        if merge and secrets and self._configuration.secrets:
            secrets = self._configuration.secrets + list(secrets)

        values = dict_utils.remove_none_values(
            {
                "enable_cache": enable_cache,
                "enable_artifact_metadata": enable_artifact_metadata,
                "enable_artifact_visualization": enable_artifact_visualization,
                "enable_step_logs": enable_step_logs,
                "environment": environment,
                "secrets": secrets,
                "enable_pipeline_logs": enable_pipeline_logs,
                "settings": settings,
                "tags": tags,
                "extra": extra,
                "failure_hook_source": failure_hook_source,
                "success_hook_source": success_hook_source,
                "init_hook_source": init_hook_source,
                "init_hook_kwargs": init_hook_kwargs,
                "cleanup_hook_source": cleanup_hook_source,
                "model": model,
                "retry": retry,
                "parameters": parameters,
                "substitutions": substitutions,
                "execution_mode": execution_mode,
                "cache_policy": cache_policy,
            }
        )
        if not self.__suppress_warnings_flag__:
            to_be_reapplied = []
            for param_, value_ in values.items():
                if (
                    param_ in PipelineRunConfiguration.model_fields
                    and param_ in self._from_config_file
                    and value_ != self._from_config_file[param_]
                ):
                    to_be_reapplied.append(
                        (param_, self._from_config_file[param_], value_)
                    )
            if to_be_reapplied:
                msg = ""
                reapply_during_run_warning = (
                    "The value of parameter '{name}' has changed from "
                    "'{file_value}' to '{new_value}' set in your configuration "
                    "file.\n"
                )
                for name, file_value, new_value in to_be_reapplied:
                    msg += reapply_during_run_warning.format(
                        name=name, file_value=file_value, new_value=new_value
                    )
                msg += (
                    "Configuration file value will be used during pipeline "
                    "run, so you change will not be efficient. Consider "
                    "updating your configuration file instead."
                )
                logger.warning(msg)

        config = PipelineConfigurationUpdate(**values)
        self._apply_configuration(config, merge=merge)
        return self

    @property
    def required_parameters(self) -> List[str]:
        """List of required parameters for the pipeline entrypoint.

        Returns:
            List of required parameters for the pipeline entrypoint.
        """
        signature = inspect.signature(self.entrypoint, follow_wrapped=True)
        return [
            parameter.name
            for parameter in signature.parameters.values()
            if parameter.default is inspect.Parameter.empty
        ]

    @property
    def missing_parameters(self) -> List[str]:
        """List of missing parameters for the pipeline entrypoint.

        Returns:
            List of missing parameters for the pipeline entrypoint.
        """
        available_parameters = set(self.configuration.parameters or {})
        if params_from_file := self._from_config_file.get("parameters", None):
            available_parameters.update(params_from_file)

        return list(set(self.required_parameters) - available_parameters)

    @property
    def is_prepared(self) -> bool:
        """If the pipeline is prepared.

        Prepared means that the pipeline entrypoint has been called and the
        pipeline is fully defined.

        Returns:
            If the pipeline is prepared.
        """
        return len(self.invocations) > 0

    def prepare(self, *args: Any, **kwargs: Any) -> None:
        """Prepares the pipeline.

        Args:
            *args: Pipeline entrypoint input arguments.
            **kwargs: Pipeline entrypoint input keyword arguments.
        """
        self._clear_state()

        kwargs = self._apply_config_parameters(kwargs)
        self._parameters = self._validate_entrypoint_args(*args, **kwargs)

        with PipelineCompilationContext(pipeline=self):
            self._prepare_invocations(**self._parameters)

    def _validate_entrypoint_args(
        self, *args: Any, **kwargs: Any
    ) -> Dict[str, Any]:
        """Validates the arguments for the pipeline entrypoint.

        Args:
            *args: Entrypoint function arguments.
            **kwargs: Entrypoint function keyword arguments.

        Raises:
            ValueError: If the arguments are invalid or missing.

        Returns:
            The validated arguments.
        """
        try:
            validated_args = pydantic_utils.validate_function_args(
                self.entrypoint,
                ConfigDict(arbitrary_types_allowed=False),
                *args,
                **kwargs,
            )
        except ValidationError as e:
            raise ValueError(
                "Invalid or missing pipeline function entrypoint arguments. "
                "Only JSON serializable inputs are allowed as pipeline inputs. "
                "Check out the pydantic error above for more details."
            ) from e

        return validated_args

    def _apply_config_parameters(
        self, kwargs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Applies the configuration parameters to the code arguments.

        Args:
            kwargs: The code arguments to apply the configuration parameters to.

        Raises:
            RuntimeError: If different values for the same key are passed in
                code and configuration.

        Returns:
            The merged arguments.
        """
        kwargs = kwargs.copy()
        conflicting_parameters = {}
        config_parameters = self.configuration.parameters or {}
        if from_file_ := self._from_config_file.get("parameters", None):
            config_parameters = dict_utils.recursive_update(
                config_parameters, from_file_
            )

        if config_parameters:
            for k, v_runtime in kwargs.items():
                if k in config_parameters:
                    v_config = config_parameters[k]
                    if v_config != v_runtime:
                        conflicting_parameters[k] = (v_config, v_runtime)

            if conflicting_parameters:
                is_plural = "s" if len(conflicting_parameters) > 1 else ""
                msg = f"Configured parameter{is_plural} for the pipeline `{self.name}` conflict{'' if not is_plural else 's'} with parameter{is_plural} passed in runtime:\n"
                for key, values in conflicting_parameters.items():
                    msg += f"`{key}`: config=`{values[0]}` | runtime=`{values[1]}`\n"
                msg += """This happens, if you define values for pipeline parameters in configuration file and pass same parameters from the code. Example:
```
# config.yaml
    parameters:
        param_name: value1
            
            
# pipeline.py
@pipeline
def pipeline_(param_name: str):
    step_name()

if __name__=="__main__":
    pipeline_.with_options(config_path="config.yaml")(param_name="value2")
```
To avoid this consider setting pipeline parameters only in one place (config or code).
"""
                raise RuntimeError(msg)

            for k, v_config in config_parameters.items():
                if k not in kwargs:
                    kwargs[k] = v_config

        return kwargs

    def _prepare_invocations(self, **kwargs: Any) -> None:
        """Prepares the invocations of the pipeline.

        Args:
            **kwargs: Keyword arguments.
        """
        outputs = self._call_entrypoint(**kwargs)

        output_artifacts = []
        if isinstance(outputs, StepArtifact):
            output_artifacts = [outputs]
        elif isinstance(outputs, tuple):
            for v in outputs:
                if isinstance(v, StepArtifact):
                    output_artifacts.append(v)
                else:
                    logger.debug(
                        "Ignore pipeline output that is not a step artifact: %s",
                        v,
                    )

        self._output_artifacts = output_artifacts

    def register(self) -> "PipelineResponse":
        """Register the pipeline in the server.

        Returns:
            The registered pipeline model.
        """
        client = Client()

        def _get() -> PipelineResponse:
            matching_pipelines = client.list_pipelines(
                name=self.name,
                size=1,
                sort_by="desc:created",
            )

            if matching_pipelines.total:
                registered_pipeline = matching_pipelines.items[0]
                return registered_pipeline
            raise RuntimeError("No matching pipelines found.")

        try:
            return _get()
        except RuntimeError:
            request = PipelineRequest(
                project=client.active_project.id,
                name=self.name,
            )

            try:
                registered_pipeline = client.zen_store.create_pipeline(
                    pipeline=request
                )
                logger.info(
                    "Registered new pipeline: `%s`.",
                    registered_pipeline.name,
                )
                return registered_pipeline
            except EntityExistsError:
                return _get()

    def build(
        self,
        settings: Optional[Mapping[str, "SettingsOrDict"]] = None,
        step_configurations: Optional[
            Mapping[str, "StepConfigurationUpdateOrDict"]
        ] = None,
        config_path: Optional[str] = None,
    ) -> Optional["PipelineBuildResponse"]:
        """Builds Docker images for the pipeline.

        Args:
            settings: Settings for the pipeline.
            step_configurations: Configurations for steps of the pipeline.
            config_path: Path to a yaml configuration file. This file will
                be parsed as a
                `zenml.config.pipeline_configurations.PipelineRunConfiguration`
                object. Options provided in this file will be overwritten by
                options provided in code using the other arguments of this
                method.

        Returns:
            The build output.
        """
        with track_handler(event=AnalyticsEvent.BUILD_PIPELINE):
            self._prepare_if_possible()

            compile_args = self._run_args.copy()
            compile_args.pop("prevent_build_reuse", None)
            if config_path:
                compile_args["config_path"] = config_path
            if step_configurations:
                compile_args["step_configurations"] = step_configurations
            if settings:
                compile_args["settings"] = settings

            snapshot, _, _ = self._compile(**compile_args)
            pipeline_id = self.register().id

            local_repo = code_repository_utils.find_active_code_repository()
            code_repository = build_utils.verify_local_repository_context(
                snapshot=snapshot, local_repo_context=local_repo
            )

            return build_utils.create_pipeline_build(
                snapshot=snapshot,
                pipeline_id=pipeline_id,
                code_repository=code_repository,
            )

    def deploy(
        self,
        deployment_name: str,
        timeout: Optional[int] = None,
        *args: Any,
        **kwargs: Any,
    ) -> DeploymentResponse:
        """Deploy the pipeline for online inference.

        Args:
            deployment_name: The name to use for the deployment.
            timeout: The maximum time in seconds to wait for the pipeline to be
                deployed.
            *args: Pipeline entrypoint input arguments.
            **kwargs: Pipeline entrypoint input keyword arguments.

        Returns:
            The deployment response.
        """
        self.prepare(*args, **kwargs)
        snapshot = self._create_snapshot(**self._run_args)

        stack = Client().active_stack

        stack.prepare_pipeline_submission(snapshot=snapshot)
        return stack.deploy_pipeline(
            snapshot=snapshot,
            deployment_name=deployment_name,
            timeout=timeout,
        )

    def _create_snapshot(
        self,
        *,
        run_name: Optional[str] = None,
        enable_cache: Optional[bool] = None,
        enable_artifact_metadata: Optional[bool] = None,
        enable_artifact_visualization: Optional[bool] = None,
        enable_step_logs: Optional[bool] = None,
        enable_pipeline_logs: Optional[bool] = None,
        schedule: Optional[Schedule] = None,
        build: Union[str, "UUID", "PipelineBuildBase", None] = None,
        settings: Optional[Mapping[str, "SettingsOrDict"]] = None,
        step_configurations: Optional[
            Mapping[str, "StepConfigurationUpdateOrDict"]
        ] = None,
        extra: Optional[Dict[str, Any]] = None,
        config_path: Optional[str] = None,
        prevent_build_reuse: bool = False,
        skip_schedule_registration: bool = False,
        **snapshot_request_kwargs: Any,
    ) -> PipelineSnapshotResponse:
        """Create a pipeline snapshot.

        Args:
            run_name: Name of the pipeline run.
            enable_cache: If caching should be enabled for this pipeline run.
            enable_artifact_metadata: If artifact metadata should be enabled
                for this pipeline run.
            enable_artifact_visualization: If artifact visualization should be
                enabled for this pipeline run.
            enable_step_logs: If step logs should be enabled for this pipeline.
            enable_pipeline_logs: If pipeline logs should be enabled for this
                pipeline run.
            schedule: Optional schedule to use for the run.
            build: Optional build to use for the run.
            settings: Settings for this pipeline run.
            step_configurations: Configurations for steps of the pipeline.
            extra: Extra configurations for this pipeline run.
            config_path: Path to a yaml configuration file. This file will
                be parsed as a
                `zenml.config.pipeline_configurations.PipelineRunConfiguration`
                object. Options provided in this file will be overwritten by
                options provided in code using the other arguments of this
                method.
            prevent_build_reuse: DEPRECATED: Use
                `DockerSettings.prevent_build_reuse` instead.
            skip_schedule_registration: Whether to skip schedule registration.
            **snapshot_request_kwargs: Additional keyword arguments to pass to
                the snapshot request.

        Returns:
            The pipeline snapshot.

        Raises:
            ValueError: If the orchestrator doesn't support scheduling, but a
                schedule was given
        """
        snapshot, schedule, build = self._compile(
            config_path=config_path,
            run_name=run_name,
            enable_cache=enable_cache,
            enable_artifact_metadata=enable_artifact_metadata,
            enable_artifact_visualization=enable_artifact_visualization,
            enable_step_logs=enable_step_logs,
            enable_pipeline_logs=enable_pipeline_logs,
            steps=step_configurations,
            settings=settings,
            schedule=schedule,
            build=build,
            extra=extra,
        )

        pipeline_id = self.register().id
        stack = Client().active_stack
        stack.validate()

        schedule_id = None
        if schedule and not skip_schedule_registration:
            if not stack.orchestrator.config.is_schedulable:
                raise ValueError(
                    f"Stack {stack.name} does not support scheduling. "
                    "Not all orchestrator types support scheduling, "
                    "kindly consult with "
                    "https://docs.zenml.io/concepts/steps_and_pipelines/scheduling "
                    "for details."
                )
            if schedule.name:
                schedule_name = schedule.name
            else:
                schedule_name = format_name_template(
                    snapshot.run_name_template,
                    substitutions=snapshot.pipeline_configuration.substitutions,
                )
            components = Client().active_stack_model.components
            orchestrator = components[StackComponentType.ORCHESTRATOR][0]
            schedule_model = ScheduleRequest(
                project=Client().active_project.id,
                pipeline_id=pipeline_id,
                orchestrator_id=orchestrator.id,
                name=schedule_name,
                active=True,
                cron_expression=schedule.cron_expression,
                start_time=schedule.start_time,
                end_time=schedule.end_time,
                interval_second=schedule.interval_second,
                catchup=schedule.catchup,
                run_once_start_time=schedule.run_once_start_time,
            )
            schedule_id = Client().zen_store.create_schedule(schedule_model).id
            logger.info(
                f"Created schedule `{schedule_name}` for pipeline "
                f"`{snapshot.pipeline_configuration.name}`."
            )

        stack = Client().active_stack
        stack.validate()
        upload_notebook_cell_code_if_necessary(snapshot=snapshot, stack=stack)

        local_repo_context = (
            code_repository_utils.find_active_code_repository()
        )
        code_repository = build_utils.verify_local_repository_context(
            snapshot=snapshot, local_repo_context=local_repo_context
        )
        can_download_from_code_repository = code_repository is not None
        if local_repo_context:
            build_utils.log_code_repository_usage(
                snapshot=snapshot, local_repo_context=local_repo_context
            )

        if prevent_build_reuse:
            logger.warning(
                "Passing `prevent_build_reuse=True` to "
                "`pipeline.with_options(...)` is deprecated. Use "
                "`DockerSettings.prevent_build_reuse` instead."
            )

        build_model = build_utils.reuse_or_create_pipeline_build(
            snapshot=snapshot,
            pipeline_id=pipeline_id,
            allow_build_reuse=not prevent_build_reuse,
            build=build,
            code_repository=code_repository,
        )
        build_id = build_model.id if build_model else None

        code_reference = None
        if local_repo_context and not local_repo_context.is_dirty:
            source_root = source_utils.get_source_root()
            subdirectory = (
                Path(source_root)
                .resolve()
                .relative_to(local_repo_context.root)
            )

            code_reference = CodeReferenceRequest(
                commit=local_repo_context.current_commit,
                subdirectory=subdirectory.as_posix(),
                code_repository=local_repo_context.code_repository.id,
            )

        code_path = None
        if build_utils.should_upload_code(
            snapshot=snapshot,
            build=build_model,
            can_download_from_code_repository=can_download_from_code_repository,
        ):
            source_root = source_utils.get_source_root()
            code_archive = code_utils.CodeArchive(root=source_root)
            logger.info(
                "Archiving pipeline code directory: `%s`. If this is taking "
                "longer than you expected, make sure your source root "
                "is set correctly by running `zenml init`, and that it "
                "does not contain unnecessarily huge files.",
                source_root,
            )

            code_path = code_utils.upload_code_if_necessary(code_archive)

        request = PipelineSnapshotRequest(
            project=Client().active_project.id,
            stack=stack.id,
            pipeline=pipeline_id,
            build=build_id,
            schedule=schedule_id,
            code_reference=code_reference,
            code_path=code_path,
            **snapshot.model_dump(),
            **snapshot_request_kwargs,
        )
        return Client().zen_store.create_snapshot(snapshot=request)

    def _run(
        self,
    ) -> Optional[PipelineRunResponse]:
        """Runs the pipeline on the active stack.

        Returns:
            The pipeline run or `None` if running with a schedule.
        """
        if should_prevent_pipeline_execution():
            logger.info("Preventing execution of pipeline '%s'.", self.name)
            return None

        logger.info(f"Initiating a new run for the pipeline: `{self.name}`.")

        with track_handler(AnalyticsEvent.RUN_PIPELINE) as analytics_handler:
            stack = Client().active_stack

            # Enable or disable pipeline run logs storage
            if self._run_args.get("schedule"):
                # Pipeline runs scheduled to run in the future are not logged
                # via the client.
                logging_enabled = False
            elif handle_bool_env_var(
                ENV_ZENML_DISABLE_PIPELINE_LOGS_STORAGE, False
            ):
                logging_enabled = False
            else:
                logging_enabled = self._run_args.get(
                    "enable_pipeline_logs",
                    self.configuration.enable_pipeline_logs
                    if self.configuration.enable_pipeline_logs is not None
                    else True,
                )

            logs_context = nullcontext()
            logs_model = None

            if logging_enabled:
                # Configure the logs
                logs_uri = prepare_logs_uri(
                    stack.artifact_store,
                )

                logs_context = PipelineLogsStorageContext(
                    logs_uri=logs_uri,
                    artifact_store=stack.artifact_store,
                    prepend_step_name=False,
                )  # type: ignore[assignment]

                logs_model = LogsRequest(
                    uri=logs_uri,
                    source="client",
                    artifact_store_id=stack.artifact_store.id,
                )

            with logs_context:
                snapshot = self._create_snapshot(**self._run_args)

                self.log_pipeline_snapshot_metadata(snapshot)
                run = (
                    create_placeholder_run(snapshot=snapshot, logs=logs_model)
                    if not snapshot.schedule
                    else None
                )

                analytics_handler.metadata = (
                    self._get_pipeline_analytics_metadata(
                        snapshot=snapshot,
                        stack=stack,
                        run_id=run.id if run else None,
                    )
                )

                if run:
                    run_url = dashboard_utils.get_run_url(run)
                    if run_url:
                        logger.info(
                            f"Dashboard URL for Pipeline Run: {run_url}"
                        )
                    else:
                        logger.info(
                            "You can visualize your pipeline runs in the `ZenML "
                            "Dashboard`. In order to try it locally, please run "
                            "`zenml login --local`."
                        )

                submit_pipeline(
                    snapshot=snapshot, stack=stack, placeholder_run=run
                )

            if run:
                return Client().get_pipeline_run(run.id)
            return None

    @staticmethod
    def log_pipeline_snapshot_metadata(
        snapshot: PipelineSnapshotResponse,
    ) -> None:
        """Displays logs based on the snapshot model upon running a pipeline.

        Args:
            snapshot: The model for the pipeline snapshot
        """
        try:
            # Log about the caching status
            if snapshot.pipeline_configuration.enable_cache is False:
                logger.info(
                    f"Caching is disabled by default for "
                    f"`{snapshot.pipeline_configuration.name}`."
                )

            # Log about the used builds
            if snapshot.build:
                logger.info("Using a build:")
                logger.info(
                    " Image(s): "
                    f"{', '.join([i.image for i in snapshot.build.images.values()])}"
                )

                # Log about version mismatches between local and build
                from zenml import __version__

                if snapshot.build.zenml_version != __version__:
                    logger.info(
                        f"ZenML version (different than the local version): "
                        f"{snapshot.build.zenml_version}"
                    )

                import platform

                if snapshot.build.python_version != platform.python_version():
                    logger.info(
                        f"Python version (different than the local version): "
                        f"{snapshot.build.python_version}"
                    )

            # Log about the user, stack and components
            if snapshot.user is not None:
                logger.info(f"Using user: `{snapshot.user.name}`")

            if snapshot.stack is not None:
                logger.info(f"Using stack: `{snapshot.stack.name}`")

                for (
                    component_type,
                    component_models,
                ) in snapshot.stack.components.items():
                    logger.info(
                        f"  {component_type.value}: `{component_models[0].name}`"
                    )
        except Exception as e:
            logger.debug(f"Logging pipeline snapshot metadata failed: {e}")

    def write_run_configuration_template(
        self, path: str, stack: Optional["Stack"] = None
    ) -> None:
        """Writes a run configuration yaml template.

        Args:
            path: The path where the template will be written.
            stack: The stack for which the template should be generated. If
                not given, the active stack will be used.
        """
        from zenml.config.base_settings import ConfigurationLevel
        from zenml.config.step_configurations import (
            PartialArtifactConfiguration,
        )

        self._prepare_if_possible()

        stack = stack or Client().active_stack

        setting_classes = stack.setting_classes
        setting_classes.update(settings_utils.get_general_settings())

        pipeline_settings = {}
        step_settings = {}
        for key, setting_class in setting_classes.items():
            fields = pydantic_utils.TemplateGenerator(setting_class).run()
            if ConfigurationLevel.PIPELINE in setting_class.LEVEL:
                pipeline_settings[key] = fields
            if ConfigurationLevel.STEP in setting_class.LEVEL:
                step_settings[key] = fields

        steps = {}
        for step_name, invocation in self.invocations.items():
            step = invocation.step
            outputs = {
                name: PartialArtifactConfiguration()
                for name in step.entrypoint_definition.outputs
            }
            step_template = StepConfigurationUpdate(
                parameters={},
                settings=step_settings,
                outputs=outputs,
            )
            steps[step_name] = step_template

        run_config = PipelineRunConfiguration(
            settings=pipeline_settings, steps=steps
        )
        template = pydantic_utils.TemplateGenerator(run_config).run()
        yaml_string = yaml.dump(template)
        yaml_string = yaml_utils.comment_out_yaml(yaml_string)

        with open(path, "w") as f:
            f.write(yaml_string)

    def _apply_configuration(
        self,
        config: PipelineConfigurationUpdate,
        merge: bool = True,
    ) -> None:
        """Applies an update to the pipeline configuration.

        Args:
            config: The configuration update.
            merge: Whether to merge the updates with the existing configuration
                or not. See the `BasePipeline.configure(...)` method for a
                detailed explanation.
        """
        self._validate_configuration(config)
        self._configuration = pydantic_utils.update_model(
            self._configuration, update=config, recursive=merge
        )
        logger.debug("Updated pipeline configuration:")
        logger.debug(self._configuration)

    @staticmethod
    def _validate_configuration(config: PipelineConfigurationUpdate) -> None:
        """Validates a configuration update.

        Args:
            config: The configuration update to validate.
        """
        settings_utils.validate_setting_keys(list(config.settings))

    def _get_pipeline_analytics_metadata(
        self,
        snapshot: "PipelineSnapshotResponse",
        stack: "Stack",
        run_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """Compute analytics metadata for the pipeline snapshot.

        Args:
            snapshot: The pipeline snapshot to track.
            stack: The stack on which the pipeline will be run.
            run_id: The ID of the pipeline run.

        Returns:
            The analytics metadata.
        """
        custom_materializer = False
        for step in snapshot.step_configurations.values():
            for output in step.config.outputs.values():
                for source in output.materializer_source:
                    if not source.is_internal:
                        custom_materializer = True

        stack_creator = Client().get_stack(stack.id).user_id
        active_user = Client().active_user
        own_stack = stack_creator and stack_creator == active_user.id

        stack_metadata = {
            component_type.value: component.flavor
            for component_type, component in stack.components.items()
        }
        return {
            "project_id": snapshot.project_id,
            "store_type": Client().zen_store.type.value,
            **stack_metadata,
            "total_steps": len(self.invocations),
            "schedule": bool(snapshot.schedule),
            "custom_materializer": custom_materializer,
            "own_stack": own_stack,
            "pipeline_run_id": str(run_id) if run_id else None,
        }

    def _compile(
        self, config_path: Optional[str] = None, **run_configuration_args: Any
    ) -> Tuple[
        "PipelineSnapshotBase",
        Optional["Schedule"],
        Union["PipelineBuildBase", UUID, None],
    ]:
        """Compiles the pipeline.

        Args:
            config_path: Path to a config file.
            **run_configuration_args: Configurations for the pipeline run.

        Returns:
            A tuple containing the snapshot, schedule and build of
            the compiled pipeline.
        """
        # Activating the built-in integrations to load all materializers
        from zenml.integrations.registry import integration_registry

        integration_registry.activate_integrations()

        _from_config_file = self._parse_config_file(
            config_path=config_path,
            matcher=list(PipelineRunConfiguration.model_fields.keys()),
        )

        self._reconfigure_from_file_with_overrides(config_path=config_path)

        run_config = PipelineRunConfiguration(**_from_config_file)

        new_values = dict_utils.remove_none_values(run_configuration_args)
        update = PipelineRunConfiguration.model_validate(new_values)

        # Update with the values in code so they take precedence
        run_config = pydantic_utils.update_model(run_config, update=update)
        run_config = env_utils.substitute_env_variable_placeholders(run_config)

        snapshot = Compiler().compile(
            pipeline=self,
            stack=Client().active_stack,
            run_configuration=run_config,
        )
        snapshot = env_utils.substitute_env_variable_placeholders(snapshot)

        return snapshot, run_config.schedule, run_config.build

    def _compute_unique_identifier(self, pipeline_spec: PipelineSpec) -> str:
        """Computes a unique identifier from the pipeline spec and steps.

        Args:
            pipeline_spec: Compiled spec of the pipeline.

        Returns:
            The unique identifier of the pipeline.
        """
        from packaging import version

        hash_ = hashlib.md5()  # nosec
        hash_.update(pipeline_spec.json_with_string_sources.encode())

        if version.parse(pipeline_spec.version) >= version.parse("0.4"):
            # Only add this for newer versions to keep backwards compatibility
            hash_.update(self.source_code.encode())

        for step_spec in pipeline_spec.steps:
            invocation = self.invocations[step_spec.invocation_id]
            step_source = invocation.step.source_code
            hash_.update(step_source.encode())

        return hash_.hexdigest()

    def add_step_invocation(
        self,
        step: "BaseStep",
        input_artifacts: Dict[str, List[StepArtifact]],
        external_artifacts: Dict[
            str, Union["ExternalArtifact", "ArtifactVersionResponse"]
        ],
        model_artifacts_or_metadata: Dict[str, "ModelVersionDataLazyLoader"],
        client_lazy_loaders: Dict[str, "ClientLazyLoader"],
        parameters: Dict[str, Any],
        default_parameters: Dict[str, Any],
        upstream_steps: Set[str],
        custom_id: Optional[str] = None,
        allow_id_suffix: bool = True,
    ) -> str:
        """Adds a step invocation to the pipeline.

        Args:
            step: The step for which to add an invocation.
            input_artifacts: The input artifacts for the invocation.
            external_artifacts: The external artifacts for the invocation.
            model_artifacts_or_metadata: The model artifacts or metadata for
                the invocation.
            client_lazy_loaders: The client lazy loaders for the invocation.
            parameters: The parameters for the invocation.
            default_parameters: The default parameters for the invocation.
            upstream_steps: The upstream steps for the invocation.
            custom_id: Custom ID to use for the invocation.
            allow_id_suffix: Whether a suffix can be appended to the invocation
                ID.

        Raises:
            RuntimeError: If the method is called on an inactive pipeline.
            RuntimeError: If the invocation was called with an artifact from
                a different pipeline.

        Returns:
            The step invocation ID.
        """
        from zenml.execution.pipeline.dynamic.run_context import (
            DynamicPipelineRunContext,
        )

        context = (
            PipelineCompilationContext.get() or DynamicPipelineRunContext.get()
        )

        if not context or context.pipeline != self:
            raise RuntimeError(
                "A step invocation can only be added to an active pipeline."
            )

        for artifact_list in input_artifacts.values():
            for artifact in artifact_list:
                if artifact.pipeline is not self:
                    raise RuntimeError(
                        "Got invalid input artifact for invocation of step "
                        f"{step.name}: The input artifact was produced by a step "
                        f"inside a different pipeline {artifact.pipeline.name}."
                    )

        invocation_id = self._compute_invocation_id(
            step=step, custom_id=custom_id, allow_suffix=allow_id_suffix
        )
        invocation = StepInvocation(
            id=invocation_id,
            step=step,
            input_artifacts=input_artifacts,
            external_artifacts=external_artifacts,
            model_artifacts_or_metadata=model_artifacts_or_metadata,
            client_lazy_loaders=client_lazy_loaders,
            parameters=parameters,
            default_parameters=default_parameters,
            upstream_steps=upstream_steps,
            pipeline=self,
        )
        self._invocations[invocation_id] = invocation
        return invocation_id

    def _compute_invocation_id(
        self,
        step: "BaseStep",
        custom_id: Optional[str] = None,
        allow_suffix: bool = True,
    ) -> str:
        """Compute the invocation ID.

        Args:
            step: The step for which to compute the ID.
            custom_id: Custom ID to use for the invocation.
            allow_suffix: Whether a suffix can be appended to the invocation
                ID.

        Raises:
            RuntimeError: If no ID suffix is allowed and an invocation for the
                same ID already exists.
            RuntimeError: If no unique invocation ID can be found.

        Returns:
            The invocation ID.
        """
        base_id = id_ = custom_id or step.name

        if id_ not in self.invocations:
            return id_

        if not allow_suffix:
            raise RuntimeError(f"Duplicate step ID `{id_}`")

        for index in range(2, 10000):
            id_ = f"{base_id}_{index}"
            if id_ not in self.invocations:
                return id_

        raise RuntimeError("Unable to find step ID")

    def _parse_config_file(
        self, config_path: Optional[str], matcher: List[str]
    ) -> Dict[str, Any]:
        """Parses the given configuration file and sets `self._from_config_file`.

        Args:
            config_path: Path to a yaml configuration file.
            matcher: List of keys to match in the configuration file.

        Returns:
            Parsed config file according to matcher settings.
        """
        _from_config_file: Dict[str, Any] = {}
        if config_path:
            with open(config_path, "r") as f:
                _from_config_file = yaml.load(f, Loader=yaml.SafeLoader)

            _from_config_file = dict_utils.remove_none_values(
                {k: v for k, v in _from_config_file.items() if k in matcher}
            )

            if "model" in _from_config_file:
                if "model" in self._from_config_file:
                    _from_config_file["model"] = self._from_config_file[
                        "model"
                    ]
                else:
                    from zenml.model.model import Model

                    _from_config_file["model"] = Model.model_validate(
                        _from_config_file["model"]
                    )
        return _from_config_file

    def with_options(
        self,
        run_name: Optional[str] = None,
        schedule: Optional[Schedule] = None,
        build: Union[str, "UUID", "PipelineBuildBase", None] = None,
        step_configurations: Optional[
            Mapping[str, "StepConfigurationUpdateOrDict"]
        ] = None,
        steps: Optional[Mapping[str, "StepConfigurationUpdateOrDict"]] = None,
        config_path: Optional[str] = None,
        unlisted: bool = False,
        prevent_build_reuse: bool = False,
        **kwargs: Any,
    ) -> "Pipeline":
        """Copies the pipeline and applies the given configurations.

        Args:
            run_name: Name of the pipeline run.
            schedule: Optional schedule to use for the run.
            build: Optional build to use for the run.
            step_configurations: Configurations for steps of the pipeline.
            steps: Configurations for steps of the pipeline. This is equivalent
                to `step_configurations`, and will be ignored if
                `step_configurations` is set as well.
            config_path: Path to a yaml configuration file. This file will
                be parsed as a
                `zenml.config.pipeline_configurations.PipelineRunConfiguration`
                object. Options provided in this file will be overwritten by
                options provided in code using the other arguments of this
                method.
            unlisted: DEPRECATED. This option is no longer supported.
            prevent_build_reuse: DEPRECATED: Use
                `DockerSettings.prevent_build_reuse` instead.
            **kwargs: Pipeline configuration options. These will be passed
                to the `pipeline.configure(...)` method.

        Returns:
            The copied pipeline instance.
        """
        if steps and step_configurations:
            logger.warning(
                "Step configurations were passed using both the "
                "`step_configurations` and `steps` keywords, ignoring the "
                "values passed using the `steps` keyword."
            )

        if unlisted:
            logger.warning(
                "The `unlisted` option is deprecated and will be removed in a "
                "future version. Every run will always be associated with a "
                "pipeline."
            )

        pipeline_copy = self.copy()

        pipeline_copy._reconfigure_from_file_with_overrides(
            config_path=config_path, **kwargs
        )

        run_args = dict_utils.remove_none_values(
            {
                "run_name": run_name,
                "schedule": schedule,
                "build": build,
                "step_configurations": step_configurations or steps,
                "config_path": config_path,
                "prevent_build_reuse": prevent_build_reuse,
            }
        )
        pipeline_copy._run_args.update(run_args)
        return pipeline_copy

    def copy(self) -> "Pipeline":
        """Copies the pipeline.

        Returns:
            The pipeline copy.
        """
        return copy.deepcopy(self)

    def __call__(
        self, *args: Any, **kwargs: Any
    ) -> Optional[PipelineRunResponse]:
        """Handle a call of the pipeline.

        This method does one of two things:
        * If there is an active pipeline context, it calls the pipeline
          entrypoint function within that context and the step invocations
          will be added to the active pipeline.
        * If no pipeline is active, it activates this pipeline before calling
          the entrypoint function.

        Args:
            *args: Entrypoint function arguments.
            **kwargs: Entrypoint function keyword arguments.

        Returns:
            If called within another pipeline, returns the outputs of the
            `entrypoint` method. Otherwise, returns the pipeline run or `None`
            if running with a schedule.
        """
        if PipelineCompilationContext.is_active():
            # Calling a pipeline inside a pipeline, we return the potential
            # outputs of the entrypoint function

            # TODO: This currently ignores the configuration of the pipeline
            #   and instead applies the configuration of the previously active
            #   pipeline. Is this what we want?
            return self.entrypoint(*args, **kwargs)  # type: ignore[no-any-return]

        self.prepare(*args, **kwargs)
        return self._run()

    def _call_entrypoint(self, *args: Any, **kwargs: Any) -> Any:
        """Calls the pipeline entrypoint function with the given arguments.

        Args:
            *args: Entrypoint function arguments.
            **kwargs: Entrypoint function keyword arguments.

        Returns:
            The return value of the entrypoint function.
        """
        self._clear_state()
        self._parameters = self._validate_entrypoint_args(*args, **kwargs)
        return self.entrypoint(**self._parameters)

    def _prepare_if_possible(self) -> None:
        """Prepares the pipeline if possible.

        Raises:
            RuntimeError: If the pipeline is not prepared and the preparation
                requires parameters.
        """
        if not self.is_prepared:
            if missing_parameters := self.missing_parameters:
                raise RuntimeError(
                    f"Failed while trying to prepare pipeline {self.name}. "
                    "The entrypoint function of the pipeline requires "
                    "arguments which have not been configured yet: "
                    f"{missing_parameters}. Please provide those parameters by "
                    "calling `pipeline_instance.configure(parameters=...)` or "
                    "by calling `pipeline_instance.prepare(...)` and try again."
                )

            self.prepare()

    def create_run_template(
        self, name: str, **kwargs: Any
    ) -> RunTemplateResponse:
        """DEPRECATED: Create a run template for the pipeline.

        Args:
            name: The name of the run template.
            **kwargs: Keyword arguments for the client method to create a run
                template.

        Returns:
            The created run template.
        """
        logger.warning(
            "The `pipeline.create_run_template(...)` method is deprecated and "
            "will be removed in a future version. Please use "
            "`pipeline.create_snapshot(..)` instead."
        )
        self._prepare_if_possible()
        snapshot = self._create_snapshot(
            **self._run_args, skip_schedule_registration=True
        )

        return Client().create_run_template(
            name=name, snapshot_id=snapshot.id, **kwargs
        )

    def create_snapshot(
        self,
        name: str,
        description: Optional[str] = None,
        replace: Optional[bool] = None,
        tags: Optional[List[str]] = None,
    ) -> PipelineSnapshotResponse:
        """Create a snapshot of the pipeline.

        Args:
            name: The name of the snapshot.
            description: The description of the snapshot.
            replace: Whether to replace the existing snapshot with the same
                name.
            tags: The tags to add to the snapshot.

        Returns:
            The created snapshot.
        """
        self._prepare_if_possible()
        return self._create_snapshot(
            skip_schedule_registration=True,
            name=name,
            description=description,
            replace=replace,
            tags=tags,
            **self._run_args,
        )

    def _reconfigure_from_file_with_overrides(
        self,
        config_path: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Update the pipeline configuration from config file.

        Accepts overrides as kwargs.

        Args:
            config_path: Path to a yaml configuration file. This file will
                be parsed as a
                `zenml.config.pipeline_configurations.PipelineRunConfiguration`
                object. Options provided in this file will be overwritten by
                options provided in code using the other arguments of this
                method.
            **kwargs: Pipeline configuration options. These will be passed
                to the `pipeline.configure(...)` method.
        """
        self._from_config_file = {}
        if config_path:
            self._from_config_file = self._parse_config_file(
                config_path=config_path,
                matcher=inspect.getfullargspec(self.configure)[0],
            )

        _from_config_file = dict_utils.recursive_update(
            self._from_config_file, kwargs
        )

        with self.__suppress_configure_warnings__():
            self.configure(**_from_config_file)

    def _compute_output_schema(self) -> Optional[Dict[str, Any]]:
        """Computes the output schema for the pipeline.

        Returns:
            The output schema for the pipeline.
        """
        try:
            # Generate unique step output names
            unique_step_output_mapping = get_unique_step_output_names(
                {
                    (o.invocation_id, o.output_name): o
                    for o in self._output_artifacts
                }
            )

            fields: Dict[str, Any] = {
                entry[1]: (
                    entry[0].annotation.resolved_annotation,
                    ...,
                )
                for _, entry in unique_step_output_mapping.items()
            }
            output_model_class: Type[BaseModel] = create_model(
                "PipelineOutput",
                __config__=ConfigDict(arbitrary_types_allowed=True),
                **fields,
            )
            return output_model_class.model_json_schema(mode="serialization")
        except Exception as e:
            logger.debug(
                f"Failed to generate the output schema for "
                f"pipeline `{self.name}: {e}. This is most likely "
                "because some of the pipeline outputs are not JSON "
                "serializable. This means that the pipeline cannot be "
                "deployed.",
            )

        return None

    def _compute_input_model(self) -> Optional[Type[BaseModel]]:
        """Create a Pydantic model that represents the pipeline input parameters.

        Returns:
            A Pydantic model that represents the pipeline input
            parameters.
        """
        from zenml.steps.entrypoint_function_utils import (
            validate_entrypoint_function,
        )

        try:
            entrypoint_definition = validate_entrypoint_function(
                self.entrypoint
            )

            defaults: Dict[str, Any] = self._parameters
            model_args: Dict[str, Any] = {}
            for name, param in entrypoint_definition.inputs.items():
                if name in defaults:
                    default_value = defaults[name]
                elif param.default is not inspect.Parameter.empty:
                    default_value = param.default
                else:
                    default_value = ...

                model_args[name] = (param.annotation, default_value)

            model_args["__config__"] = ConfigDict(extra="forbid")
            params_model: Type[BaseModel] = create_model(
                "PipelineInput",
                **model_args,
            )
            return params_model
        except Exception as e:
            logger.debug(
                f"Failed to generate the input parameters model for pipeline "
                f"`{self.name}: {e}. This means that the pipeline cannot be "
                "deployed.",
            )
            return None

    def _compute_input_schema(self) -> Optional[Dict[str, Any]]:
        """Create a JSON schema that represents the pipeline input parameters.

        Returns:
            A JSON schema that represents the pipeline input parameters.
        """
        input_model = self._compute_input_model()
        if not input_model:
            return None

        try:
            return input_model.model_json_schema()
        except Exception as e:
            logger.debug(
                f"Failed to generate the input parameters schema for "
                f"pipeline `{self.name}: {e}. This is most likely "
                "because some of the pipeline inputs are not JSON "
                "serializable. This means that the pipeline cannot be "
                "deployed.",
            )

        return None

    def _clear_state(self) -> None:
        """Clears the state of the pipeline."""
        self._invocations = {}
        self._parameters = {}
        self._output_artifacts = []
