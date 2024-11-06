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
"""Utility functions for handling artifacts."""

import base64
import os
import tempfile
import zipfile
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Optional,
    Type,
    Union,
    cast,
)
from uuid import UUID, uuid4

from zenml.artifacts.preexisting_data_materializer import (
    PreexistingDataMaterializer,
)
from zenml.client import Client
from zenml.constants import (
    MODEL_METADATA_YAML_FILE_NAME,
)
from zenml.enums import (
    ArtifactType,
    ExecutionStatus,
    MetadataResourceTypes,
    StackComponentType,
    VisualizationType,
)
from zenml.exceptions import (
    DoesNotExistException,
    StepContextError,
)
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.metadata.metadata_types import validate_metadata
from zenml.models import (
    ArtifactVersionRequest,
    ArtifactVersionResponse,
    ArtifactVisualizationRequest,
    LoadedVisualization,
    PipelineRunResponse,
    StepRunResponse,
    StepRunUpdate,
)
from zenml.stack import StackComponent
from zenml.steps.step_context import get_step_context
from zenml.utils import source_utils
from zenml.utils.yaml_utils import read_yaml, write_yaml

if TYPE_CHECKING:
    from zenml.artifact_stores.base_artifact_store import BaseArtifactStore
    from zenml.config.source import Source
    from zenml.materializers.base_materializer import BaseMaterializer
    from zenml.metadata.metadata_types import MetadataType
    from zenml.zen_stores.base_zen_store import BaseZenStore

    MaterializerClassOrSource = Union[str, Source, Type[BaseMaterializer]]

logger = get_logger(__name__)

# ----------
# Public API
# ----------


def _save_artifact_visualizations(
    data: Any, materializer: "BaseMaterializer"
) -> List[ArtifactVisualizationRequest]:
    """Save artifact visualizations.

    Args:
        data: The data for which to save the visualizations.
        materializer: The materializer that should be used to generate and
            save the visualizations.

    Returns:
        List of requests for the saved visualizations.
    """
    try:
        visualizations = materializer.save_visualizations(data)
    except Exception as e:
        logger.warning("Failed to save artifact visualizations: %s", e)
        return []

    return [
        ArtifactVisualizationRequest(
            type=type,
            uri=uri,
        )
        for uri, type in visualizations.items()
    ]


def _store_artifact_data_and_prepare_request(
    data: Any,
    name: str,
    uri: str,
    materializer_class: Type["BaseMaterializer"],
    version: Optional[Union[int, str]] = None,
    artifact_type: Optional[ArtifactType] = None,
    tags: Optional[List[str]] = None,
    store_metadata: bool = True,
    store_visualizations: bool = True,
    has_custom_name: bool = True,
    metadata: Optional[Dict[str, "MetadataType"]] = None,
) -> ArtifactVersionRequest:
    """Store artifact data and prepare a request to the server.

    Args:
        data: The artifact data.
        name: The artifact name.
        uri: The artifact URI.
        materializer_class: The materializer class to use for storing the
            artifact data.
        version: The artifact version.
        artifact_type: The artifact type. If not given, the type will be defined
            by the materializer that is used to save the artifact.
        tags: Tags for the artifact version.
        store_metadata: Whether to store metadata for the artifact version.
        store_visualizations: Whether to store visualizations for the artifact
            version.
        has_custom_name: Whether the artifact has a custom name.
        metadata: Metadata to store for the artifact version. This will be
            ignored if `store_metadata` is set to `False`.

    Returns:
        Artifact version request for the artifact data that was stored.
    """
    artifact_store = Client().active_stack.artifact_store
    artifact_store.makedirs(uri)

    materializer = materializer_class(uri=uri, artifact_store=artifact_store)
    materializer.uri = materializer.uri.replace("\\", "/")

    data_type = type(data)
    materializer.validate_save_type_compatibility(data_type)
    materializer.save(data)

    visualizations = (
        _save_artifact_visualizations(data=data, materializer=materializer)
        if store_visualizations
        else None
    )

    combined_metadata: Dict[str, "MetadataType"] = {}
    if store_metadata:
        try:
            combined_metadata = materializer.extract_full_metadata(data)
        except Exception as e:
            logger.warning("Failed to extract materializer metadata: %s", e)

        # Update with user metadata to potentially overwrite values coming from
        # the materializer
        combined_metadata.update(metadata or {})

    artifact_version_request = ArtifactVersionRequest(
        artifact_name=name,
        version=version,
        tags=tags,
        type=artifact_type or materializer.ASSOCIATED_ARTIFACT_TYPE,
        uri=materializer.uri,
        materializer=source_utils.resolve(materializer.__class__),
        data_type=source_utils.resolve(data_type),
        user=Client().active_user.id,
        workspace=Client().active_workspace.id,
        artifact_store_id=artifact_store.id,
        visualizations=visualizations,
        has_custom_name=has_custom_name,
        metadata=validate_metadata(combined_metadata)
        if combined_metadata
        else None,
    )

    return artifact_version_request


def save_artifact(
    data: Any,
    name: str,
    version: Optional[Union[int, str]] = None,
    artifact_type: Optional[ArtifactType] = None,
    tags: Optional[List[str]] = None,
    extract_metadata: bool = True,
    include_visualizations: bool = True,
    user_metadata: Optional[Dict[str, "MetadataType"]] = None,
    materializer: Optional["MaterializerClassOrSource"] = None,
    uri: Optional[str] = None,
    # TODO: remove these once external artifact does not use this function anymore
    manual_save: bool = True,
    has_custom_name: bool = True,
) -> "ArtifactVersionResponse":
    """Upload and publish an artifact.

    Args:
        name: The name of the artifact.
        data: The artifact data.
        version: The version of the artifact. If not provided, a new
            auto-incremented version will be used.
        tags: Tags to associate with the artifact.
        artifact_type: The artifact type. If not given, the type will be defined
            by the materializer that is used to save the artifact.
        extract_metadata: If artifact metadata should be extracted and returned.
        include_visualizations: If artifact visualizations should be generated.
        user_metadata: User-provided metadata to store with the artifact.
        materializer: The materializer to use for saving the artifact to the
            artifact store.
        uri: The URI within the artifact store to upload the artifact
            to. If not provided, the artifact will be uploaded to
            `custom_artifacts/{name}/{version}`.
        manual_save: If this function is called manually and should therefore
            link the artifact to the current step run.
        has_custom_name: If the artifact name is custom and should be listed in
            the dashboard "Artifacts" tab.

    Returns:
        The saved artifact response.
    """
    from zenml.materializers.materializer_registry import (
        materializer_registry,
    )
    from zenml.utils import source_utils

    client = Client()
    artifact_store = client.active_stack.artifact_store

    if not uri:
        uri = os.path.join("custom_artifacts", name, str(uuid4()))
    if not uri.startswith(artifact_store.path):
        uri = os.path.join(artifact_store.path, uri)

    if manual_save:
        # This check is only necessary for manual saves as we already check
        # it when creating the directory for step output artifacts
        _check_if_artifact_with_given_uri_already_registered(
            artifact_store=artifact_store,
            uri=uri,
            name=name,
        )

    if isinstance(materializer, type):
        materializer_class = materializer
    elif materializer:
        materializer_class = source_utils.load_and_validate_class(
            materializer, expected_class=BaseMaterializer
        )
    else:
        materializer_class = materializer_registry[type(data)]

    artifact_version_request = _store_artifact_data_and_prepare_request(
        data=data,
        name=name,
        uri=uri,
        materializer_class=materializer_class,
        version=version,
        artifact_type=artifact_type,
        tags=tags,
        store_metadata=extract_metadata,
        store_visualizations=include_visualizations,
        has_custom_name=has_custom_name,
        metadata=user_metadata,
    )
    artifact_version = client.zen_store.create_artifact_version(
        artifact_version=artifact_version_request
    )

    if manual_save:
        _link_artifact_version_to_the_step_and_model(
            artifact_version=artifact_version,
        )

    return artifact_version


def register_artifact(
    folder_or_file_uri: str,
    name: str,
    version: Optional[Union[int, str]] = None,
    artifact_type: Optional[ArtifactType] = None,
    tags: Optional[List[str]] = None,
    has_custom_name: bool = True,
    artifact_metadata: Dict[str, "MetadataType"] = {},
) -> "ArtifactVersionResponse":
    """Register existing data stored in the artifact store as a ZenML Artifact.

    Args:
        folder_or_file_uri: The full URI within the artifact store to the folder
            or to the file.
        name: The name of the artifact.
        version: The version of the artifact. If not provided, a new
            auto-incremented version will be used.
        artifact_type: The artifact type. If not given, the type will default
            to `data`.
        tags: Tags to associate with the artifact.
        has_custom_name: If the artifact name is custom and should be listed in
            the dashboard "Artifacts" tab.
        artifact_metadata: Metadata dictionary to attach to the artifact version.

    Returns:
        The saved artifact response.

    Raises:
        FileNotFoundError: If the folder URI is outside of the artifact store
            bounds.
    """
    client = Client()

    # Get the current artifact store
    artifact_store = client.active_stack.artifact_store

    if not folder_or_file_uri.startswith(artifact_store.path):
        raise FileNotFoundError(
            f"Folder `{folder_or_file_uri}` is outside of "
            f"artifact store bounds `{artifact_store.path}`"
        )

    _check_if_artifact_with_given_uri_already_registered(
        artifact_store=artifact_store,
        uri=folder_or_file_uri,
        name=name,
    )

    artifact_version_request = ArtifactVersionRequest(
        artifact_name=name,
        version=version,
        tags=tags,
        type=artifact_type or ArtifactType.DATA,
        uri=folder_or_file_uri,
        materializer=source_utils.resolve(PreexistingDataMaterializer),
        data_type=source_utils.resolve(Path),
        user=Client().active_user.id,
        workspace=Client().active_workspace.id,
        artifact_store_id=artifact_store.id,
        has_custom_name=has_custom_name,
        metadata=validate_metadata(artifact_metadata)
        if artifact_metadata
        else None,
    )
    artifact_version = client.zen_store.create_artifact_version(
        artifact_version=artifact_version_request
    )

    _link_artifact_version_to_the_step_and_model(
        artifact_version=artifact_version,
    )

    return artifact_version


def load_artifact(
    name_or_id: Union[str, UUID],
    version: Optional[str] = None,
) -> Any:
    """Load an artifact.

    Args:
        name_or_id: The name or ID of the artifact to load.
        version: The version of the artifact to load, if `name_or_id` is a
            name. If not provided, the latest version will be loaded.

    Returns:
        The loaded artifact.
    """
    artifact = Client().get_artifact_version(name_or_id, version)
    try:
        step_run = get_step_context().step_run
        client = Client()
        client.zen_store.update_run_step(
            step_run_id=step_run.id,
            step_run_update=StepRunUpdate(
                loaded_artifact_versions={artifact.name: artifact.id}
            ),
        )
    except RuntimeError:
        pass  # Cannot link to step run if called outside of a step
    return load_artifact_from_response(artifact)


def log_artifact_metadata(
    metadata: Dict[str, "MetadataType"],
    artifact_name: Optional[str] = None,
    artifact_version: Optional[str] = None,
) -> None:
    """Log artifact metadata.

    This function can be used to log metadata for either existing artifact
    versions or artifact versions that are newly created in the same step.

    Args:
        metadata: The metadata to log.
        artifact_name: The name of the artifact to log metadata for. Can
            be omitted when being called inside a step with only one output.
        artifact_version: The version of the artifact to log metadata for. If
            not provided, when being called inside a step that produces an
            artifact named `artifact_name`, the metadata will be associated to
            the corresponding newly created artifact. Or, if not provided when
            being called outside of a step, or in a step that does not produce
            any artifact named `artifact_name`, the metadata will be associated
            to the latest version of that artifact.

    Raises:
        ValueError: If no artifact name is provided and the function is not
            called inside a step with a single output, or, if neither an
            artifact nor an output with the given name exists.
    """
    try:
        step_context = get_step_context()
        in_step_outputs = (artifact_name in step_context._outputs) or (
            not artifact_name and len(step_context._outputs) == 1
        )
    except RuntimeError:
        step_context = None
        in_step_outputs = False

    if not step_context or not in_step_outputs or artifact_version:
        if not artifact_name:
            raise ValueError(
                "Artifact name must be provided unless the function is called "
                "inside a step with a single output."
            )
        client = Client()
        response = client.get_artifact_version(artifact_name, artifact_version)
        client.create_run_metadata(
            metadata=metadata,
            resource_id=response.id,
            resource_type=MetadataResourceTypes.ARTIFACT_VERSION,
        )

    else:
        try:
            step_context.add_output_metadata(
                metadata=metadata, output_name=artifact_name
            )
        except StepContextError as e:
            raise ValueError(e)


# -----------------
# End of Public API
# -----------------


def load_artifact_visualization(
    artifact: "ArtifactVersionResponse",
    index: int = 0,
    zen_store: Optional["BaseZenStore"] = None,
    encode_image: bool = False,
) -> LoadedVisualization:
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
    try:
        mode = "rb" if visualization.type == VisualizationType.IMAGE else "r"
        value = _load_file_from_artifact_store(
            uri=visualization.uri,
            artifact_store=artifact_store,
            mode=mode,
        )

        # Encode image visualizations if requested
        if visualization.type == VisualizationType.IMAGE and encode_image:
            value = base64.b64encode(bytes(value))

        return LoadedVisualization(type=visualization.type, value=value)
    finally:
        artifact_store.cleanup()


def load_artifact_from_response(artifact: "ArtifactVersionResponse") -> Any:
    """Load the given artifact into memory.

    Args:
        artifact: The artifact to load.

    Returns:
        The artifact loaded into memory.
    """
    artifact_store = _get_artifact_store_from_response_or_from_active_stack(
        artifact=artifact
    )

    return _load_artifact_from_uri(
        materializer=artifact.materializer,
        data_type=artifact.data_type,
        uri=artifact.uri,
        artifact_store=artifact_store,
    )


def download_artifact_files_from_response(
    artifact: "ArtifactVersionResponse",
    path: str,
    overwrite: bool = False,
) -> None:
    """Download the given artifact into a file.

    Args:
        artifact: The artifact to download.
        path: The path to which to download the artifact.
        overwrite: Whether to overwrite the file if it already exists.

    Raises:
        FileExistsError: If the file already exists and `overwrite` is `False`.
        Exception: If the artifact could not be downloaded to the zip file.
    """
    if not overwrite and fileio.exists(path):
        raise FileExistsError(
            f"File '{path}' already exists and `overwrite` is set to `False`."
        )

    artifact_store = _get_artifact_store_from_response_or_from_active_stack(
        artifact=artifact
    )

    if filepaths := artifact_store.listdir(artifact.uri):
        # save a zipfile to 'path' containing all the files
        # in 'filepaths' with compression
        try:
            with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for file in filepaths:
                    # Ensure 'file' is a string for path operations
                    # and ZIP entry naming
                    file_str = (
                        file.decode() if isinstance(file, bytes) else file
                    )
                    file_path = str(Path(artifact.uri) / file_str)
                    with artifact_store.open(
                        name=file_path, mode="rb"
                    ) as store_file:
                        # Use a loop to read and write chunks of the file
                        # instead of reading the entire file into memory
                        CHUNK_SIZE = 8192
                        while True:
                            if file_content := store_file.read(CHUNK_SIZE):
                                zipf.writestr(file_str, file_content)
                            else:
                                break
        except Exception as e:
            logger.error(
                f"Failed to save artifact '{artifact.id}' to zip file "
                f" '{path}': {e}"
            )
            raise


def get_producer_step_of_artifact(
    artifact: "ArtifactVersionResponse",
) -> "StepRunResponse":
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


def get_artifacts_versions_of_pipeline_run(
    pipeline_run: "PipelineRunResponse", only_produced: bool = False
) -> List["ArtifactVersionResponse"]:
    """Get all artifact versions produced during a pipeline run.

    Args:
        pipeline_run: The pipeline run.
        only_produced: If only artifact versions produced by the pipeline run
            should be returned or also cached artifact versions.

    Returns:
        A list of all artifact versions produced during the pipeline run.
    """
    artifact_versions: List["ArtifactVersionResponse"] = []
    for step in pipeline_run.steps.values():
        if not only_produced or step.status == ExecutionStatus.COMPLETED:
            artifact_versions.extend(step.outputs.values())
    return artifact_versions


# -------------------------
# Internal Helper Functions
# -------------------------


def _check_if_artifact_with_given_uri_already_registered(
    artifact_store: "BaseArtifactStore",
    uri: str,
    name: str,
) -> None:
    """Check if the given artifact store already contains an artifact with the given URI.

    Args:
        artifact_store: The artifact store to check.
        uri: The uri of the artifact.
        name: The name of the artifact.

    Raises:
        RuntimeError: If the artifact store already contains an artifact with
            the given URI.
    """
    if artifact_store.exists(uri):
        # This check is only necessary for manual saves as we already check
        # it when creating the directory for step output artifacts
        other_artifacts = Client().list_artifact_versions(uri=uri, size=1)
        if other_artifacts and (other_artifact := other_artifacts[0]):
            raise RuntimeError(
                f"Cannot create new artifact {name} version with URI "
                f"{uri} because the URI is already used by artifact "
                f"{other_artifact.name} (version {other_artifact.version})."
            )


def _link_artifact_version_to_the_step_and_model(
    artifact_version: ArtifactVersionResponse,
) -> None:
    """Link an artifact version to the step and its' context model.

    This function links the AV to:
        - the step run
        - the MV from the step context

    Args:
        artifact_version: The artifact version to link.
    """
    client = Client()
    try:
        error_message = "step run"
        step_context = get_step_context()
        step_run = step_context.step_run
        client.zen_store.update_run_step(
            step_run_id=step_run.id,
            step_run_update=StepRunUpdate(
                saved_artifact_versions={
                    artifact_version.artifact.name: artifact_version.id
                }
            ),
        )
        error_message = "model"

        if step_context.model_version:
            from zenml.model.utils import (
                link_artifact_version_to_model_version,
            )

            link_artifact_version_to_model_version(
                artifact_version=artifact_version,
                model_version=step_context.model_version,
            )
    except (RuntimeError, StepContextError):
        logger.debug(f"Unable to link saved artifact to {error_message}.")


def _load_artifact_from_uri(
    materializer: Union["Source", str],
    data_type: Union["Source", str],
    uri: str,
    artifact_store: Optional["BaseArtifactStore"] = None,
) -> Any:
    """Load an artifact using the given materializer.

    Args:
        materializer: The source of the materializer class to use.
        data_type: The source of the artifact data type.
        uri: The uri of the artifact.
        artifact_store: The artifact store used to store this artifact.

    Returns:
        The artifact loaded into memory.

    Raises:
        ModuleNotFoundError: If the materializer or data type cannot be found.
    """
    from zenml.materializers.base_materializer import BaseMaterializer

    if not artifact_store:
        artifact_versions_by_uri = Client().list_artifact_versions(uri=uri)
        if artifact_versions_by_uri.total == 1:
            artifact_store = (
                _get_artifact_store_from_response_or_from_active_stack(
                    artifact_versions_by_uri.items[0]
                )
            )

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
    materializer_object: BaseMaterializer = materializer_class(
        uri, artifact_store
    )
    artifact = materializer_object.load(artifact_class)
    logger.debug("Artifact loaded successfully.")

    return artifact


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
        link = "https://docs.zenml.io/stack-components/artifact-stores/custom#enabling-artifact-visualizations-with-custom-artifact-stores"
        raise NotImplementedError(
            f"Artifact store '{artifact_store_model.name}' could not be "
            f"instantiated. This is likely because the artifact store's "
            f"dependencies are not installed. For more information, see {link}."
        )

    return artifact_store


def _get_artifact_store_from_response_or_from_active_stack(
    artifact: ArtifactVersionResponse,
) -> "BaseArtifactStore":
    if artifact.artifact_store_id:
        try:
            artifact_store_model = Client().get_stack_component(
                component_type=StackComponentType.ARTIFACT_STORE,
                name_id_or_prefix=artifact.artifact_store_id,
            )
            return cast(
                "BaseArtifactStore",
                StackComponent.from_model(artifact_store_model),
            )
        except KeyError:
            raise RuntimeError(
                "Unable to fetch the artifact store with id: "
                f"'{artifact.artifact_store_id}'. Check whether the artifact "
                "store still exists and you have the right permissions to "
                "access it."
            )
        except ImportError:
            raise RuntimeError(
                "Unable to load the implementation of the artifact store with"
                f"id: '{artifact.artifact_store_id}'. Please make sure that "
                "the environment that you are loading this artifact from "
                "has the right dependencies."
            )
    return Client().active_stack.artifact_store


def _load_file_from_artifact_store(
    uri: str,
    artifact_store: "BaseArtifactStore",
    mode: str = "rb",
    offset: int = 0,
    length: Optional[int] = None,
) -> Any:
    """Load the given uri from the given artifact store.

    Args:
        uri: The uri of the file to load.
        artifact_store: The artifact store from which to load the file.
        mode: The mode in which to open the file.
        offset: The offset from which to start reading.
        length: The amount of bytes that should be read.

    Returns:
        The loaded file.

    Raises:
        DoesNotExistException: If the file does not exist in the artifact store.
        NotImplementedError: If the artifact store cannot open the file.
        IOError: If the artifact store rejects the request.
    """
    try:
        with artifact_store.open(uri, mode) as text_file:
            if offset < 0:
                # If the offset is negative, we seek backwards from the end of
                # the file
                try:
                    text_file.seek(offset, os.SEEK_END)
                except OSError:
                    # The negative offset was too large for the file, we seek
                    # to the start of the file
                    text_file.seek(0, os.SEEK_SET)
            elif offset > 0:
                text_file.seek(offset, os.SEEK_SET)

            return text_file.read(length)
    except FileNotFoundError:
        raise DoesNotExistException(
            f"File '{uri}' does not exist in artifact store "
            f"'{artifact_store.name}'."
        )
    except IOError as e:
        raise e
    except Exception as e:
        logger.exception(e)
        link = "https://docs.zenml.io/stack-components/artifact-stores/custom#enabling-artifact-visualizations-with-custom-artifact-stores"
        raise NotImplementedError(
            f"File '{uri}' could not be loaded because the underlying artifact "
            f"store '{artifact_store.name}' could not open the file. This is "
            f"likely because the authentication credentials are not configured "
            f"in the artifact store itself. For more information, see {link}."
        )


# --------------------
# Model Artifact Utils
# --------------------


def save_model_metadata(model_artifact: "ArtifactVersionResponse") -> str:
    """Save a zenml model artifact metadata to a YAML file.

    This function is used to extract and save information from a zenml model
    artifact such as the model type and materializer. The extracted information
    will be the key to loading the model into memory in the inference
    environment.

    datatype: the model type. This is the path to the model class.
    materializer: The path to the materializer class.

    Args:
        model_artifact: the artifact to extract the metadata from.

    Returns:
        The path to the temporary file where the model metadata is saved
    """
    metadata = dict()
    metadata["datatype"] = model_artifact.data_type
    metadata["materializer"] = model_artifact.materializer

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
    artifact_versions_by_uri = Client().list_artifact_versions(uri=model_uri)
    if artifact_versions_by_uri.total == 1:
        artifact_store = (
            _get_artifact_store_from_response_or_from_active_stack(
                artifact_versions_by_uri.items[0]
            )
        )
    else:
        artifact_store = Client().active_stack.artifact_store

    with artifact_store.open(
        os.path.join(model_uri, MODEL_METADATA_YAML_FILE_NAME), "r"
    ) as f:
        metadata = read_yaml(f.name)
    data_type = metadata["datatype"]
    materializer = metadata["materializer"]
    model = _load_artifact_from_uri(
        materializer=materializer,
        data_type=data_type,
        uri=model_uri,
        artifact_store=artifact_store,
    )

    # Switch to eval mode if the model is a torch model
    try:
        import torch.nn as nn

        if isinstance(model, nn.Module):
            model.eval()
    except ImportError:
        pass

    return model
