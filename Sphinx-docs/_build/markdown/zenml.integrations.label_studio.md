# zenml.integrations.label_studio package

## Subpackages

* [zenml.integrations.label_studio.annotators package](zenml.integrations.label_studio.annotators.md)
  * [Submodules](zenml.integrations.label_studio.annotators.md#submodules)
  * [zenml.integrations.label_studio.annotators.label_studio_annotator module](zenml.integrations.label_studio.annotators.md#zenml-integrations-label-studio-annotators-label-studio-annotator-module)
  * [Module contents](zenml.integrations.label_studio.annotators.md#module-contents)
* [zenml.integrations.label_studio.flavors package](zenml.integrations.label_studio.flavors.md)
  * [Submodules](zenml.integrations.label_studio.flavors.md#submodules)
  * [zenml.integrations.label_studio.flavors.label_studio_annotator_flavor module](zenml.integrations.label_studio.flavors.md#zenml-integrations-label-studio-flavors-label-studio-annotator-flavor-module)
  * [Module contents](zenml.integrations.label_studio.flavors.md#module-contents)
* [zenml.integrations.label_studio.label_config_generators package](zenml.integrations.label_studio.label_config_generators.md)
  * [Submodules](zenml.integrations.label_studio.label_config_generators.md#submodules)
  * [zenml.integrations.label_studio.label_config_generators.label_config_generators module](zenml.integrations.label_studio.label_config_generators.md#module-zenml.integrations.label_studio.label_config_generators.label_config_generators)
    * [`generate_basic_object_detection_bounding_boxes_label_config()`](zenml.integrations.label_studio.label_config_generators.md#zenml.integrations.label_studio.label_config_generators.label_config_generators.generate_basic_object_detection_bounding_boxes_label_config)
    * [`generate_basic_ocr_label_config()`](zenml.integrations.label_studio.label_config_generators.md#zenml.integrations.label_studio.label_config_generators.label_config_generators.generate_basic_ocr_label_config)
    * [`generate_image_classification_label_config()`](zenml.integrations.label_studio.label_config_generators.md#zenml.integrations.label_studio.label_config_generators.label_config_generators.generate_image_classification_label_config)
    * [`generate_text_classification_label_config()`](zenml.integrations.label_studio.label_config_generators.md#zenml.integrations.label_studio.label_config_generators.label_config_generators.generate_text_classification_label_config)
  * [Module contents](zenml.integrations.label_studio.label_config_generators.md#module-zenml.integrations.label_studio.label_config_generators)
    * [`generate_image_classification_label_config()`](zenml.integrations.label_studio.label_config_generators.md#zenml.integrations.label_studio.label_config_generators.generate_image_classification_label_config)
    * [`generate_text_classification_label_config()`](zenml.integrations.label_studio.label_config_generators.md#zenml.integrations.label_studio.label_config_generators.generate_text_classification_label_config)
* [zenml.integrations.label_studio.steps package](zenml.integrations.label_studio.steps.md)
  * [Submodules](zenml.integrations.label_studio.steps.md#submodules)
  * [zenml.integrations.label_studio.steps.label_studio_standard_steps module](zenml.integrations.label_studio.steps.md#module-zenml.integrations.label_studio.steps.label_studio_standard_steps)
    * [`LabelStudioDatasetSyncParameters`](zenml.integrations.label_studio.steps.md#zenml.integrations.label_studio.steps.label_studio_standard_steps.LabelStudioDatasetSyncParameters)
      * [`LabelStudioDatasetSyncParameters.aws_access_key_id`](zenml.integrations.label_studio.steps.md#zenml.integrations.label_studio.steps.label_studio_standard_steps.LabelStudioDatasetSyncParameters.aws_access_key_id)
      * [`LabelStudioDatasetSyncParameters.aws_secret_access_key`](zenml.integrations.label_studio.steps.md#zenml.integrations.label_studio.steps.label_studio_standard_steps.LabelStudioDatasetSyncParameters.aws_secret_access_key)
      * [`LabelStudioDatasetSyncParameters.aws_session_token`](zenml.integrations.label_studio.steps.md#zenml.integrations.label_studio.steps.label_studio_standard_steps.LabelStudioDatasetSyncParameters.aws_session_token)
      * [`LabelStudioDatasetSyncParameters.azure_account_key`](zenml.integrations.label_studio.steps.md#zenml.integrations.label_studio.steps.label_studio_standard_steps.LabelStudioDatasetSyncParameters.azure_account_key)
      * [`LabelStudioDatasetSyncParameters.azure_account_name`](zenml.integrations.label_studio.steps.md#zenml.integrations.label_studio.steps.label_studio_standard_steps.LabelStudioDatasetSyncParameters.azure_account_name)
      * [`LabelStudioDatasetSyncParameters.description`](zenml.integrations.label_studio.steps.md#zenml.integrations.label_studio.steps.label_studio_standard_steps.LabelStudioDatasetSyncParameters.description)
      * [`LabelStudioDatasetSyncParameters.google_application_credentials`](zenml.integrations.label_studio.steps.md#zenml.integrations.label_studio.steps.label_studio_standard_steps.LabelStudioDatasetSyncParameters.google_application_credentials)
      * [`LabelStudioDatasetSyncParameters.label_config_type`](zenml.integrations.label_studio.steps.md#zenml.integrations.label_studio.steps.label_studio_standard_steps.LabelStudioDatasetSyncParameters.label_config_type)
      * [`LabelStudioDatasetSyncParameters.model_computed_fields`](zenml.integrations.label_studio.steps.md#zenml.integrations.label_studio.steps.label_studio_standard_steps.LabelStudioDatasetSyncParameters.model_computed_fields)
      * [`LabelStudioDatasetSyncParameters.model_config`](zenml.integrations.label_studio.steps.md#zenml.integrations.label_studio.steps.label_studio_standard_steps.LabelStudioDatasetSyncParameters.model_config)
      * [`LabelStudioDatasetSyncParameters.model_fields`](zenml.integrations.label_studio.steps.md#zenml.integrations.label_studio.steps.label_studio_standard_steps.LabelStudioDatasetSyncParameters.model_fields)
      * [`LabelStudioDatasetSyncParameters.prefix`](zenml.integrations.label_studio.steps.md#zenml.integrations.label_studio.steps.label_studio_standard_steps.LabelStudioDatasetSyncParameters.prefix)
      * [`LabelStudioDatasetSyncParameters.presign`](zenml.integrations.label_studio.steps.md#zenml.integrations.label_studio.steps.label_studio_standard_steps.LabelStudioDatasetSyncParameters.presign)
      * [`LabelStudioDatasetSyncParameters.presign_ttl`](zenml.integrations.label_studio.steps.md#zenml.integrations.label_studio.steps.label_studio_standard_steps.LabelStudioDatasetSyncParameters.presign_ttl)
      * [`LabelStudioDatasetSyncParameters.regex_filter`](zenml.integrations.label_studio.steps.md#zenml.integrations.label_studio.steps.label_studio_standard_steps.LabelStudioDatasetSyncParameters.regex_filter)
      * [`LabelStudioDatasetSyncParameters.s3_endpoint`](zenml.integrations.label_studio.steps.md#zenml.integrations.label_studio.steps.label_studio_standard_steps.LabelStudioDatasetSyncParameters.s3_endpoint)
      * [`LabelStudioDatasetSyncParameters.s3_region_name`](zenml.integrations.label_studio.steps.md#zenml.integrations.label_studio.steps.label_studio_standard_steps.LabelStudioDatasetSyncParameters.s3_region_name)
      * [`LabelStudioDatasetSyncParameters.storage_type`](zenml.integrations.label_studio.steps.md#zenml.integrations.label_studio.steps.label_studio_standard_steps.LabelStudioDatasetSyncParameters.storage_type)
      * [`LabelStudioDatasetSyncParameters.use_blob_urls`](zenml.integrations.label_studio.steps.md#zenml.integrations.label_studio.steps.label_studio_standard_steps.LabelStudioDatasetSyncParameters.use_blob_urls)
  * [Module contents](zenml.integrations.label_studio.steps.md#module-zenml.integrations.label_studio.steps)

## Submodules

## zenml.integrations.label_studio.label_studio_utils module

Utility functions for the Label Studio annotator integration.

### zenml.integrations.label_studio.label_studio_utils.clean_url(url: str) → str

Remove extraneous parts of the URL prior to mapping.

Removes the query and netloc parts of the URL, and strips the leading slash
from the path. For example, a string like
‘gs%3A//label-studio/load_image_data/images/fdbcd451-0c80-495c-a9c5-6b51776f5019/1/0/image_file.JPEG’
would become
label-studio/load_image_data/images/fdbcd451-0c80-495c-a9c5-6b51776f5019/1/0/image_file.JPEG.

Args:
: url: A URL string.

Returns:
: A cleaned URL string.

### zenml.integrations.label_studio.label_studio_utils.convert_pred_filenames_to_task_ids(preds: List[Dict[str, Any]], tasks: List[Dict[str, Any]]) → List[Dict[str, Any]]

Converts a list of predictions from local file references to task id.

Args:
: preds: List of predictions.
  tasks: List of tasks.

Returns:
: List of predictions using task ids as reference.

### zenml.integrations.label_studio.label_studio_utils.get_file_extension(path_str: str) → str

Return the file extension of the given filename.

Args:
: path_str: Path to the file.

Returns:
: File extension.

### zenml.integrations.label_studio.label_studio_utils.is_azure_url(url: str) → bool

Return whether the given URL is an Azure URL.

Args:
: url: URL to check.

Returns:
: True if the URL is an Azure URL, False otherwise.

### zenml.integrations.label_studio.label_studio_utils.is_gcs_url(url: str) → bool

Return whether the given URL is an GCS URL.

Args:
: url: URL to check.

Returns:
: True if the URL is an GCS URL, False otherwise.

### zenml.integrations.label_studio.label_studio_utils.is_s3_url(url: str) → bool

Return whether the given URL is an S3 URL.

Args:
: url: URL to check.

Returns:
: True if the URL is an S3 URL, False otherwise.

## Module contents

Initialization of the Label Studio integration.

### *class* zenml.integrations.label_studio.LabelStudioIntegration

Bases: [`Integration`](zenml.integrations.md#zenml.integrations.integration.Integration)

Definition of Label Studio integration for ZenML.

#### NAME *= 'label_studio'*

#### REQUIREMENTS *: List[str]* *= ['label-studio-sdk>=1.0.0']*

#### *classmethod* flavors() → List[Type[[Flavor](zenml.stack.md#zenml.stack.flavor.Flavor)]]

Declare the stack component flavors for the Label Studio integration.

Returns:
: List of stack component flavors for this integration.
