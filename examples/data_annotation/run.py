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

from zenml.cli import utils as cli_utils
from zenml.pipelines import pipeline
from zenml.steps import StepContext, step


@step
def import_inference_data() -> ImageList:
    pass


@step
def import_model():
    pass


@step
def batch_inference(
    context: StepContext,
    model,
):
    annotator = context.stack.annotator
    new_annotations = annotator.get_unannotated_artifacts()
    if new_annotations:
        annotator.annotate()
    else:
        cli_utils.declare("No unannotated artifacts found.")
        # finetune model using new data
        annotated_data = annotator.get_new_annotations()
        model.fit(annotated_data)


@pipeline
def annotation_pipeline(data_importer, model_importer, batch_inference):
    inference_data = data_importer()
    model = model_importer()
    batch_inference(model=model, data=inference_data)
