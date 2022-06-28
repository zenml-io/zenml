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

# # --- we get new steps from the labeling tool integration to "export/extract" data
# @step(options={
# 		task: "classification",
# 		annotation_types: "images",
# 		input_format: "json",
# 		export_format: "coco",
# })
# def label_studio_export_data_for_labelling(data: DataSource, ...tags,) -> LabelStudioRecords
#    annotator = Repository().active_stack.annotator
#    # it "converts" from DataSource to a format that the
# 	 # data labelling tool supports
# 	 exported_data = annotator.export(data)
#    # tag, label, mark the exported data as an object that can be
#    # visualized and edited with Label Studio (?)
#    register_new_dataset_for_labelling(exported_data.name, tags...)
#    return exported_data # or just the ID/tag

from typing import Any, Dict, List, Optional

from zenml.artifacts.data_artifact import DataArtifact
from zenml.exceptions import StackComponentInterfaceError
from zenml.logger import get_logger
from zenml.steps import BaseStep, BaseStepConfig, Output, StepContext

logger = get_logger(__name__)


class AnnotationInputArtifact(DataArtifact):
    """Annotation input data artifact."""

    predictions: Optional[Dict[Any, Any]]


IMAGE_CLASSIFICATION_LABEL_CONFIG = """
    <View>
    <Image name="image" value="$image"/>
    <Choices name="choice" toName="image">
        <Choice value="Mr Blupus"/>
        <Choice value="Other" />
    </Choices>
    </View>
    """


class AzureDatasetCreationConfig(BaseStepConfig):
    """Step config definition for Azure."""

    label_config: str = IMAGE_CLASSIFICATION_LABEL_CONFIG
    storage_type: str

    dataset_name: str
    container_name: str
    prefix: Optional[str]
    regex_filter: Optional[str]
    use_blob_urls: Optional[bool] = True
    presign: Optional[bool] = True
    presign_ttl: Optional[int] = 1
    description: Optional[str]
    account_name: Optional[str]
    account_key: Optional[str]
    # project_sampling: Optional[ProjectSampling] = ProjectSampling.RANDOM


class LabelStudioDatasetCreationStep(BaseStep):
    """Creates a dataset based on data and labels passed in."""

    def entrypoint(
        self,
        # data: AnnotationInputArtifact,
        config: AzureDatasetCreationConfig,
        context: StepContext,
    ) -> Output(dataset_id=int, exported_dataset=List):
        """Main entrypoint function for the Label Studio export step."""
        annotator = context.stack.annotator
        if annotator and annotator._connection_available():
            registered_dataset_id = annotator.register_dataset_for_annotation(
                config
            )
            imported_tasks = annotator.get_unlabeled_data(registered_dataset_id)
            return registered_dataset_id, imported_tasks  # or just the ID/tag
        else:
            raise StackComponentInterfaceError("No active annotator.")


# def label_studio_export_step() -> LabelStudioExportStep:
#     """Shortcut function to create a new instance of the export step.

#     Combines the config and the step classes to create a new instance of the
#     step.
#     """
#     # TODO: convenience step to be implemented later
