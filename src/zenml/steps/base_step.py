import inspect
import json
from abc import abstractmethod

from pydantic import create_model

from zenml.artifacts.base_artifact import BaseArtifact
from zenml.artifacts.data_artifact import DataArtifact
from zenml.exceptions import StepInterfaceError
from zenml.logger import get_logger
from zenml.materializers.default_materializer_registry import (
    default_materializer_factory,
)
from zenml.steps.base_step_config import BaseStepConfig
from zenml.steps.utils import generate_component

logger = get_logger(__name__)

STEP_INNER_FUNC_NAME: str = "process"


class BaseStepMeta(type):
    """Meta class for `BaseStep`.

    Checks whether everything passed in:
    * Has a matching materializer.
    * Is a subclass of the Config class
    """

    def __new__(mcs, name, bases, dct):
        """Set up a new class with a qualified spec."""
        logger.debug(f"Registering class {name}, bases: {bases}, dct: {dct}")
        cls = super().__new__(mcs, name, bases, dct)

        cls.INPUT_SPEC = dict()  # all input params
        cls.OUTPUT_SPEC = dict()  # all output params
        cls.PARAM_SPEC = dict()  # all execution params

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
            if issubclass(arg_type, BaseStepConfig):
                cls.PARAM_SPEC.update({arg: arg_type})
            elif default_materializer_factory.is_registered(arg_type):
                cls.INPUT_SPEC.update({arg: BaseArtifact})
            else:
                raise StepInterfaceError(
                    f"In a ZenML step, you can only pass in a "
                    f"`BaseStepConfig` or an arg type with a default "
                    f"materializer. You passed in {arg_type}, which does not "
                    f"have a default materializer."
                )

        # Infer the returned values
        return_spec = process_spec.annotations.get("return", None)
        if return_spec is not None:
            cls.OUTPUT_SPEC.update({"return_output": DataArtifact})

        # Infer the defaults
        cls.PARAM_DEFAULTS = dict()

        process_defaults = process_spec.defaults
        if process_defaults is not None:
            raise StepInterfaceError(
                "The usage of default values for "
                "parameters is not fully implemented yet."
                "Please do not use default values in "
                "your step definition."
            )
            # for i, default in enumerate(process_defaults):
            #     # TODO: [HIGH] fix the implementation
            #     process_args.reverse()
            #     arg = process_args[i]
            #     arg_type = process_spec.annotations.get(arg, None)
            #     if not isinstance(arg_type, Param):
            #         raise StepInterfaceError(
            #             f"A default value in the signature of a step can
            #             only "
            #             f"be used for a Param[...] not {arg_type}."
            #         )

        return cls


class BaseStep(metaclass=BaseStepMeta):
    """The base implementation of a ZenML Step which will be inherited by all
    the other step implementations"""

    def __init__(self, *args, **kwargs):
        self.__component_class = generate_component(self)

        # TODO [LOW]: Support args
        if args:
            raise StepInterfaceError(
                "When you are creating an instance of a step, please only "
                "use key-word arguments."
            )

        self.__component = None

        self.__inputs = dict()
        self.__params = dict()

        # TODO: [MEDIUM] add defaults to kwargs
        try:
            # create a pydantic model out of a primitive type
            pydantic_c = create_model(
                "params", **{k: (self.PARAM_SPEC[k], ...) for k in kwargs}
            )
            model_dict = pydantic_c(**kwargs).dict()
            self.__params = {k: json.dumps(v) for k, v in model_dict.items()}

        except RuntimeError:
            # TODO [MED]: Change this to say more clearly what
            #  happened: Even pydantic didnt support this type.
            raise StepInterfaceError()

    @property
    def component(self):
        """Returns a TFX component."""
        if self.__component is None and len(self.INPUT_SPEC) == 0:
            self.__component = generate_component(self)(**self.__params)
        return self.__component

    def __call__(self, **artifacts):
        """Generates a component when called."""
        self.__component = generate_component(self)(
            **artifacts, **self.__params
        )

    def __getattr__(self, item):
        """OVerrides the __getattr__ metho."""
        if item == "outputs":
            return self.component.outputs
        else:
            raise AttributeError(f"{item}")

    @abstractmethod
    def process(self, *args, **kwargs):
        """Abstract method for core step logic."""
