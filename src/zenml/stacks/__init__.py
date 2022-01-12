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
"""
A stack is made up of the following three core components: an Artifact Store, a
Metadata Store, and an Orchestrator (backend).

A ZenML stack also happens to be a Pydantic `BaseSettings` class, which means
that there are multiple ways to use it.
"""
from zenml.stacks.base_stack import BaseStack

__all__ = ["BaseStack"]
