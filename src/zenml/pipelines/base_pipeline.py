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

import inspect
from abc import abstractmethod
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    List,
    Mapping,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)

import yaml

from zenml import constants
from zenml.client import Client
from zenml.config.config_keys import (
    PipelineConfigurationKeys,
    StepConfigurationKeys,
)
from zenml.config.pipeline_configurations import (
    PipelineConfiguration,
    PipelineConfigurationUpdate,
    PipelineRunConfiguration,
    PipelineSpec,
)
from zenml.config.pipeline_deployment import PipelineDeployment
from zenml.config.schedule import Schedule
from zenml.config.step_configurations import StepConfigurationUpdate
from zenml.exceptions import PipelineConfigurationError, PipelineInterfaceError
from zenml.logger import get_logger
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

if TYPE_CHECKING:
    from zenml.config.base_settings import SettingsOrDict
    from zenml.post_execution import PipelineRunView

    StepConfigurationUpdateOrDict = Union[
        Dict[str, Any], StepConfigurationUpdate
    ]

logger = get_logger(__name__)
PIPELINE_INNER_FUNC_NAME = "connect"
PARAM_ENABLE_CACHE = "enable_cache"
INSTANCE_CONFIGURATION = "INSTANCE_CONFIGURATION"
PARAM_SETTINGS = "settings"
PARAM_EXTRA_OPTIONS = "extra"


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
        cls = cast(Type["BasePipeline"], super().__new__(mcs, name, bases, dct))

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
            enable_cache=kwargs.pop(PARAM_ENABLE_CACHE, True),
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
    def enable_cache(self) -> bool:
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

    def configure(
        self: T,
        enable_cache: Optional[bool] = None,
        settings: Optional[Mapping[str, "SettingsOrDict"]] = None,
        extra: Optional[Dict[str, Any]] = None,
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
            settings: settings for this pipeline.
            extra: Extra configurations for this pipeline.
            merge: If `True`, will merge the given dictionary configurations
                like `extra` and `settings` with existing
                configurations. If `False` the given configurations will
                overwrite all existing ones. See the general description of this
                method for an example.

        Returns:
            The pipeline instance that this method was called on.
        """
        values = dict_utils.remove_none_values(
            {
                "enable_cache": enable_cache,
                "settings": settings,
                "extra": extra,
            }
        )
        config = PipelineConfigurationUpdate(**values)
        self._apply_configuration(config, merge=merge)
        return self

    def _apply_class_configuration(self, options: Dict[str, Any]) -> None:
        """Applies the configurations specified on the pipeline class.

        Args:
            options: Class configurations.
        """
        settings = options.pop(PARAM_SETTINGS, None)
        extra = options.pop(PARAM_EXTRA_OPTIONS, None)
        self.configure(settings=settings, extra=extra)

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

            step.pipeline_parameter_name = key
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

    def _get_pipeline_analytics_metadata(
        self,
        deployment: "PipelineDeployment",
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
        for step in deployment.steps.values():
            for output in step.config.outputs.values():
                if not output.materializer_source.startswith("zenml."):
                    custom_materializer = True

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
        }

    def run(
        self,
        *,
        run_name: Optional[str] = None,
        enable_cache: Optional[bool] = None,
        schedule: Optional[Schedule] = None,
        settings: Optional[Mapping[str, "SettingsOrDict"]] = None,
        step_configurations: Optional[
            Mapping[str, "StepConfigurationUpdateOrDict"]
        ] = None,
        extra: Optional[Dict[str, Any]] = None,
        config_path: Optional[str] = None,
        unlisted: bool = False,
    ) -> Any:
        """Runs the pipeline on the active stack of the current repository.

        Args:
            run_name: Name of the pipeline run.
            enable_cache: If caching should be enabled for this pipeline run.
            schedule: Optional schedule of the pipeline.
            settings: settings for this pipeline run.
            step_configurations: Configurations for steps of the pipeline.
            extra: Extra configurations for this pipeline run.
            config_path: Path to a yaml configuration file. This file will
                be parsed as a `zenml.config.pipeline_configurations.PipelineRunConfiguration`
                object. Options provided in this file will be overwritten by
                options provided in code using the other arguments of this
                method.
            unlisted: Whether the pipeline run should be unlisted (not assigned
                to any pipeline).

        Returns:
            The result of the pipeline.
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

        with event_handler(AnalyticsEvent.RUN_PIPELINE) as analytics_handler:
            stack = Client().active_stack

            # Activating the built-in integrations through lazy loading
            from zenml.integrations.registry import integration_registry

            integration_registry.activate_integrations()

            if config_path:
                config_dict = yaml_utils.read_yaml(config_path)
                run_config = PipelineRunConfiguration.parse_obj(config_dict)
            else:
                run_config = PipelineRunConfiguration()

            new_values = dict_utils.remove_none_values(
                {
                    "run_name": run_name,
                    "enable_cache": enable_cache,
                    "steps": step_configurations,
                    "settings": settings,
                    "schedule": schedule,
                    "extra": extra,
                }
            )

            # Update with the values in code so they take precedence
            run_config = pydantic_utils.update_model(
                run_config, update=new_values
            )
            from zenml.config.compiler import Compiler

            pipeline_deployment = Compiler().compile(
                pipeline=self, stack=stack, run_configuration=run_config
            )

            skip_pipeline_registration = constants.handle_bool_env_var(
                constants.ENV_ZENML_SKIP_PIPELINE_REGISTRATION, default=False
            )

            register_pipeline = not (skip_pipeline_registration or unlisted)

            pipeline_id = None
            if register_pipeline:
                step_specs = [
                    step.spec for step in pipeline_deployment.steps.values()
                ]
                pipeline_spec = PipelineSpec(steps=step_specs)

                pipeline_id = Client().create_pipeline(
                    pipeline_name=pipeline_deployment.pipeline.name,
                    pipeline_spec=pipeline_spec,
                    pipeline_docstring=self.__doc__,
                )
                pipeline_deployment = pipeline_deployment.copy(
                    update={"pipeline_id": pipeline_id}
                )

            analytics_handler.metadata = self._get_pipeline_analytics_metadata(
                deployment=pipeline_deployment, stack=stack
            )
            caching_status = (
                "enabled"
                if pipeline_deployment.pipeline.enable_cache
                else "disabled"
            )
            logger.info(
                "%s %s on stack `%s` (caching %s)",
                "Scheduling" if pipeline_deployment.schedule else "Running",
                f"pipeline `{pipeline_deployment.pipeline.name}`"
                if register_pipeline
                else "unlisted pipeline",
                stack.name,
                caching_status,
            )
            stack.prepare_pipeline_deployment(deployment=pipeline_deployment)

            # Prevent execution of nested pipelines which might lead to
            # unexpected behavior
            constants.SHOULD_PREVENT_PIPELINE_EXECUTION = True
            try:
                return_value = stack.deploy_pipeline(pipeline_deployment)
            finally:
                constants.SHOULD_PREVENT_PIPELINE_EXECUTION = False

            # Log the dashboard URL
            dashboard_utils.print_run_url(
                run_name=pipeline_deployment.run_name, pipeline_id=pipeline_id
            )

            return return_value

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

    def with_config(
        self: T, config_file: str, overwrite_step_parameters: bool = False
    ) -> T:
        """DEPRECATED: Configures this pipeline using a yaml file.

        Args:
            config_file: Path to a yaml file which contains configuration
                options for running this pipeline. See
                https://docs.zenml.io/advanced-guide/pipelines/settings
                for details regarding the specification of this file.
            overwrite_step_parameters: If set to `True`, values from the
                configuration file will overwrite configuration parameters
                passed in code.

        Returns:
            The pipeline object that this method was called on.
        """
        logger.warning(
            "The `with_config(...)` method is deprecated. Use "
            "`pipeline.configure(...)` or `pipeline.run(config_path=...)` "
            "instead."
        )

        config_yaml = yaml_utils.read_yaml(config_file)

        if PipelineConfigurationKeys.STEPS in config_yaml:
            self._read_config_steps(
                config_yaml[PipelineConfigurationKeys.STEPS],
                overwrite=overwrite_step_parameters,
            )

        return self

    def _read_config_steps(
        self, steps: Dict[str, Dict[str, Any]], overwrite: bool = False
    ) -> None:
        """Reads and sets step parameters from a config file.

        Args:
            steps: Maps step names to dicts of parameter names and values.
            overwrite: If `True`, overwrite previously set step parameters.

        Raises:
            PipelineConfigurationError: If the configuration file contains
                invalid data.
        """
        for step_name, step_dict in steps.items():
            StepConfigurationKeys.key_check(step_dict)

            if step_name not in self.__steps:
                raise PipelineConfigurationError(
                    f"Found '{step_name}' step in configuration yaml but it "
                    f"doesn't exist in the pipeline steps "
                    f"{list(self.__steps.keys())}."
                )

            step = self.__steps[step_name]
            parameters = step_dict.get(StepConfigurationKeys.PARAMETERS_, {})
            enable_cache = parameters.pop(PARAM_ENABLE_CACHE, None)

            if not overwrite:
                parameters.update(step.configuration.parameters)

            step.configure(
                enable_cache=enable_cache,
                parameters=parameters,
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
