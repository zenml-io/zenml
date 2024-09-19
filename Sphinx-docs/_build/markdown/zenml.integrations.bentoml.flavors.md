# zenml.integrations.bentoml.flavors package

## Submodules

## zenml.integrations.bentoml.flavors.bentoml_model_deployer_flavor module

BentoML model deployer flavor.

### *class* zenml.integrations.bentoml.flavors.bentoml_model_deployer_flavor.BentoMLModelDeployerConfig(warn_about_plain_text_secrets: bool = False, \*, service_path: str = '')

Bases: [`BaseModelDeployerConfig`](zenml.model_deployers.md#zenml.model_deployers.base_model_deployer.BaseModelDeployerConfig)

Configuration for the BentoMLModelDeployer.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'service_path': FieldInfo(annotation=str, required=False, default='')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### service_path *: str*

### *class* zenml.integrations.bentoml.flavors.bentoml_model_deployer_flavor.BentoMLModelDeployerFlavor

Bases: [`BaseModelDeployerFlavor`](zenml.model_deployers.md#zenml.model_deployers.base_model_deployer.BaseModelDeployerFlavor)

Flavor for the BentoML model deployer.

#### *property* config_class *: Type[[BentoMLModelDeployerConfig](#zenml.integrations.bentoml.flavors.bentoml_model_deployer_flavor.BentoMLModelDeployerConfig)]*

Returns BentoMLModelDeployerConfig config class.

Returns:
: The config class.

#### *property* docs_url *: str | None*

A url to point at docs explaining this flavor.

Returns:
: A flavor docs url.

#### *property* implementation_class *: Type[BentoMLModelDeployer]*

Implementation class for this flavor.

Returns:
: The implementation class.

#### *property* logo_url *: str*

A url to represent the flavor in the dashboard.

Returns:
: The flavor logo.

#### *property* name *: str*

Name of the flavor.

Returns:
: Name of the flavor.

#### *property* sdk_docs_url *: str | None*

A url to point at SDK docs explaining this flavor.

Returns:
: A flavor SDK docs url.

## Module contents

BentoML integration flavors.

### *class* zenml.integrations.bentoml.flavors.BentoMLModelDeployerConfig(warn_about_plain_text_secrets: bool = False, \*, service_path: str = '')

Bases: [`BaseModelDeployerConfig`](zenml.model_deployers.md#zenml.model_deployers.base_model_deployer.BaseModelDeployerConfig)

Configuration for the BentoMLModelDeployer.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'service_path': FieldInfo(annotation=str, required=False, default='')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### service_path *: str*

### *class* zenml.integrations.bentoml.flavors.BentoMLModelDeployerFlavor

Bases: [`BaseModelDeployerFlavor`](zenml.model_deployers.md#zenml.model_deployers.base_model_deployer.BaseModelDeployerFlavor)

Flavor for the BentoML model deployer.

#### *property* config_class *: Type[[BentoMLModelDeployerConfig](#zenml.integrations.bentoml.flavors.bentoml_model_deployer_flavor.BentoMLModelDeployerConfig)]*

Returns BentoMLModelDeployerConfig config class.

Returns:
: The config class.

#### *property* docs_url *: str | None*

A url to point at docs explaining this flavor.

Returns:
: A flavor docs url.

#### *property* implementation_class *: Type[BentoMLModelDeployer]*

Implementation class for this flavor.

Returns:
: The implementation class.

#### *property* logo_url *: str*

A url to represent the flavor in the dashboard.

Returns:
: The flavor logo.

#### *property* name *: str*

Name of the flavor.

Returns:
: Name of the flavor.

#### *property* sdk_docs_url *: str | None*

A url to point at SDK docs explaining this flavor.

Returns:
: A flavor SDK docs url.
