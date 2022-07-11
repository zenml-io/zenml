import glob
import os
import tempfile
from typing import Any, Dict, List

from fastai.learner import Learner
from fastai.vision.all import *
from huggingface_hub import from_pretrained_fastai
from PIL import Image

from examples.annotation_label_studio.materializers import (
    FastaiLearnerMaterializer,
    PillowImageMaterializer,
)
from zenml.integrations.label_studio.label_config_generators import (
    generate_image_classification_label_config,
)
from zenml.integrations.label_studio.label_studio_utils import download_image
from zenml.integrations.label_studio.steps import (
    LabelStudioDatasetRegistrationConfig,
    LabelStudioDatasetSyncConfig,
    get_labeled_data,
    get_or_create_dataset,
    sync_new_data_to_label_studio,
)
from zenml.logger import get_logger
from zenml.pipelines import pipeline
from zenml.steps import Output, step
from zenml.steps.step_context import StepContext

LOCAL_IMAGE_FILES = "./assets/images/"

logger = get_logger(__name__)


label_config, label_config_type = generate_image_classification_label_config(
    ["cat", "dog"]
)

label_studio_registration_config = LabelStudioDatasetRegistrationConfig(
    label_config=label_config,
    dataset_name="catvsdog",
)

IMAGE_REGEX_FILTER = ".*(jpe?g|png)"

zenml_azure_artifact_store_sync_config = LabelStudioDatasetSyncConfig(
    storage_type="azure",
    label_config_type=label_config_type,
    regex_filter=IMAGE_REGEX_FILTER,
)

zenml_gcs_artifact_store_sync_config = LabelStudioDatasetSyncConfig(
    storage_type="gcs",
    label_config_type=label_config_type,
    regex_filter=IMAGE_REGEX_FILTER,
)

zenml_s3_artifact_store_sync_config = LabelStudioDatasetSyncConfig(
    storage_type="s3",
    label_config_type=label_config_type,
    regex_filter=IMAGE_REGEX_FILTER,
    region_name="eu-west-1",  # change this to your closest region
)


get_or_create_the_dataset = get_or_create_dataset(
    label_studio_registration_config
)


@step(enable_cache=True)
def load_image_data(context: StepContext) -> Output(images=Dict, uri=str):
    """Gets images from a cloud artifact store directory."""
    image_files = glob.glob(f"{LOCAL_IMAGE_FILES}/*.jpeg")
    return {
        os.path.basename(image_file): Image.open(image_file)
        for image_file in image_files
    }, context.get_output_artifact_uri("images")


azure_data_sync = sync_new_data_to_label_studio(
    config=zenml_azure_artifact_store_sync_config,
)

gcs_data_sync = sync_new_data_to_label_studio(
    config=zenml_gcs_artifact_store_sync_config,
)

s3_data_sync = sync_new_data_to_label_studio(
    config=zenml_s3_artifact_store_sync_config,
)


@step
def convert_annotation(
    label_studio_annotations: List[Dict[Any, Any]]
) -> Output(image_urls=List, image_labels=List,):
    """Converts the annotation from Label Studio to a dictionary."""
    image_urls = [
        annotation["data"]["image"] for annotation in label_studio_annotations
    ]

    labels = [
        {
            annotation["data"]["image"]: annotation["annotations"][0]["result"][
                0
            ]["value"]["choices"][0]
        }
        for annotation in label_studio_annotations
    ]
    return image_urls, labels


def is_cat(x):
    # NEEDED FOR FASTAI MODEL IMPORT (when / if we use it)
    # return labels[x] == "cat"
    return True


@step(enable_cache=True)
def model_loader() -> Learner:
    return from_pretrained_fastai("fastai/cat_or_dog")


@step
def fine_tuning_step(
    old_model: Learner,
    training_images: List[str],
    labels: List[Dict[str, str]],
    context: StepContext,
) -> Learner:
    with tempfile.TemporaryDirectory() as temp_dir:
        for url in training_images:
            download_image(url, temp_dir.name)

        training_images = glob.glob(f"{temp_dir.name}/*{IMAGE_REGEX_FILTER}")

        dls = ImageDataLoaders.from_name_func(
            temp_dir,
            get_image_files(temp_dir),
            valid_pct=0.2,
            seed=42,
            label_func=is_cat,
            item_tfms=Resize(224),
        )

        learn = vision_learner(dls, old_model, metrics=error_rate)
        learn.fine_tune(1)


@step(enable_cache=True)
def batch_inference(image_dict: Dict, model: Learner) -> List:
    """Execute batch inference on some images.

    Returns a list of predictions compatible with Label Studio.
    """
    # TODO: Actually implement the batch inference step
    # below are just dummy values
    return [
        {
            "filename": image_name,
            "result": [
                {
                    "value": {"choices": ["cat"]},
                    "from_name": "choice",
                    "to_name": "image",
                    "type": "choices",
                    "origin": "manual",
                },
            ],
        }
        for image_name in image_dict.keys()
    ]


@pipeline
def continuous_training_pipeline(
    get_or_create_dataset,
    get_labeled_data,
    annotation_converter,
    get_model,
    # fine_tuner,
    images_loader,
    batch_inference,
    data_syncer,
) -> None:
    dataset_name = get_or_create_dataset()
    # TODO: get any *fresh* labeled data for our dataset
    # Use an option to pass in filters (or use the 'meta' field)
    new_annotations = get_labeled_data(dataset_name)

    training_images, training_annotations = annotation_converter(
        new_annotations
    )
    model = get_model()
    # new_model = fine_tuner(model, training_images, training_annotations)
    # model = compare_and_validate(model, new_model)

    # TODO: POSSIBLY SPLIT PIPELINE HERE INTO NEW PIPELINE??
    # uploads some new local images to the ZenML artifact store
    new_images_dict, new_images_uri = images_loader()

    preds = batch_inference(new_images_dict, model)

    # sync from zenml artifact store to label studio (azure blob storage)
    data_syncer(
        uri=new_images_uri, dataset_name=dataset_name, predictions=preds
    )


if __name__ == "__main__":
    ct_pipeline = continuous_training_pipeline(
        get_or_create_the_dataset,
        get_labeled_data(),
        convert_annotation(),
        model_loader().with_return_materializers(FastaiLearnerMaterializer),
        # fine_tuning_step().with_return_materializers(
        #     FastaiLearnerMaterializer
        # ),
        load_image_data().with_return_materializers(
            {"images": PillowImageMaterializer}
        ),
        batch_inference(),
        azure_data_sync,
    )

    ct_pipeline.run()
