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


from typing import List, Optional

from zenml.exceptions import StackComponentInterfaceError
from zenml.logger import get_logger
from zenml.steps import BaseStepConfig, StepContext, step

logger = get_logger(__name__)


IMAGE_CLASSIFICATION_LABEL_CONFIG = """
    <View>
    <Image name="image" value="$image"/>
    <Choices name="choice" toName="image">
        <Choice value="Mr Blupus"/>
        <Choice value="Other" />
    </Choices>
    </View>
    """


class LabelStudioDatasetSyncConfig(BaseStepConfig):
    label_config: str
    storage_type: str
    storage_name: str

    prefix: Optional[str] = None
    regex_filter: Optional[str] = "*.*"
    use_blob_urls: Optional[bool] = True
    presign: Optional[bool] = True
    presign_ttl: Optional[int] = 1
    description: Optional[str] = ""


@step
def get_or_create_dataset(
    config: LabelStudioDatasetSyncConfig,
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
    elif annotator and annotator._connection_available():
        registered_dataset = preexisting_dataset_list[0]
        annotator.sync_external_storage(config, registered_dataset)
    else:
        raise StackComponentInterfaceError("No active annotator.")

    return registered_dataset.get_params()["id"]


@step
def get_labeled_data(dataset_id: int, context: StepContext) -> List:
    """Gets labeled data from the dataset."""
    annotator = context.stack.annotator
    if annotator and annotator._connection_available():
        dataset = annotator.get_dataset(dataset_id)
        return dataset.get_labeled_tasks()
    else:
        raise StackComponentInterfaceError("No active annotator.")


@step
def sync_new_data_to_label_studio(
    uri: str,
    dataset_id: int,
    config: LabelStudioDatasetSyncConfig,
    context: StepContext,
) -> None:
    """Syncs new data to Label Studio."""
    annotator = context.stack.annotator
    dataset = annotator.get_dataset(dataset_id)
    if annotator and annotator._connection_available():
        annotator.sync_external_storage(
            config=LabelStudioDatasetSyncConfig, dataset=dataset
        )
    else:
        raise StackComponentInterfaceError("No active annotator.")
