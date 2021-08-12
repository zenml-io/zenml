import inspect
from abc import abstractmethod

from playground.artifacts.base_artifact import BaseArtifact
from playground.utils.annotations import GenericType
from playground.utils.exceptions import StepInterfaceError
from playground.utils.step_utils import convert_to_component

Input = type("Input",
             (GenericType,),
             {"VALID_TYPES": [BaseArtifact]})

Output = type("Output",
              (GenericType,),
              {"VALID_TYPES": [BaseArtifact]})

Param = type("Param",
             (GenericType,),
             {"VALID_TYPES": [int, float, str, bytes, dict]})


class BaseStepMeta(type):
    def __new__(mcs, name, bases, dct):
        cls = super().__new__(mcs, name, bases, dct)

        cls.INPUT_SPEC = dict()
        cls.OUTPUT_SPEC = dict()
        cls.PARAM_SPEC = dict()
        cls.PARAM_DEFAULTS = dict()  # TODO: handle defaults

        process_spec = inspect.getfullargspec(cls.process)
        process_args = process_spec.args

        if process_args and process_args[0] == "self":
            process_args.pop(0)

        for arg in process_args:
            arg_type = process_spec.annotations.get(arg, None)
            if isinstance(arg_type, Input):
                cls.INPUT_SPEC.update({arg: arg_type.type})
            elif isinstance(arg_type, Output):
                cls.OUTPUT_SPEC.update({arg: arg_type.type})
            elif isinstance(arg_type, Param):
                cls.PARAM_SPEC.update({arg: arg_type.type})
            else:
                raise StepInterfaceError("")  # TODO: fill message

        return cls


class BaseStep(metaclass=BaseStepMeta):
    def __init__(self, *args, **kwargs):
        self.__component = None
        self.__params = dict()

        if args:
            raise StepInterfaceError("")  # TODO: fill

        for k, v in kwargs.items():
            assert k in self.PARAM_SPEC
            try:
                self.__params[k] = self.PARAM_SPEC[k](v)
            except TypeError or ValueError:
                raise StepInterfaceError("")

    def __call__(self, **artifacts):
        # TODO: Check artifact types
        self.__component = convert_to_component(step=self)(**artifacts,
                                                           **self.__params)

    def __getattr__(self, item):
        if item == "outputs":
            return self.__component.outputs
        else:
            raise AttributeError(f"{item}")

    @abstractmethod
    def process(self, *args, **kwargs):
        pass

    def get_component(self):
        return self.__component
