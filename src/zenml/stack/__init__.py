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
The stack is essentially all the configuration for the infrastructure of your 
MLOps platform.

A stack is made up of multiple components. Some examples are:

- An Artifact Store
- A Metadata Store
- An Orchestrator
- A Step Operator (Optional)
- A Container Registry (Optional)
"""

from zenml.stack.stack import Stack
from zenml.stack.stack_component import StackComponent
from zenml.stack.stack_validator import StackValidator

__all__ = [
    "Stack",
    "StackComponent",
    "StackValidator",
]
