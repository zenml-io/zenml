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
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ClassVar,
    Dict,
    Iterator,
    List,
    Mapping,
    Optional,
    Set,
    Tuple,
    TypeVar,
    Union,
)
from uuid import UUID

import yaml
from pydantic import ConfigDict, ValidationError

from zenml import constants
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
from zenml.enums import StackComponentType
from zenml.exceptions import EntityExistsError
from zenml.hooks.hook_validators import resolve_and_validate_hook
from zenml.logger import get_logger
from zenml.models import (
    CodeReferenceRequest,
    PipelineBuildBase,
    PipelineBuildResponse,
    PipelineDeploymentBase,
    PipelineDeploymentRequest,
    PipelineDeploymentResponse,
    PipelineRequest,
    PipelineResponse,
    PipelineRunResponse,
    ScheduleRequest,
)
from zenml.new.pipelines import build_utils
from zenml.new.pipelines.run_utils import (
    create_placeholder_run,
    deploy_pipeline,
    prepare_model_versions,
)
from zenml.stack import Stack
from zenml.steps import BaseStep
from zenml.steps.entrypoint_function_utils import (
    StepArtifact,
)
from zenml.steps.step_invocation import StepInvocation
from zenml.utils import (
    code_repository_utils,
    dashboard_utils,
    dict_utils,
    pydantic_utils,
    settings_utils,
    source_utils,
    yaml_utils,
)

if TYPE_CHECKING:
    from zenml.artifacts.external_artifact import ExternalArtifact
    from zenml.client_lazy_loader import ClientLazyLoader
    from zenml.config.base_settings import SettingsOrDict
    from zenml.config.source import Source
    from zenml.model.lazy_load import ModelVersionDataLazyLoader
    from zenml.model.model import Model
    from zenml.types import HookSpecification

    StepConfigurationUpdateOrDict = Union[
        Dict[str, Any], StepConfigurationUpdate
    ]

logger = get_logger(__name__)

T = TypeVar("T", bound="Pipeline")
F = TypeVar("F", bound=Callable[..., None])


class Pipeline:
    """ZenML pipeline class."""

    # The active pipeline is the pipeline to which step invocations will be
    # added when a step is called. It is set using a context manager when a
    # pipeline is called (see Pipeline.__call__ for more context)
    ACTIVE_PIPELINE: ClassVar[Optional["Pipeline"]] = None

    def __init__(
        self,
        name: str,
        entrypoint: F,
        enable_cache: Optional[bool] = None,
        enable_artifact_metadata: Optional[bool] = None,
        enable_artifact_visualization: Optional[bool] = None,
        enable_step_logs: Optional[bool] = None,
        settings: Optional[Mapping[str, "SettingsOrDict"]] = None,
        extra: Optional[Dict[str, Any]] = None,
        on_failure: Optional["HookSpecification"] = None,
        on_success: Optional["HookSpecification"] = None,
        model: Optional["Model"] = None,
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
            settings: settings for this pipeline.
            extra: Extra configurations for this pipeline.
            on_failure: Callback function in event of failure of the step. Can
                be a function with a single argument of type `BaseException`, or
                a source path to such a function (e.g. `module.my_function`).
            on_success: Callback function in event of success of the step. Can
                be a function with no arguments, or a source path to such a
                function (e.g. `module.my_function`).
            model: configuration of the model in the Model Control Plane.
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
                settings=settings,
                extra=extra,
                on_failure=on_failure,
                on_success=on_success,
                model=model,
            )
        self.entrypoint = entrypoint
        self._parameters: Dict[str, Any] = {}

        self.__suppress_warnings_flag__ = False

    @property
    def name(self) -> str:
        """The name of the pipeline.

        Returns:
            The name of the pipeline.
        """
        return self.configuration.name

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
        self._prepare_if_possible()

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
        self: T,
        enable_cache: Optional[bool] = None,
        enable_artifact_metadata: Optional[bool] = None,
        enable_artifact_visualization: Optional[bool] = None,
        enable_step_logs: Optional[bool] = None,
        settings: Optional[Mapping[str, "SettingsOrDict"]] = None,
        extra: Optional[Dict[str, Any]] = None,
        on_failure: Optional["HookSpecification"] = None,
        on_success: Optional["HookSpecification"] = None,
        model: Optional["Model"] = None,
        parameters: Optional[Dict[str, Any]] = None,
        merge: bool = True,
    ) -> T:
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
            settings: settings for this pipeline.
            extra: Extra configurations for this pipeline.
            on_failure: Callback function in event of failure of the step. Can
                be a function with a single argument of type `BaseException`, or
                a source path to such a function (e.g. `module.my_function`).
            on_success: Callback function in event of success of the step. Can
                be a function with no arguments, or a source path to such a
                function (e.g. `module.my_function`).
            merge: If `True`, will merge the given dictionary configurations
                like `extra` and `settings` with existing
                configurations. If `False` the given configurations will
                overwrite all existing ones. See the general description of this
                method for an example.
            model: configuration of the model version in the Model Control Plane.
            parameters: input parameters for the pipeline.

        Returns:
            The pipeline instance that this method was called on.
        """
        failure_hook_source = None
        if on_failure:
            # string of on_failure hook function to be used for this pipeline
            failure_hook_source = resolve_and_validate_hook(on_failure)

        success_hook_source = None
        if on_success:
            # string of on_success hook function to be used for this pipeline
            success_hook_source = resolve_and_validate_hook(on_success)

        values = dict_utils.remove_none_values(
            {
                "enable_cache": enable_cache,
                "enable_artifact_metadata": enable_artifact_metadata,
                "enable_artifact_visualization": enable_artifact_visualization,
                "enable_step_logs": enable_step_logs,
                "settings": settings,
                "extra": extra,
                "failure_hook_source": failure_hook_source,
                "success_hook_source": success_hook_source,
                "model": model,
                "parameters": parameters,
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
    def requires_parameters(self) -> bool:
        """If the pipeline entrypoint requires parameters.

        Returns:
            If the pipeline entrypoint requires parameters.
        """
        signature = inspect.signature(self.entrypoint, follow_wrapped=True)
        return any(
            parameter.default is inspect.Parameter.empty
            for parameter in signature.parameters.values()
        )

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

        Raises:
            RuntimeError: If the pipeline has parameters configured differently in
                configuration file and code.
        """
        # Clear existing parameters and invocations
        self._parameters = {}
        self._invocations = {}

        conflicting_parameters = {}
        parameters_ = (self.configuration.parameters or {}).copy()
        if from_file_ := self._from_config_file.get("parameters", None):
            parameters_ = dict_utils.recursive_update(parameters_, from_file_)
        if parameters_:
            for k, v_runtime in kwargs.items():
                if k in parameters_:
                    v_config = parameters_[k]
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
    pipeline_.with_options(config_file="config.yaml")(param_name="value2")
```
To avoid this consider setting pipeline parameters only in one place (config or code).
"""
                raise RuntimeError(msg)
            for k, v_config in parameters_.items():
                if k not in kwargs:
                    kwargs[k] = v_config

        with self:
            # Enter the context manager, so we become the active pipeline. This
            # means that all steps that get called while the entrypoint function
            # is executed will be added as invocation to this pipeline instance.
            self._call_entrypoint(*args, **kwargs)

    def register(self) -> "PipelineResponse":
        """Register the pipeline in the server.

        Returns:
            The registered pipeline model.
        """
        # Activating the built-in integrations to load all materializers
        from zenml.integrations.registry import integration_registry

        self._prepare_if_possible()
        integration_registry.activate_integrations()

        if self.configuration.model_dump(
            exclude_defaults=True, exclude={"name"}
        ):
            logger.warning(
                f"The pipeline `{self.name}` that you're registering has "
                "custom configurations applied to it. These will not be "
                "registered with the pipeline and won't be set when you build "
                "images or run the pipeline from the CLI. To provide these "
                "configurations, use the `--config` option of the `zenml "
                "pipeline build/run` commands."
            )

        return self._register()

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
            deployment, _, _ = self._compile(
                config_path=config_path,
                steps=step_configurations,
                settings=settings,
            )
            pipeline_id = self._register().id

            local_repo = code_repository_utils.find_active_code_repository()
            code_repository = build_utils.verify_local_repository_context(
                deployment=deployment, local_repo_context=local_repo
            )

            return build_utils.create_pipeline_build(
                deployment=deployment,
                pipeline_id=pipeline_id,
                code_repository=code_repository,
            )

    def _run(
        self,
        *,
        run_name: Optional[str] = None,
        enable_cache: Optional[bool] = None,
        enable_artifact_metadata: Optional[bool] = None,
        enable_artifact_visualization: Optional[bool] = None,
        enable_step_logs: Optional[bool] = None,
        schedule: Optional[Schedule] = None,
        build: Union[str, "UUID", "PipelineBuildBase", None] = None,
        settings: Optional[Mapping[str, "SettingsOrDict"]] = None,
        step_configurations: Optional[
            Mapping[str, "StepConfigurationUpdateOrDict"]
        ] = None,
        extra: Optional[Dict[str, Any]] = None,
        config_path: Optional[str] = None,
        unlisted: bool = False,
        prevent_build_reuse: bool = False,
    ) -> Optional[PipelineRunResponse]:
        """Runs the pipeline on the active stack.

        Args:
            run_name: Name of the pipeline run.
            enable_cache: If caching should be enabled for this pipeline run.
            enable_artifact_metadata: If artifact metadata should be enabled
                for this pipeline run.
            enable_artifact_visualization: If artifact visualization should be
                enabled for this pipeline run.
            enable_step_logs: If step logs should be enabled for this pipeline.
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
            unlisted: Whether the pipeline run should be unlisted (not assigned
                to any pipeline).
            prevent_build_reuse: Whether to prevent the reuse of a build.

        Returns:
            Model of the pipeline run if running without a schedule, `None` if
            running with a schedule.
        """
        if constants.SHOULD_PREVENT_PIPELINE_EXECUTION:
            # An environment variable was set to stop the execution of
            # pipelines. This is done to prevent execution of module-level
            # pipeline.run() calls when importing modules needed to run a step.
            logger.info(
                "Preventing execution of pipeline '%s'. If this is not "
                "intended behavior, make sure to unset the environment "
                "variable '%s'.",
                self.name,
                constants.ENV_ZENML_PREVENT_PIPELINE_EXECUTION,
            )
            return None

        logger.info(f"Initiating a new run for the pipeline: `{self.name}`.")

        with track_handler(AnalyticsEvent.RUN_PIPELINE) as analytics_handler:
            deployment, schedule, build = self._compile(
                config_path=config_path,
                run_name=run_name,
                enable_cache=enable_cache,
                enable_artifact_metadata=enable_artifact_metadata,
                enable_artifact_visualization=enable_artifact_visualization,
                enable_step_logs=enable_step_logs,
                steps=step_configurations,
                settings=settings,
                schedule=schedule,
                build=build,
                extra=extra,
            )

            skip_pipeline_registration = constants.handle_bool_env_var(
                constants.ENV_ZENML_SKIP_PIPELINE_REGISTRATION,
                default=False,
            )

            register_pipeline = not (skip_pipeline_registration or unlisted)

            pipeline_id = None
            if register_pipeline:
                pipeline_id = self._register().id

            else:
                logger.debug(f"Pipeline {self.name} is unlisted.")

            # TODO: check whether orchestrator even support scheduling before
            #   registering the schedule
            schedule_id = None
            if schedule:
                if schedule.name:
                    schedule_name = schedule.name
                else:
                    date = datetime.utcnow().strftime("%Y_%m_%d")
                    time = datetime.utcnow().strftime("%H_%M_%S_%f")
                    schedule_name = deployment.run_name_template.format(
                        date=date, time=time
                    )
                components = Client().active_stack_model.components
                orchestrator = components[StackComponentType.ORCHESTRATOR][0]
                schedule_model = ScheduleRequest(
                    workspace=Client().active_workspace.id,
                    user=Client().active_user.id,
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
                schedule_id = (
                    Client().zen_store.create_schedule(schedule_model).id
                )
                logger.info(
                    f"Created schedule `{schedule_name}` for pipeline "
                    f"`{deployment.pipeline_configuration.name}`."
                )

            stack = Client().active_stack
            stack.validate()

            prepare_model_versions(deployment)

            local_repo_context = (
                code_repository_utils.find_active_code_repository()
            )
            code_repository = build_utils.verify_local_repository_context(
                deployment=deployment, local_repo_context=local_repo_context
            )

            build_model = build_utils.reuse_or_create_pipeline_build(
                deployment=deployment,
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
                    code_repository=local_repo_context.code_repository_id,
                )

            deployment_request = PipelineDeploymentRequest(
                user=Client().active_user.id,
                workspace=Client().active_workspace.id,
                stack=stack.id,
                pipeline=pipeline_id,
                build=build_id,
                schedule=schedule_id,
                code_reference=code_reference,
                **deployment.model_dump(),
            )
            deployment_model = Client().zen_store.create_deployment(
                deployment=deployment_request
            )

            self.log_pipeline_deployment_metadata(deployment_model)
            run = create_placeholder_run(deployment=deployment_model)

            analytics_handler.metadata = self._get_pipeline_analytics_metadata(
                deployment=deployment_model,
                stack=stack,
                run_id=run.id if run else None,
            )

            if run:
                run_url = dashboard_utils.get_run_url(run)
                if run_url:
                    logger.info(f"Dashboard URL: {run_url}")
                else:
                    logger.info(
                        "You can visualize your pipeline runs in the `ZenML "
                        "Dashboard`. In order to try it locally, please run "
                        "`zenml up`."
                    )

            deploy_pipeline(
                deployment=deployment_model, stack=stack, placeholder_run=run
            )
            if run:
                return Client().get_pipeline_run(run.id)
            return None

    @staticmethod
    def log_pipeline_deployment_metadata(
        deployment_model: PipelineDeploymentResponse,
    ) -> None:
        """Displays logs based on the deployment model upon running a pipeline.

        Args:
            deployment_model: The model for the pipeline deployment
        """
        try:
            # Log about the schedule/run
            if deployment_model.schedule:
                logger.info(
                    "Scheduling a run with the schedule: "
                    f"`{deployment_model.schedule.name}`"
                )
            else:
                logger.info("Executing a new run.")

            # Log about the caching status
            if deployment_model.pipeline_configuration.enable_cache is False:
                logger.info(
                    f"Caching is disabled by default for "
                    f"`{deployment_model.pipeline_configuration.name}`."
                )

            # Log about the used builds
            if deployment_model.build:
                logger.info("Using a build:")
                logger.info(
                    " Image(s): "
                    f"{', '.join([i.image for i in deployment_model.build.images.values()])}"
                )

                # Log about version mismatches between local and build
                from zenml import __version__

                if deployment_model.build.zenml_version != __version__:
                    logger.info(
                        f"ZenML version (different than the local version): "
                        f"{deployment_model.build.zenml_version}"
                    )

                import platform

                if (
                    deployment_model.build.python_version
                    != platform.python_version()
                ):
                    logger.info(
                        f"Python version (different than the local version): "
                        f"{deployment_model.build.python_version}"
                    )

            # Log about the user, stack and components
            if deployment_model.user is not None:
                logger.info(f"Using user: `{deployment_model.user.name}`")

            if deployment_model.stack is not None:
                logger.info(f"Using stack: `{deployment_model.stack.name}`")

                for (
                    component_type,
                    component_models,
                ) in deployment_model.stack.components.items():
                    logger.info(
                        f"  {component_type.value}: `{component_models[0].name}`"
                    )
        except Exception as e:
            logger.debug(f"Logging pipeline deployment metadata failed: {e}")

    def get_runs(self, **kwargs: Any) -> List["PipelineRunResponse"]:
        """(Deprecated) Get runs of this pipeline.

        Args:
            **kwargs: Further arguments for filtering or pagination that are
                passed to `client.list_pipeline_runs()`.

        Returns:
            List of runs of this pipeline.
        """
        logger.warning(
            "`Pipeline.get_runs()` is deprecated and will be removed in a "
            "future version. Please use `Pipeline.model.get_runs()` instead."
        )
        return self.model.get_runs(**kwargs)

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
            parameters = (
                pydantic_utils.TemplateGenerator(
                    step.entrypoint_definition.legacy_params.annotation
                ).run()
                if step.entrypoint_definition.legacy_params
                else {}
            )
            outputs = {
                name: PartialArtifactConfiguration()
                for name in step.entrypoint_definition.outputs
            }
            step_template = StepConfigurationUpdate(
                parameters=parameters,
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
        deployment: "PipelineDeploymentResponse",
        stack: "Stack",
        run_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """Returns the pipeline deployment metadata.

        Args:
            deployment: The pipeline deployment to track.
            stack: The stack on which the pipeline will be deployed.
            run_id: The ID of the pipeline run.

        Returns:
            the metadata about the pipeline deployment
        """
        custom_materializer = False
        for step in deployment.step_configurations.values():
            for output in step.config.outputs.values():
                for source in output.materializer_source:
                    if not source.is_internal:
                        custom_materializer = True

        stack_creator = Client().get_stack(stack.id).user
        active_user = Client().active_user
        own_stack = stack_creator and stack_creator.id == active_user.id

        stack_metadata = {
            component_type.value: component.flavor
            for component_type, component in stack.components.items()
        }
        return {
            "store_type": Client().zen_store.type.value,
            **stack_metadata,
            "total_steps": len(self.invocations),
            "schedule": bool(deployment.schedule),
            "custom_materializer": custom_materializer,
            "own_stack": own_stack,
            "pipeline_run_id": str(run_id) if run_id else None,
        }

    def _compile(
        self, config_path: Optional[str] = None, **run_configuration_args: Any
    ) -> Tuple[
        "PipelineDeploymentBase",
        Optional["Schedule"],
        Union["PipelineBuildBase", UUID, None],
    ]:
        """Compiles the pipeline.

        Args:
            config_path: Path to a config file.
            **run_configuration_args: Configurations for the pipeline run.

        Returns:
            A tuple containing the deployment, schedule and build of
            the compiled pipeline.
        """
        # Activating the built-in integrations to load all materializers
        from zenml.integrations.registry import integration_registry

        integration_registry.activate_integrations()

        self._parse_config_file(
            config_path=config_path,
            matcher=list(PipelineRunConfiguration.model_fields.keys()),
        )

        run_config = PipelineRunConfiguration(**self._from_config_file)

        new_values = dict_utils.remove_none_values(run_configuration_args)
        update = PipelineRunConfiguration.model_validate(new_values)

        # Update with the values in code so they take precedence
        run_config = pydantic_utils.update_model(run_config, update=update)

        deployment = Compiler().compile(
            pipeline=self,
            stack=Client().active_stack,
            run_configuration=run_config,
        )

        return deployment, run_config.schedule, run_config.build

    def _register(self) -> "PipelineResponse":
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
                workspace=client.active_workspace.id,
                user=client.active_user.id,
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
            invocation = self.invocations[step_spec.pipeline_parameter_name]
            step_source = invocation.step.source_code
            hash_.update(step_source.encode())

        return hash_.hexdigest()

    def add_step_invocation(
        self,
        step: "BaseStep",
        input_artifacts: Dict[str, StepArtifact],
        external_artifacts: Dict[str, "ExternalArtifact"],
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
        if Pipeline.ACTIVE_PIPELINE != self:
            raise RuntimeError(
                "A step invocation can only be added to an active pipeline."
            )

        for artifact in input_artifacts.values():
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
            raise RuntimeError("Duplicate step ID")

        for index in range(2, 10000):
            id_ = f"{base_id}_{index}"
            if id_ not in self.invocations:
                return id_

        raise RuntimeError("Unable to find step ID")

    def __enter__(self: T) -> T:
        """Activate the pipeline context.

        Raises:
            RuntimeError: If a different pipeline is already active.

        Returns:
            The pipeline instance.
        """
        if Pipeline.ACTIVE_PIPELINE:
            raise RuntimeError(
                "Unable to enter pipeline context. A different pipeline "
                f"{Pipeline.ACTIVE_PIPELINE.name} is already active."
            )

        Pipeline.ACTIVE_PIPELINE = self
        return self

    def __exit__(self, *args: Any) -> None:
        """Deactivates the pipeline context.

        Args:
            *args: The arguments passed to the context exit handler.
        """
        Pipeline.ACTIVE_PIPELINE = None

    def _parse_config_file(
        self, config_path: Optional[str], matcher: List[str]
    ) -> None:
        """Parses the given configuration file and sets `self._from_config_file`.

        Args:
            config_path: Path to a yaml configuration file.
            matcher: List of keys to match in the configuration file.
        """
        _from_config_file: Dict[str, Any] = {}
        if config_path:
            with open(config_path, "r") as f:
                _from_config_file = yaml.load(f, Loader=yaml.SafeLoader)
            _from_config_file = dict_utils.remove_none_values(
                {k: v for k, v in _from_config_file.items() if k in matcher}
            )

            # TODO: deprecate me
            if "model_version" in _from_config_file:
                logger.warning(
                    "YAML config option `model_version` is deprecated. Please use `model`."
                )
                _from_config_file["model"] = _from_config_file["model_version"]
                del _from_config_file["model_version"]

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
        self._from_config_file = _from_config_file

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
            unlisted: Whether the pipeline run should be unlisted (not assigned
                to any pipeline).
            prevent_build_reuse: Whether to prevent the reuse of a build.
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

        pipeline_copy = self.copy()

        pipeline_copy._parse_config_file(
            config_path=config_path,
            matcher=inspect.getfullargspec(self.configure)[0]
            + ["model_version"],  # TODO: deprecate `model_version` later on
        )
        pipeline_copy._from_config_file = dict_utils.recursive_update(
            pipeline_copy._from_config_file, kwargs
        )

        with pipeline_copy.__suppress_configure_warnings__():
            pipeline_copy.configure(**pipeline_copy._from_config_file)

        run_args = dict_utils.remove_none_values(
            {
                "run_name": run_name,
                "schedule": schedule,
                "build": build,
                "step_configurations": step_configurations or steps,
                "config_path": config_path,
                "unlisted": unlisted,
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

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
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
            The outputs of the entrypoint function call.
        """
        if Pipeline.ACTIVE_PIPELINE:
            # Calling a pipeline inside a pipeline, we return the potential
            # outputs of the entrypoint function

            # TODO: This currently ignores the configuration of the pipeline
            #   and instead applies the configuration of the previously active
            #   pipeline. Is this what we want?
            return self.entrypoint(*args, **kwargs)

        self.prepare(*args, **kwargs)
        return self._run(**self._run_args)

    def _call_entrypoint(self, *args: Any, **kwargs: Any) -> None:
        """Calls the pipeline entrypoint function with the given arguments.

        Args:
            *args: Entrypoint function arguments.
            **kwargs: Entrypoint function keyword arguments.

        Raises:
            ValueError: If an input argument is missing or not JSON
                serializable.
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
                "Only JSON serializable inputs are allowed as pipeline inputs."
                "Check out the pydantic error above for more details."
            ) from e

        self._parameters = validated_args
        self.entrypoint(**validated_args)

    def _prepare_if_possible(self) -> None:
        """Prepares the pipeline if possible.

        Raises:
            RuntimeError: If the pipeline is not prepared and the preparation
                requires parameters.
        """
        if not self.is_prepared:
            if self.requires_parameters:
                raise RuntimeError(
                    f"Failed while trying to prepare pipeline {self.name}. "
                    "The entrypoint function of the pipeline requires "
                    "arguments. Please prepare the pipeline by calling "
                    "`pipeline_instance.prepare(...)` and try again."
                )
            else:
                self.prepare()
