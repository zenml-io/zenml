import inspect
import json
from abc import abstractmethod

from pydantic import create_model

from zenml.annotations import Input, Output
from zenml.artifacts.base_artifact import BaseArtifact
from zenml.artifacts.data_artifact import DataArtifact
from zenml.logger import get_logger
from zenml.steps.utils import generate_component
from zenml.utils.exceptions import StepInterfaceError

logger = get_logger(__name__)


class BaseStepMeta(type):
    """Meta class for `BaseStep`."""

    def __new__(mcs, name, bases, dct):
        """Set up a new class with a qualified spec."""
        logger.debug(f"Registering class {name}, bases: {bases}, dct: {dct}")
        cls = super().__new__(mcs, name, bases, dct)

        cls.INPUT_SPEC = dict()  # all input params
        cls.OUTPUT_SPEC = dict()  # all output params
        cls.PARAM_SPEC = dict()  # all execution params

        # Looking into the signature of the provided process function
        process_spec = inspect.getfullargspec(cls.process)
        process_args = process_spec.args
        logger.debug(f"{name} args: {process_args}")

        # Remove the self from the signature if it exists
        if process_args and process_args[0] == "self":
            process_args.pop(0)

        # Parse the input signature of the function
        for arg in process_args:
            arg_type = process_spec.annotations.get(arg, None)
            if isinstance(arg_type, Input):
                if issubclass(arg_type.type, BaseArtifact):
                    cls.INPUT_SPEC.update({arg: arg_type.type})
                else:
                    cls.INPUT_SPEC.update({arg: DataArtifact})
            elif isinstance(arg_type, Output):
                cls.OUTPUT_SPEC.update({arg: arg_type.type})
            else:
                cls.PARAM_SPEC.update({arg: arg_type})

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
            #             f"A default value in the signature of a step can only "
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
