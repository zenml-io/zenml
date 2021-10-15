#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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

import os
from typing import Text

from zenml import __version__


def handle_bool_env_var(var: Text, default=False):
    """Converts normal env var to boolean"""
    var = os.getenv(var, None)
    for i in ["1", "y", "yes", "True", "true"]:
        if i == var:
            return True
    return default


def handle_int_env_var(var: Text, default: int = 0):
    """Converts normal env var to int"""
    value = os.getenv(var, None)
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


# Global constants
APP_NAME = "zenml"
CONFIG_VERSION = "1"

# Environment variables
ENV_ZENML_DEBUG = "ZENML_DEBUG"
ENV_ZENML_LOGGING_VERBOSITY = "ZENML_LOGGING_VERBOSITY"
ENV_ABSL_LOGGING_VERBOSITY = "ZENML_ABSL_LOGGING_VERBOSITY"

# Logging variables
IS_DEBUG_ENV = handle_bool_env_var(ENV_ZENML_DEBUG, default=False)

if IS_DEBUG_ENV:
    ZENML_LOGGING_VERBOSITY = handle_int_env_var(
        ENV_ZENML_LOGGING_VERBOSITY, default=4
    )
else:
    ZENML_LOGGING_VERBOSITY = handle_int_env_var(
        ENV_ZENML_LOGGING_VERBOSITY, default=3
    )


ABSL_LOGGING_VERBOSITY = os.getenv(ENV_ABSL_LOGGING_VERBOSITY, -100)

# Base images for zenml
ZENML_REGISTRY = "eu.gcr.io/maiot-zenml"
ZENML_BASE_IMAGE_NAME = f"{ZENML_REGISTRY}/zenml:base-{__version__}"
ZENML_TRAINER_IMAGE_NAME = f"{ZENML_REGISTRY}/zenml:cuda-{__version__}"
ZENML_DATAFLOW_IMAGE_NAME = f"{ZENML_REGISTRY}/zenml:dataflow-{__version__}"

# Evaluation utils constants
COMPARISON_NOTEBOOK = "comparison_notebook.ipynb"
EVALUATION_NOTEBOOK = "evaluation_notebook.ipynb"

# Pipeline related constants
PREPROCESSING_FN = (
    "zenml.components.transform.transform_module" ".preprocessing_fn"
)
TRAINER_FN = "zenml.components.trainer.trainer_module.run_fn"

# GCP Orchestration
GCP_ENTRYPOINT = "zenml.backends.orchestrator.entrypoint"
AWS_ENTRYPOINT = "zenml.backends.orchestrator.entrypoint"
K8S_ENTRYPOINT = "zenml.backends.orchestrator.entrypoint"

# Analytics constants
VALID_OPERATING_SYSTEMS = ["Windows", "Darwin", "Linux"]

# Path utilities constants

REMOTE_FS_PREFIX = ["gs://", "hdfs://", "s3://"]
