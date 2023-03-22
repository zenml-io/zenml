#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
"""Abstract base class for all ZenML pipelines."""
import hashlib
import inspect
from abc import abstractmethod
from datetime import datetime
from types import FunctionType
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ClassVar,
    Dict,
    List,
    Mapping,
    Optional,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)
from uuid import UUID

import yaml
from packaging import version

from zenml import constants
from zenml.client import Client
from zenml.config.compiler import Compiler
from zenml.config.pipeline_configurations import (
    PipelineConfiguration,
    PipelineConfigurationUpdate,
    PipelineRunConfiguration,
    PipelineSpec,
)
from zenml.config.schedule import Schedule
from zenml.config.step_configurations import StepConfigurationUpdate
from zenml.enums import StackComponentType
from zenml.exceptions import PipelineInterfaceError
from zenml.hooks.hook_validators import resolve_and_validate_hook
from zenml.logger import get_logger
from zenml.models import (
    PipelineBuildRequestModel,
    PipelineBuildResponseModel,
    PipelineDeploymentRequestModel,
    PipelineDeploymentResponseModel,
    PipelineRequestModel,
    PipelineResponseModel,
    ScheduleRequestModel,
)
from zenml.models.pipeline_build_models import (
    BuildItem,
    PipelineBuildBaseModel,
)
from zenml.models.pipeline_deployment_models import PipelineDeploymentBaseModel
from zenml.stack import Stack
from zenml.steps import BaseStep
from zenml.steps.base_step import BaseStepMeta
from zenml.utils import (
    dashboard_utils,
    dict_utils,
    pydantic_utils,
    settings_utils,
    yaml_utils,
)
from zenml.utils.analytics_utils import AnalyticsEvent, event_handler
from zenml.utils.pipeline_docker_image_builder import (
    PipelineDockerImageBuilder,
)

if TYPE_CHECKING:
    from zenml.config.base_settings import SettingsOrDict
    from zenml.post_execution import PipelineRunView

    StepConfigurationUpdateOrDict = Union[
        Dict[str, Any], StepConfigurationUpdate
    ]
    HookSpecification = Union[str, FunctionType]

logger = get_logger(__name__)
PIPELINE_INNER_FUNC_NAME = "connect"
PARAM_ENABLE_CACHE = "enable_cache"
PARAM_ENABLE_ARTIFACT_METADATA = "enable_artifact_metadata"
INSTANCE_CONFIGURATION = "INSTANCE_CONFIGURATION"
PARAM_SETTINGS = "settings"
PARAM_EXTRA_OPTIONS = "extra"
PARAM_ON_FAILURE = "on_failure"
PARAM_ON_SUCCESS = "on_success"


class BasePipelineMeta(type):
    """Pipeline Metaclass responsible for validating the pipeline definition."""

    def __new__(
        mcs, name: str, bases: Tuple[Type[Any], ...], dct: Dict[str, Any]
    ) -> "BasePipelineMeta":
        """Saves argument names for later verification purposes.

        Args:
            name: The name of the class.
            bases: The base classes of the class.
            dct: The dictionary of the class.

        Returns:
            The class.
        """
        dct.setdefault(INSTANCE_CONFIGURATION, {})
        cls = cast(
            Type["BasePipeline"], super().__new__(mcs, name, bases, dct)
        )

        cls.STEP_SPEC = {}

        connect_spec = inspect.getfullargspec(
            inspect.unwrap(getattr(cls, PIPELINE_INNER_FUNC_NAME))
        )
        connect_args = connect_spec.args

        if connect_args and connect_args[0] == "self":
            connect_args.pop(0)

        for arg in connect_args:
            arg_type = connect_spec.annotations.get(arg, None)
            cls.STEP_SPEC.update({arg: arg_type})
        return cls


T = TypeVar("T", bound="BasePipeline")


class BasePipeline(metaclass=BasePipelineMeta):
    """Abstract base class for all ZenML pipelines.

    Attributes:
        name: The name of this pipeline.
        enable_cache: A boolean indicating if caching is enabled for this
            pipeline.
        enable_artifact_metadata: A boolean indicating if artifact metadata
            is enabled for this pipeline.
    """

    STEP_SPEC: ClassVar[Dict[str, Any]] = None  # type: ignore[assignment]

    INSTANCE_CONFIGURATION: Dict[str, Any] = {}

    def __init__(self, *args: BaseStep, **kwargs: Any) -> None:
        """Initialize the BasePipeline.

        Args:
            *args: The steps to be executed by this pipeline.
            **kwargs: The configuration for this pipeline.
        """
        kwargs.update(self.INSTANCE_CONFIGURATION)

        self._configuration = PipelineConfiguration(
            name=self.__class__.__name__,
            enable_cache=kwargs.pop(PARAM_ENABLE_CACHE, None),
            enable_artifact_metadata=kwargs.pop(
                PARAM_ENABLE_ARTIFACT_METADATA, None
            ),
        )
        self._apply_class_configuration(kwargs)

        self.__steps: Dict[str, BaseStep] = {}
        self._verify_steps(*args, **kwargs)

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
    def steps(self) -> Dict[str, BaseStep]:
        """Returns a dictionary of pipeline steps.

        Returns:
            A dictionary of pipeline steps.
        """
        return self.__steps

    @classmethod
    def from_model(cls: Type[T], model: "PipelineResponseModel") -> T:
        """Creates a pipeline instance from a model.

        Args:
            model: The model to load the pipeline instance from.

        Returns:
            The pipeline instance.

        Raises:
            ValueError: If the spec version of the given model is <0.2
        """
        if version.parse(model.spec.version) < version.parse("0.2"):
            raise ValueError(
                "Loading a pipeline is only possible for pipeline specs with "
                "version 0.2 or higher."
            )

        steps = cls._load_and_verify_steps(pipeline_spec=model.spec)
        connect_method = cls._generate_connect_method(model=model)

        pipeline_class: Type[T] = type(
            model.name,
            (cls,),
            {
                PIPELINE_INNER_FUNC_NAME: staticmethod(connect_method),
                "__doc__": model.docstring,
            },
        )

        pipeline_instance = pipeline_class(**steps)

        version_hash = pipeline_instance._compute_unique_identifier(
            pipeline_spec=model.spec
        )
        if version_hash != model.version_hash:
            logger.warning(
                "Trying to load pipeline version `%s`, but the local step code "
                "changed since this pipeline version was registered. Using "
                "this pipeline instance will result in a different pipeline "
                "version being registered or reused.",
                model.version,
            )

        return pipeline_instance

    def configure(
        self: T,
        enable_cache: Optional[bool] = None,
        enable_artifact_metadata: Optional[bool] = None,
        settings: Optional[Mapping[str, "SettingsOrDict"]] = None,
        extra: Optional[Dict[str, Any]] = None,
        merge: bool = True,
        on_failure: Optional["HookSpecification"] = None,
        on_success: Optional["HookSpecification"] = None,
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
            merge: If `True`, will merge the given dictionary configurations
                like `extra` and `settings` with existing
                configurations. If `False` the given configurations will
                overwrite all existing ones. See the general description of this
                method for an example.
            on_failure: Callback function in event of failure of the step. Can be
                a function with three possible parameters, `StepContext`, `BaseParameters`,
                and `BaseException`, or a source path to a function of the same specifications
                (e.g. `module.my_function`)
            on_success: Callback function in event of failure of the step. Can be
                a function with two possible parameters, `StepContext` and `BaseParameters, or
                a source path to a function of the same specifications
                (e.g. `module.my_function`).

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

    @abstractmethod
    def connect(self, *args: BaseStep, **kwargs: BaseStep) -> None:
        """Function that connects inputs and outputs of the pipeline steps.

        Args:
            *args: The positional arguments passed to the pipeline.
            **kwargs: The keyword arguments passed to the pipeline.

        Raises:
            NotImplementedError: Always.
        """
        raise NotImplementedError

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
                be parsed as a `zenml.config.pipeline_configurations.PipelineRunConfiguration`
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

            return self._build(deployment=deployment, pipeline_id=pipeline_id)

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
    ) -> None:
        """Runs the pipeline on the active stack of the current repository.

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
                be parsed as a `zenml.config.pipeline_configurations.PipelineRunConfiguration`
                object. Options provided in this file will be overwritten by
                options provided in code using the other arguments of this
                method.
            unlisted: Whether the pipeline run should be unlisted (not assigned
                to any pipeline).
        """
        if constants.SHOULD_PREVENT_PIPELINE_EXECUTION:
            # An environment variable was set to stop the execution of
            # pipelines. This is done to prevent execution of module-level
            # pipeline.run() calls inside docker containers which should only
            # run a single step.
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

            build_model = self._load_or_create_pipeline_build(
                deployment=deployment,
                pipeline_spec=pipeline_spec,
                pipeline_id=pipeline_id,
                build=build,
            )
            build_id = build_model.id if build_model else None

            deployment_request = PipelineDeploymentRequestModel(
                user=Client().active_user.id,
                workspace=Client().active_workspace.id,
                stack=stack.id,
                pipeline=pipeline_id,
                build=build_id,
                schedule=schedule_id,
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
                stack.deploy_pipeline(
                    deployment=deployment_model,
                )
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
        for step_name, step in self.steps.items():
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

    def _apply_class_configuration(self, options: Dict[str, Any]) -> None:
        """Applies the configurations specified on the pipeline class.

        Args:
            options: Class configurations.
        """
        settings = options.pop(PARAM_SETTINGS, None)
        extra = options.pop(PARAM_EXTRA_OPTIONS, None)
        on_failure = options.pop(PARAM_ON_FAILURE, None)
        on_success = options.pop(PARAM_ON_SUCCESS, None)
        self.configure(
            settings=settings,
            extra=extra,
            on_failure=on_failure,
            on_success=on_success,
        )

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

    def _verify_steps(self, *steps: BaseStep, **kw_steps: Any) -> None:
        """Verifies the initialization args and kwargs of this pipeline.

        This method makes sure that no missing/unexpected arguments or
        arguments of a wrong type are passed when creating a pipeline. If
        all arguments are correct, saves the steps to `self.__steps`.

        Args:
            *steps: The args passed to the init method of this pipeline.
            **kw_steps: The kwargs passed to the init method of this pipeline.

        Raises:
            PipelineInterfaceError: If there are too many/few arguments or
                arguments with a wrong name/type.
        """
        input_step_keys = list(self.STEP_SPEC.keys())
        if len(steps) > len(input_step_keys):
            raise PipelineInterfaceError(
                f"Too many input steps for pipeline '{self.name}'. "
                f"This pipeline expects {len(input_step_keys)} step(s) "
                f"but got {len(steps) + len(kw_steps)}."
            )

        combined_steps = {}
        step_ids: Dict[int, str] = {}

        def _verify_step(key: str, step: BaseStep) -> None:
            """Verifies a single step of the pipeline.

            Args:
                key: The key of the step.
                step: The step to verify.

            Raises:
                PipelineInterfaceError: If the step is not of the correct type
                    or is of the same class as another step.
            """
            step_class = type(step)

            if isinstance(step, BaseStepMeta):
                raise PipelineInterfaceError(
                    f"Wrong argument type (`{step_class}`) for argument "
                    f"'{key}' of pipeline '{self.name}'. "
                    f"A `BaseStep` subclass was provided instead of an "
                    f"instance. "
                    f"This might have been caused due to missing brackets of "
                    f"your steps when creating a pipeline with `@step` "
                    f"decorated functions, "
                    f"for which the correct syntax is `pipeline(step=step())`."
                )

            if not isinstance(step, BaseStep):
                raise PipelineInterfaceError(
                    f"Wrong argument type (`{step_class}`) for argument "
                    f"'{key}' of pipeline '{self.name}'. Only "
                    f"`@step` decorated functions or instances of `BaseStep` "
                    f"subclasses can be used as arguments when creating "
                    f"a pipeline."
                )

            if id(step) in step_ids:
                previous_key = step_ids[id(step)]
                raise PipelineInterfaceError(
                    f"Found the same step object for arguments "
                    f"'{previous_key}' and '{key}' in pipeline '{self.name}'. "
                    "Step object cannot be reused inside a ZenML pipeline. "
                    "A possible solution is to create two instances of the "
                    "same step class and assigning them different names: "
                    "`first_instance = step_class(name='s1')` and "
                    "`second_instance = step_class(name='s2')`."
                )

            step_ids[id(step)] = key
            combined_steps[key] = step

        # verify args
        for i, step in enumerate(steps):
            key = input_step_keys[i]
            _verify_step(key, step)

        # verify kwargs
        for key, step in kw_steps.items():
            if key in combined_steps:
                # a step for this key was already set by
                # the positional input steps
                raise PipelineInterfaceError(
                    f"Unexpected keyword argument '{key}' for pipeline "
                    f"'{self.name}'. A step for this key was "
                    f"already passed as a positional argument."
                )
            _verify_step(key, step)

        # check if there are any missing or unexpected steps
        expected_steps = set(self.STEP_SPEC.keys())
        actual_steps = set(combined_steps.keys())
        missing_steps = expected_steps - actual_steps
        unexpected_steps = actual_steps - expected_steps

        if missing_steps:
            raise PipelineInterfaceError(
                f"Missing input step(s) for pipeline "
                f"'{self.name}': {missing_steps}."
            )

        if unexpected_steps:
            raise PipelineInterfaceError(
                f"Unexpected input step(s) for pipeline "
                f"'{self.name}': {unexpected_steps}. This pipeline "
                f"only requires the following steps: {expected_steps}."
            )

        self.__steps = combined_steps

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
                if not output.materializer_source.startswith("zenml."):
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

    @staticmethod
    def _load_and_verify_steps(
        pipeline_spec: "PipelineSpec",
    ) -> Dict[str, BaseStep]:
        """Loads steps and verifies their names and inputs/outputs names.

        Args:
            pipeline_spec: The pipeline spec from which to load the steps.

        Raises:
            RuntimeError: If the step names or input/output names of the
                loaded steps don't match with the names defined in the spec.

        Returns:
            The loaded steps.
        """
        steps = {}
        available_outputs: Dict[str, Set[str]] = {}

        for step_spec in pipeline_spec.steps:
            for upstream_step in step_spec.upstream_steps:
                if upstream_step not in available_outputs:
                    raise RuntimeError(
                        f"Unable to find upstream step `{upstream_step}`. "
                        "This is probably because the step was renamed in code."
                    )

            for input_spec in step_spec.inputs.values():
                if (
                    input_spec.output_name
                    not in available_outputs[input_spec.step_name]
                ):
                    raise RuntimeError(
                        f"Missing output `{input_spec.output_name}` for step "
                        f"`{input_spec.step_name}`. This is probably because "
                        "the output of the step was renamed."
                    )

            step = BaseStep.load_from_source(step_spec.source)
            input_names = set(step.INPUT_SIGNATURE)
            spec_input_names = set(step_spec.inputs)

            if input_names != spec_input_names:
                raise RuntimeError(
                    f"Input names of step {step_spec.source} and the spec "
                    f"from the database don't match. Step inputs: "
                    f"`{input_names}`, spec inputs: `{spec_input_names}`."
                )

            steps[step_spec.pipeline_parameter_name] = step
            available_outputs[step.name] = set(step.OUTPUT_SIGNATURE.keys())

        return steps

    @staticmethod
    def _generate_connect_method(
        model: "PipelineResponseModel",
    ) -> Callable[..., None]:
        """Dynamically generates a connect method for a pipeline model.

        Args:
            model: The model for which to generate the method.

        Returns:
            The generated connect method.
        """

        def connect(**steps: BaseStep) -> None:
            # Bind **steps to the connect signature assigned to this method
            # below. This ensures that the method inputs get verified and only
            # the arguments defined in the signature are allowed
            inspect.signature(connect).bind(**steps)

            step_outputs: Dict[str, Dict[str, BaseStep._OutputArtifact]] = {}
            for step_spec in model.spec.steps:
                step = steps[step_spec.pipeline_parameter_name]

                step_inputs = {}
                for input_name, input_ in step_spec.inputs.items():
                    try:
                        upstream_step = step_outputs[input_.step_name]
                        step_input = upstream_step[input_.output_name]
                        step_inputs[input_name] = step_input
                    except KeyError:
                        raise RuntimeError(
                            f"Unable to find upstream step "
                            f"`{input_.step_name}` in pipeline `{model.name}`. "
                            "This is probably due to configuring a new step "
                            "name after loading a pipeline using "
                            "`BasePipeline.from_model`."
                        )

                step_output = step(**step_inputs)
                output_keys = list(step.OUTPUT_SIGNATURE.keys())

                if isinstance(step_output, BaseStep._OutputArtifact):
                    step_output = [step_output]

                step_outputs[step.name] = {
                    key: step_output[i] for i, key in enumerate(output_keys)
                }

        # Create the connect method signature based on the expected steps
        parameters = [
            inspect.Parameter(
                name=step_spec.pipeline_parameter_name,
                kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
            )
            for step_spec in model.spec.steps
        ]
        signature = inspect.Signature(parameters=parameters)
        connect.__signature__ = signature  # type: ignore[attr-defined]

        return connect

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
        hash_.update(pipeline_spec.json(sort_keys=False).encode())

        for step_spec in pipeline_spec.steps:
            step_source = self.steps[
                step_spec.pipeline_parameter_name
            ].source_code
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

    def _load_or_create_pipeline_build(
        self,
        deployment: "PipelineDeploymentBaseModel",
        pipeline_spec: "PipelineSpec",
        pipeline_id: Optional[UUID] = None,
        build: Union["UUID", "PipelineBuildBaseModel", None] = None,
    ) -> Optional["PipelineBuildResponseModel"]:
        """Loads or creates a pipeline build.

        Args:
            deployment: The pipeline deployment for which to load or create the
                build.
            pipeline_spec: Spec of the pipeline.
            pipeline_id: Optional ID of the pipeline to reference in the build.
            build: Optional existing build. If given, the build will be loaded
                (or registered) in the database. If not given, a new build will
                be created.

        Returns:
            The build response.
        """
        if not build:
            return self._build(deployment=deployment, pipeline_id=pipeline_id)

        logger.info(
            "Using an old build for a pipeline run can lead to "
            "unexpected behavior as the pipeline will run with the step "
            "code that was included in the Docker images which might "
            "differ from the code in your client environment."
        )

        build_model = None

        if isinstance(build, UUID):
            build_model = Client().zen_store.get_build(build_id=build)

            if build_model.pipeline:
                build_hash = build_model.pipeline.version_hash
                current_hash = self._compute_unique_identifier(
                    pipeline_spec=pipeline_spec
                )

                if build_hash != current_hash:
                    logger.warning(
                        "The pipeline associated with the build you "
                        "specified for this run has a different spec "
                        "or step code. This might lead to unexpected "
                        "behavior as this pipeline run will use the "
                        "code that was included in the Docker images which "
                        "might differ from the code in your client "
                        "environment."
                    )
        else:
            build_request = PipelineBuildRequestModel(
                user=Client().active_user.id,
                workspace=Client().active_workspace.id,
                stack=Client().active_stack_model.id,
                pipeline=pipeline_id,
                **build.dict(),
            )
            build_model = Client().zen_store.create_build(build=build_request)

        if build_model.is_local:
            logger.warning(
                "You're using a local build to run your pipeline. This "
                "might lead to errors if the images don't exist on "
                "your local machine or the image tags have been "
                "overwritten since the original build happened."
            )

        return build_model

    def _build(
        self,
        deployment: "PipelineDeploymentBaseModel",
        pipeline_id: Optional[UUID] = None,
    ) -> Optional["PipelineBuildResponseModel"]:
        """Builds images and registers the output in the server.

        Args:
            deployment: The compiled pipeline deployment.
            pipeline_id: The ID of the pipeline.

        Returns:
            The build output.

        Raises:
            RuntimeError: If multiple builds with the same key but different
                settings were specified.
        """
        client = Client()
        stack = client.active_stack
        required_builds = stack.get_docker_builds(deployment=deployment)

        if not required_builds:
            logger.debug("No docker builds required.")
            return None

        logger.info(
            "Building Docker image(s) for pipeline `%s`.",
            deployment.pipeline_configuration.name,
        )

        docker_image_builder = PipelineDockerImageBuilder()
        images: Dict[str, BuildItem] = {}
        image_names: Dict[str, str] = {}

        for build_config in required_builds:
            combined_key = PipelineBuildBaseModel.get_image_key(
                component_key=build_config.key, step=build_config.step_name
            )
            checksum = build_config.compute_settings_checksum(stack=stack)

            if combined_key in images:
                previous_checksum = images[combined_key].settings_checksum

                if previous_checksum != checksum:
                    raise RuntimeError(
                        f"Trying to build image for key `{combined_key}` but "
                        "an image for this key was already built with a "
                        "different configuration. This happens if multiple "
                        "stack components specified Docker builds for the same "
                        "key in the `StackComponent.get_docker_builds(...)` "
                        "method. If you're using custom components, make sure "
                        "to provide unique keys when returning your build "
                        "configurations to avoid this error."
                    )
                else:
                    continue

            if checksum in image_names:
                image_name_or_digest = image_names[checksum]
            else:
                tag = deployment.pipeline_configuration.name
                if build_config.step_name:
                    tag += f"-{build_config.step_name}"
                tag += f"-{build_config.key}"

                image_name_or_digest = docker_image_builder.build_docker_image(
                    docker_settings=build_config.settings,
                    tag=tag,
                    stack=stack,
                    entrypoint=build_config.entrypoint,
                    extra_files=build_config.extra_files,
                )

            images[combined_key] = BuildItem(
                image=image_name_or_digest, settings_checksum=checksum
            )
            image_names[checksum] = image_name_or_digest

        logger.info("Finished building Docker image(s).")

        is_local = stack.container_registry is None
        build_request = PipelineBuildRequestModel(
            user=client.active_user.id,
            workspace=client.active_workspace.id,
            stack=client.active_stack_model.id,
            pipeline=pipeline_id,
            is_local=is_local,
            images=images,
        )
        return client.zen_store.create_build(build_request)
