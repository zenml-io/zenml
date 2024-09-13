# zenml.integrations.deepchecks package

## Subpackages

* [zenml.integrations.deepchecks.data_validators package](zenml.integrations.deepchecks.data_validators.md)
  * [Submodules](zenml.integrations.deepchecks.data_validators.md#submodules)
  * [zenml.integrations.deepchecks.data_validators.deepchecks_data_validator module](zenml.integrations.deepchecks.data_validators.md#zenml-integrations-deepchecks-data-validators-deepchecks-data-validator-module)
  * [zenml.integrations.deepchecks.data_validators.test_pipeline module](zenml.integrations.deepchecks.data_validators.md#zenml-integrations-deepchecks-data-validators-test-pipeline-module)
  * [Module contents](zenml.integrations.deepchecks.data_validators.md#module-contents)
* [zenml.integrations.deepchecks.flavors package](zenml.integrations.deepchecks.flavors.md)
  * [Submodules](zenml.integrations.deepchecks.flavors.md#submodules)
  * [zenml.integrations.deepchecks.flavors.deepchecks_data_validator_flavor module](zenml.integrations.deepchecks.flavors.md#module-zenml.integrations.deepchecks.flavors.deepchecks_data_validator_flavor)
    * [`DeepchecksDataValidatorFlavor`](zenml.integrations.deepchecks.flavors.md#zenml.integrations.deepchecks.flavors.deepchecks_data_validator_flavor.DeepchecksDataValidatorFlavor)
      * [`DeepchecksDataValidatorFlavor.docs_url`](zenml.integrations.deepchecks.flavors.md#zenml.integrations.deepchecks.flavors.deepchecks_data_validator_flavor.DeepchecksDataValidatorFlavor.docs_url)
      * [`DeepchecksDataValidatorFlavor.implementation_class`](zenml.integrations.deepchecks.flavors.md#zenml.integrations.deepchecks.flavors.deepchecks_data_validator_flavor.DeepchecksDataValidatorFlavor.implementation_class)
      * [`DeepchecksDataValidatorFlavor.logo_url`](zenml.integrations.deepchecks.flavors.md#zenml.integrations.deepchecks.flavors.deepchecks_data_validator_flavor.DeepchecksDataValidatorFlavor.logo_url)
      * [`DeepchecksDataValidatorFlavor.name`](zenml.integrations.deepchecks.flavors.md#zenml.integrations.deepchecks.flavors.deepchecks_data_validator_flavor.DeepchecksDataValidatorFlavor.name)
      * [`DeepchecksDataValidatorFlavor.sdk_docs_url`](zenml.integrations.deepchecks.flavors.md#zenml.integrations.deepchecks.flavors.deepchecks_data_validator_flavor.DeepchecksDataValidatorFlavor.sdk_docs_url)
  * [Module contents](zenml.integrations.deepchecks.flavors.md#module-zenml.integrations.deepchecks.flavors)
    * [`DeepchecksDataValidatorFlavor`](zenml.integrations.deepchecks.flavors.md#zenml.integrations.deepchecks.flavors.DeepchecksDataValidatorFlavor)
      * [`DeepchecksDataValidatorFlavor.docs_url`](zenml.integrations.deepchecks.flavors.md#zenml.integrations.deepchecks.flavors.DeepchecksDataValidatorFlavor.docs_url)
      * [`DeepchecksDataValidatorFlavor.implementation_class`](zenml.integrations.deepchecks.flavors.md#zenml.integrations.deepchecks.flavors.DeepchecksDataValidatorFlavor.implementation_class)
      * [`DeepchecksDataValidatorFlavor.logo_url`](zenml.integrations.deepchecks.flavors.md#zenml.integrations.deepchecks.flavors.DeepchecksDataValidatorFlavor.logo_url)
      * [`DeepchecksDataValidatorFlavor.name`](zenml.integrations.deepchecks.flavors.md#zenml.integrations.deepchecks.flavors.DeepchecksDataValidatorFlavor.name)
      * [`DeepchecksDataValidatorFlavor.sdk_docs_url`](zenml.integrations.deepchecks.flavors.md#zenml.integrations.deepchecks.flavors.DeepchecksDataValidatorFlavor.sdk_docs_url)
* [zenml.integrations.deepchecks.materializers package](zenml.integrations.deepchecks.materializers.md)
  * [Submodules](zenml.integrations.deepchecks.materializers.md#submodules)
  * [zenml.integrations.deepchecks.materializers.deepchecks_dataset_materializer module](zenml.integrations.deepchecks.materializers.md#zenml-integrations-deepchecks-materializers-deepchecks-dataset-materializer-module)
  * [zenml.integrations.deepchecks.materializers.deepchecks_results_materializer module](zenml.integrations.deepchecks.materializers.md#zenml-integrations-deepchecks-materializers-deepchecks-results-materializer-module)
  * [Module contents](zenml.integrations.deepchecks.materializers.md#module-contents)
* [zenml.integrations.deepchecks.steps package](zenml.integrations.deepchecks.steps.md)
  * [Submodules](zenml.integrations.deepchecks.steps.md#submodules)
  * [zenml.integrations.deepchecks.steps.deepchecks_data_drift module](zenml.integrations.deepchecks.steps.md#zenml-integrations-deepchecks-steps-deepchecks-data-drift-module)
  * [zenml.integrations.deepchecks.steps.deepchecks_data_integrity module](zenml.integrations.deepchecks.steps.md#zenml-integrations-deepchecks-steps-deepchecks-data-integrity-module)
  * [zenml.integrations.deepchecks.steps.deepchecks_model_drift module](zenml.integrations.deepchecks.steps.md#zenml-integrations-deepchecks-steps-deepchecks-model-drift-module)
  * [zenml.integrations.deepchecks.steps.deepchecks_model_validation module](zenml.integrations.deepchecks.steps.md#zenml-integrations-deepchecks-steps-deepchecks-model-validation-module)
  * [Module contents](zenml.integrations.deepchecks.steps.md#module-contents)

## Submodules

## zenml.integrations.deepchecks.validation_checks module

## Module contents

Deepchecks integration for ZenML.

The Deepchecks integration provides a way to validate your data in your
pipelines. It includes a way to detect data anomalies and define checks to
ensure quality of data.

The integration includes custom materializers to store and visualize Deepchecks
SuiteResults.

### *class* zenml.integrations.deepchecks.DeepchecksIntegration

Bases: [`Integration`](zenml.integrations.md#zenml.integrations.integration.Integration)

Definition of [Deepchecks]([https://github.com/deepchecks/deepchecks](https://github.com/deepchecks/deepchecks)) integration for ZenML.

#### APT_PACKAGES *: List[str]* *= ['ffmpeg', 'libsm6', 'libxext6']*

#### NAME *= 'deepchecks'*

#### REQUIREMENTS *: List[str]* *= ['deepchecks[vision]>=0.18.0', 'torchvision>=0.14.0', 'opencv-python==4.5.5.64', 'opencv-python-headless==4.5.5.64', 'tenacity!=8.4.0', 'pandas<2.2.0']*

#### REQUIREMENTS_IGNORED_ON_UNINSTALL *: List[str]* *= ['pandas', 'torchvision', 'tenacity']*

#### *classmethod* activate() → None

Activate the Deepchecks integration.

#### *classmethod* flavors() → List[Type[[Flavor](zenml.stack.md#zenml.stack.flavor.Flavor)]]

Declare the stack component flavors for the Deepchecks integration.

Returns:
: List of stack component flavors for this integration.

#### *classmethod* get_requirements(target_os: str | None = None) → List[str]

Method to get the requirements for the integration.

Args:
: target_os: The target operating system to get the requirements for.

Returns:
: A list of requirements.
