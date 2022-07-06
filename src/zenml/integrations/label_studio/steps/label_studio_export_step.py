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
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from zenml.enums import AnnotationTasks
from zenml.exceptions import StackComponentInterfaceError
from zenml.logger import get_logger
from zenml.steps import BaseStepConfig, StepContext, step

logger = get_logger(__name__)

TASK_TO_FILENAME_REFERENCE_MAPPING = {
    AnnotationTasks.IMAGE_CLASSIFICATION: "image",
    AnnotationTasks.OBJECT_DETECTION_BOUNDING_BOXES: "image",
}


def generate_image_classification_label_config(
    labels: List[str],
) -> Tuple[str, str]:
    """Generates a Label Studio label config for image classification.

    This is based on the basig config example shown at https://labelstud.io/templates/image_classification.html.
    """
    label_config_type = AnnotationTasks.IMAGE_CLASSIFICATION

    label_config_start = f"""<View>
    <Image name="image" value="$image"/>
    <Choices name="choice" toName="image">
    """
    label_config_choices = "".join(
        f"<Choice value='{label}' />\n" for label in labels
    )
    label_config_end = "</Choices>\n</View>"

    return (
        label_config_start + label_config_choices + label_config_end,
        label_config_type,
    )


def generate_basic_object_detection_bounding_boxes_label_config(
    labels: List[str],
) -> Tuple[str, str]:
    """Generates a Label Studio config for object detection with bounding boxes.

    This is based on the basic config example shown at https://labelstud.io/templates/image_bbox.html.
    """
    label_config_type = AnnotationTasks.OBJECT_DETECTION_BOUNDING_BOXES

    label_config_start = f"""<View>
    <Image name="image" value="$image"/>
    <RectangleLabels name="label" toName="image">
    """
    label_config_choices = "".join(
        f"<Label value='{label}' />\n" for label in labels
    )
    label_config_end = "</RectangleLabels>\n</View>"

    return (
        label_config_start + label_config_choices + label_config_end,
        label_config_type,
    )


class LabelStudioDatasetRegistrationConfig(BaseStepConfig):
    label_config: str
    dataset_name: str


class LabelStudioDatasetSyncConfig(BaseStepConfig):
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
    region_name: Optional[str]
    s3_endpoint: Optional[str]


@step
def get_or_create_dataset(
    config: LabelStudioDatasetRegistrationConfig,
    context: StepContext,
) -> int:
    """Gets preexisting dataset or creates a new one."""
    annotator = context.stack.annotator
    if annotator and annotator._connection_available():
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
            registered_dataset = annotator.register_dataset_for_annotation(
                config
            )
        elif preexisting_dataset_list:
            return preexisting_dataset_list[0].get_params()["id"]
        else:
            raise StackComponentInterfaceError("No active annotator.")

        return registered_dataset.get_params()["id"]
    else:
        raise StackComponentInterfaceError("No active annotator.")


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


def convert_pred_filenames_to_task_ids(
    preds: List[Dict[str, Any]],
    tasks: List[Dict[str, Any]],
    filename_reference: str,
) -> List[Dict[str, Any]]:
    """Converts a list of predictions from local file references to task id."""
    filename_id_mapping = {
        os.path.basename(urlparse(task["data"][filename_reference]).path): task[
            "id"
        ]
        for task in tasks
    }

    return [
        {
            "task": int(
                filename_id_mapping[os.path.basename(pred["filename"])]
            ),
            "result": pred["result"],
        }
        for pred in preds
    ]


@step(enable_cache=False)
def sync_new_data_to_label_studio(
    uri: str,
    dataset_id: int,
    predictions: List[Dict[str, Any]],
    config: LabelStudioDatasetSyncConfig,
    context: StepContext,
) -> None:
    """Syncs new data to Label Studio."""
    annotator = context.stack.annotator
    # TODO: check that annotator is connected before querying it
    dataset = annotator.get_dataset(dataset_id)
    artifact_store = context.stack.artifact_store
    if not uri.startswith(artifact_store.path):
        raise ValueError(
            "ZenML only currently supports syncing data passed from other ZenML steps and via the Artifact Store."
        )

    if config.storage_type == "azure":
        account_name, account_key = get_azure_credentials()
        config.azure_account_name = account_name
        config.azure_account_key = account_key
        # removes the initial backslash from the prefix attribute by slicing
        config.prefix = urlparse(uri).path[1:]
        base_uri = urlparse(uri).netloc
    elif config.storage_type == "gcp":
        return NotImplementedError("GCP storage not yet implemented.")
    elif config.storage_type == "s3":
        return NotImplementedError("S3 storage not yet implemented.")

    if annotator and annotator._connection_available():
        # TODO: get existing (CHECK!) or create the sync connection
        annotator.connect_and_sync_external_storage(
            uri=base_uri,
            config=config,
            dataset=dataset,
        )
        if predictions:
            filename_reference = TASK_TO_FILENAME_REFERENCE_MAPPING[
                config.label_config_type
            ]
            preds_with_task_ids = convert_pred_filenames_to_task_ids(
                predictions, dataset.tasks, filename_reference
            )
            # TODO: filter out any predictions that exist + have already been
            # made (maybe?). Only pass in preds for tasks without pre-annotations.
            dataset.create_predictions(preds_with_task_ids)
    else:
        raise StackComponentInterfaceError("No active annotator.")


# def get_new_tasks(tasks_before_sync, tasks_after_sync) -> List[Dict]:
#     """Returns a list of tasks that are new since the last sync."""
#     return [task for task in tasks_after_sync if task not in tasks_before_sync]


# def get_filename(url: str) -> str:
#     """Returns the filename of a url."""
#     return urlparse(url).path.split("/")[-1]


# def get_transformed_azure_url(url: str, scheme: str) -> str:
#     """Returns the transformed url for Azure."""
#     new_scheme_url = url.replace(scheme, "azure-blob")
#     return f"{urlparse(new_scheme_url).scheme}://{urlparse(new_scheme_url).netloc}{urlparse(new_scheme_url).path}"


# def switch_local_urls_for_cloud_urls(
#     predictions: List[Dict], new_tasks: List[Dict]
# ) -> List[Dict]:
#     """Switches local urls for cloud urls."""
#     if new_tasks:
#         uri_prefix = urlparse(new_tasks[0]["data"]["image"]).scheme
#     image_name_mapping = {
#         get_filename(task["data"]["image"]): get_transformed_azure_url(
#             task["data"]["image"], uri_prefix
#         )
#         for task in new_tasks
#     }
#     for prediction in predictions:
#         prediction["data"]["image"] = image_name_mapping[
#             os.path.basename(prediction["data"]["image"])
#         ]
#     return predictions
