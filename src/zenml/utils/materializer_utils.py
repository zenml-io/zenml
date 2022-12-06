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
from typing import TYPE_CHECKING, Any

from zenml.artifacts.model_artifact import ModelArtifact
from zenml.constants import MODEL_METADATA_YAML_FILE_NAME
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.utils import source_utils
from zenml.utils.yaml_utils import read_yaml, write_yaml

if TYPE_CHECKING:
    from zenml.models import ArtifactResponseModel

logger = get_logger(__name__)

METADATA_DATATYPE = "datatype"
METADATA_MATERIALIZER = "materializer"


def save_model_metadata(model_artifact: "ArtifactResponseModel") -> str:
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
    metadata[METADATA_DATATYPE] = model_artifact.data_type
    metadata[METADATA_MATERIALIZER] = model_artifact.materializer

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

    Args:
        model_uri: the artifact to extract the metadata from.

    Returns:
        The ML model object loaded into memory.
    """
    with fileio.open(
        os.path.join(model_uri, MODEL_METADATA_YAML_FILE_NAME), "r"
    ) as f:
        metadata = read_yaml(f.name)

    data_type = metadata[METADATA_DATATYPE]
    materializer = metadata[METADATA_MATERIALIZER]

    model_artifact = ModelArtifact(
        uri=model_uri,
        data_type=data_type,
        materializer=materializer,
    )
    materializer_class = source_utils.load_source_path_class(materializer)
    model_class = source_utils.load_source_path_class(data_type)
    materializer_object: BaseMaterializer = materializer_class(model_artifact)
    model = materializer_object.handle_input(model_class)
    try:
        import torch.nn as nn

        if issubclass(model_class, nn.Module):
            model.eval()
    except ImportError:
        pass
    logger.debug(f"Model loaded successfully :\n{model}")
    return model


def model_from_model_artifact(model_artifact: ModelArtifact) -> Any:
    """Load model to memory from a model artifact.

    Args:
        model_artifact: The model artifact to load.

    Returns:
        The ML model object loaded into memory.

    Raises:
        RuntimeError: If the model artifact has no materializer or data type.
    """
    if not model_artifact.materializer:
        raise RuntimeError(
            "Cannot load model from model artifact without materializer."
        )
    if not model_artifact.data_type:
        raise RuntimeError(
            "Cannot load model from model artifact without data type."
        )
    materializer_class = source_utils.load_source_path_class(
        model_artifact.materializer
    )
    model_class = source_utils.load_source_path_class(model_artifact.data_type)
    materializer_object: BaseMaterializer = materializer_class(model_artifact)
    model = materializer_object.handle_input(model_class)
    logger.debug(f"Model loaded successfully :\n{model}")
    return model
