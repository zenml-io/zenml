# zenml.integrations.whylogs package

## Subpackages

* [zenml.integrations.whylogs.data_validators package](zenml.integrations.whylogs.data_validators.md)
  * [Submodules](zenml.integrations.whylogs.data_validators.md#submodules)
  * [zenml.integrations.whylogs.data_validators.whylogs_data_validator module](zenml.integrations.whylogs.data_validators.md#zenml-integrations-whylogs-data-validators-whylogs-data-validator-module)
  * [Module contents](zenml.integrations.whylogs.data_validators.md#module-contents)
* [zenml.integrations.whylogs.flavors package](zenml.integrations.whylogs.flavors.md)
  * [Submodules](zenml.integrations.whylogs.flavors.md#submodules)
  * [zenml.integrations.whylogs.flavors.whylogs_data_validator_flavor module](zenml.integrations.whylogs.flavors.md#zenml-integrations-whylogs-flavors-whylogs-data-validator-flavor-module)
  * [Module contents](zenml.integrations.whylogs.flavors.md#module-contents)
* [zenml.integrations.whylogs.materializers package](zenml.integrations.whylogs.materializers.md)
  * [Submodules](zenml.integrations.whylogs.materializers.md#submodules)
  * [zenml.integrations.whylogs.materializers.whylogs_materializer module](zenml.integrations.whylogs.materializers.md#zenml-integrations-whylogs-materializers-whylogs-materializer-module)
  * [Module contents](zenml.integrations.whylogs.materializers.md#module-contents)
* [zenml.integrations.whylogs.secret_schemas package](zenml.integrations.whylogs.secret_schemas.md)
  * [Submodules](zenml.integrations.whylogs.secret_schemas.md#submodules)
  * [zenml.integrations.whylogs.secret_schemas.whylabs_secret_schema module](zenml.integrations.whylogs.secret_schemas.md#module-zenml.integrations.whylogs.secret_schemas.whylabs_secret_schema)
    * [`WhylabsSecretSchema`](zenml.integrations.whylogs.secret_schemas.md#zenml.integrations.whylogs.secret_schemas.whylabs_secret_schema.WhylabsSecretSchema)
      * [`WhylabsSecretSchema.model_computed_fields`](zenml.integrations.whylogs.secret_schemas.md#zenml.integrations.whylogs.secret_schemas.whylabs_secret_schema.WhylabsSecretSchema.model_computed_fields)
      * [`WhylabsSecretSchema.model_config`](zenml.integrations.whylogs.secret_schemas.md#zenml.integrations.whylogs.secret_schemas.whylabs_secret_schema.WhylabsSecretSchema.model_config)
      * [`WhylabsSecretSchema.model_fields`](zenml.integrations.whylogs.secret_schemas.md#zenml.integrations.whylogs.secret_schemas.whylabs_secret_schema.WhylabsSecretSchema.model_fields)
      * [`WhylabsSecretSchema.whylabs_api_key`](zenml.integrations.whylogs.secret_schemas.md#zenml.integrations.whylogs.secret_schemas.whylabs_secret_schema.WhylabsSecretSchema.whylabs_api_key)
      * [`WhylabsSecretSchema.whylabs_default_dataset_id`](zenml.integrations.whylogs.secret_schemas.md#zenml.integrations.whylogs.secret_schemas.whylabs_secret_schema.WhylabsSecretSchema.whylabs_default_dataset_id)
      * [`WhylabsSecretSchema.whylabs_default_org_id`](zenml.integrations.whylogs.secret_schemas.md#zenml.integrations.whylogs.secret_schemas.whylabs_secret_schema.WhylabsSecretSchema.whylabs_default_org_id)
  * [Module contents](zenml.integrations.whylogs.secret_schemas.md#module-zenml.integrations.whylogs.secret_schemas)
    * [`WhylabsSecretSchema`](zenml.integrations.whylogs.secret_schemas.md#zenml.integrations.whylogs.secret_schemas.WhylabsSecretSchema)
      * [`WhylabsSecretSchema.model_computed_fields`](zenml.integrations.whylogs.secret_schemas.md#zenml.integrations.whylogs.secret_schemas.WhylabsSecretSchema.model_computed_fields)
      * [`WhylabsSecretSchema.model_config`](zenml.integrations.whylogs.secret_schemas.md#zenml.integrations.whylogs.secret_schemas.WhylabsSecretSchema.model_config)
      * [`WhylabsSecretSchema.model_fields`](zenml.integrations.whylogs.secret_schemas.md#zenml.integrations.whylogs.secret_schemas.WhylabsSecretSchema.model_fields)
      * [`WhylabsSecretSchema.whylabs_api_key`](zenml.integrations.whylogs.secret_schemas.md#zenml.integrations.whylogs.secret_schemas.WhylabsSecretSchema.whylabs_api_key)
      * [`WhylabsSecretSchema.whylabs_default_dataset_id`](zenml.integrations.whylogs.secret_schemas.md#zenml.integrations.whylogs.secret_schemas.WhylabsSecretSchema.whylabs_default_dataset_id)
      * [`WhylabsSecretSchema.whylabs_default_org_id`](zenml.integrations.whylogs.secret_schemas.md#zenml.integrations.whylogs.secret_schemas.WhylabsSecretSchema.whylabs_default_org_id)
* [zenml.integrations.whylogs.steps package](zenml.integrations.whylogs.steps.md)
  * [Submodules](zenml.integrations.whylogs.steps.md#submodules)
  * [zenml.integrations.whylogs.steps.whylogs_profiler module](zenml.integrations.whylogs.steps.md#zenml-integrations-whylogs-steps-whylogs-profiler-module)
  * [Module contents](zenml.integrations.whylogs.steps.md#module-contents)

## Submodules

## zenml.integrations.whylogs.constants module

Whylogs integration constants.

## Module contents

Initialization of the whylogs integration.

### *class* zenml.integrations.whylogs.WhylogsIntegration

Bases: [`Integration`](zenml.integrations.md#zenml.integrations.integration.Integration)

Definition of [whylogs]([https://github.com/whylabs/whylogs](https://github.com/whylabs/whylogs)) integration for ZenML.

#### NAME *= 'whylogs'*

#### REQUIREMENTS *: List[str]* *= ['whylogs[viz]~=1.0.5', 'whylogs[whylabs]~=1.0.5']*

#### REQUIREMENTS_IGNORED_ON_UNINSTALL *: List[str]* *= ['pandas']*

#### *classmethod* activate() → None

Activates the integration.

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
