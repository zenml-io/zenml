from zenml.integrations.label_studio.label_config_generators import (
    generate_image_classification_label_config,
)
from zenml.integrations.label_studio.steps import (
    LabelStudioDatasetRegistrationConfig,
    get_or_create_dataset,
)

LABELS = ["aria", "not_aria"]

label_config, _ = generate_image_classification_label_config(LABELS)

label_studio_registration_config = LabelStudioDatasetRegistrationConfig(
    label_config=label_config,
    dataset_name="aria_detector",
)

get_or_create_the_dataset = get_or_create_dataset(
    label_studio_registration_config
)
