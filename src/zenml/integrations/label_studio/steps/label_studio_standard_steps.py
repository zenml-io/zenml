#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""Implementation of standard steps for the Label Studio annotator integration."""

from typing import Any, Dict, List, Optional, cast
from urllib.parse import urlparse

from pydantic import BaseModel

from zenml import step
from zenml.client import Client
from zenml.exceptions import StackComponentInterfaceError
from zenml.integrations.label_studio.label_studio_utils import (
    convert_pred_filenames_to_task_ids,
)
from zenml.logger import get_logger

logger = get_logger(__name__)


class LabelStudioDatasetSyncParameters(BaseModel):
    """Step parameters when syncing data to Label Studio.

    Attributes:
        storage_type: The type of storage to sync to. Can be one of
            ["gcs", "s3", "azure", "local"]. Defaults to "local".
        label_config_type: The type of label config to use.
        prefix: Specify the prefix within the cloud store to import your data
            from. For local storage, this is the full absolute path to the
            directory containing your data.
        regex_filter: Specify a regex filter to filter the files to import.
        use_blob_urls: Specify whether your data is raw image or video data, or
            JSON tasks.
        presign: Specify whether or not to create presigned URLs.
        presign_ttl: Specify how long to keep presigned URLs active.
        description: Specify a description for the dataset.

        azure_account_name: Specify the Azure account name to use for the
            storage.
        azure_account_key: Specify the Azure account key to use for the
            storage.
        google_application_credentials: Specify the file with Google application
            credentials to use for the storage.
        aws_access_key_id: Specify the AWS access key ID to use for the
            storage.
        aws_secret_access_key: Specify the AWS secret access key to use for the
            storage.
        aws_session_token: Specify the AWS session token to use for the
            storage.
        s3_region_name: Specify the S3 region name to use for the storage.
        s3_endpoint: Specify the S3 endpoint to use for the storage.
    """

    storage_type: str = "local"
    label_config_type: str

    prefix: Optional[str] = None
    regex_filter: Optional[str] = ".*"
    use_blob_urls: Optional[bool] = True
    presign: Optional[bool] = True
    presign_ttl: Optional[int] = 1
    description: Optional[str] = ""

    # credentials specific to the main cloud providers
    azure_account_name: Optional[str] = None
    azure_account_key: Optional[str] = None
    google_application_credentials: Optional[str] = None
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_session_token: Optional[str] = None
    s3_region_name: Optional[str] = None
    s3_endpoint: Optional[str] = None


@step(enable_cache=False)
def get_or_create_dataset(
    label_config: str,
    dataset_name: str,
) -> str:
    """Gets preexisting dataset or creates a new one.

    Args:
        label_config: The label config to use for the annotation interface.
        dataset_name: Name of the dataset to register.

    Returns:
        The dataset name.

    Raises:
        TypeError: If you are trying to use it with an annotator that is not
            Label Studio.
        StackComponentInterfaceError: If no active annotator could be found.
    """
    annotator = Client().active_stack.annotator
    from zenml.integrations.label_studio.annotators.label_studio_annotator import (
        LabelStudioAnnotator,
    )

    if not isinstance(annotator, LabelStudioAnnotator):
        raise TypeError(
            "This step can only be used with the Label Studio annotator."
        )

    if annotator and annotator._connection_available():
        for dataset in annotator.get_datasets():
            if dataset.get_params()["title"] == dataset_name:
                return cast(str, dataset.get_params()["title"])

        dataset = annotator.register_dataset_for_annotation(
            label_config=label_config,
            dataset_name=dataset_name,
        )
        return cast(str, dataset.get_params()["title"])

    raise StackComponentInterfaceError("No active annotator.")


@step(enable_cache=False)
def get_labeled_data(dataset_name: str) -> List:  # type: ignore[type-arg]
    """Gets labeled data from the dataset.

    Args:
        dataset_name: Name of the dataset.

    Returns:
        List of labeled data.

    Raises:
        TypeError: If you are trying to use it with an annotator that is not
            Label Studio.
        StackComponentInterfaceError: If no active annotator could be found.
    """
    # TODO [MEDIUM]: have this check for new data *since the last time this step ran*
    annotator = Client().active_stack.annotator
    if not annotator:
        raise StackComponentInterfaceError("No active annotator.")
    from zenml.integrations.label_studio.annotators.label_studio_annotator import (
        LabelStudioAnnotator,
    )

    if not isinstance(annotator, LabelStudioAnnotator):
        raise TypeError(
            "This step can only be used with the Label Studio annotator."
        )
    if annotator._connection_available():
        dataset = annotator.get_dataset(dataset_name=dataset_name)
        return dataset.get_labeled_tasks()  # type: ignore[no-any-return]

    raise StackComponentInterfaceError(
        "Unable to connect to annotator stack component."
    )


@step(enable_cache=False)
def sync_new_data_to_label_studio(
    uri: str,
    dataset_name: str,
    predictions: List[Dict[str, Any]],
    params: LabelStudioDatasetSyncParameters,
) -> None:
    """Syncs new data to Label Studio.

    Args:
        uri: The URI of the data to sync.
        dataset_name: The name of the dataset to sync to.
        predictions: The predictions to sync.
        params: The parameters for the sync.

    Raises:
        TypeError: If you are trying to use it with an annotator that is not
            Label Studio.
        ValueError: if you are trying to sync from outside ZenML.
        StackComponentInterfaceError: If no active annotator could be found.
    """
    stack = Client().active_stack
    annotator = stack.annotator
    artifact_store = stack.artifact_store
    if not annotator or not artifact_store:
        raise StackComponentInterfaceError(
            "An active annotator and artifact store are required to run this step."
        )

    from zenml.integrations.label_studio.annotators.label_studio_annotator import (
        LabelStudioAnnotator,
    )

    if not isinstance(annotator, LabelStudioAnnotator):
        raise TypeError(
            "This step can only be used with the Label Studio annotator."
        )

    # TODO: check that annotator is connected before querying it
    dataset = annotator.get_dataset(dataset_name=dataset_name)
    if not uri.startswith(artifact_store.path):
        raise ValueError(
            "ZenML only currently supports syncing data passed from other ZenML steps and via the Artifact Store."
        )
    # removes the initial forward slash from the prefix attribute by slicing
    params.prefix = urlparse(uri).path.lstrip("/")
    base_uri = urlparse(uri).netloc

    annotator.populate_artifact_store_parameters(
        params=params, artifact_store=artifact_store
    )

    if annotator and annotator._connection_available():
        # TODO: get existing (CHECK!) or create the sync connection
        annotator.connect_and_sync_external_storage(
            uri=base_uri,
            params=params,
            dataset=dataset,
        )
        if predictions:
            preds_with_task_ids = convert_pred_filenames_to_task_ids(
                predictions,
                dataset.tasks,
            )
            # TODO: filter out any predictions that exist + have already been
            # made (maybe?). Only pass in preds for tasks without pre-annotations.
            dataset.create_predictions(preds_with_task_ids)
    else:
        raise StackComponentInterfaceError("No active annotator.")
