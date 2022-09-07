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
## Exemplary Steps
"""
from zenml.integrations.spark.step_operators.spark_step_operator import (
    SparkStepOperator,
)
from zenml.repository import Repository

step_operator = Repository().active_stack.step_operator
if not step_operator or not isinstance(step_operator, SparkStepOperator):
    raise RuntimeError(
        "Your active stack needs to contain a Spark step operator for this "
        "example to work."
    )

from .importer_step.importer_step import ImporterConfig, importer_step
from .split_step.split_step import SplitConfig, split_step
from .statistics_step.statistics_step import statistics_step
from .trainer_step.trainer_step import trainer_step
from .transformer_step.transformer_step import transformer_step

__all__ = [
    "importer_step",
    "ImporterConfig",
    "split_step",
    "SplitConfig",
    "statistics_step",
    "transformer_step",
    "trainer_step",
]
