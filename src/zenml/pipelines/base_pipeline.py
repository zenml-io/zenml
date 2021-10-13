#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
import inspect
from abc import abstractmethod
from typing import Any, Dict, Type

from zenml.core.repo import Repository
from zenml.exceptions import PipelineInterfaceError
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.stacks.base_stack import BaseStack
from zenml.steps.base_step import BaseStep

PIPELINE_INNER_FUNC_NAME: str = "connect"


class BasePipelineMeta(type):
    """Pipeline Metaclass responsible for validating the pipeline definition."""

    def __new__(mcs, name, bases, dct):
        """Ensures that all function arguments are either a `Step`
        or an `Input`."""
        cls = super().__new__(mcs, name, bases, dct)
        cls.NAME = name
        cls.STEP_SPEC = dict()

        connect_spec = inspect.getfullargspec(
            getattr(cls, PIPELINE_INNER_FUNC_NAME)
        )
        connect_args = connect_spec.args

        if connect_args and connect_args[0] == "self":
            connect_args.pop(0)

        for arg in connect_args:
            arg_type = connect_spec.annotations.get(arg, None)
            if issubclass(arg_type, BaseStep):
                cls.STEP_SPEC.update({arg: arg_type})
            else:
                raise PipelineInterfaceError(
                    "When you are designing a pipeline, you can only pass in "
                    "@step like annotated objects."
                )
        return cls


class BasePipeline(metaclass=BasePipelineMeta):
    """Base ZenML pipeline."""

    def __init__(self, *args, **kwargs):
        self.materializers = None
        self.__stack = Repository().get_active_stack()

        self.__steps = dict()

        if args:
            raise PipelineInterfaceError(
                "You can only use keyword arguments while you are creating an "
                "instance of a pipeline."
            )

        for k, v in kwargs.items():
            if k in self.STEP_SPEC:
                if issubclass(type(v), self.STEP_SPEC[k]):  # noqa
                    self.__steps.update({k: v})
                else:
                    raise PipelineInterfaceError(
                        f"Type {type(v)} does not match type specified in "
                        f"pipeline: {self.STEP_SPEC[k]}"
                    )
            else:
                raise PipelineInterfaceError(
                    f"The argument {k} is an unknown argument. Needs to be "
                    f"one of {self.STEP_SPEC.keys()}"
                )

    @abstractmethod
    def connect(self, *args, **kwargs):
        """Function that connects inputs and outputs of the pipeline steps."""

    @property
    def name(self) -> str:
        """Name of pipeline is always equal to self.NAME"""
        return self.NAME

    @property
    def stack(self) -> BaseStack:
        """Returns the stack for this pipeline."""
        return self.__stack

    @stack.setter
    def stack(self, stack: BaseStack):
        """Setting the stack property is not allowed. This method always
        raises a PipelineInterfaceError.
        """
        raise PipelineInterfaceError(
            "The stack will be automatically inferred from your environment. "
            "Please do no attempt to manually change it."
        )

    @property
    def steps(self) -> Dict:
        """Returns a dictionary of pipeline steps."""
        return self.__steps

    @steps.setter
    def steps(self, steps: Dict):
        """Setting the steps property is not allowed. This method always
        raises a PipelineInterfaceError.
        """
        raise PipelineInterfaceError("Cannot set steps manually!")

    def run(self):
        """Runs the pipeline using the orchestrator of the pipeline stack."""
        return self.stack.orchestrator.run(self)

    def with_materializers(
        self, materializers: Dict[Type[Any], Type[BaseMaterializer]]
    ):
        """Inject materializers from the outside."""
        self.materializers = materializers
        return self
