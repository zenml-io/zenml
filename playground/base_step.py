import inspect
from abc import abstractmethod

from playground.artifacts import Input, Output
from playground.exceptions import StepInterfaceError
from playground.utils import to_component


class BaseStep:
    def __init__(self):

        self.__component = None

        self.__input_spec = dict()
        self.__output_spec = dict()
        self.__param_spec = dict()

        process_spec = inspect.getfullargspec(self.process)
        instance_spec = inspect.getfullargspec(self.__init__)

        if instance_spec.varargs is not None:
            raise StepInterfaceError(
                "As ZenML aims to track all the configuration parameters "
                "that you provide to your steps, please refrain from using "
                "a non-descriptive parameter definition such as '*args'.")

        if instance_spec.varkw is not None:
            raise StepInterfaceError(
                "As ZenML aims to track all the configuration parameters "
                "that you provide to your steps, please refrain from using "
                "a non-descriptive parameter definition such as '**kwargs'.")

        for arg, arg_type in process_spec.annotations.items():
            if isinstance(arg_type, Input):
                self.__input_spec.update({arg: arg_type.type})
            elif isinstance(arg_type, Output):
                self.__output_spec.update({arg: arg_type.type})
            else:
                raise StepInterfaceError(
                    "While designing the 'process' function of your steps, "
                    "you can only use Input[Artifact] or Output[Artifact] "
                    "types as input. In order to define parameters, please "
                    "use the __init__ function.")

    def __call__(self, **kwargs):
        self.__component = to_component(step=self)(**kwargs)

    def __getattr__(self, item):
        if item == "outputs":
            return self.__component.outputs
        else:
            raise AttributeError

    @abstractmethod
    def process(self, *args, **kwargs):
        pass

    def get_input_spec(self):
        return self.__input_spec

    def get_output_spec(self):
        return self.__output_spec

    def get_param_spec(self):
        return self.__param_spec

    def get_component(self):
        return self.__component
