#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
from typing import Any, Type, TypeVar

from zenml.pipelines import BasePipeline
from zenml.steps import BaseStep

DP = TypeVar("DP", bound="DynamicPipeline")


class DynamicPipeline(BasePipeline):
    """Abstract class for dynamic ZenML pipelines, enabling creation of pipeline templates without predefining
    the exact number of steps the pipeline can depend on.
    """

    def __init__(self, *steps: BaseStep, **kwargs: Any) -> None:
        """
        Initializes the dynamic pipeline
        Args:
            *steps: the steps to be executed by this pipeline
            **kwargs: the configuration of this pipeline
        """
        if type(self).STEP_SPEC != {}:
            raise RuntimeError(
                f"A dynamic pipeline {self.__class__.__name__} was already initialized. "
                f"Consider generating new pipelines based on this template with "
                f"{self.__class__.__name__}.{self.as_template_of.__name__}()"
            )
        type(self).STEP_SPEC = {s.name: type(s) for s in steps}
        super().__init__(*steps, **kwargs)

    def connect(self, *args: BaseStep, **kwargs: BaseStep) -> None:
        super().connect(*args, **kwargs)

    @classmethod
    def as_template_of(
        cls: Type[DP], pipeline_name: str, **kwargs: Any
    ) -> Type[DP]:
        """
        Generates a new type of pipeline that directly inherits from the current dynamic pipeline.
        This is useful to create multiple dynamic pipelines based on the dynamic pipeline class.
        Args:
            pipeline_name: The name of the new pipeline instance.
            **kwargs: dictionary for the type constructor.

        Returns:
            The new pipeline instance generated.
        """
        return type(  # noqa
            pipeline_name,
            (cls,),
            {"__module__": cls.__module__, "__doc__": cls.__doc__, **kwargs},
        )
