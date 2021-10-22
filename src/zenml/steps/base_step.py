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
import json
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
from zenml.exceptions import StepInterfaceError
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
        cls.CONFIG = None

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
                if cls.CONFIG is not None:
                    raise StepInterfaceError(
                        "Please only use one `BaseStepConfig` type object in "
                        "your step."
                    )
                cls.CONFIG = arg_type
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

        return cls


T = TypeVar("T", bound="BaseStep")


class BaseStep(metaclass=BaseStepMeta):
    """The base implementation of a ZenML Step which will be inherited by all
    the other step implementations"""

    # TODO [MEDIUM]: Ensure these are ordered
    INPUT_SIGNATURE: ClassVar[Dict[str, Type[Any]]] = None  # type: ignore[assignment] # noqa
    OUTPUT_SIGNATURE: ClassVar[Dict[str, Type[Any]]] = None  # type: ignore[assignment] # noqa
    CONFIG: ClassVar[Optional[Type[BaseStepConfig]]] = None

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.materializers: Dict[str, Type[BaseMaterializer]] = {}
        self.__component = None
        self.step_name = self.__class__.__name__
        self.PARAM_SPEC: Dict[str, Any] = {}
        self.INPUT_SPEC: Dict[str, Type[BaseArtifact]] = {}
        self.OUTPUT_SPEC: Dict[str, Type[BaseArtifact]] = {}
        self.spec_materializer_registry = SpecMaterializerRegistry()

        # TODO [LOW]: Support args
        # TODO [LOW]: Currently the kwarg name doesn't matter
        #  and will be used as the config
        if args:
            raise StepInterfaceError(
                "When you are creating an instance of a step, please only "
                "use key-word arguments."
            )

        maximum_kwarg_count = 1 if self.CONFIG else 0
        if len(kwargs) > maximum_kwarg_count:
            raise StepInterfaceError(
                f"Too many keyword arguments ({len(kwargs)}, "
                f"expected: {maximum_kwarg_count}) passed when "
                f"creating a '{self.step_name}' step."
            )

        if self.CONFIG and len(kwargs) == 1:
            config = kwargs.popitem()[1]

            if not isinstance(config, self.CONFIG):
                raise StepInterfaceError(
                    f"`{config}` object passed when creating a "
                    f"'{self.step_name}' step is not a "
                    f"`{self.CONFIG.__name__}` instance."
                )

            try:
                self.PARAM_SPEC = {
                    k: json.dumps(v) for k, v in config.dict().items()
                }
            except RuntimeError as e:
                # TODO [LOW]: Attach a URL with all supported types.
                logger.debug(f"Pydantic Error: {str(e)}")
                raise StepInterfaceError(
                    "You passed in a parameter that we cannot serialize!"
                )

    def __call__(
        self, **artifacts: BaseArtifact
    ) -> Union[Channel, List[Channel]]:
        """Generates a component when called."""
        # TODO [MEDIUM]: Support *args as well.
        # register defaults
        if check_dict_keys_match(self.INPUT_SIGNATURE, self.OUTPUT_SIGNATURE):
            raise StepInterfaceError(
                "The input names and output names cannot be the same!"
            )

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
            **artifacts, **self.PARAM_SPEC
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
