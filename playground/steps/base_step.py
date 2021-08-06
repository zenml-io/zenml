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
             {"VALID_TYPES": [int, float, str, bytes]})


class BaseStepMeta(type):
    def __new__(mcs, name, bases, dct):
        cls = super().__new__(mcs, name, bases, dct)

        input_spec, output_spec, param_spec = dict(), dict(), dict()
        param_defaults = dict()  # TODO: handle defaults

        process_spec = inspect.getfullargspec(cls.process)
        process_args = process_spec.args

        if process_args and process_args[0] == "self":
            process_args.pop(0)

        for arg in process_args:
            arg_type = process_spec.annotations.get(arg, None)
            if isinstance(arg_type, Input):
                input_spec.update({arg: arg_type.type})
            elif isinstance(arg_type, Output):
                output_spec.update({arg: arg_type.type})
            elif isinstance(arg_type, Param):
                param_spec.update({arg: arg_type.type})
            else:
                raise StepInterfaceError("")  # TODO: fill message

        cls.INPUT_SPEC = input_spec
        cls.OUTPUT_SPEC = output_spec
        cls.PARAM_SPEC = param_spec
        cls.PARAM_DEFAULTS = param_defaults

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
