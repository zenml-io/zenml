import inspect
import types
from abc import abstractmethod
from typing import Type

from playground.utils.exceptions import StepInterfaceError
from playground.utils.step_utils import convert_to_component


class BaseStep:

    def __init__(self, *args, **kwargs):
        if args:
            raise StepInterfaceError("")  # TODO: fill

        self.__component = None
        self.__params = dict()

        self.__input_spec = dict()
        self.__output_spec = dict()
        self.__param_spec = dict()

        process_spec = inspect.getfullargspec(self.process)
        process_args = process_spec.args
        process_args.pop(0)  # Remove the self
        from playground.utils.annotations import Input, Output, Param

        for arg in process_args:
            arg_type = process_spec.annotations.get(arg, None)
            if isinstance(arg_type, Input):
                self.__input_spec.update({arg: arg_type.type})
            elif isinstance(arg_type, Output):
                self.__output_spec.update({arg: arg_type.type})
            elif isinstance(arg_type, Param):
                self.__param_spec.update({arg: arg_type.type})
            else:
                raise StepInterfaceError("")  # TODO: fill

        for k, v in kwargs.items():
            # TODO: implement handling defaults
            assert k in self.__param_spec
            try:
                self.__params[k] = self.__param_spec[k](v)
            except TypeError or ValueError:
                raise StepInterfaceError("")

    def __call__(self, **artifacts):
        # TODO: Check artifact types
        self.__component = convert_to_component(step=self)(**artifacts,
                                                           **self.__params)

    @abstractmethod
    def process(self, *args, **kwargs):
        pass

    def __getattr__(self, item):
        if item == "outputs":
            return self.__component.outputs
        else:
            raise AttributeError

    def get_input_spec(self):
        return self.__input_spec

    def get_output_spec(self):
        return self.__output_spec

    def get_param_spec(self):
        return self.__param_spec

    def get_component(self):
        return self.__component


def step(func: types.FunctionType) -> Type:
    step_class = type(func.__name__,
                      (BaseStep,),
                      {})
    step_class.process = func
    return step_class
