#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Initializer for ZenML steps.

A step is a single piece or stage of a ZenML pipeline. Think of each step as
being one of the nodes of a Directed Acyclic Graph (or DAG). Steps are
responsible for one aspect of processing or interacting with the data /
artifacts in the pipeline.

Conceptually, a Step is a discrete and independent part of a pipeline that is
responsible for one particular aspect of data manipulation inside a ZenML
pipeline.

Steps can be subclassed from the `BaseStep` class, or used via our `@step`
decorator.
"""

from zenml.config import ResourceSettings
from zenml.steps.base_parameters import BaseParameters
from zenml.steps.base_step import BaseStep
from zenml.steps.step_context import StepContext
from zenml.steps.step_decorator import step
from zenml.steps.step_environment import STEP_ENVIRONMENT_NAME, StepEnvironment
from zenml.steps.step_output import Output

__all__ = [
    "step",
    "BaseStep",
    "BaseParameters",
    "Output",
    "ResourceSettings",
    "StepContext",
    "StepEnvironment",
    "STEP_ENVIRONMENT_NAME",
]
