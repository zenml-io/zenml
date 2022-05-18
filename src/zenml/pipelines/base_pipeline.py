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
import inspect
from abc import abstractmethod
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    List,
    NoReturn,
    Optional,
    Set,
    Text,
    Tuple,
    Type,
    TypeVar,
    cast,
)

import zenml.cli.utils as cli_utils
from zenml import constants
from zenml.config.config_keys import (
    PipelineConfigurationKeys,
    StepConfigurationKeys,
)
from zenml.exceptions import (
    DuplicatedConfigurationError,
    PipelineConfigurationError,
    PipelineInterfaceError,
    StackValidationError,
)
from zenml.integrations.registry import integration_registry
from zenml.io import fileio, utils
from zenml.logger import get_logger
from zenml.pipelines.schedule import Schedule
from zenml.repository import Repository
from zenml.runtime_configuration import RuntimeConfiguration
from zenml.steps import BaseStep
from zenml.steps.base_step import BaseStepMeta
from zenml.utils import yaml_utils
from zenml.utils.analytics_utils import AnalyticsEvent, track_event

if TYPE_CHECKING:
    from zenml.stack import Stack

logger = get_logger(__name__)
PIPELINE_INNER_FUNC_NAME: str = "connect"
PARAM_ENABLE_CACHE: str = "enable_cache"
PARAM_REQUIRED_INTEGRATIONS: str = "required_integrations"
PARAM_REQUIREMENTS_FILE: str = "requirements_file"
PARAM_REQUIREMENTS: str = "requirements"
PARAM_DOCKERIGNORE_FILE: str = "dockerignore_file"
INSTANCE_CONFIGURATION = "INSTANCE_CONFIGURATION"
PARAM_SECRETS: str = "secrets"


class BasePipelineMeta(type):
    """Pipeline Metaclass responsible for validating the pipeline definition."""

    def __new__(
        mcs, name: str, bases: Tuple[Type[Any], ...], dct: Dict[str, Any]
    ) -> "BasePipelineMeta":
        """Saves argument names for later verification purposes"""
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
        requirements_file: DEPRECATED: Optional path to a pip requirements file
            that contains all requirements to run the pipeline. (Use
            `requirements` instead.)
        requirements: Optional list of (string) pip requirements to run the pipeline, or a string path to a requirements file.
        required_integrations: Optional set of integrations that need to be
            installed for this pipeline to run.
    """

    STEP_SPEC: ClassVar[Dict[str, Any]] = None  # type: ignore[assignment]

    INSTANCE_CONFIGURATION: Dict[Text, Any] = {}

    def __init__(self, *args: BaseStep, **kwargs: Any) -> None:
        kwargs.update(getattr(self, INSTANCE_CONFIGURATION))
        self.enable_cache = kwargs.pop(PARAM_ENABLE_CACHE, True)
        self.required_integrations = kwargs.pop(PARAM_REQUIRED_INTEGRATIONS, ())
        self.requirements_file = kwargs.pop(PARAM_REQUIREMENTS_FILE, None)
        if self.requirements_file:
            logger.warning(
                "The `requirements_file` argument has been deprecated. Please use `requirements` instead to pass in either a string path to a file listing your 'requirements' or a list of the individual requirements."
            )
        self._requirements = kwargs.pop(PARAM_REQUIREMENTS, None)
        self.dockerignore_file = kwargs.pop(PARAM_DOCKERIGNORE_FILE, None)
        self.secrets = kwargs.pop(PARAM_SECRETS, [])

        self.name = self.__class__.__name__
        self.__steps: Dict[str, BaseStep] = {}
        self._verify_arguments(*args, **kwargs)

    def _verify_arguments(self, *steps: BaseStep, **kw_steps: BaseStep) -> None:
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
        step_classes: Dict[Type[BaseStep], str] = {}

        def _verify_step(key: str, step: BaseStep) -> None:
            """Verifies a single step of the pipeline."""
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

            if step_class in step_classes:
                previous_key = step_classes[step_class]
                raise PipelineInterfaceError(
                    f"Found multiple step objects of the same class "
                    f"(`{step_class}`) for arguments '{previous_key}' and "
                    f"'{key}' in pipeline '{self.name}'. Only one step object "
                    f"per class is allowed inside a ZenML pipeline."
                )

            step.pipeline_parameter_name = key
            combined_steps[key] = step
            step_classes[step_class] = key

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
        """Function that connects inputs and outputs of the pipeline steps."""
        raise NotImplementedError

    @property
    def requirements(self) -> Set[str]:
        """Set of Python requirements of this pipeline.

        This property is a combination of the requirements of
        - required integrations for this pipeline
        - the `requirements` specified for this pipeline
        """
        requirements = set()

        for integration_name in self.required_integrations:
            try:
                integration_requirements = (
                    integration_registry.select_integration_requirements(
                        integration_name
                    )
                )
                requirements.update(integration_requirements)
            except KeyError as e:
                raise KeyError(
                    f"Unable to find requirements for integration "
                    f"'{integration_name}'."
                ) from e

        if isinstance(self._requirements, str) and fileio.exists(
            self._requirements
        ):
            with fileio.open(self._requirements, "r") as f:
                requirements.update(
                    {
                        requirement.strip()
                        for requirement in f.read().split("\n")
                    }
                )
            if self.requirements_file:
                cli_utils.warning(
                    f"Using the file path passed in as `requirements` and ignoring the file '{self.requirements_file}'."
                )
        # Add this logic back in (described in #ENG-882)
        #
        # elif isinstance(self._requirements, str) and self._requirements:
        #     root = str(Repository().root)
        #     if root:
        #         assumed_requirements_file = os.path.join(
        #             root, "requirements.txt"
        #         )
        #         if fileio.exists(assumed_requirements_file):
        #             with fileio.open(assumed_requirements_file, "r") as f:
        #                 requirements.update(
        #                     {
        #                         requirement.strip()
        #                         for requirement in f.read().split("\n")
        #                     }
        #                 )
        #                 logger.info(
        #                     "Using requirements file: `%s`",
        #                     assumed_requirements_file,
        #                 )
        elif isinstance(self._requirements, List):
            requirements.update(self._requirements)
            if self.requirements_file:
                cli_utils.warning(
                    f"Using the values passed in as `requirements` and ignoring the file '{self.requirements_file}'."
                )
        elif self.requirements_file and fileio.exists(self.requirements_file):
            # TODO [ENG-883]: Deprecate the `requirements_file` option
            with fileio.open(self.requirements_file, "r") as f:
                requirements.update(
                    {
                        requirement.strip()
                        for requirement in f.read().split("\n")
                    }
                )

        return requirements

    @property
    def steps(self) -> Dict[str, BaseStep]:
        """Returns a dictionary of pipeline steps."""
        return self.__steps

    @steps.setter
    def steps(self, steps: Dict[str, BaseStep]) -> NoReturn:
        """Setting the steps property is not allowed. This method always
        raises a PipelineInterfaceError.
        """
        raise PipelineInterfaceError("Cannot set steps manually!")

    def validate_stack(self, stack: "Stack") -> None:
        """Validates if a stack is able to run this pipeline."""
        available_step_operators = (
            {stack.step_operator.name} if stack.step_operator else set()
        )

        for step in self.steps.values():
            if (
                step.custom_step_operator
                and step.custom_step_operator not in available_step_operators
            ):
                raise StackValidationError(
                    f"Step '{step.name}' requires custom step operator "
                    f"'{step.custom_step_operator}' which is not configured in "
                    f"the active stack. Available step operators: "
                    f"{available_step_operators}."
                )

    def _reset_step_flags(self) -> None:
        """Reset the _has_been_called flag at the beginning of a pipeline run,
        to make sure a pipeline instance can be called more than once."""
        for step in self.steps.values():
            step._has_been_called = False

    def run(
        self,
        *,
        run_name: Optional[str] = None,
        schedule: Optional[Schedule] = None,
        **additional_parameters: Any,
    ) -> Any:
        """Runs the pipeline on the active stack of the current repository.

        Args:
            run_name: Name of the pipeline run.
            schedule: Optional schedule of the pipeline.
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

        logger.info("Creating run for pipeline: `%s`", self.name)
        logger.info(
            f'Cache {"enabled" if self.enable_cache else "disabled"} for '
            f"pipeline `{self.name}`"
        )

        # Activating the built-in integrations through lazy loading
        from zenml.integrations.registry import integration_registry

        integration_registry.activate_integrations()

        # Path of the file where pipeline.run() was called. This is needed by
        # the airflow orchestrator so it knows which file to copy into the DAG
        # directory
        dag_filepath = utils.resolve_relative_path(
            inspect.currentframe().f_back.f_code.co_filename  # type: ignore[union-attr]
        )
        runtime_configuration = RuntimeConfiguration(
            run_name=run_name,
            dag_filepath=dag_filepath,
            schedule=schedule,
            **additional_parameters,
        )
        stack = Repository().active_stack

        stack_metadata = {
            component_type.value: component.FLAVOR
            for component_type, component in stack.components.items()
        }
        track_event(
            event=AnalyticsEvent.RUN_PIPELINE,
            metadata={
                "store_type": Repository().active_profile.store_type.value,
                **stack_metadata,
                "total_steps": len(self.steps),
                "schedule": bool(schedule),
            },
        )

        self._reset_step_flags()
        self.validate_stack(stack)

        return stack.deploy_pipeline(
            self, runtime_configuration=runtime_configuration
        )

    def with_config(
        self: T, config_file: str, overwrite_step_parameters: bool = False
    ) -> T:
        """Configures this pipeline using a yaml file.

        Args:
            config_file: Path to a yaml file which contains configuration
                options for running this pipeline. See
                https://docs.zenml.io/features/pipeline-configuration#setting
                -step-parameters-using-a-config-file
                for details regarding the specification of this file.
            overwrite_step_parameters: If set to `True`, values from the
                configuration file will overwrite configuration parameters
                passed in code.

        Returns:
            The pipeline object that this method was called on.
        """
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
            step_parameters = (
                step.CONFIG_CLASS.__fields__.keys() if step.CONFIG_CLASS else {}
            )
            parameters = step_dict.get(StepConfigurationKeys.PARAMETERS_, {})
            for parameter, value in parameters.items():
                if parameter not in step_parameters:
                    raise PipelineConfigurationError(
                        f"Found parameter '{parameter}' for '{step_name}' step "
                        f"in configuration yaml but it doesn't exist in the "
                        f"configuration class `{step.CONFIG_CLASS}`. Available "
                        f"parameters for this step: "
                        f"{list(step_parameters)}."
                    )

                previous_value = step.PARAM_SPEC.get(parameter, None)

                if overwrite:
                    step.PARAM_SPEC[parameter] = value
                else:
                    step.PARAM_SPEC.setdefault(parameter, value)

                if overwrite or not previous_value:
                    logger.debug(
                        "Setting parameter %s=%s for step '%s'.",
                        parameter,
                        value,
                        step_name,
                    )
                if previous_value and not overwrite:
                    raise DuplicatedConfigurationError(
                        "The value for parameter '{}' is set twice for step "
                        "'{}' ({} vs. {}). This can happen when you "
                        "instantiate your step with a step configuration that "
                        "sets the parameter, while also setting the same "
                        "parameter within a config file that is added to the "
                        "pipeline instance using the `.with_config()` method. "
                        "Make sure each parameter is only defined **once**. \n"
                        "While it is not recommended, you can overwrite the "
                        "step configuration using the configuration file: \n"
                        "`.with_config('config.yaml', "
                        "overwrite_step_parameters=True)".format(
                            parameter, step_name, previous_value, value
                        )
                    )
