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
from dynamic_pipelines.gather_step import OutputParameters

from zenml.steps.base_parameters import BaseParameters


class EvaluationOutputParams(OutputParameters):
    """Output parameters of evaluation steps"""

    score: float
    metric_name: str
    model_parameters: dict


class EvaluationParams(BaseParameters):
    """Parameters for evaluation steps"""

    evaluation_type: str
    model_parameters: dict = {}
