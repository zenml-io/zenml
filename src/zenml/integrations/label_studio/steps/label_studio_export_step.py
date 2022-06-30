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

import os
from typing import List, Optional, Tuple
from urllib.parse import urlparse

from zenml.exceptions import StackComponentInterfaceError
from zenml.logger import get_logger
from zenml.steps import BaseStepConfig, StepContext, step

logger = get_logger(__name__)

# TODO: use this to dynamically generate the classification label config
def generate_image_classification_label_config(labels: List[str]) -> str:
    """Generates a Label Studio label config for image classification."""
    label_config_start = """<View>
    <Image name="image" value="$image"/>
    <Choices name="choice" toName="image">
    """
    label_config_choices = "".join(
        f"<Choice value='{label}' />\n" for label in labels
    )
    label_config_end = "</Choices>\n</View>"

    return label_config_start + label_config_choices + label_config_end


IMAGE_CLASSIFICATION_LABEL_CONFIG = generate_image_classification_label_config(
    ["cat", "dog"]
)


class LabelStudioDatasetRegistrationConfig(BaseStepConfig):
    label_config: str
    dataset_name: str


class LabelStudioDatasetSyncConfig(BaseStepConfig):
    storage_type: str

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
    region_name: Optional[str]
    s3_endpoint: Optional[str]


@step
def get_or_create_dataset(
    config: LabelStudioDatasetRegistrationConfig,
    context: StepContext,
) -> int:
    """Gets preexisting dataset or creates a new one."""
    annotator = context.stack.annotator
    preexisting_dataset_list = [
        dataset
        for dataset in annotator.get_datasets()
        if dataset.get_params()["title"] == config.dataset_name
    ]
    if (
        not preexisting_dataset_list
        and annotator
        and annotator._connection_available()
    ):
        registered_dataset = annotator.register_dataset_for_annotation(config)
    elif preexisting_dataset_list:
        return preexisting_dataset_list[0].get_params()["id"]
    else:
        raise StackComponentInterfaceError("No active annotator.")

    return registered_dataset.get_params()["id"]


@step
def get_labeled_data(dataset_id: int, context: StepContext) -> List:
    """Gets labeled data from the dataset."""
    # TODO: have this check for new data *since the last time this step ran*
    annotator = context.stack.annotator
    if annotator and annotator._connection_available():
        dataset = annotator.get_dataset(dataset_id)
        return dataset.get_labeled_tasks()
    else:
        raise StackComponentInterfaceError("No active annotator.")


def get_azure_credentials() -> Tuple[str]:
    # TODO: add other ways to get credentials
    account_key = os.environ.get("AZURE_STORAGE_ACCOUNT_KEY")
    account_name = os.environ.get("AZURE_STORAGE_ACCOUNT_NAME")
    return account_name, account_key


@step(enable_cache=False)
def sync_new_data_to_label_studio(
    uri: str,
    dataset_id: int,
    config: LabelStudioDatasetSyncConfig,
    context: StepContext,
) -> None:
    """Syncs new data to Label Studio."""
    annotator = context.stack.annotator
    dataset = annotator.get_dataset(dataset_id)
    artifact_store = context.stack.artifact_store
    if uri.startswith(artifact_store.path):
        if config.storage_type == "azure":
            account_name, account_key = get_azure_credentials()
            config.azure_account_name = account_name
            config.azure_account_key = account_key
            base_uri = urlparse(uri).netloc

    if annotator and annotator._connection_available():
        annotator.sync_external_storage(
            uri=base_uri,
            config=config,
            dataset=dataset,
        )
    else:
        raise StackComponentInterfaceError("No active annotator.")
