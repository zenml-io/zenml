# zenml.integrations.huggingface.flavors package

## Submodules

## zenml.integrations.huggingface.flavors.huggingface_model_deployer_flavor module

Hugging Face model deployer flavor.

### *class* zenml.integrations.huggingface.flavors.huggingface_model_deployer_flavor.HuggingFaceBaseConfig(\*, repository: str | None = None, framework: str | None = None, accelerator: str | None = None, instance_size: str | None = None, instance_type: str | None = None, region: str | None = None, vendor: str | None = None, account_id: str | None = None, min_replica: int = 0, max_replica: int = 1, revision: str | None = None, task: str | None = None, custom_image: Dict[str, Any] | None = None, endpoint_type: str = 'public', secret_name: str | None = None, namespace: str | None = None)

Bases: `BaseModel`

Hugging Face Inference Endpoint configuration.

#### accelerator *: str | None*

#### account_id *: str | None*

#### custom_image *: Dict[str, Any] | None*

#### endpoint_type *: str*

#### framework *: str | None*

#### instance_size *: str | None*

#### instance_type *: str | None*

#### max_replica *: int*

#### min_replica *: int*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'accelerator': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'account_id': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'custom_image': FieldInfo(annotation=Union[Dict[str, Any], NoneType], required=False, default=None), 'endpoint_type': FieldInfo(annotation=str, required=False, default='public'), 'framework': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'instance_size': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'instance_type': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'max_replica': FieldInfo(annotation=int, required=False, default=1), 'min_replica': FieldInfo(annotation=int, required=False, default=0), 'namespace': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'region': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'repository': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'revision': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'secret_name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'task': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'vendor': FieldInfo(annotation=Union[str, NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### namespace *: str | None*

#### region *: str | None*

#### repository *: str | None*

#### revision *: str | None*

#### secret_name *: str | None*

#### task *: str | None*

#### vendor *: str | None*

### *class* zenml.integrations.huggingface.flavors.huggingface_model_deployer_flavor.HuggingFaceModelDeployerConfig(warn_about_plain_text_secrets: bool = False, \*, repository: str | None = None, framework: str | None = None, accelerator: str | None = None, instance_size: str | None = None, instance_type: str | None = None, region: str | None = None, vendor: str | None = None, account_id: str | None = None, min_replica: int = 0, max_replica: int = 1, revision: str | None = None, task: str | None = None, custom_image: Dict[str, Any] | None = None, endpoint_type: str = 'public', secret_name: str | None = None, namespace: str, token: str | None = None)

Bases: [`BaseModelDeployerConfig`](zenml.model_deployers.md#zenml.model_deployers.base_model_deployer.BaseModelDeployerConfig), [`HuggingFaceBaseConfig`](#zenml.integrations.huggingface.flavors.huggingface_model_deployer_flavor.HuggingFaceBaseConfig)

Configuration for the Hugging Face model deployer.

Attributes:
: token: Hugging Face token used for authentication
  namespace: Hugging Face namespace used to list endpoints

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'accelerator': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'account_id': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'custom_image': FieldInfo(annotation=Union[Dict[str, Any], NoneType], required=False, default=None), 'endpoint_type': FieldInfo(annotation=str, required=False, default='public'), 'framework': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'instance_size': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'instance_type': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'max_replica': FieldInfo(annotation=int, required=False, default=1), 'min_replica': FieldInfo(annotation=int, required=False, default=0), 'namespace': FieldInfo(annotation=str, required=True), 'region': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'repository': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'revision': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'secret_name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'task': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'token': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, json_schema_extra={'sensitive': True}), 'vendor': FieldInfo(annotation=Union[str, NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### namespace *: str*

#### token *: str | None*

### *class* zenml.integrations.huggingface.flavors.huggingface_model_deployer_flavor.HuggingFaceModelDeployerFlavor

Bases: [`BaseModelDeployerFlavor`](zenml.model_deployers.md#zenml.model_deployers.base_model_deployer.BaseModelDeployerFlavor)

Hugging Face Endpoint model deployer flavor.

#### *property* config_class *: Type[[HuggingFaceModelDeployerConfig](#zenml.integrations.huggingface.flavors.huggingface_model_deployer_flavor.HuggingFaceModelDeployerConfig)]*

Returns HuggingFaceModelDeployerConfig config class.

Returns:
: The config class.

#### *property* docs_url *: str | None*

A url to point at docs explaining this flavor.

Returns:
: A flavor docs url.

#### *property* implementation_class *: Type[HuggingFaceModelDeployer]*

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
: The name of the flavor.

#### *property* sdk_docs_url *: str | None*

A url to point at SDK docs explaining this flavor.

Returns:
: A flavor SDK docs url.

## Module contents

Hugging Face integration flavors.

### *class* zenml.integrations.huggingface.flavors.HuggingFaceBaseConfig(\*, repository: str | None = None, framework: str | None = None, accelerator: str | None = None, instance_size: str | None = None, instance_type: str | None = None, region: str | None = None, vendor: str | None = None, account_id: str | None = None, min_replica: int = 0, max_replica: int = 1, revision: str | None = None, task: str | None = None, custom_image: Dict[str, Any] | None = None, endpoint_type: str = 'public', secret_name: str | None = None, namespace: str | None = None)

Bases: `BaseModel`

Hugging Face Inference Endpoint configuration.

#### accelerator *: str | None*

#### account_id *: str | None*

#### custom_image *: Dict[str, Any] | None*

#### endpoint_type *: str*

#### framework *: str | None*

#### instance_size *: str | None*

#### instance_type *: str | None*

#### max_replica *: int*

#### min_replica *: int*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'accelerator': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'account_id': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'custom_image': FieldInfo(annotation=Union[Dict[str, Any], NoneType], required=False, default=None), 'endpoint_type': FieldInfo(annotation=str, required=False, default='public'), 'framework': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'instance_size': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'instance_type': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'max_replica': FieldInfo(annotation=int, required=False, default=1), 'min_replica': FieldInfo(annotation=int, required=False, default=0), 'namespace': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'region': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'repository': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'revision': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'secret_name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'task': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'vendor': FieldInfo(annotation=Union[str, NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### namespace *: str | None*

#### region *: str | None*

#### repository *: str | None*

#### revision *: str | None*

#### secret_name *: str | None*

#### task *: str | None*

#### vendor *: str | None*

### *class* zenml.integrations.huggingface.flavors.HuggingFaceModelDeployerConfig(warn_about_plain_text_secrets: bool = False, \*, repository: str | None = None, framework: str | None = None, accelerator: str | None = None, instance_size: str | None = None, instance_type: str | None = None, region: str | None = None, vendor: str | None = None, account_id: str | None = None, min_replica: int = 0, max_replica: int = 1, revision: str | None = None, task: str | None = None, custom_image: Dict[str, Any] | None = None, endpoint_type: str = 'public', secret_name: str | None = None, namespace: str, token: str | None = None)

Bases: [`BaseModelDeployerConfig`](zenml.model_deployers.md#zenml.model_deployers.base_model_deployer.BaseModelDeployerConfig), [`HuggingFaceBaseConfig`](#zenml.integrations.huggingface.flavors.huggingface_model_deployer_flavor.HuggingFaceBaseConfig)

Configuration for the Hugging Face model deployer.

Attributes:
: token: Hugging Face token used for authentication
  namespace: Hugging Face namespace used to list endpoints

#### accelerator *: str | None*

#### account_id *: str | None*

#### custom_image *: Dict[str, Any] | None*

#### endpoint_type *: str*

#### framework *: str | None*

#### instance_size *: str | None*

#### instance_type *: str | None*

#### max_replica *: int*

#### min_replica *: int*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'accelerator': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'account_id': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'custom_image': FieldInfo(annotation=Union[Dict[str, Any], NoneType], required=False, default=None), 'endpoint_type': FieldInfo(annotation=str, required=False, default='public'), 'framework': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'instance_size': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'instance_type': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'max_replica': FieldInfo(annotation=int, required=False, default=1), 'min_replica': FieldInfo(annotation=int, required=False, default=0), 'namespace': FieldInfo(annotation=str, required=True), 'region': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'repository': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'revision': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'secret_name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'task': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'token': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, json_schema_extra={'sensitive': True}), 'vendor': FieldInfo(annotation=Union[str, NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### namespace *: str*

#### region *: str | None*

#### repository *: str | None*

#### revision *: str | None*

#### secret_name *: str | None*

#### task *: str | None*

#### token *: str | None*

#### vendor *: str | None*

### *class* zenml.integrations.huggingface.flavors.HuggingFaceModelDeployerFlavor

Bases: [`BaseModelDeployerFlavor`](zenml.model_deployers.md#zenml.model_deployers.base_model_deployer.BaseModelDeployerFlavor)

Hugging Face Endpoint model deployer flavor.

#### *property* config_class *: Type[[HuggingFaceModelDeployerConfig](#zenml.integrations.huggingface.flavors.huggingface_model_deployer_flavor.HuggingFaceModelDeployerConfig)]*

Returns HuggingFaceModelDeployerConfig config class.

Returns:
: The config class.

#### *property* docs_url *: str | None*

A url to point at docs explaining this flavor.

Returns:
: A flavor docs url.

#### *property* implementation_class *: Type[HuggingFaceModelDeployer]*

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
: The name of the flavor.

#### *property* sdk_docs_url *: str | None*

A url to point at SDK docs explaining this flavor.

Returns:
: A flavor SDK docs url.
