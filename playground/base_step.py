import inspect
from abc import abstractmethod

from playground.artifacts import Input, Output
from playground.exceptions import StepInterfaceError
from playground.utils import to_component


class BaseStep:
    def __init__(self):
        self.__id = None
        self.__component = None

        self.__input_spec = dict()
        self.__output_spec = dict()
        self.__param_spec = dict()

        instance_spec = inspect.getfullargspec(self.__init__)
        process_spec = inspect.getfullargspec(self.process)

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

        process_args = process_spec.args
        process_args.pop(0)  # Remove the self
        for arg in process_args:
            arg_type = process_spec.annotations.get(arg, None)
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

        instance_args = instance_spec.args
        instance_args.pop(0)  # Remove the self
        for param in instance_args:
            param_type = instance_spec.annotations.get(param, None)
            if param_type in [int, float, str, bytes, bool]:
                self.__param_spec.update({param: param_type})
            else:
                raise StepInterfaceError(
                    "While designing the '__init__' function of your steps, "
                    "please annotate the input parameters that you want to "
                    "use. The supported parameters include, int, float, str")

    def __call__(self, **artifacts):
        params = {p: self.__getattribute__(p) for p in self.__param_spec}
        self.__component = to_component(step=self)(**artifacts, **params)

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

    def get_id(self):
        return self.__id
