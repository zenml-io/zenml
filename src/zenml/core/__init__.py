#  Copyright (c) ZenML GmbH 2020. All Rights Reserved.
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
The ``core`` module is where all the base ZenML functionality is defined,
including a Pydantic base class for components, a git wrapper and a class for ZenML's own
repository methods.

This module is also where the local service functionality (which keeps track of all the ZenML
components) is defined. Every ZenML project has its own ZenML repository, and
the ``repo`` module is where associated methods are defined. The
``repo.init_repo`` method is where all our functionality is kickstarted
when you first initialize everything through the ``zenml init` CLI command.
"""
