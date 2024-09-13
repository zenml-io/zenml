# zenml.integrations.label_studio.label_config_generators package

## Submodules

## zenml.integrations.label_studio.label_config_generators.label_config_generators module

Implementation of label config generators for Label Studio.

### zenml.integrations.label_studio.label_config_generators.label_config_generators.generate_basic_object_detection_bounding_boxes_label_config(labels: List[str]) → Tuple[str, str]

Generates a Label Studio config for object detection with bounding boxes.

This is based on the basic config example shown at
[https://labelstud.io/templates/image_bbox.html](https://labelstud.io/templates/image_bbox.html).

Args:
: labels: A list of labels to be used in the label config.

Returns:
: A tuple of the generated label config and the label config type.

Raises:
: ValueError: If no labels are provided.

### zenml.integrations.label_studio.label_config_generators.label_config_generators.generate_basic_ocr_label_config(labels: List[str]) → Tuple[str, str]

Generates a Label Studio config for optical character recognition (OCR) labeling task.

This is based on the basic config example shown at
[https://labelstud.io/templates/optical_character_recognition.html](https://labelstud.io/templates/optical_character_recognition.html)

Args:
: labels: A list of labels to be used in the label config.

Returns:
: A tuple of the generated label config and the label config type.

Raises:
: ValueError: If no labels are provided.

### zenml.integrations.label_studio.label_config_generators.label_config_generators.generate_image_classification_label_config(labels: List[str]) → Tuple[str, str]

Generates a Label Studio label config for image classification.

This is based on the basic config example shown at
[https://labelstud.io/templates/image_classification.html](https://labelstud.io/templates/image_classification.html).

Args:
: labels: A list of labels to be used in the label config.

Returns:
: A tuple of the generated label config and the label config type.

Raises:
: ValueError: If no labels are provided.

### zenml.integrations.label_studio.label_config_generators.label_config_generators.generate_text_classification_label_config(labels: List[str]) → Tuple[str, str]

Generates a Label Studio label config for text classification.

This is based on the basic config example shown at
[https://labelstud.io/templates/sentiment_analysis.html](https://labelstud.io/templates/sentiment_analysis.html).

Args:
: labels: A list of labels to be used in the label config.

Returns:
: A tuple of the generated label config and the label config type.

Raises:
: ValueError: If no labels are provided.

## Module contents

Initialization of the Label Studio config generators submodule.

### zenml.integrations.label_studio.label_config_generators.generate_image_classification_label_config(labels: List[str]) → Tuple[str, str]

Generates a Label Studio label config for image classification.

This is based on the basic config example shown at
[https://labelstud.io/templates/image_classification.html](https://labelstud.io/templates/image_classification.html).

Args:
: labels: A list of labels to be used in the label config.

Returns:
: A tuple of the generated label config and the label config type.

Raises:
: ValueError: If no labels are provided.

### zenml.integrations.label_studio.label_config_generators.generate_text_classification_label_config(labels: List[str]) → Tuple[str, str]

Generates a Label Studio label config for text classification.

This is based on the basic config example shown at
[https://labelstud.io/templates/sentiment_analysis.html](https://labelstud.io/templates/sentiment_analysis.html).

Args:
: labels: A list of labels to be used in the label config.

Returns:
: A tuple of the generated label config and the label config type.

Raises:
: ValueError: If no labels are provided.
