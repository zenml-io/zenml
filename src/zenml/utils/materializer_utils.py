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
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.utils import source_utils
from zenml.utils.yaml_utils import read_yaml, write_yaml

logger = get_logger(__name__)

METADATA_DATATYPE = "datatype"
METADATA_MATERIALIZER = "materializer"


def save_model_metadata(model_artifact: Artifact) -> str:
    """Save a zenml model artifact metadata to a YAML file.

    This function is used to extract and save information from a zenml model artifact
    such as the model type and materializer. The extracted information will be
    the key to loading the model into memory in the inference environment.

    datatype: the model type. This is the path to the model class.
    materializer: the materializer class. This is the path to the materializer class.

    Args:
        model_artifact: the artifact to extract the metadata from.

    Returns:
        The path to the temporary file where the model metadata is saved
    """
    metadata = dict()
    metadata[METADATA_DATATYPE] = model_artifact.properties[
        METADATA_DATATYPE
    ].string_value
    metadata[METADATA_MATERIALIZER] = model_artifact.properties[
        METADATA_MATERIALIZER
    ].string_value

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False
    ) as f:
        write_yaml(f.name, metadata)
    return f.name


def load_model_from_metadata(model_uri: str) -> Any:
    """Load a zenml model artifact from a json file.

    This function is used to load information from a Yaml file that was created
    by the save_model_metadata function. The information in the Yaml file is
    used to load the model into memory in the inference environment.

    model_uri: the URI of the model checkpoint/files to load.
    datatype: the model type. This is the path to the model class.
    materializer: the materializer class. This is the path to the materializer class.

    Args:
        model_uri: the artifact to extract the metadata from.

    Returns:
        The ML model object loaded into memory.
    """
    with fileio.open(
        os.path.join(model_uri, MODEL_METADATA_YAML_FILE_NAME), "r"
    ) as f:
        metadata = read_yaml(f.name)
    model_artifact = Artifact()
    model_artifact.uri = model_uri
    model_artifact.properties[METADATA_DATATYPE].string_value = metadata[
        METADATA_DATATYPE
    ]
    model_artifact.properties[METADATA_MATERIALIZER].string_value = metadata[
        METADATA_MATERIALIZER
    ]
    materializer_class = source_utils.load_source_path_class(
        model_artifact.properties[METADATA_MATERIALIZER].string_value
    )
    model_class = source_utils.load_source_path_class(
        model_artifact.properties[METADATA_DATATYPE].string_value
    )
    materializer_object: BaseMaterializer = materializer_class(model_artifact)
    model = materializer_object.handle_input(model_class)
    try:
        import torch.nn as nn

        if issubclass(model_class, nn.Module):  # type: ignore
            model.eval()
    except ImportError:
        pass
    logger.debug(f"Model loaded successfully :\n{model}")
    return model
