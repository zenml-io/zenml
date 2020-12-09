#  Copyright (c) maiot GmbH 2020. All Rights Reserved.
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
"""Factory to register step classes to steps"""

from zenml.core.steps.deployer import DeployerStep
from zenml.core.steps.evaluator import EvaluatorStep
from zenml.core.steps.preprocesser import PreprocesserStep
from zenml.core.steps.split import SplitStep
from zenml.core.steps.timeseries import TimeseriesStep
from zenml.core.steps.trainer import TrainerStep


class StepFactory:
    """Definition of StepFactory to track all steps in ZenML.

    All steps (including custom steps) are to be registered here.
    """

    def __init__(self):
        self.steps = {}

    def get_steps(self):
        return self.steps

    def get_single_step(self, key):
        return self.steps[key]

    def register_step(self, key, step_):
        self.steps[key] = step_


# Register the injections into the factory
type_factory = StepFactory()
type_factory.register_step('trainer', TrainerStep)
type_factory.register_step('split', SplitStep)
type_factory.register_step('evaluator', EvaluatorStep)
type_factory.register_step('timeseries', TimeseriesStep)
type_factory.register_step('preprocessor', PreprocesserStep)
type_factory.register_step('deployer', DeployerStep)
