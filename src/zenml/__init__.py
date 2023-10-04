#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Initialization for ZenML."""

# Define ROOT_DIR
import os

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

# Set the version
with open(os.path.join(ROOT_DIR, "VERSION")) as version_file:
    __version__: str = version_file.read().strip()

# Initialize logging
from zenml.logger import init_logging  # noqa

init_logging()

# The following code is needed for `zenml.hub` subpackages to be found
from pkgutil import extend_path

__path__ = extend_path(__path__, __name__)

# Define public Python API
from zenml.api import show
from zenml.new.pipelines.pipeline_decorator import pipeline
from zenml.new.steps.step_decorator import step
from zenml.new.steps.step_context import get_step_context

__all__ = ["show", "pipeline", "step", "get_step_context"]
