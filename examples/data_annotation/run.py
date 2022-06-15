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

from pathlib import Path

from huggingface_hub import from_pretrained_fastai
from fastai.data.core import DataLoaders
from fastai.learner import Learner
from fastai.vision.all import *

from zenml.cli import utils as cli_utils
from zenml.pipelines import pipeline
from zenml.steps import StepContext, step

CAT_IMAGES_PATH = "data/images/"


@step
def import_inference_data() -> DataLoaders:
    data_block = DataBlock(
        blocks=(ImageBlock, CategoryBlock),
        get_items=get_image_files,
        splitter=RandomSubsetSplitter(train_sz=0, val_sz=1),
        item_tfms=Resize(224),
    )
    return data_block.dataloaders(CAT_IMAGES_PATH, bs=8)


@step
def import_model() -> Learner:
    return from_pretrained_fastai("strickvl/redaction-classifier-fastai")


@step
def annotate_finetune(
    context: StepContext,
    model,
):
    try:
        annotator = context.stack.annotator
    except AttributeError:
        cli_utils.error("No annotator found in stack.")

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


if __name__ == "__main__":
    annotation_pipeline.run(
        import_inference_data, import_model, annotate_finetune
    )
