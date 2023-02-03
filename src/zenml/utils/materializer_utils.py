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
    # Load the model from its metadata
    with fileio.open(
        os.path.join(model_uri, MODEL_METADATA_YAML_FILE_NAME), "r"
    ) as f:
        metadata = read_yaml(f.name)
    data_type = metadata[METADATA_DATATYPE]
    materializer = metadata[METADATA_MATERIALIZER]
    model = _load_artifact(
        materializer=materializer, data_type=data_type, uri=model_uri
    )

    # Switch to eval mode if the model is a torch model
    try:
        import torch.nn as nn

        if isinstance(model, nn.Module):
            model.eval()
    except ImportError:
        pass

    return model


def load_artifact(artifact: "ArtifactResponseModel") -> Any:
    """Load the given artifact into memory.

    Args:
        artifact: The artifact to load.

    Returns:
        The artifact loaded into memory.
    """
    return _load_artifact(
        materializer=artifact.materializer,
        data_type=artifact.data_type,
        uri=artifact.uri,
    )


def _load_artifact(
    materializer: str,
    data_type: str,
    uri: str,
) -> Any:
    """Load an artifact using the given materializer.

    Args:
        materializer: The path of the materializer class to use.
        data_type: The data type of the artifact.
        uri: The uri of the artifact.

    Returns:
        The artifact loaded into memory.

    Raises:
        ModuleNotFoundError: If the materializer or data type cannot be found.
    """
    # Resolve the materializer class
    try:
        materializer_class = source_utils.load_source_path_class(materializer)
    except (ModuleNotFoundError, AttributeError) as e:
        logger.error(
            f"ZenML cannot locate and import the materializer module "
            f"'{materializer}' which was used to write this artifact."
        )
        raise ModuleNotFoundError(e) from e

    # Resolve the artifact class
    try:
        artifact_class = source_utils.load_source_path_class(data_type)
    except (ModuleNotFoundError, AttributeError) as e:
        logger.error(
            f"ZenML cannot locate and import the data type of this "
            f"artifact '{data_type}'."
        )
        raise ModuleNotFoundError(e) from e

    # Load the artifact
    logger.debug(
        "Using '%s' to load artifact of type '%s' from '%s'.",
        materializer_class.__qualname__,
        artifact_class.__qualname__,
        uri,
    )
    materializer_object: BaseMaterializer = materializer_class(uri)
    artifact = materializer_object.load(artifact_class)
    logger.debug("Artifact loaded successfully.")

    return artifact
