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


def check_dict_keys_match(x: Dict[Any, Any], y: Dict[Any, Any]) -> bool:
    """Checks whether there is even one key shared between two dicts.

    Returns:
        True if there is a shared key, otherwise False.
    """
    shared_items = {k: x[k] for k in x if k in y and x[k] == y[k]}
    if len(shared_items) == 0:
        return False
    logger.debug(f"Matched keys for dicts {x} and {y}: {shared_items}")
    return True


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

        # Looking into the signature of the provided process function
        process_spec = inspect.getfullargspec(
            getattr(cls, STEP_INNER_FUNC_NAME)
        )
        process_args = process_spec.args
        logger.debug(f"{name} args: {process_args}")

        # Remove the self from the signature if it exists
        if process_args and process_args[0] == "self":
            process_args.pop(0)

        # Parse the input signature of the function
        for arg in process_args:
            arg_type = process_spec.annotations.get(arg, None)
            # Check whether its a `BaseStepConfig` or a registered
            # materializer type.
            if issubclass(arg_type, BaseStepConfig):
                # It needs to be None at this point, otherwise multi configs.
                if cls.CONFIG_CLASS is not None:
                    raise StepInterfaceError(
                        "Please only use one `BaseStepConfig` type object in "
                        "your step."
                    )
                cls.CONFIG_PARAMETER_NAME = arg
                cls.CONFIG_CLASS = arg_type
            else:
                cls.INPUT_SIGNATURE.update({arg: arg_type})

        # Infer the returned values
        return_spec = process_spec.annotations.get("return", None)
        if return_spec is not None:
            if isinstance(return_spec, Output):
                # If its a named, potentially multi, outputs we go through
                #  each and create a spec.
                for return_tuple in return_spec.items():
                    cls.OUTPUT_SIGNATURE.update(
                        {return_tuple[0]: return_tuple[1]}
                    )
            else:
                # If its one output, then give it a single return name.
                cls.OUTPUT_SIGNATURE.update(
                    {SINGLE_RETURN_OUT_NAME: return_spec}
                )

        if check_dict_keys_match(cls.INPUT_SIGNATURE, cls.OUTPUT_SIGNATURE):
            raise StepInterfaceError(
                "The input names and output names cannot be the same!"
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

    def __call__(
        self, **artifacts: BaseArtifact
    ) -> Union[Channel, List[Channel]]:
        """Generates a component when called."""
        # TODO [MEDIUM]: Support *args as well.

        self._prepare_parameter_spec()

        # Construct INPUT_SPEC from INPUT_SIGNATURE
        self.resolve_signature_materializers(self.INPUT_SIGNATURE, True)
        # Construct OUTPUT_SPEC from OUTPUT_SIGNATURE
        self.resolve_signature_materializers(self.OUTPUT_SIGNATURE, False)

        # Basic checks
        for artifact in artifacts.keys():
            if artifact not in self.INPUT_SPEC:
                raise ValueError(
                    f"Artifact `{artifact}` is not defined in the input "
                    f"signature of the step. Defined artifacts: "
                    f"{list(self.INPUT_SPEC.keys())}"
                )

        for artifact in self.INPUT_SPEC.keys():
            if artifact not in artifacts.keys():
                raise ValueError(
                    f"Artifact {artifact} is defined in the input signature "
                    f"of the step but not connected in the pipeline creation!"
                )

        self.__component = generate_component(self)(
            **artifacts,
            **self.PARAM_SPEC,
            **self._internal_execution_properties,
        )

        # Resolve the returns in the right order.
        returns = []
        for k in self.OUTPUT_SPEC.keys():
            returns.append(getattr(self.component.outputs, k))

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
        """Inject materializers from the outside. If one materializer is passed
        in then all outputs are assigned that materializer. If a dict is passed
        in then we make sure the output names match.

        Args:
            materializers: Either a `Type[BaseMaterializer]`, or a
            dict that maps {output_name: Type[BaseMaterializer]}.
        """
        if not isinstance(materializers, dict):
            assert isinstance(materializers, type) and issubclass(
                materializers, BaseMaterializer
            ), "Need to pass in a subclass of `BaseMaterializer`!"
            if len(self.OUTPUT_SIGNATURE) == 1:
                # If only one return, assign to `SINGLE_RETURN_OUT_NAME`.
                self.materializers = {SINGLE_RETURN_OUT_NAME: materializers}
            else:
                # If multi return, then assign to all.
                self.materializers = {
                    k: materializers for k in self.OUTPUT_SIGNATURE
                }
        else:
            # Check whether signature matches.
            assert all([x in self.OUTPUT_SIGNATURE for x in materializers]), (
                f"One of {materializers.keys()} not defined in outputs: "
                f"{self.OUTPUT_SIGNATURE.keys()}"
            )
            self.materializers = materializers
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
