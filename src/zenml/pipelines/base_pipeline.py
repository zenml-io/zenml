#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
import inspect
from abc import abstractmethod
from datetime import datetime
from typing import (
    Any,
    ClassVar,
    Dict,
    NoReturn,
    Optional,
    Tuple,
    Type,
    TypeVar,
    cast,
)

from zenml.config.config_keys import (
    PipelineConfigurationKeys,
    StepConfigurationKeys,
)
from zenml.core.repo import Repository
from zenml.exceptions import (
    DoesNotExistException,
    PipelineConfigurationError,
    PipelineInterfaceError,
)
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.stacks.base_stack import BaseStack
from zenml.steps.base_step import BaseStep
from zenml.utils import analytics_utils, yaml_utils

logger = get_logger(__name__)
PIPELINE_INNER_FUNC_NAME: str = "connect"
PARAM_ENABLE_CACHE: str = "enable_cache"


class BasePipelineMeta(type):
    """Pipeline Metaclass responsible for validating the pipeline definition."""

    def __new__(
        mcs, name: str, bases: Tuple[Type[Any], ...], dct: Dict[str, Any]
    ) -> "BasePipelineMeta":
        """Saves argument names for later verification purposes"""
        cls = cast(Type["BasePipeline"], super().__new__(mcs, name, bases, dct))

        cls.NAME = name
        cls.STEP_SPEC = {}

        connect_spec = inspect.getfullargspec(
            getattr(cls, PIPELINE_INNER_FUNC_NAME)
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
    """Base ZenML pipeline."""

    NAME: ClassVar[str] = ""
    STEP_SPEC: ClassVar[Dict[str, Any]] = None  # type: ignore[assignment]

    def __init__(self, *args: BaseStep, **kwargs: BaseStep) -> None:

        try:
            self.__stack = Repository().get_active_stack()
        except DoesNotExistException as exc:
            raise DoesNotExistException(
                "Could not retrieve any active stack. Make sure to set a "
                "stack active via `zenml stack set STACK_NAME`"
            ) from exc

        self.enable_cache = getattr(self, PARAM_ENABLE_CACHE)
        self.pipeline_name = self.__class__.__name__
        logger.info(f"Creating pipeline: {self.pipeline_name}")
        logger.info(
            f'Cache {"enabled" if self.enable_cache else "disabled"} for '
            f"pipeline `{self.pipeline_name}`"
        )

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
                f"Too many input steps for pipeline '{self.pipeline_name}'. "
                f"This pipeline expects {len(input_step_keys)} step(s) "
                f"but got {len(steps) + len(kw_steps)}."
            )

        combined_steps = {}

        for i, step in enumerate(steps):
            if not isinstance(step, BaseStep):
                raise PipelineInterfaceError(
                    f"Wrong argument type (`{type(step)}`) for positional "
                    f"argument {i} of pipeline '{self.pipeline_name}'. Only "
                    f"`@step` decorated functions or instances of `BaseStep` "
                    f"subclasses can be used as arguments when creating "
                    f"a pipeline."
                )

            key = input_step_keys[i]
            combined_steps[key] = step

        for key, step in kw_steps.items():
            if key in combined_steps:
                # a step for this key was already set by
                # the positional input steps
                raise PipelineInterfaceError(
                    f"Unexpected keyword argument '{key}' for pipeline "
                    f"'{self.pipeline_name}'. A step for this key was "
                    f"already passed as a positional argument."
                )

            if not isinstance(step, BaseStep):
                raise PipelineInterfaceError(
                    f"Wrong argument type (`{type(step)}`) for argument "
                    f"'{key}' of pipeline '{self.pipeline_name}'. Only "
                    f"`@step` decorated functions or instances of `BaseStep` "
                    f"subclasses can be used as arguments when creating "
                    f"a pipeline."
                )

            combined_steps[key] = step

        # check if there are any missing or unexpected steps
        expected_steps = set(self.STEP_SPEC.keys())
        actual_steps = set(combined_steps.keys())
        missing_steps = expected_steps - actual_steps
        unexpected_steps = actual_steps - expected_steps

        if missing_steps:
            raise PipelineInterfaceError(
                f"Missing input step(s) for pipeline "
                f"'{self.pipeline_name}': {missing_steps}."
            )

        if unexpected_steps:
            raise PipelineInterfaceError(
                f"Unexpected input step(s) for pipeline "
                f"'{self.pipeline_name}': {unexpected_steps}. This pipeline "
                f"only requires the following steps: {expected_steps}."
            )

        self.__steps = combined_steps

    @abstractmethod
    def connect(self, *args: BaseStep, **kwargs: BaseStep) -> None:
        """Function that connects inputs and outputs of the pipeline steps."""
        raise NotImplementedError

    @property
    def name(self) -> str:
        """Name of pipeline is always equal to self.NAME"""
        return self.NAME

    @property
    def stack(self) -> BaseStack:
        """Returns the stack for this pipeline."""
        return self.__stack

    @stack.setter
    def stack(self, stack: BaseStack) -> NoReturn:
        """Setting the stack property is not allowed. This method always
        raises a PipelineInterfaceError.
        """
        raise PipelineInterfaceError(
            "The stack will be automatically inferred from your environment. "
            "Please do no attempt to manually change it."
        )

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

    def run(self, run_name: Optional[str] = None) -> Any:
        """Runs the pipeline using the orchestrator of the pipeline stack.

        Args:
            run_name: Optional name for the run.
        """
        # Activating the built-in integrations through lazy loading
        from zenml.integrations.registry import integration_registry

        integration_registry.activate()

        if run_name is None:
            run_name = (
                f"{self.pipeline_name}-"
                f'{datetime.now().strftime("%d_%h_%y-%H_%M_%S_%f")}'
            )

        analytics_utils.track_event(
            event=analytics_utils.RUN_PIPELINE,
            metadata={
                "stack_type": self.stack.stack_type,
                "total_steps": len(self.steps),
            },
        )

        logger.info(
            f"Using orchestrator `{self.stack.orchestrator_name}` for "
            f"pipeline `{self.pipeline_name}`. Running pipeline.."
        )

        # filepath of the file where pipeline.run() was called
        caller_filepath = fileio.resolve_relative_path(
            inspect.currentframe().f_back.f_code.co_filename  # type: ignore[union-attr] # noqa
        )

        self.stack.orchestrator.pre_run(caller_filepath=caller_filepath)
        ret = self.stack.orchestrator.run(self, run_name)
        self.stack.orchestrator.post_run()
        return ret

    def with_config(
        self: T, config_file: str, overwrite_step_parameters: bool = False
    ) -> T:
        """Configures this pipeline using a yaml file.

        Args:
            config_file: Path to a yaml file which contains configuration
                options for running this pipeline. See
                https://docs.zenml.io/guides/pipeline-configuration for details
                regarding the specification of this file.
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
                    logger.warning(
                        "Parameter '%s' from configuration yaml will NOT be "
                        "set as a configuration object was given when "
                        "creating the step. Set `overwrite_step_parameters="
                        "True` when setting the configuration yaml to always "
                        "use the options specified in the yaml file.",
                        parameter,
                    )
