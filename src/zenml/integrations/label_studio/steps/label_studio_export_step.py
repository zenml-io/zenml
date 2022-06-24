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

from typing import Dict, List, Optional

from zenml.artifacts.data_artifact import DataArtifact
from zenml.logger import get_logger
from zenml.steps import BaseStep, BaseStepConfig, StepContext

logger = get_logger(__name__)


class AnnotationInputArtifact(DataArtifact):
    """Annotation input data artifact."""

    predictions: Optional[Dict[str]]


class ImageClassificationInputArtifact(AnnotationInputArtifact):
    """Image classification input artifact."""

    images_dir: str
    labels: List[str]


class AnnotationOutputArtifact(DataArtifact):
    """Annotation output data artifact."""


class LabelStudioExportStepConfig(BaseStepConfig):
    """Step config definition for Label studio export step."""


class LabelStudioRecords(DataArtifact):
    """Label studio records data artifact."""


class LabelStudioExportStep(BaseStep):
    """Exports data in a format that Label Studio can understand."""

    def entrypoint(
        self,
        data: AnnotationInputArtifact,
        config: LabelStudioExportStepConfig,
        context: StepContext,
    ) -> Optional[LabelStudioRecords]:
        """Main entrypoint function for the Label Studio export step."""
        annotator = context.stack.annotator
        if annotator and annotator._connection_available():
            # it "converts" from DataSource to a format that the
            # data labelling tool supports
            exported_data = annotator.export(data)
            # tag, label, mark the exported data as an object that can be
            # visualized and edited with Label Studio (?)
            # annotator.register_new_dataset_for_labelling(exported_data.name, tags...)
            return exported_data  # or just the ID/tag
        else:
            logger.warning("No active annotator.")


def label_studio_export_step() -> LabelStudioExportStep:
    """Shortcut function to create a new instance of the export step.

    Combines the config and the step classes to create a new instance of the
    step.
    """
    # TODO: convenience step to be implemented later
