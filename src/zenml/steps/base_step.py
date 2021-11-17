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

import hashlib
import inspect
import json
import random
from abc import abstractmethod
from typing import (
    Any,
    ClassVar,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)

from tfx.types.channel import Channel

from zenml.artifacts.base_artifact import BaseArtifact
from zenml.exceptions import MissingStepParameterError, StepInterfaceError
from zenml.logger import get_logger
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.materializers.default_materializer_registry import (
    default_materializer_registry,
)
from zenml.materializers.spec_materializer_registry import (
    SpecMaterializerRegistry,
)
from zenml.steps.base_step_config import BaseStepConfig
from zenml.steps.step_output import Output
from zenml.steps.utils import (
    INTERNAL_EXECUTION_PARAMETER_PREFIX,
    PARAM_ENABLE_CACHE,
    SINGLE_RETURN_OUT_NAME,
    STEP_INNER_FUNC_NAME,
    _ZenMLSimpleComponent,
    generate_component,
)

logger = get_logger(__name__)


class BaseStepMeta(type):
    """Meta class for `BaseStep`.

    Checks whether everything passed in:
    * Has a matching materializer.
    * Is a subclass of the Config class
    """

    def __new__(
        mcs, name: str, bases: Tuple[Type[Any], ...], dct: Dict[str, Any]
    ) -> "BaseStepMeta":
        """Set up a new class with a qualified spec."""
        logger.debug(f"Registering class {name}, bases: {bases}, dct: {dct}")
        cls = cast(Type["BaseStep"], super().__new__(mcs, name, bases, dct))

        cls.INPUT_SIGNATURE = {}
        cls.OUTPUT_SIGNATURE = {}
        cls.CONFIG_PARAMETER_NAME = None
        cls.CONFIG_CLASS = None

        # Get the signature of the step function
        step_function_signature = inspect.getfullargspec(
            getattr(cls, STEP_INNER_FUNC_NAME)
        )

        if bases:
            # We're not creating the abstract `BaseStep` class
            # but a concrete implementation. Make sure the step function
            # signature does not contain variable **args or **kwargs
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
            else:
                # Can't do any check for existing materializers right now
                # as they might get passed later, so we simply store the
                # argument name and type for later use.
                cls.INPUT_SIGNATURE.update({arg: arg_type})

        # Parse the returns of the step function
        return_type = step_function_signature.annotations.get("return", None)
        if return_type is not None:
            if isinstance(return_type, Output):
                cls.OUTPUT_SIGNATURE = dict(return_type.items())
            else:
                cls.OUTPUT_SIGNATURE[SINGLE_RETURN_OUT_NAME] = return_type

        # Raise an exception if input and output names of a step overlap as
        # that makes it impossible to distinguish their materializers
        # TODO [MEDIUM]: Can we use two factories to avoid this issue?
        shared_input_output_keys = set(cls.INPUT_SIGNATURE).intersection(
            set(cls.OUTPUT_SIGNATURE)
        )
        if shared_input_output_keys:
            raise StepInterfaceError(
                f"There is an overlap in the input and output names of "
                f"step '{name}': {shared_input_output_keys}. Please make "
                f"sure that your input and output names are distinct."
            )

        return cls


T = TypeVar("T", bound="BaseStep")


class BaseStep(metaclass=BaseStepMeta):
    """The base implementation of a ZenML Step which will be inherited by all
    the other step implementations"""

    # TODO [MEDIUM]: Ensure these are ordered
    INPUT_SIGNATURE: ClassVar[Dict[str, Type[Any]]] = None  # type: ignore[assignment] # noqa
    OUTPUT_SIGNATURE: ClassVar[Dict[str, Type[Any]]] = None  # type: ignore[assignment] # noqa
    CONFIG_PARAMETER_NAME: ClassVar[Optional[str]] = None
    CONFIG_CLASS: ClassVar[Optional[Type[BaseStepConfig]]] = None

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.materializers: Dict[str, Type[BaseMaterializer]] = {}
        self.__component = None
        self.step_name = self.__class__.__name__
        self.enable_cache = getattr(self, PARAM_ENABLE_CACHE)
        self.PARAM_SPEC: Dict[str, Any] = {}
        self.INPUT_SPEC: Dict[str, Type[BaseArtifact]] = {}
        self.OUTPUT_SPEC: Dict[str, Type[BaseArtifact]] = {}
        self.spec_materializer_registry = SpecMaterializerRegistry()

        self._verify_arguments(*args, **kwargs)

    @property
    def _internal_execution_properties(self) -> Dict[str, str]:
        """ZenML internal execution properties for this step.

        **IMPORTANT**: When modifying this dictionary, make sure to
        prefix the key with `INTERNAL_EXECUTION_PARAMETER_PREFIX` and serialize
        the value using `json.dumps(...)`.
        """
        properties = {}
        if not self.enable_cache:
            # add a random string to the execution properties to disable caching
            key = INTERNAL_EXECUTION_PARAMETER_PREFIX + "disable_cache"
            random_string = f"{random.getrandbits(128):032x}"
            properties[key] = json.dumps(random_string)
        else:
            # caching is enabled so we compute a hash of the step function code
            # to catch changes in the step implementation
            key = INTERNAL_EXECUTION_PARAMETER_PREFIX + "step_source"
            step_source = inspect.getsource(self.process)
            step_hash = hashlib.sha256(step_source.encode("utf-8")).hexdigest()
            properties[key] = json.dumps(step_hash)

        return properties

    def _verify_arguments(self, *args: Any, **kwargs: Any) -> None:
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
                f"'{self.step_name}' step."
            )

        if self.CONFIG_PARAMETER_NAME and self.CONFIG_CLASS:
            if args:
                config = args[0]
            elif kwargs:
                key, config = kwargs.popitem()

                if key != self.CONFIG_PARAMETER_NAME:
                    raise StepInterfaceError(
                        f"Unknown keyword argument '{key}' when creating a "
                        f"'{self.step_name}' step, only expected a single "
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
                    f"'{self.step_name}' step is not a "
                    f"`{self.CONFIG_CLASS.__name__}` instance."
                )

            self.PARAM_SPEC = config.dict()

    def _prepare_parameter_spec(self) -> None:
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

                if field.default is not None:
                    # use default value from the pydantic config class
                    self.PARAM_SPEC[name] = field.default
                else:
                    missing_keys.append(name)

            if missing_keys:
                raise MissingStepParameterError(
                    self.step_name, missing_keys, self.CONFIG_CLASS
                )

            # convert config parameter values to strings
            try:
                self.PARAM_SPEC = {
                    k: json.dumps(v) for k, v in self.PARAM_SPEC.items()
                }
            except TypeError as e:
                raise StepInterfaceError(
                    f"Failed to serialize config parameters for step "
                    f"'{self.step_name}'. Please make sure to only use "
                    f"json serializable parameter values."
                ) from e

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
        input_artifact_keys = list(self.INPUT_SPEC.keys())
        if len(artifacts) > len(input_artifact_keys):
            raise StepInterfaceError(
                f"Too many input artifacts for step '{self.step_name}'. "
                f"This step expects {len(input_artifact_keys)} artifact(s) "
                f"but got {len(artifacts) + len(kw_artifacts)}."
            )

        combined_artifacts = {}

        for i, artifact in enumerate(artifacts):
            if not isinstance(artifact, Channel):
                raise StepInterfaceError(
                    f"Wrong argument type (`{type(artifact)}`) for positional "
                    f"argument {i} of step '{self.step_name}'. Only outputs "
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
                    f"'{self.step_name}'. An artifact for this key was "
                    f"already passed as a positional argument."
                )

            if not isinstance(artifact, Channel):
                raise StepInterfaceError(
                    f"Wrong argument type (`{type(artifact)}`) for argument "
                    f"'{key}' of step '{self.step_name}'. Only outputs from "
                    f"previous steps can be used as arguments when "
                    f"connecting steps."
                )

            combined_artifacts[key] = artifact

        # check if there are any missing or unexpected artifacts
        expected_artifacts = set(self.INPUT_SPEC.keys())
        actual_artifacts = set(combined_artifacts.keys())
        missing_artifacts = expected_artifacts - actual_artifacts
        unexpected_artifacts = actual_artifacts - expected_artifacts

        if missing_artifacts:
            raise StepInterfaceError(
                f"Missing input artifact(s) for step "
                f"'{self.step_name}': {missing_artifacts}."
            )

        if unexpected_artifacts:
            raise StepInterfaceError(
                f"Unexpected input artifact(s) for step "
                f"'{self.step_name}': {unexpected_artifacts}. This step "
                f"only requires the following artifacts: {expected_artifacts}."
            )

        return combined_artifacts

    def __call__(
        self, *artifacts: Channel, **kw_artifacts: Channel
    ) -> Union[Channel, List[Channel]]:
        """Generates a component when called."""
        # TODO [MEDIUM]: replaces Channels with ZenML class (BaseArtifact?)
        self._prepare_parameter_spec()

        # Construct INPUT_SPEC from INPUT_SIGNATURE
        self.resolve_signature_materializers(self.INPUT_SIGNATURE, True)
        # Construct OUTPUT_SPEC from OUTPUT_SIGNATURE
        self.resolve_signature_materializers(self.OUTPUT_SIGNATURE, False)

        input_artifacts = self._prepare_input_artifacts(
            *artifacts, **kw_artifacts
        )

        self.__component = generate_component(self)(
            **input_artifacts,
            **self.PARAM_SPEC,
            **self._internal_execution_properties,
        )

        # Resolve the returns in the right order.
        returns = [self.component.outputs[key] for key in self.OUTPUT_SPEC]

        # If its one return we just return the one channel not as a list
        if len(returns) == 1:
            returns = returns[0]
        return returns

    @property
    def component(self) -> _ZenMLSimpleComponent:
        """Returns a TFX component."""
        if not self.__component:
            raise StepInterfaceError(
                "Trying to access the step component "
                "before creating it via calling the step."
            )
        return self.__component

    @abstractmethod
    def process(self, *args: Any, **kwargs: Any) -> Any:
        """Abstract method for core step logic."""

    def with_return_materializers(
        self: T,
        materializers: Union[
            Type[BaseMaterializer], Dict[str, Type[BaseMaterializer]]
        ],
    ) -> T:
        """Register materializers for step outputs.

        If a single materializer is passed, it will be used for all step
        outputs. Otherwise the dictionary keys specify the output names
        for which the materializers will be used.

        Args:
            materializers: The materializers for the outputs of this step.

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
                        f"output '{output_name}' in step '{self.step_name}'. "
                        f"Only materializers for the outputs "
                        f"{allowed_output_names} of this step can"
                        f" be registered."
                    )

                if not _is_materializer_class(materializer):
                    raise StepInterfaceError(
                        f"Got unexpected object `{materializer}` as "
                        f"materializer for output '{output_name}' of step "
                        f"'{self.step_name}'. Only `BaseMaterializer` "
                        f"subclasses are allowed."
                    )
                self.materializers[output_name] = materializer

        elif _is_materializer_class(materializers):
            # Set the materializer for all outputs of this step
            self.materializers = {
                key: materializers for key in self.OUTPUT_SIGNATURE
            }
        else:
            raise StepInterfaceError(
                f"Got unexpected object `{materializers}` as output "
                f"materializer for step '{self.step_name}'. Only "
                f"`BaseMaterializer` subclasses or dictionaries mapping "
                f"output names to `BaseMaterializer` subclasses are allowed "
                f"as input when specifying return materializers."
            )

        return self

    def resolve_signature_materializers(
        self, signature: Dict[str, Type[Any]], is_input: bool = True
    ) -> None:
        """Takes either the INPUT_SIGNATURE and OUTPUT_SIGNATURE and resolves
        the materializers for them in the `spec_materializer_registry`.

        Args:
            signature: Either self.INPUT_SIGNATURE or self.OUTPUT_SIGNATURE.
            is_input: If True, then self.INPUT_SPEC used, else self.OUTPUT_SPEC.
        """
        for arg, arg_type in signature.items():
            if arg in self.materializers:
                self.spec_materializer_registry.register_materializer_type(
                    arg, self.materializers[arg]
                )
            elif default_materializer_registry.is_registered(arg_type):
                self.spec_materializer_registry.register_materializer_type(
                    arg,
                    default_materializer_registry.get_single_materializer_type(
                        arg_type
                    ),
                )
            else:
                raise StepInterfaceError(
                    f"Argument `{arg}` of type `{arg_type}` does not have an "
                    f"associated materializer. ZenML steps can only take input "
                    f"and output artifacts with an associated materializer. It "
                    f"looks like we do not have a default materializer for "
                    f"`{arg_type}`, and you have not provided a custom "
                    f"materializer either. Please do so and re-run the "
                    f"pipeline."
                )

        spec = self.INPUT_SPEC if is_input else self.OUTPUT_SPEC
        # For now, all artifacts are BaseArtifacts
        for k in signature.keys():
            spec[k] = BaseArtifact
