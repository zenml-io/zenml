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

import collections
import inspect
import json
import random
from abc import abstractmethod
from typing import (
    Any,
    ClassVar,
    Counter,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)

from tfx.orchestration.portable.base_executor_operator import (
    BaseExecutorOperator,
)
from tfx.orchestration.portable.python_executor_operator import (
    PythonExecutorOperator,
)
from tfx.types.channel import Channel

from zenml.artifacts.base_artifact import BaseArtifact
from zenml.artifacts.type_registry import type_registry
from zenml.exceptions import MissingStepParameterError, StepInterfaceError
from zenml.logger import get_logger
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.materializers.default_materializer_registry import (
    default_materializer_registry,
)
from zenml.step_operators.step_executor_operator import StepExecutorOperator
from zenml.steps.base_step_config import BaseStepConfig
from zenml.steps.step_context import StepContext
from zenml.steps.step_output import Output
from zenml.steps.utils import (
    INSTANCE_CONFIGURATION,
    INTERNAL_EXECUTION_PARAMETER_PREFIX,
    PARAM_CREATED_BY_FUNCTIONAL_API,
    PARAM_CUSTOM_STEP_OPERATOR,
    PARAM_ENABLE_CACHE,
    PARAM_PIPELINE_PARAMETER_NAME,
    SINGLE_RETURN_OUT_NAME,
    _ZenMLSimpleComponent,
    generate_component_class,
    resolve_type_annotation,
)
from zenml.utils.source_utils import get_hashed_source

logger = get_logger(__name__)


class BaseStepMeta(type):
    """Metaclass for `BaseStep`.

    Checks whether everything passed in:
    * Has a matching materializer.
    * Is a subclass of the Config class
    """

    def __new__(
        mcs, name: str, bases: Tuple[Type[Any], ...], dct: Dict[str, Any]
    ) -> "BaseStepMeta":
        """Set up a new class with a qualified spec."""
        dct.setdefault("PARAM_SPEC", {})
        dct.setdefault("INPUT_SPEC", {})
        dct.setdefault("OUTPUT_SPEC", {})
        cls = cast(Type["BaseStep"], super().__new__(mcs, name, bases, dct))

        cls.INPUT_SIGNATURE = {}
        cls.OUTPUT_SIGNATURE = {}
        cls.CONFIG_PARAMETER_NAME = None
        cls.CONFIG_CLASS = None
        cls.CONTEXT_PARAMETER_NAME = None

        # Get the signature of the step function
        step_function_signature = inspect.getfullargspec(
            inspect.unwrap(cls.entrypoint)
        )

        if bases:
            # We're not creating the abstract `BaseStep` class
            # but a concrete implementation. Make sure the step function
            # signature does not contain variable *args or **kwargs
            variable_arguments = None
            if step_function_signature.varargs:
                variable_arguments = f"*{step_function_signature.varargs}"
            elif step_function_signature.varkw:
                variable_arguments = f"**{step_function_signature.varkw}"

            if variable_arguments:
                raise StepInterfaceError(
                    f"Unable to create step '{name}' with variable arguments "
                    f"'{variable_arguments}'. Please make sure your step "
                    f"functions are defined with a fixed amount of arguments."
                )

        step_function_args = (
            step_function_signature.args + step_function_signature.kwonlyargs
        )

        # Remove 'self' from the signature if it exists
        if step_function_args and step_function_args[0] == "self":
            step_function_args.pop(0)

        # Verify the input arguments of the step function
        for arg in step_function_args:
            arg_type = step_function_signature.annotations.get(arg, None)
            arg_type = resolve_type_annotation(arg_type)

            if not arg_type:
                raise StepInterfaceError(
                    f"Missing type annotation for argument '{arg}' when "
                    f"trying to create step '{name}'. Please make sure to "
                    f"include type annotations for all your step inputs "
                    f"and outputs."
                )

            if issubclass(arg_type, BaseStepConfig):
                # Raise an error if we already found a config in the signature
                if cls.CONFIG_CLASS is not None:
                    raise StepInterfaceError(
                        f"Found multiple configuration arguments "
                        f"('{cls.CONFIG_PARAMETER_NAME}' and '{arg}') when "
                        f"trying to create step '{name}'. Please make sure to "
                        f"only have one `BaseStepConfig` subclass as input "
                        f"argument for a step."
                    )
                cls.CONFIG_PARAMETER_NAME = arg
                cls.CONFIG_CLASS = arg_type

            elif issubclass(arg_type, StepContext):
                if cls.CONTEXT_PARAMETER_NAME is not None:
                    raise StepInterfaceError(
                        f"Found multiple context arguments "
                        f"('{cls.CONTEXT_PARAMETER_NAME}' and '{arg}') when "
                        f"trying to create step '{name}'. Please make sure to "
                        f"only have one `StepContext` as input "
                        f"argument for a step."
                    )
                cls.CONTEXT_PARAMETER_NAME = arg
            else:
                # Can't do any check for existing materializers right now
                # as they might get be defined later, so we simply store the
                # argument name and type for later use.
                cls.INPUT_SIGNATURE.update({arg: arg_type})

        # Parse the returns of the step function
        if "return" not in step_function_signature.annotations:
            raise StepInterfaceError(
                f"Missing return type annotation when "
                f"trying to create step '{name}'. Please make sure to "
                f"include type annotations for all your step inputs "
                f"and outputs. If your step returns nothing, please annotate it with `-> None`."
            )
        return_type = step_function_signature.annotations.get("return", None)
        if return_type is not None:
            if isinstance(return_type, Output):
                cls.OUTPUT_SIGNATURE = {
                    name: resolve_type_annotation(type_)
                    for (name, type_) in return_type.items()
                }
            else:
                cls.OUTPUT_SIGNATURE[
                    SINGLE_RETURN_OUT_NAME
                ] = resolve_type_annotation(return_type)

        # Raise an exception if input and output names of a step overlap as
        # tfx requires them to be unique
        # TODO [ENG-155]: Can we prefix inputs and outputs to avoid this
        #  restriction?
        counter: Counter[str] = collections.Counter()
        counter.update(list(cls.INPUT_SIGNATURE))
        counter.update(list(cls.OUTPUT_SIGNATURE))
        if cls.CONFIG_CLASS:
            counter.update(list(cls.CONFIG_CLASS.__fields__.keys()))

        shared_keys = {k for k in counter.elements() if counter[k] > 1}
        if shared_keys:
            raise StepInterfaceError(
                f"The following keys are overlapping in the input, output and "
                f"config parameter names of step '{name}': {shared_keys}. "
                f"Please make sure that your input, output and config "
                f"parameter names are unique."
            )

        return cls


T = TypeVar("T", bound="BaseStep")


class BaseStep(metaclass=BaseStepMeta):
    """Abstract base class for all ZenML steps.

    Attributes:
        name: The name of this step.
        pipeline_parameter_name: The name of the pipeline parameter for which
            this step was passed as an argument.
        enable_cache: A boolean indicating if caching is enabled for this step.
        custom_step_operator: Optional name of a custom step operator to use
            for this step.
        requires_context: A boolean indicating if this step requires a
            `StepContext` object during execution.
    """

    # TODO [ENG-156]: Ensure these are ordered
    INPUT_SIGNATURE: ClassVar[Dict[str, Type[Any]]] = None  # type: ignore[assignment] # noqa
    OUTPUT_SIGNATURE: ClassVar[Dict[str, Type[Any]]] = None  # type: ignore[assignment] # noqa
    CONFIG_PARAMETER_NAME: ClassVar[Optional[str]] = None
    CONFIG_CLASS: ClassVar[Optional[Type[BaseStepConfig]]] = None
    CONTEXT_PARAMETER_NAME: ClassVar[Optional[str]] = None

    PARAM_SPEC: Dict[str, Any] = {}
    INPUT_SPEC: Dict[str, Type[BaseArtifact]] = {}
    OUTPUT_SPEC: Dict[str, Type[BaseArtifact]] = {}

    INSTANCE_CONFIGURATION: Dict[str, Any] = {}

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.name = self.__class__.__name__
        self.pipeline_parameter_name: Optional[str] = None

        kwargs.update(getattr(self, INSTANCE_CONFIGURATION))

        self.requires_context = bool(self.CONTEXT_PARAMETER_NAME)
        self._created_by_functional_api = kwargs.pop(
            PARAM_CREATED_BY_FUNCTIONAL_API, False
        )
        self.custom_step_operator = kwargs.pop(PARAM_CUSTOM_STEP_OPERATOR, None)

        enable_cache = kwargs.pop(PARAM_ENABLE_CACHE, None)
        if enable_cache is None:
            if self.requires_context:
                # Using the StepContext inside a step provides access to
                # external resources which might influence the step execution.
                # We therefore disable caching unless it is explicitly enabled
                enable_cache = False
                logger.debug(
                    "Step '%s': Step context required and caching not "
                    "explicitly enabled.",
                    self.name,
                )
            else:
                # Default to cache enabled if not explicitly set
                enable_cache = True

        logger.debug(
            "Step '%s': Caching %s.",
            self.name,
            "enabled" if enable_cache else "disabled",
        )
        self.enable_cache = enable_cache

        self._explicit_materializers: Dict[str, Type[BaseMaterializer]] = {}
        self._component: Optional[_ZenMLSimpleComponent] = None
        self._has_been_called = False

        self._verify_init_arguments(*args, **kwargs)
        self._verify_output_spec()

    @abstractmethod
    def entrypoint(self, *args: Any, **kwargs: Any) -> Any:
        """Abstract method for core step logic."""

    def get_materializers(
        self, ensure_complete: bool = False
    ) -> Dict[str, Type[BaseMaterializer]]:
        """Returns available materializers for the outputs of this step.

        Args:
            ensure_complete: If set to `True`, this method will raise a
                `StepInterfaceError` if no materializer can be found for an
                output.

        Returns:
            A dictionary mapping output names to `BaseMaterializer` subclasses.
                If no explicit materializer was set using
                `step.with_return_materializers(...)`, this checks the
                default materializer registry to find a materializer for the
                type of the output. If no materializer is registered, the
                output of this method will not contain an entry for this output.

        Raises:
            StepInterfaceError: (Only if `ensure_complete` is set to `True`)
                If an output does not have an explicit materializer assigned
                to it and there is no default materializer registered for
                the output type.
        """
        materializers = self._explicit_materializers.copy()

        for output_name, output_type in self.OUTPUT_SIGNATURE.items():
            if output_name in materializers:
                # Materializer for this output was set explicitly
                pass
            elif default_materializer_registry.is_registered(output_type):
                materializer = default_materializer_registry[output_type]
                materializers[output_name] = materializer
            else:
                if ensure_complete:
                    raise StepInterfaceError(
                        f"Unable to find materializer for output "
                        f"'{output_name}' of type `{output_type}` in step "
                        f"'{self.name}'. Please make sure to either "
                        f"explicitly set a materializer for step outputs "
                        f"using `step.with_return_materializers(...)` or "
                        f"registering a default materializer for specific "
                        f"types by subclassing `BaseMaterializer` and setting "
                        f"its `ASSOCIATED_TYPES` class variable.",
                        url="https://docs.zenml.io/guides/index/custom-materializer",
                    )

        return materializers

    @property
    def _internal_execution_parameters(self) -> Dict[str, Any]:
        """ZenML internal execution parameters for this step."""
        parameters = {
            PARAM_PIPELINE_PARAMETER_NAME: self.pipeline_parameter_name,
            PARAM_CUSTOM_STEP_OPERATOR: self.custom_step_operator,
        }

        if self.enable_cache:
            # Caching is enabled so we compute a hash of the step function code
            # and materializers to catch changes in the step behavior

            # If the step was defined using the functional api, only track
            # changes to the entrypoint function. Otherwise track changes to
            # the entire step class.
            source_object = (
                self.entrypoint
                if self._created_by_functional_api
                else self.__class__
            )
            parameters["step_source"] = get_hashed_source(source_object)

            for name, materializer in self.get_materializers().items():
                key = f"{name}_materializer_source"
                parameters[key] = get_hashed_source(materializer)
        else:
            # Add a random string to the execution properties to disable caching
            random_string = f"{random.getrandbits(128):032x}"
            parameters["disable_cache"] = random_string

        return {
            INTERNAL_EXECUTION_PARAMETER_PREFIX + key: value
            for key, value in parameters.items()
        }

    def _verify_init_arguments(self, *args: Any, **kwargs: Any) -> None:
        """Verifies the initialization args and kwargs of this step.

        This method makes sure that there is only a config object passed at
        initialization and that it was passed using the correct name and
        type specified in the step declaration.
        If the correct config object was found, additionally saves the
        config parameters to `self.PARAM_SPEC`.

        Args:
            *args: The args passed to the init method of this step.
            **kwargs: The kwargs passed to the init method of this step.

        Raises:
            StepInterfaceError: If there are too many arguments or arguments
                with a wrong name/type.
        """
        maximum_arg_count = 1 if self.CONFIG_CLASS else 0
        arg_count = len(args) + len(kwargs)
        if arg_count > maximum_arg_count:
            raise StepInterfaceError(
                f"Too many arguments ({arg_count}, expected: "
                f"{maximum_arg_count}) passed when creating a "
                f"'{self.name}' step."
            )

        if self.CONFIG_PARAMETER_NAME and self.CONFIG_CLASS:
            if args:
                config = args[0]
            elif kwargs:
                key, config = kwargs.popitem()

                if key != self.CONFIG_PARAMETER_NAME:
                    raise StepInterfaceError(
                        f"Unknown keyword argument '{key}' when creating a "
                        f"'{self.name}' step, only expected a single "
                        f"argument with key '{self.CONFIG_PARAMETER_NAME}'."
                    )
            else:
                # This step requires configuration parameters but no config
                # object was passed as an argument. The parameters might be
                # set via default values in the config class or in a
                # configuration file, so we continue for now and verify
                # that all parameters are set before running the step
                return

            if not isinstance(config, self.CONFIG_CLASS):
                raise StepInterfaceError(
                    f"`{config}` object passed when creating a "
                    f"'{self.name}' step is not a "
                    f"`{self.CONFIG_CLASS.__name__}` instance."
                )

            self.PARAM_SPEC = config.dict()

    def _verify_output_spec(self) -> None:
        """Verifies the explicitly set output artifact types of this step.

        Raises:
            StepInterfaceError: If an output artifact type is specified for a
                non-existent step output or the artifact type is not allowed
                for the corresponding output type.
        """
        for output_name, artifact_type in self.OUTPUT_SPEC.items():
            if output_name not in self.OUTPUT_SIGNATURE:
                raise StepInterfaceError(
                    f"Found explicit artifact type for unrecognized output "
                    f"'{output_name}' in step '{self.name}'. Output "
                    f"artifact types can only be specified for the outputs "
                    f"of this step: {set(self.OUTPUT_SIGNATURE)}."
                )

            if not issubclass(artifact_type, BaseArtifact):
                raise StepInterfaceError(
                    f"Invalid artifact type ({artifact_type}) for output "
                    f"'{output_name}' of step '{self.name}'. Only "
                    f"`BaseArtifact` subclasses are allowed as artifact types."
                )

            output_type = self.OUTPUT_SIGNATURE[output_name]
            allowed_artifact_types = set(
                type_registry.get_artifact_type(output_type)
            )

            if artifact_type not in allowed_artifact_types:
                raise StepInterfaceError(
                    f"Artifact type `{artifact_type}` for output "
                    f"'{output_name}' of step '{self.name}' is not an "
                    f"allowed artifact type for the defined output type "
                    f"`{output_type}`. Allowed artifact types: "
                    f"{allowed_artifact_types}. If you want to extend the "
                    f"allowed artifact types, implement a custom "
                    f"`BaseMaterializer` subclass and set its "
                    f"`ASSOCIATED_ARTIFACT_TYPES` and `ASSOCIATED_TYPES` "
                    f"accordingly."
                )

    def _update_and_verify_parameter_spec(self) -> None:
        """Verifies and prepares the config parameters for running this step.

        When the step requires config parameters, this method:
            - checks if config parameters were set via a config object or file
            - tries to set missing config parameters from default values of the
              config class

        Raises:
            MissingStepParameterError: If no value could be found for one or
                more config parameters.
            StepInterfaceError: If a config parameter value couldn't be
                serialized to json.
        """
        if self.CONFIG_CLASS:
            # we need to store a value for all config keys inside the
            # metadata store to make sure caching works as expected
            missing_keys = []
            for name, field in self.CONFIG_CLASS.__fields__.items():
                if name in self.PARAM_SPEC:
                    # a value for this parameter has been set already
                    continue

                if field.required:
                    # this field has no default value set and therefore needs
                    # to be passed via an initialized config object
                    missing_keys.append(name)
                else:
                    # use default value from the pydantic config class
                    self.PARAM_SPEC[name] = field.default

            if missing_keys:
                raise MissingStepParameterError(
                    self.name, missing_keys, self.CONFIG_CLASS
                )

    def _prepare_input_artifacts(
        self, *artifacts: Channel, **kw_artifacts: Channel
    ) -> Dict[str, Channel]:
        """Verifies and prepares the input artifacts for running this step.

        Args:
            *artifacts: Positional input artifacts passed to
                the __call__ method.
            **kw_artifacts: Keyword input artifacts passed to
                the __call__ method.

        Returns:
            Dictionary containing both the positional and keyword input
            artifacts.

        Raises:
            StepInterfaceError: If there are too many or too few artifacts.
        """
        input_artifact_keys = list(self.INPUT_SIGNATURE.keys())
        if len(artifacts) > len(input_artifact_keys):
            raise StepInterfaceError(
                f"Too many input artifacts for step '{self.name}'. "
                f"This step expects {len(input_artifact_keys)} artifact(s) "
                f"but got {len(artifacts) + len(kw_artifacts)}."
            )

        combined_artifacts = {}

        for i, artifact in enumerate(artifacts):
            if not isinstance(artifact, Channel):
                raise StepInterfaceError(
                    f"Wrong argument type (`{type(artifact)}`) for positional "
                    f"argument {i} of step '{self.name}'. Only outputs "
                    f"from previous steps can be used as arguments when "
                    f"connecting steps."
                )

            key = input_artifact_keys[i]
            combined_artifacts[key] = artifact

        for key, artifact in kw_artifacts.items():
            if key in combined_artifacts:
                # an artifact for this key was already set by
                # the positional input artifacts
                raise StepInterfaceError(
                    f"Unexpected keyword argument '{key}' for step "
                    f"'{self.name}'. An artifact for this key was "
                    f"already passed as a positional argument."
                )

            if not isinstance(artifact, Channel):
                raise StepInterfaceError(
                    f"Wrong argument type (`{type(artifact)}`) for argument "
                    f"'{key}' of step '{self.name}'. Only outputs from "
                    f"previous steps can be used as arguments when "
                    f"connecting steps."
                )

            combined_artifacts[key] = artifact

        # check if there are any missing or unexpected artifacts
        expected_artifacts = set(self.INPUT_SIGNATURE.keys())
        actual_artifacts = set(combined_artifacts.keys())
        missing_artifacts = expected_artifacts - actual_artifacts
        unexpected_artifacts = actual_artifacts - expected_artifacts

        if missing_artifacts:
            raise StepInterfaceError(
                f"Missing input artifact(s) for step "
                f"'{self.name}': {missing_artifacts}."
            )

        if unexpected_artifacts:
            raise StepInterfaceError(
                f"Unexpected input artifact(s) for step "
                f"'{self.name}': {unexpected_artifacts}. This step "
                f"only requires the following artifacts: {expected_artifacts}."
            )

        return combined_artifacts

    # TODO [ENG-157]: replaces Channels with ZenML class (BaseArtifact?)
    def __call__(
        self, *artifacts: Channel, **kw_artifacts: Channel
    ) -> Union[Channel, List[Channel]]:
        """Generates a component when called."""
        if self._has_been_called:
            raise StepInterfaceError(
                f"Step {self.name} has already been called. A ZenML step "
                f"instance can only be called once per pipeline run."
            )
        self._has_been_called = True

        self._update_and_verify_parameter_spec()

        # Prepare the input artifacts and spec
        input_artifacts = self._prepare_input_artifacts(
            *artifacts, **kw_artifacts
        )

        self.INPUT_SPEC = {
            arg_name: artifact_type.type
            for arg_name, artifact_type in input_artifacts.items()
        }

        # make sure we have registered materializers for each output
        materializers = self.get_materializers(ensure_complete=True)

        # Prepare the output artifacts and spec
        for key, value in self.OUTPUT_SIGNATURE.items():
            verified_types = type_registry.get_artifact_type(value)
            if key not in self.OUTPUT_SPEC:
                self.OUTPUT_SPEC[key] = verified_types[0]

        execution_parameters = {
            **self.PARAM_SPEC,
            **self._internal_execution_parameters,
        }

        # Convert execution parameter values to strings
        try:
            execution_parameters = {
                k: json.dumps(v) for k, v in execution_parameters.items()
            }
        except TypeError as e:
            raise StepInterfaceError(
                f"Failed to serialize execution parameters for step "
                f"'{self.name}'. Please make sure to only use "
                f"json serializable parameter values."
            ) from e

        component_class = generate_component_class(
            step_name=self.name,
            step_module=self.__module__,
            input_spec=self.INPUT_SPEC,
            output_spec=self.OUTPUT_SPEC,
            execution_parameter_names=set(execution_parameters),
            step_function=self.entrypoint,
            materializers=materializers,
        )
        self._component = component_class(
            **input_artifacts, **execution_parameters
        )

        # Resolve the returns in the right order.
        returns = [self.component.outputs[key] for key in self.OUTPUT_SIGNATURE]

        # If its one return we just return the one channel not as a list
        if len(returns) == 1:
            return returns[0]
        else:
            return returns

    @property
    def component(self) -> _ZenMLSimpleComponent:
        """Returns a TFX component."""
        if not self._component:
            raise StepInterfaceError(
                "Trying to access the step component "
                "before creating it via calling the step."
            )
        return self._component

    @property
    def executor_operator(self) -> Type[BaseExecutorOperator]:
        """Executor operator class that should be used to run this step."""
        if self.custom_step_operator:
            return StepExecutorOperator
        else:
            return PythonExecutorOperator

    def with_return_materializers(
        self: T,
        materializers: Union[
            Type[BaseMaterializer], Dict[str, Type[BaseMaterializer]]
        ],
    ) -> T:
        """Register materializers for step outputs.

        If a single materializer is passed, it will be used for all step
        outputs. Otherwise, the dictionary keys specify the output names
        for which the materializers will be used.

        Args:
            materializers: The materializers for the outputs of this step.

        Returns:
            The object that this method was called on.

        Raises:
            StepInterfaceError: If a materializer is not a `BaseMaterializer`
                subclass or a materializer for a non-existent output is given.
        """

        def _is_materializer_class(value: Any) -> bool:
            """Checks whether the given object is a `BaseMaterializer`
            subclass."""
            is_class = isinstance(value, type)
            return is_class and issubclass(value, BaseMaterializer)

        if isinstance(materializers, dict):
            allowed_output_names = set(self.OUTPUT_SIGNATURE)

            for output_name, materializer in materializers.items():
                if output_name not in allowed_output_names:
                    raise StepInterfaceError(
                        f"Got unexpected materializers for non-existent "
                        f"output '{output_name}' in step '{self.name}'. "
                        f"Only materializers for the outputs "
                        f"{allowed_output_names} of this step can"
                        f" be registered."
                    )

                if not _is_materializer_class(materializer):
                    raise StepInterfaceError(
                        f"Got unexpected object `{materializer}` as "
                        f"materializer for output '{output_name}' of step "
                        f"'{self.name}'. Only `BaseMaterializer` "
                        f"subclasses are allowed."
                    )
                self._explicit_materializers[output_name] = materializer

        elif _is_materializer_class(materializers):
            # Set the materializer for all outputs of this step
            self._explicit_materializers = {
                key: materializers for key in self.OUTPUT_SIGNATURE
            }
        else:
            raise StepInterfaceError(
                f"Got unexpected object `{materializers}` as output "
                f"materializer for step '{self.name}'. Only "
                f"`BaseMaterializer` subclasses or dictionaries mapping "
                f"output names to `BaseMaterializer` subclasses are allowed "
                f"as input when specifying return materializers."
            )

        return self
