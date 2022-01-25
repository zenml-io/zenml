#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""
An orchestrator is a special kind of backend that manages the running of each
step of the pipeline. Orchestrators administer the actual pipeline runs. You can
think of it as the 'root' of any pipeline job that you run during your
experimentation.

ZenML supports a local orchestrator out of the box which allows you to run your
pipelines in a local environment. We also support using Apache Airflow as the
orchestrator to handle the steps of your pipeline.
"""
import json
from typing import TYPE_CHECKING

from zenml.enums import ContextTypes

if TYPE_CHECKING:
    from tfx.proto.orchestration.pipeline_pb2 import ContextSpec

    from zenml.stack import Stack


def add_stack_as_context(stack: "Stack", context: "ContextSpec") -> None:
    """Given an instance of a stack object, the function adds it to the context
    of a pipeline node in proper format

    Args:
        stack: an instance of a Zenml Stack object
        context: a context proto message within a pipeline node
    """
    # Adding the type of context
    context.type.name = ContextTypes.STACK.name

    # Converting the stack into a dict to prepare for hashing
    stack_dict = stack.dict()

    # Setting the name of the context
    name = str(hash(json.dumps(stack_dict, sort_keys=True)))
    context.name.field_value.string_value = name

    # Setting the properties of the context
    for k, v in stack_dict.items():
        context.properties[k].field_value.string_value = v
