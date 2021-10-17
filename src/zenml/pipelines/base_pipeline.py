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
from typing import Dict

from zenml.core.repo import Repository
from zenml.exceptions import PipelineInterfaceError
from zenml.logger import get_logger
from zenml.stacks.base_stack import BaseStack

logger = get_logger(__name__)
PIPELINE_INNER_FUNC_NAME: str = "connect"
PARAM_ENABLE_CACHE: str = "enable_cache"


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
            cls.STEP_SPEC.update({arg: arg_type})
        return cls


class BasePipeline(metaclass=BasePipelineMeta):
    """Base ZenML pipeline."""

    def __init__(self, *args, **kwargs):
        self.__stack = Repository().get_active_stack()
        self.enable_cache = getattr(self, PARAM_ENABLE_CACHE)
        self.pipeline_name = self.__class__.__name__
        self.__steps = dict()
        logger.info(f"Creating pipeline: {self.pipeline_name}")
        logger.info(
            f'Cache {"enabled" if self.enable_cache else "disabled"} for '
            f"pipeline `{self.pipeline_name}`"
        )

        if args:
            raise PipelineInterfaceError(
                "You can only use keyword arguments while you are creating an "
                "instance of a pipeline."
            )

        for k, v in kwargs.items():
            if k in self.STEP_SPEC:
                self.__steps.update({k: v})
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
        logger.info(
            f"Using orchestrator `{self.stack.orchestrator_name}` for "
            f"pipeline `{self.pipeline_name}`. Running pipeline.."
        )
        return self.stack.orchestrator.run(self)
