import inspect
from abc import abstractmethod

from playground.annotations import Input, Output, Param
from playground.utils.exceptions import StepInterfaceError
from playground.utils.step_utils import generate_component


class BaseStepMeta(type):
    def __new__(mcs, name, bases, dct):
        cls = super().__new__(mcs, name, bases, dct)

        cls.INPUT_SPEC = dict()
        cls.OUTPUT_SPEC = dict()
        cls.PARAM_SPEC = dict()
        cls.PARAM_DEFAULTS = dict()  # TODO: handle defaults

        process_spec = inspect.getfullargspec(cls.get_executable())
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
        self.__backend = None
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
        self.__component = generate_component(self)(**artifacts, **self.__params)

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

    @classmethod
    def get_executable(cls):
        return cls.process

    def with_backend(self, backend):
        # TODO: temporary implementation
        self.__backend = backend
        return self
