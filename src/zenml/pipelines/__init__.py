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
"""A ZenML pipeline consists of tasks that execute in order and yield artifacts.

The artifacts are automatically stored within the artifact store and metadata 
is tracked by ZenML. Each individual task within a pipeline is known as a
step. The standard pipelines within ZenML are designed to have easy interfaces
to add pre-decided steps, with the order also pre-decided. Other sorts of
pipelines can be created as well from scratch, building on the `BasePipeline` class.

Pipelines can be written as simple functions. They are created by using decorators appropriate to the specific use case you have. The moment it is `run`, a pipeline is compiled and passed directly to the orchestrator.
"""


from zenml.config import DockerSettings
from zenml.config.schedule import Schedule
from zenml.pipelines.base_pipeline import BasePipeline
from zenml.pipelines.pipeline_decorator import pipeline

__all__ = ["BasePipeline", "DockerSettings", "pipeline", "Schedule"]
