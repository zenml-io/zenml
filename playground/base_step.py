import inspect
from abc import abstractmethod

from playground.artifacts import Input, Output
from playground.exceptions import StepInterfaceError
from playground.util import to_component


class StepDict(dict):
    __getattr__ = dict.__getitem__


class BaseStep:
    def __init__(self):
        self.__inputs = StepDict()
        self.__outputs = StepDict()
        self.__params = StepDict()

        process_spec = inspect.getfullargspec(self.process)
        instance_spec = inspect.getfullargspec(self.__init__)

        if instance_spec.varkw is not None:
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
                self.__inputs.update({arg: arg_type.type})
            elif isinstance(arg_type, Output):
                self.__outputs.update({arg: arg_type.type})
            else:
                raise StepInterfaceError(
                    "While designing the 'process' function of your steps, "
                    "you can only use Input[Artifact] or Output[Artifact] "
                    "types as input. In order to define parameters, please "
                    "use the __init__ function.")

    def __call__(self, **kwargs):
        return to_component(step=self)(**kwargs)

    @abstractmethod
    def process(self, *args, **kwargs):
        pass

    @property
    def inputs(self):
        return self.__inputs

    @property
    def outputs(self):
        return self.__outputs

    @property
    def params(self):
        return self.__params

    @property
    def component(self):
        return self.__component

    @inputs.setter
    def inputs(self, inputs):
        raise PermissionError('The attribute inputs is used internally by '
                              'ZenML. Please avoid making changes to it.')

    @outputs.setter
    def outputs(self, outputs):
        raise PermissionError('The attribute outputs is used internally by '
                              'ZenML. Please avoid making changes to it.')

    @params.setter
    def params(self, params):
        raise PermissionError('The attribute params is used internally by '
                              'ZenML. Please avoid making changes to it.')

    @component.setter
    def component(self, component):
        raise PermissionError('The attribute component is used internally by '
                              'ZenML. Please avoid making changes to it.')

    @inputs.deleter
    def inputs(self):
        self.__inputs = StepDict()

    @outputs.deleter
    def outputs(self):
        self.__outputs = StepDict()

    @params.deleter
    def params(self):
        self.__params = StepDict()

    @component.deleter
    def component(self):
        self.__component = None
