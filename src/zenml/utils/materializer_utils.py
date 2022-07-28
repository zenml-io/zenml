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
"""Util functions for models and materializers."""

import os
import tempfile
from typing import Any

from ml_metadata.proto.metadata_store_pb2 import Artifact

from zenml.constants import MODEL_METADATA_YAML_FILE_NAME
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.utils import source_utils
from zenml.utils.yaml_utils import read_yaml, write_yaml

logger = get_logger(__name__)


def save_model_metadata(model_artifact: Artifact) -> str:
    """Save a zenml artifact to a json file.

    Args:
        model_artifact: the directory where the model files are stored

    Returns:
        The path to the temporary file where the model metadata is saved
    """
    metadata = dict()
    metadata["datatype"] = model_artifact.properties["datatype"].string_value
    metadata["materializer"] = model_artifact.properties[
        "materializer"
    ].string_value

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False
    ) as f:
        write_yaml(f.name, metadata)
    return f.name


def load_model_from_metadata(model_uri: str) -> Any:
    """Load a zenml artifact from a json file.

    Args:
        model_uri: the directory where the model files are stored

    Returns:
        The ML model loaded into a Python object
    """
    with fileio.open(
        os.path.join(model_uri, MODEL_METADATA_YAML_FILE_NAME), "r"
    ) as f:
        metadata = read_yaml(f.name)
    model_artifact = Artifact()
    model_artifact.uri = model_uri
    model_artifact.properties["datatype"].string_value = metadata["datatype"]
    model_artifact.properties["materializer"].string_value = metadata[
        "materializer"
    ]
    materializer_class = source_utils.load_source_path_class(
        model_artifact.properties["materializer"].string_value
    )
    model_class = source_utils.load_source_path_class(
        model_artifact.properties["datatype"].string_value
    )
    materialzer_object = materializer_class(model_artifact)
    model = materialzer_object.handle_input(model_class)
    try:
        import torch.nn as nn

        if issubclass(model_class, nn.Module):  # type: ignore
            model.eval()
    except ImportError:
        pass
    logger.debug(f"model loaded successfully :\n{model}")
    return model
