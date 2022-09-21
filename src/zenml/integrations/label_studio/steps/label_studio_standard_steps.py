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

from zenml.exceptions import StackComponentInterfaceError
from zenml.integrations.label_studio.label_config_generators import (
    TASK_TO_FILENAME_REFERENCE_MAPPING,
)
from zenml.integrations.label_studio.label_studio_utils import (
    convert_pred_filenames_to_task_ids,
)
from zenml.logger import get_logger
from zenml.secret.schemas import (
    AWSSecretSchema,
    AzureSecretSchema,
    GCPSecretSchema,
)
from zenml.stack.authentication_mixin import AuthenticationMixin
from zenml.steps import BaseParameters, StepContext, step

logger = get_logger(__name__)

LABEL_STUDIO_AWS_SECRET_NAME = "aws_label_studio"


class LabelStudioDatasetRegistrationParameters(BaseParameters):
    """Step parameters when registering a dataset with Label Studio.

    Attributes:
        label_config: The label config to use for the annotation interface.
        dataset_name: Name of the dataset to register.
    """

    label_config: str
    dataset_name: str


class LabelStudioDatasetSyncParameters(BaseParameters):
    """Step parameters when syncing data to Label Studio.

    Attributes:
        storage_type: The type of storage to sync to.
        label_config_type: The type of label config to use.

        prefix: Specify the prefix within the cloud store to import your data
            from.
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
        google_application_credentials: Specify the Google application
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

    storage_type: str
    label_config_type: str

    prefix: Optional[str] = None
    regex_filter: Optional[str] = ".*"
    use_blob_urls: Optional[bool] = True
    presign: Optional[bool] = True
    presign_ttl: Optional[int] = 1
    description: Optional[str] = ""

    # credentials specific to the main cloud providers
    azure_account_name: Optional[str]
    azure_account_key: Optional[str]
    google_application_credentials: Optional[str]
    aws_access_key_id: Optional[str]
    aws_secret_access_key: Optional[str]
    aws_session_token: Optional[str]
    s3_region_name: Optional[str]
    s3_endpoint: Optional[str]


@step(enable_cache=False)
def get_or_create_dataset(
    params: LabelStudioDatasetRegistrationParameters,
    context: StepContext,
) -> str:
    """Gets preexisting dataset or creates a new one.

    Args:
        params: Step parameters.
        context: Step context.

    Returns:
        The dataset name.

    Raises:
        TypeError: If you are trying to use it with an annotator that is not
            Label Studio.
        StackComponentInterfaceError: If no active annotator could be found.
    """
    annotator = context.stack.annotator  # type: ignore[union-attr]
    from zenml.integrations.label_studio.annotators.label_studio_annotator import (
        LabelStudioAnnotator,
    )

    if not isinstance(annotator, LabelStudioAnnotator):
        raise TypeError(
            "This step can only be used with the Label Studio annotator."
        )

    if annotator and annotator._connection_available():
        for dataset in annotator.get_datasets():
            if dataset.get_params()["title"] == params.dataset_name:
                return cast(str, dataset.get_params()["title"])

        dataset = annotator.register_dataset_for_annotation(params)
        return cast(str, dataset.get_params()["title"])

    raise StackComponentInterfaceError("No active annotator.")
    # if annotator and annotator._connection_available():
    #     preexisting_dataset_list = [
    #         dataset
    #         for dataset in annotator.get_datasets()
    #         if dataset.get_params()["title"] == config.dataset_name
    #     ]
    #     if (
    #         not preexisting_dataset_list
    #         and annotator
    #         and annotator._connection_available()
    #     ):
    #         registered_dataset = annotator.register_dataset_for_annotation(
    #             config
    #         )
    #     elif preexisting_dataset_list:
    #         return cast(str, preexisting_dataset_list[0].get_params()["title"])
    #     else:
    #         raise StackComponentInterfaceError("No active annotator.")

    #     return cast(str, registered_dataset.get_params()["title"])
    # else:
    #     raise StackComponentInterfaceError("No active annotator.")


@step(enable_cache=False)
def get_labeled_data(dataset_name: str, context: StepContext) -> List:  # type: ignore[type-arg]
    """Gets labeled data from the dataset.

    Args:
        dataset_name: Name of the dataset.
        context: The StepContext.

    Returns:
        List of labeled data.

    Raises:
        TypeError: If you are trying to use it with an annotator that is not
            Label Studio.
        StackComponentInterfaceError: If no active annotator could be found.
    """
    # TODO [MEDIUM]: have this check for new data *since the last time this step ran*
    annotator = context.stack.annotator  # type: ignore[union-attr]
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
    context: StepContext,
) -> None:
    """Syncs new data to Label Studio.

    Args:
        uri: The URI of the data to sync.
        dataset_name: The name of the dataset to sync to.
        predictions: The predictions to sync.
        params: The parameters for the sync.
        context: The StepContext.

    Raises:
        TypeError: If you are trying to use it with an annotator that is not
            Label Studio.
        ValueError: if you are trying to sync from outside ZenML.
        StackComponentInterfaceError: If no active annotator could be found.
    """
    annotator = context.stack.annotator  # type: ignore[union-attr]
    artifact_store = context.stack.artifact_store  # type: ignore[union-attr]
    secrets_manager = context.stack.secrets_manager  # type: ignore[union-attr]
    if not annotator or not artifact_store or not secrets_manager:
        raise StackComponentInterfaceError(
            "An active annotator, artifact store and secrets manager are required to run this step."
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

    # gets the secret used for authentication
    if params.storage_type == "azure":
        if not isinstance(artifact_store, AuthenticationMixin):
            raise TypeError(
                "The artifact store must inherit from "
                f"{AuthenticationMixin.__name__} to work with a Label Studio "
                f"`{params.storage_type}` storage."
            )

        azure_secret = artifact_store.get_authentication_secret(
            expected_schema_type=AzureSecretSchema
        )

        if not azure_secret:
            raise ValueError(
                "Missing secret to authenticate cloud storage for Label Studio."
            )

        params.azure_account_name = azure_secret.account_name
        params.azure_account_key = azure_secret.account_key
    elif params.storage_type == "gcs":
        if not isinstance(artifact_store, AuthenticationMixin):
            raise TypeError(
                "The artifact store must inherit from "
                f"{AuthenticationMixin.__name__} to work with a Label Studio "
                f"`{params.storage_type}` storage."
            )

        gcp_secret = artifact_store.get_authentication_secret(
            expected_schema_type=GCPSecretSchema
        )
        if not gcp_secret:
            raise ValueError(
                "Missing secret to authenticate cloud storage for Label Studio."
            )

        params.google_application_credentials = gcp_secret.token
    elif params.storage_type == "s3":
        aws_secret = secrets_manager.get_secret(LABEL_STUDIO_AWS_SECRET_NAME)
        if not isinstance(aws_secret, AWSSecretSchema):
            raise TypeError(
                f"The secret `{LABEL_STUDIO_AWS_SECRET_NAME}` needs to be "
                f"an `aws` schema secret."
            )

        params.aws_access_key_id = aws_secret.aws_access_key_id
        params.aws_secret_access_key = aws_secret.aws_secret_access_key
        params.aws_session_token = aws_secret.aws_session_token

    if annotator and annotator._connection_available():
        # TODO: get existing (CHECK!) or create the sync connection
        annotator.connect_and_sync_external_storage(
            uri=base_uri,
            params=params,
            dataset=dataset,
        )
        if predictions:
            filename_reference = TASK_TO_FILENAME_REFERENCE_MAPPING[
                params.label_config_type
            ]
            preds_with_task_ids = convert_pred_filenames_to_task_ids(
                predictions,
                dataset.tasks,
                filename_reference,
                params.storage_type,
            )
            # TODO: filter out any predictions that exist + have already been
            # made (maybe?). Only pass in preds for tasks without pre-annotations.
            dataset.create_predictions(preds_with_task_ids)
    else:
        raise StackComponentInterfaceError("No active annotator.")
