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
import hashlib
from datetime import datetime
from pathlib import Path
from types import FunctionType
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    TypeVar,
    Union,
)
from uuid import UUID

import yaml

from zenml import constants
from zenml.client import Client
from zenml.config.compiler import Compiler
from zenml.config.pipeline_configurations import (
    PipelineConfiguration,
    PipelineConfigurationUpdate,
    PipelineRunConfiguration,
)
from zenml.config.pipeline_spec import PipelineSpec
from zenml.config.schedule import Schedule
from zenml.config.step_configurations import StepConfigurationUpdate
from zenml.enums import StackComponentType
from zenml.hooks.hook_validators import resolve_and_validate_hook
from zenml.logger import get_logger
from zenml.models import (
    CodeReferenceRequestModel,
    PipelineBuildResponseModel,
    PipelineDeploymentRequestModel,
    PipelineDeploymentResponseModel,
    PipelineRequestModel,
    PipelineResponseModel,
    ScheduleRequestModel,
)
from zenml.models.pipeline_build_models import (
    PipelineBuildBaseModel,
)
from zenml.models.pipeline_deployment_models import PipelineDeploymentBaseModel
from zenml.pipelines import build_utils
from zenml.stack import Stack
from zenml.steps import BaseStep
from zenml.steps.base_step import StepInvocation
from zenml.utils import (
    dashboard_utils,
    dict_utils,
    pydantic_utils,
    settings_utils,
    source_utils,
    yaml_utils,
)
from zenml.utils.analytics_utils import AnalyticsEvent, event_handler

if TYPE_CHECKING:
    from zenml.config.base_settings import SettingsOrDict
    from zenml.config.source import Source
    from zenml.post_execution import PipelineRunView

    StepConfigurationUpdateOrDict = Union[
        Dict[str, Any], StepConfigurationUpdate
    ]
    HookSpecification = Union[str, "Source", FunctionType]

logger = get_logger(__name__)

T = TypeVar("T", bound="Pipeline")


class Pipeline:
    ACTIVE_PIPELINE: ClassVar[Optional["Pipeline"]] = None

    def __init__(
        self,
        name: str,
        enable_cache: Optional[bool] = None,
        enable_artifact_metadata: Optional[bool] = None,
        settings: Optional[Mapping[str, "SettingsOrDict"]] = None,
        extra: Optional[Dict[str, Any]] = None,
        on_failure: Optional["HookSpecification"] = None,
        on_success: Optional["HookSpecification"] = None,
    ) -> None:
        self._steps: Dict[str, BaseStep] = {}
        self._configuration = PipelineConfiguration(
            name=name,
        )
        self.configure(
            enable_cache=enable_cache,
            enable_artifact_metadata=enable_artifact_metadata,
            settings=settings,
            extra=extra,
            on_failure=on_failure,
            on_success=on_success,
        )

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
    def steps(self) -> Dict[str, StepInvocation]:
        """Returns a dictionary of pipeline steps.

        Returns:
            A dictionary of pipeline steps.
        """
        return self._steps

    @classmethod
    def from_model(cls, model: "PipelineResponseModel") -> "Pipeline":
        """Creates a pipeline instance from a model.

        Args:
            model: The model to load the pipeline instance from.

        Returns:
            The pipeline instance.

        Raises:
            ValueError: If the spec version of the given model is <0.2
        """
        from zenml.pipelines.deserialization_utils import load_pipeline

        return load_pipeline(model=model)

    def configure(
        self: T,
        enable_cache: Optional[bool] = None,
        enable_artifact_metadata: Optional[bool] = None,
        settings: Optional[Mapping[str, "SettingsOrDict"]] = None,
        extra: Optional[Dict[str, Any]] = None,
        on_failure: Optional["HookSpecification"] = None,
        on_success: Optional["HookSpecification"] = None,
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
            settings: settings for this pipeline.
            extra: Extra configurations for this pipeline.
            on_failure: Callback function in event of failure of the step. Can
                be a function with three possible parameters, `StepContext`,
                `BaseParameters`, and `BaseException`, or a source path to a
                function of the same specifications (e.g. `module.my_function`).
            on_success: Callback function in event of failure of the step. Can
                be a function with two possible parameters, `StepContext` and
                `BaseParameters, or a source path to a function of the same
                specifications (e.g. `module.my_function`).
            merge: If `True`, will merge the given dictionary configurations
                like `extra` and `settings` with existing
                configurations. If `False` the given configurations will
                overwrite all existing ones. See the general description of this
                method for an example.

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
                "settings": settings,
                "extra": extra,
                "failure_hook_source": failure_hook_source,
                "success_hook_source": success_hook_source,
            }
        )
        config = PipelineConfigurationUpdate(**values)
        self._apply_configuration(config, merge=merge)
        return self

    def register(self) -> "PipelineResponseModel":
        """Register the pipeline in the server.

        Returns:
            The registered pipeline model.
        """
        # Activating the built-in integrations to load all materializers
        from zenml.integrations.registry import integration_registry

        integration_registry.activate_integrations()

        custom_configurations = self.configuration.dict(
            exclude_defaults=True, exclude={"name"}
        )
        if custom_configurations:
            logger.warning(
                f"The pipeline `{self.name}` that you're registering has "
                "custom configurations applied to it. These will not be "
                "registered with the pipeline and won't be set when you build "
                "images or run the pipeline from the CLI. To provide these "
                "configurations, use the `--config` option of the `zenml "
                "pipeline build/run` commands."
            )

        pipeline_spec = Compiler().compile_spec(self)
        return self._register(pipeline_spec=pipeline_spec)

    def build(
        self,
        *,
        settings: Optional[Mapping[str, "SettingsOrDict"]] = None,
        step_configurations: Optional[
            Mapping[str, "StepConfigurationUpdateOrDict"]
        ] = None,
        config_path: Optional[str] = None,
    ) -> Optional["PipelineBuildResponseModel"]:
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
        with event_handler(event=AnalyticsEvent.BUILD_PIPELINE, v2=True):
            deployment, pipeline_spec, _, _ = self._compile(
                config_path=config_path,
                steps=step_configurations,
                settings=settings,
            )
            pipeline_id = self._register(pipeline_spec=pipeline_spec).id

            local_repo = source_utils.find_active_code_repository()
            code_repository = build_utils.verify_local_repository_context(
                deployment=deployment, local_repo_context=local_repo
            )

            return build_utils.create_pipeline_build(
                deployment=deployment,
                pipeline_id=pipeline_id,
                code_repository=code_repository,
            )

    def run(
        self,
        *,
        run_name: Optional[str] = None,
        enable_cache: Optional[bool] = None,
        enable_artifact_metadata: Optional[bool] = None,
        schedule: Optional[Schedule] = None,
        build: Union[str, "UUID", "PipelineBuildBaseModel", None] = None,
        settings: Optional[Mapping[str, "SettingsOrDict"]] = None,
        step_configurations: Optional[
            Mapping[str, "StepConfigurationUpdateOrDict"]
        ] = None,
        extra: Optional[Dict[str, Any]] = None,
        config_path: Optional[str] = None,
        unlisted: bool = False,
        prevent_build_reuse: bool = False,
    ) -> None:
        """Runs the pipeline on the active stack.

        Args:
            run_name: Name of the pipeline run.
            enable_cache: If caching should be enabled for this pipeline run.
            enable_artifact_metadata: If artifact metadata should be enabled
                for this pipeline run.
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
            return

        with event_handler(
            event=AnalyticsEvent.RUN_PIPELINE, v2=True
        ) as analytics_handler:
            deployment, pipeline_spec, schedule, build = self._compile(
                config_path=config_path,
                run_name=run_name,
                enable_cache=enable_cache,
                enable_artifact_metadata=enable_artifact_metadata,
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
                pipeline_id = self._register(pipeline_spec=pipeline_spec).id

            # TODO: check whether orchestrator even support scheduling before
            # registering the schedule
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
                schedule_model = ScheduleRequestModel(
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
                )
                schedule_id = (
                    Client().zen_store.create_schedule(schedule_model).id
                )
                logger.info(
                    f"Created schedule `{schedule_name}` for pipeline "
                    f"`{deployment.pipeline_configuration.name}`."
                )

            stack = Client().active_stack

            local_repo_context = source_utils.find_active_code_repository()
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

                code_reference = CodeReferenceRequestModel(
                    commit=local_repo_context.current_commit,
                    subdirectory=subdirectory.as_posix(),
                    code_repository=local_repo_context.code_repository_id,
                )

            deployment_request = PipelineDeploymentRequestModel(
                user=Client().active_user.id,
                workspace=Client().active_workspace.id,
                stack=stack.id,
                pipeline=pipeline_id,
                build=build_id,
                schedule=schedule_id,
                code_reference=code_reference,
                **deployment.dict(),
            )
            deployment_model = Client().zen_store.create_deployment(
                deployment=deployment_request
            )

            analytics_handler.metadata = self._get_pipeline_analytics_metadata(
                deployment=deployment_model, stack=stack
            )
            caching_status = (
                "enabled"
                if deployment.pipeline_configuration.enable_cache is not False
                else "disabled"
            )
            logger.info(
                "%s %s on stack `%s` (caching %s)",
                "Scheduling" if deployment_model.schedule else "Running",
                f"pipeline `{deployment_model.pipeline_configuration.name}`"
                if register_pipeline
                else "unlisted pipeline",
                stack.name,
                caching_status,
            )

            stack.prepare_pipeline_deployment(deployment=deployment_model)

            # Prevent execution of nested pipelines which might lead to
            # unexpected behavior
            constants.SHOULD_PREVENT_PIPELINE_EXECUTION = True
            try:
                stack.deploy_pipeline(deployment=deployment_model)
            finally:
                constants.SHOULD_PREVENT_PIPELINE_EXECUTION = False

            # Log the dashboard URL
            dashboard_utils.print_run_url(
                run_name=deployment.run_name_template,
                pipeline_id=pipeline_id,
            )

    @classmethod
    def get_runs(cls) -> Optional[List["PipelineRunView"]]:
        """Get all past runs from the associated PipelineView.

        Returns:
            A list of all past PipelineRunViews.

        Raises:
            RuntimeError: In case the repository does not contain the view
                of the current pipeline.
        """
        from zenml.post_execution import get_pipeline

        pipeline_view = get_pipeline(cls)
        if pipeline_view:
            return pipeline_view.runs  # type: ignore[no-any-return]
        else:
            raise RuntimeError(
                f"The PipelineView for `{cls.__name__}` could "
                f"not be found. Are you sure this pipeline has "
                f"been run already?"
            )

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
        for step_name, invocation in self.steps.items():
            step = invocation.step
            parameters = (
                pydantic_utils.TemplateGenerator(step.PARAMETERS_CLASS).run()
                if step.PARAMETERS_CLASS
                else {}
            )
            outputs = {
                name: PartialArtifactConfiguration()
                for name in step.OUTPUT_SIGNATURE
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
        deployment: "PipelineDeploymentResponseModel",
        stack: "Stack",
    ) -> Dict[str, Any]:
        """Returns the pipeline deployment metadata.

        Args:
            deployment: The pipeline deployment to track.
            stack: The stack on which the pipeline will be deployed.

        Returns:
            the metadata about the pipeline deployment
        """
        custom_materializer = False
        for step in deployment.step_configurations.values():
            for output in step.config.outputs.values():
                if not output.materializer_source.is_internal:
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
            "total_steps": len(self.steps),
            "schedule": bool(deployment.schedule),
            "custom_materializer": custom_materializer,
            "own_stack": own_stack,
        }

    def _compile(
        self, config_path: Optional[str] = None, **run_configuration_args: Any
    ) -> Tuple[
        "PipelineDeploymentBaseModel",
        "PipelineSpec",
        Optional["Schedule"],
        Union["PipelineBuildBaseModel", UUID, None],
    ]:
        """Compiles the pipeline.

        Args:
            config_path: Path to a config file.
            **run_configuration_args: Configurations for the pipeline run.

        Returns:
            A tuple containing the deployment, spec, schedule and build of
            the compiled pipeline.
        """
        # Activating the built-in integrations to load all materializers
        from zenml.integrations.registry import integration_registry

        integration_registry.activate_integrations()

        if config_path:
            run_config = PipelineRunConfiguration.from_yaml(config_path)
        else:
            run_config = PipelineRunConfiguration()

        new_values = dict_utils.remove_none_values(run_configuration_args)
        update = PipelineRunConfiguration.parse_obj(new_values)

        # Update with the values in code so they take precedence
        run_config = pydantic_utils.update_model(run_config, update=update)

        deployment, pipeline_spec = Compiler().compile(
            pipeline=self,
            stack=Client().active_stack,
            run_configuration=run_config,
        )

        return deployment, pipeline_spec, run_config.schedule, run_config.build

    def _register(
        self, pipeline_spec: "PipelineSpec"
    ) -> "PipelineResponseModel":
        """Register the pipeline in the server.

        Args:
            pipeline_spec: The pipeline spec to register.

        Returns:
            The registered pipeline model.
        """
        version_hash = self._compute_unique_identifier(
            pipeline_spec=pipeline_spec
        )

        client = Client()
        matching_pipelines = client.list_pipelines(
            name=self.name,
            version_hash=version_hash,
            size=1,
            sort_by="desc:created",
        )
        if matching_pipelines.total:
            registered_pipeline = matching_pipelines.items[0]
            logger.info(
                "Reusing registered pipeline `%s` (version: %s).",
                registered_pipeline.name,
                registered_pipeline.version,
            )
            return registered_pipeline

        latest_version = self._get_latest_version() or 0
        version = str(latest_version + 1)

        request = PipelineRequestModel(
            workspace=client.active_workspace.id,
            user=client.active_user.id,
            name=self.name,
            version=version,
            version_hash=version_hash,
            spec=pipeline_spec,
            docstring=self.__doc__,
        )

        registered_pipeline = client.zen_store.create_pipeline(
            pipeline=request
        )
        logger.info(
            "Registered pipeline `%s` (version %s).",
            registered_pipeline.name,
            registered_pipeline.version,
        )
        return registered_pipeline

    def _compute_unique_identifier(self, pipeline_spec: PipelineSpec) -> str:
        """Computes a unique identifier from the pipeline spec and steps.

        Args:
            pipeline_spec: Compiled spec of the pipeline.

        Returns:
            The unique identifier of the pipeline.
        """
        hash_ = hashlib.md5()
        hash_.update(pipeline_spec.json_with_string_sources.encode())

        for step_spec in pipeline_spec.steps:
            invocation = self.steps[step_spec.pipeline_parameter_name]
            step_source = invocation.step.source_code
            hash_.update(step_source.encode())

        return hash_.hexdigest()

    def _get_latest_version(self) -> Optional[int]:
        """Gets the latest version of this pipeline.

        Returns:
            The latest version or `None` if no version exists.
        """
        all_pipelines = Client().list_pipelines(
            name=self.name, sort_by="desc:created", size=1
        )
        if all_pipelines.total:
            pipeline = all_pipelines.items[0]
            if pipeline.version == "UNVERSIONED":
                return None
            return int(all_pipelines.items[0].version)
        else:
            return None

    def _get_registered_model(self) -> Optional[PipelineResponseModel]:
        """Gets the registered pipeline model for this instance.

        Returns:
            The registered pipeline model or None if no model is registered yet.
        """
        pipeline_spec = Compiler().compile_spec(self)
        version_hash = self._compute_unique_identifier(
            pipeline_spec=pipeline_spec
        )

        pipelines = Client().list_pipelines(
            name=self.name, version_hash=version_hash
        )
        if len(pipelines) == 1:
            return pipelines.items[0]

        return None

    def add_step(
        self,
        step: "BaseStep",
        input_artifacts: Dict[str, BaseStep._OutputArtifact],
        parameters: Dict[str, Any],
        upstream_steps: Sequence[str],
        custom_id: Optional[str] = None,
        allow_suffix: bool = True,
    ) -> str:
        if Pipeline.ACTIVE_PIPELINE != self:
            raise RuntimeError(
                "Add_step can only be called on an active pipeline."
            )

        for artifact in input_artifacts.values():
            if artifact.pipeline is not self:
                raise RuntimeError(
                    "Got input artifact from a different pipeline."
                )

        invocation_id = self._compute_invocation_id(
            step=step, custom_id=custom_id, allow_suffix=allow_suffix
        )
        invocation = StepInvocation(
            id=invocation_id,
            step=step,
            input_artifacts=input_artifacts,
            parameters=parameters,
            upstream_steps=upstream_steps,
        )
        self._steps[invocation_id] = invocation
        return invocation_id

    def _compute_invocation_id(
        self,
        step: "BaseStep",
        custom_id: Optional[str] = None,
        allow_suffix: bool = True,
    ) -> str:
        base_id = custom_id or step.name

        if base_id in self.steps and not allow_suffix:
            raise RuntimeError("Duplicate step ID")

        id_ = base_id
        for index in range(2, 100):
            if id_ not in self.steps:
                break

            id_ = f"{base_id}_{index}"
        else:
            raise RuntimeError("Unable to find step ID")

        return id_

    def __enter__(self: T) -> T:
        if Pipeline.ACTIVE_PIPELINE:
            raise RuntimeError("Pipeline already active.")

        Pipeline.ACTIVE_PIPELINE = self
        return self

    def __exit__(self, type, value, traceback):
        Pipeline.ACTIVE_PIPELINE = None
