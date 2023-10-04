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
"""Util functions for artifact handling."""

import base64
import os
import tempfile
from typing import TYPE_CHECKING, Any, List, Optional, Union, cast
from uuid import UUID

from zenml.client import Client
from zenml.constants import MODEL_METADATA_YAML_FILE_NAME
from zenml.enums import ExecutionStatus, StackComponentType, VisualizationType
from zenml.exceptions import DoesNotExistException
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.models import ArtifactRequestModel, ArtifactResponseModel
from zenml.models.visualization_models import (
    LoadedVisualizationModel,
    VisualizationModel,
)
from zenml.stack import StackComponent
from zenml.utils import source_utils
from zenml.utils.yaml_utils import read_yaml, write_yaml

if TYPE_CHECKING:
    from zenml.artifact_stores.base_artifact_store import BaseArtifactStore
    from zenml.config.source import Source
    from zenml.materializers.base_materializer import BaseMaterializer
    from zenml.models.pipeline_run_models import PipelineRunResponseModel
    from zenml.models.step_run_models import StepRunResponseModel
    from zenml.zen_stores.base_zen_store import BaseZenStore


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
    artifact_store_loaded = False
    if artifact.artifact_store_id:
        try:
            artifact_store_model = Client().get_stack_component(
                component_type=StackComponentType.ARTIFACT_STORE,
                name_id_or_prefix=artifact.artifact_store_id,
            )
            _ = StackComponent.from_model(artifact_store_model)
            artifact_store_loaded = True
        except KeyError:
            pass

    if not artifact_store_loaded:
        logger.warning(
            "Unable to restore artifact store while trying to load artifact "
            "`%s`. If this artifact is stored in a remote artifact store, "
            "this might lead to issues when trying to load the artifact.",
            artifact.id,
        )

    return _load_artifact(
        materializer=artifact.materializer,
        data_type=artifact.data_type,
        uri=artifact.uri,
    )


def _load_artifact(
    materializer: Union["Source", str],
    data_type: Union["Source", str],
    uri: str,
) -> Any:
    """Load an artifact using the given materializer.

    Args:
        materializer: The source of the materializer class to use.
        data_type: The source of the artifact data type.
        uri: The uri of the artifact.

    Returns:
        The artifact loaded into memory.

    Raises:
        ModuleNotFoundError: If the materializer or data type cannot be found.
    """
    from zenml.materializers.base_materializer import BaseMaterializer

    # Resolve the materializer class
    try:
        materializer_class = source_utils.load(materializer)
    except (ModuleNotFoundError, AttributeError) as e:
        logger.error(
            f"ZenML cannot locate and import the materializer module "
            f"'{materializer}' which was used to write this artifact."
        )
        raise ModuleNotFoundError(e) from e

    # Resolve the artifact class
    try:
        artifact_class = source_utils.load(data_type)
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


def load_artifact_visualization(
    artifact: "ArtifactResponseModel",
    index: int = 0,
    zen_store: Optional["BaseZenStore"] = None,
    encode_image: bool = False,
) -> LoadedVisualizationModel:
    """Load a visualization of the given artifact.

    Args:
        artifact: The artifact to visualize.
        index: The index of the visualization to load.
        zen_store: The ZenStore to use for finding the artifact store. If not
            provided, the client's ZenStore will be used.
        encode_image: Whether to base64 encode image visualizations.

    Returns:
        The loaded visualization.

    Raises:
        DoesNotExistException: If the artifact does not have the requested
            visualization or if the visualization was not found in the artifact
            store.
    """
    # Get the visualization to load
    if not artifact.visualizations:
        raise DoesNotExistException(
            f"Artifact '{artifact.id}' has no visualizations."
        )
    if index < 0 or index >= len(artifact.visualizations):
        raise DoesNotExistException(
            f"Artifact '{artifact.id}' only has {len(artifact.visualizations)} "
            f"visualizations, but index {index} was requested."
        )
    visualization = artifact.visualizations[index]

    # Load the visualization from the artifact's artifact store
    if not artifact.artifact_store_id:
        raise DoesNotExistException(
            f"Artifact '{artifact.id}' cannot be visualized because the "
            "underlying artifact store was deleted."
        )
    artifact_store = _load_artifact_store(
        artifact_store_id=artifact.artifact_store_id, zen_store=zen_store
    )
    mode = "rb" if visualization.type == VisualizationType.IMAGE else "r"
    value = _load_file_from_artifact_store(
        uri=visualization.uri,
        artifact_store=artifact_store,
        mode=mode,
    )

    # Encode image visualizations if requested
    if visualization.type == VisualizationType.IMAGE and encode_image:
        value = base64.b64encode(bytes(value))

    return LoadedVisualizationModel(type=visualization.type, value=value)


def _load_artifact_store(
    artifact_store_id: Union[str, "UUID"],
    zen_store: Optional["BaseZenStore"] = None,
) -> "BaseArtifactStore":
    """Load an artifact store (potentially inside the server).

    Args:
        artifact_store_id: The id of the artifact store to load.
        zen_store: The ZenStore to use for finding the artifact store. If not
            provided, the client's ZenStore will be used.

    Returns:
        The loaded artifact store.

    Raises:
        DoesNotExistException: If the artifact store does not exist or is not
            an artifact store.
        NotImplementedError: If the artifact store could not be loaded.
    """
    if isinstance(artifact_store_id, str):
        artifact_store_id = UUID(artifact_store_id)

    if zen_store is None:
        zen_store = Client().zen_store

    try:
        artifact_store_model = zen_store.get_stack_component(artifact_store_id)
    except KeyError:
        raise DoesNotExistException(
            f"Artifact store '{artifact_store_id}' does not exist."
        )

    if not artifact_store_model.type == StackComponentType.ARTIFACT_STORE:
        raise DoesNotExistException(
            f"Stack component '{artifact_store_id}' is not an artifact store."
        )

    try:
        artifact_store = cast(
            "BaseArtifactStore",
            StackComponent.from_model(artifact_store_model),
        )
    except ImportError:
        link = "https://docs.zenml.io/stacks-and-components/component-guide/artifact-stores/custom#enabling-artifact-visualizations-with-custom-artifact-stores"
        raise NotImplementedError(
            f"Artifact store '{artifact_store_model.name}' could not be "
            f"instantiated. This is likely because the artifact store's "
            f"dependencies are not installed. For more information, see {link}."
        )

    return artifact_store


def _load_file_from_artifact_store(
    uri: str,
    artifact_store: "BaseArtifactStore",
    mode: str = "rb",
) -> Any:
    """Load the given uri from the given artifact store.

    Args:
        uri: The uri of the file to load.
        artifact_store: The artifact store from which to load the file.
        mode: The mode in which to open the file.

    Returns:
        The loaded file.

    Raises:
        DoesNotExistException: If the file does not exist in the artifact store.
        NotImplementedError: If the artifact store cannot open the file.
    """
    try:
        with artifact_store.open(uri, mode) as text_file:
            return text_file.read()
    except FileNotFoundError:
        raise DoesNotExistException(
            f"File '{uri}' does not exist in artifact store "
            f"'{artifact_store.name}'."
        )
    except Exception as e:
        logger.exception(e)
        link = "https://docs.zenml.io/stacks-and-components/component-guide/artifact-stores/custom#enabling-artifact-visualizations-with-custom-artifact-stores"
        raise NotImplementedError(
            f"File '{uri}' could not be loaded because the underlying artifact "
            f"store '{artifact_store.name}' could not open the file. This is "
            f"likely because the authentication credentials are not configured "
            f"in the artifact store itself. For more information, see {link}."
        )


def upload_artifact(
    name: str,
    data: Any,
    materializer: "BaseMaterializer",
    artifact_store_id: "UUID",
    extract_metadata: bool,
    include_visualizations: bool,
) -> "UUID":
    """Upload and publish an artifact.

    Args:
        name: The name of the artifact.
        data: The artifact data.
        materializer: The materializer to store the artifact.
        artifact_store_id: ID of the artifact store in which the artifact should
            be stored.
        extract_metadata: If artifact metadata should be extracted and returned.
        include_visualizations: If artifact visualizations should be generated.

    Returns:
        The ID of the published artifact.
    """
    data_type = type(data)
    materializer.validate_type_compatibility(data_type)
    materializer.save(data)

    visualizations: List[VisualizationModel] = []
    if include_visualizations:
        try:
            vis_data = materializer.save_visualizations(data)
            for vis_uri, vis_type in vis_data.items():
                vis_model = VisualizationModel(
                    type=vis_type,
                    uri=vis_uri,
                )
                visualizations.append(vis_model)
        except Exception as e:
            logger.warning(
                f"Failed to save visualization for output artifact '{name}': "
                f"{e}"
            )

    artifact_metadata = {}
    if extract_metadata:
        try:
            artifact_metadata = materializer.extract_full_metadata(data)
        except Exception as e:
            logger.warning(
                f"Failed to extract metadata for output artifact '{name}': {e}"
            )

    artifact = ArtifactRequestModel(
        name=name,
        type=materializer.ASSOCIATED_ARTIFACT_TYPE,
        uri=materializer.uri,
        materializer=source_utils.resolve(materializer.__class__),
        data_type=source_utils.resolve(data_type),
        user=Client().active_user.id,
        workspace=Client().active_workspace.id,
        artifact_store_id=artifact_store_id,
        visualizations=visualizations,
    )
    response = Client().zen_store.create_artifact(artifact=artifact)
    if artifact_metadata:
        Client().create_run_metadata(
            metadata=artifact_metadata, artifact_id=response.id
        )

    return response.id


def get_producer_step_of_artifact(
    artifact: "ArtifactResponseModel",
) -> "StepRunResponseModel":
    """Get the step run that produced a given artifact.

    Args:
        artifact: The artifact.

    Returns:
        The step run that produced the artifact.

    Raises:
        RuntimeError: If the run that created the artifact no longer exists.
    """
    if not artifact.producer_step_run_id:
        raise RuntimeError(
            f"The run that produced the artifact with id '{artifact.id}' no "
            "longer exists. This can happen if the run was deleted."
        )
    return Client().get_run_step(artifact.producer_step_run_id)


def get_artifacts_of_pipeline_run(
    pipeline_run: "PipelineRunResponseModel", only_produced: bool = False
) -> List["ArtifactResponseModel"]:
    """Get all artifacts produced during a pipeline run.

    Args:
        pipeline_run: The pipeline run.
        only_produced: If only artifacts produced by the pipeline run should be
            returned or also cached artifacts.

    Returns:
        A list of all artifacts produced during the pipeline run.
    """
    artifacts: List["ArtifactResponseModel"] = []
    for step in pipeline_run.steps.values():
        if not only_produced or step.status == ExecutionStatus.COMPLETED:
            artifacts.extend(step.outputs.values())
    return artifacts
