# zenml.integrations.great_expectations package

## Subpackages

* [zenml.integrations.great_expectations.data_validators package](zenml.integrations.great_expectations.data_validators.md)
  * [Submodules](zenml.integrations.great_expectations.data_validators.md#submodules)
  * [zenml.integrations.great_expectations.data_validators.ge_data_validator module](zenml.integrations.great_expectations.data_validators.md#zenml-integrations-great-expectations-data-validators-ge-data-validator-module)
  * [Module contents](zenml.integrations.great_expectations.data_validators.md#module-contents)
* [zenml.integrations.great_expectations.flavors package](zenml.integrations.great_expectations.flavors.md)
  * [Submodules](zenml.integrations.great_expectations.flavors.md#submodules)
  * [zenml.integrations.great_expectations.flavors.great_expectations_data_validator_flavor module](zenml.integrations.great_expectations.flavors.md#zenml-integrations-great-expectations-flavors-great-expectations-data-validator-flavor-module)
  * [Module contents](zenml.integrations.great_expectations.flavors.md#module-contents)
* [zenml.integrations.great_expectations.materializers package](zenml.integrations.great_expectations.materializers.md)
  * [Submodules](zenml.integrations.great_expectations.materializers.md#submodules)
  * [zenml.integrations.great_expectations.materializers.ge_materializer module](zenml.integrations.great_expectations.materializers.md#zenml-integrations-great-expectations-materializers-ge-materializer-module)
  * [Module contents](zenml.integrations.great_expectations.materializers.md#module-contents)
* [zenml.integrations.great_expectations.steps package](zenml.integrations.great_expectations.steps.md)
  * [Submodules](zenml.integrations.great_expectations.steps.md#submodules)
  * [zenml.integrations.great_expectations.steps.ge_profiler module](zenml.integrations.great_expectations.steps.md#zenml-integrations-great-expectations-steps-ge-profiler-module)
  * [zenml.integrations.great_expectations.steps.ge_validator module](zenml.integrations.great_expectations.steps.md#zenml-integrations-great-expectations-steps-ge-validator-module)
  * [Module contents](zenml.integrations.great_expectations.steps.md#module-contents)

## Submodules

## zenml.integrations.great_expectations.ge_store_backend module

## zenml.integrations.great_expectations.test_gx module

## zenml.integrations.great_expectations.utils module

## Module contents

Great Expectation integration for ZenML.

The Great Expectations integration enables you to use Great Expectations as a
way of profiling and validating your data.

### *class* zenml.integrations.great_expectations.GreatExpectationsIntegration

Bases: [`Integration`](zenml.integrations.md#zenml.integrations.integration.Integration)

Definition of Great Expectations integration for ZenML.

#### NAME *= 'great_expectations'*

#### REQUIREMENTS *: List[str]* *= ['great-expectations>=0.17.15,<1.0']*

#### REQUIREMENTS_IGNORED_ON_UNINSTALL *: List[str]* *= ['pandas']*

#### *classmethod* activate() → None

Activate the Great Expectations integration.

#### *classmethod* flavors() → List[Type[[Flavor](zenml.stack.md#zenml.stack.flavor.Flavor)]]

Declare the stack component flavors for the Great Expectations integration.

Returns:
: List of stack component flavors for this integration.

#### *classmethod* get_requirements(target_os: str | None = None) → List[str]

Method to get the requirements for the integration.

Args:
: target_os: The target operating system to get the requirements for.

Returns:
: A list of requirements.
