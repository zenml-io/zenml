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

import os

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

# Set the version
with open(os.path.join(ROOT_DIR, "VERSION")) as version_file:
    __version__: str = version_file.read().strip()

# Initialize logging
from zenml.logger import init_logging  # noqa

init_logging()


# Need to import zenml.models before zenml.config to avoid circular imports
from zenml.models import *  # noqa: F401

# Define public Python API
from zenml.utils.dashboard_utils import show_dashboard as show
from zenml.artifacts.utils import (
    log_artifact_metadata,
    save_artifact,
    load_artifact,
    register_artifact,
)
from zenml.model.utils import (
    log_model_metadata,
    link_artifact_to_model,
)
from zenml.artifacts.artifact_config import ArtifactConfig
from zenml.artifacts.external_artifact import ExternalArtifact
from zenml.model.model import Model
from zenml.pipelines import get_pipeline_context, pipeline
from zenml.steps import step, get_step_context
from zenml.steps.utils import log_step_metadata
from zenml.utils.metadata_utils import log_metadata
from zenml.utils.tag_utils import Tag, add_tags, remove_tags
from zenml.entrypoints import entrypoint

__all__ = [
    "add_tags",
    "remove_tags",
    "Tag",
    "ArtifactConfig",
    "ExternalArtifact",
    "get_pipeline_context",
    "get_step_context",
    "load_artifact",
    "log_metadata",
    "log_artifact_metadata",
    "log_model_metadata",
    "log_step_metadata",
    "Model",
    "link_artifact_to_model",
    "pipeline",
    "save_artifact",
    "register_artifact",
    "show",
    "step",
    "entrypoint",
]
