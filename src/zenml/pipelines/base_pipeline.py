import inspect
from abc import abstractmethod
from typing import Any, Dict

from zenml.annotations.artifact_annotations import Input
from zenml.annotations.step_annotations import Step
from zenml.core.repo import Repository
from zenml.stacks.base_stack import BaseStack
from zenml.utils.exceptions import PipelineInterfaceError


class BasePipelineMeta(type):
    """Pipeline Metaclass responsible for validating the pipeline definition."""

    def __new__(mcs, name, bases, dct):
        """Ensures that all function arguments are either a `Step`
        or an `Input`."""
        cls = super().__new__(mcs, name, bases, dct)
        cls.NAME = name
        cls.STEP_SPEC = dict()
        cls.INPUT_SPEC = dict()

        connect_spec = inspect.getfullargspec(cls.connect)
        connect_args = connect_spec.args

        if connect_args and connect_args[0] == "self":
            connect_args.pop(0)

        for arg in connect_args:
            arg_type = connect_spec.annotations.get(arg, None)
            if isinstance(arg_type, Step):
                cls.STEP_SPEC.update({arg: arg_type.type})
            elif isinstance(arg_type, Input):
                cls.INPUT_SPEC.update({arg: arg_type.type})
            else:
                raise PipelineInterfaceError(
                    "When you are designing a pipeline, the input signature "
                    "can only parameters which are annotated by either the "
                    "step- and the input annotations."
                )
        return cls


class BasePipeline(metaclass=BasePipelineMeta):
    """Base ZenML pipeline."""

    def __init__(self, *args, **kwargs):

        self.__stack = Repository().get_active_stack()

        self.__steps = dict()
        self.__inputs = dict()

        if args:
            raise PipelineInterfaceError(
                "You can only use keyword arguments while you are creating an"
                "instance of a pipeline."
            )

        for k, v in kwargs.items():
            if k in self.STEP_SPEC:
                self.__steps.update({k: v})
            elif k in self.INPUT_SPEC:
                self.__inputs.update({k: v})
            else:
                raise PipelineInterfaceError(
                    f"The argument {k} is an unknown argument. Needs to be "
                    f"one of either {self.INPUT_SPEC.keys()} or "
                    f"{self.STEP_SPEC.keys()}"
                )

    @abstractmethod
    def connect(self, *args, **kwargs):
        """Function that connects inputs and outputs of the pipeline steps."""

    @classmethod
    def get_executable(cls):
        """Returns the `connect` function."""
        return cls.connect

    @property
    def name(self) -> str:
        """Name of pipeline is always equal to self.NAME"""
        return self.NAME

    @property
    def stack(self) -> BaseStack:
        """Returns the stack for this pipeline."""
        return self.__stack

    @stack.setter
    def stack(self, stack: Any):
        """Setting the stack property is not allowed. This method always
        raises a PipelineInterfaceError.
        """
        raise PipelineInterfaceError(
            "The provider will be automatically"
            "inferred from your environment. Please "
            "do no attempt to manually change it."
        )

    @property
    def inputs(self) -> Dict:
        """Returns a dictionary of pipeline inputs."""
        return self.__inputs

    @inputs.setter
    def inputs(self, inputs: Any):
        """Setting the inputs property is not allowed. This method always
        raises a PipelineInterfaceError.
        """
        raise PipelineInterfaceError(
            "The provider will be automatically"
            "inferred from your environment. Please "
            "do no attempt to manually change it."
        )

    @property
    def steps(self) -> Dict:
        """Returns a dictionary of pipeline steps."""
        return self.__steps

    @steps.setter
    def steps(self, steps: Any):
        """Setting the steps property is not allowed. This method always
        raises a PipelineInterfaceError.
        """
        raise PipelineInterfaceError(
            "The provider will be automatically"
            "inferred from your environment. Please "
            "do no attempt to manually change it."
        )

    def run(self):
        """Runs the pipeline using the orchestrator of the pipeline stack."""
        return self.stack.orchestrator.run(self)
