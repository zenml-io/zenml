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
While an orchestrator defines how and where your entire pipeline runs, a step 
operator defines how and where an individual step runs. This can be useful in a 
variety of scenarios. An example could be if one step within a pipeline should 
run on a separate environment equipped with a GPU (like a trainer step).
"""
from zenml.step_operators.base_step_operator import BaseStepOperator

__all__ = ["BaseStepOperator"]
