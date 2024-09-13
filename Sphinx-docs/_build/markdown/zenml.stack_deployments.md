# zenml.stack_deployments package

## Submodules

## zenml.stack_deployments.aws_stack_deployment module

Functionality to deploy a ZenML stack to AWS.

### *class* zenml.stack_deployments.aws_stack_deployment.AWSZenMLCloudStackDeployment(\*, terraform: bool = False, stack_name: str, zenml_server_url: str, zenml_server_api_token: str, location: str | None = None)

Bases: [`ZenMLCloudStackDeployment`](#zenml.stack_deployments.stack_deployment.ZenMLCloudStackDeployment)

AWS ZenML Cloud Stack Deployment.

#### deployment *: ClassVar[str]* *= 'cloud-formation'*

#### *classmethod* description() → str

Return a description of the ZenML Cloud Stack Deployment.

This will be displayed when the user is prompted to deploy
the ZenML stack.

Returns:
: A MarkDown description of the ZenML Cloud Stack Deployment.

#### get_deployment_config() → [StackDeploymentConfig](zenml.models.v2.misc.md#zenml.models.v2.misc.stack_deployment.StackDeploymentConfig)

Return the configuration to deploy the ZenML stack to the specified cloud provider.

The configuration should include:

* a cloud provider console URL where the user will be redirected to

deploy the ZenML stack. The URL should include as many pre-filled
URL query parameters as possible.
\* a textual description of the URL
\* a Terraform script used to deploy the ZenML stack
\* some deployment providers may require additional configuration
parameters or scripts to be passed to the cloud provider in addition to
the deployment URL query parameters. Where that is the case, this method
should also return a string that the user can copy and paste into the
cloud provider console to deploy the ZenML stack (e.g. a set of
environment variables, YAML configuration snippet, bash or Terraform
script etc.).

Returns:
: The configuration or script to deploy the ZenML stack to the
  specified cloud provider.

#### *classmethod* instructions() → str

Return instructions on how to deploy the ZenML stack to the specified cloud provider.

This will be displayed before the user is prompted to deploy the ZenML
stack.

Returns:
: MarkDown instructions on how to deploy the ZenML stack to the
  specified cloud provider.

#### *classmethod* integrations() → List[str]

Return the ZenML integrations required for the stack.

Returns:
: The list of ZenML integrations that need to be installed for the
  stack to be usable.

#### *classmethod* locations() → Dict[str, str]

Return the locations where the ZenML stack can be deployed.

Returns:
: The regions where the ZenML stack can be deployed as a map of region
  names to region descriptions.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'location': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'stack_name': FieldInfo(annotation=str, required=True), 'terraform': FieldInfo(annotation=bool, required=False, default=False), 'zenml_server_api_token': FieldInfo(annotation=str, required=True), 'zenml_server_url': FieldInfo(annotation=str, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### *classmethod* permissions() → Dict[str, List[str]]

Return the permissions granted to ZenML to access the cloud resources.

Returns:
: The permissions granted to ZenML to access the cloud resources, as
  a dictionary grouping permissions by resource.

#### *classmethod* post_deploy_instructions() → str

Return instructions on what to do after the deployment is complete.

This will be displayed after the deployment is complete.

Returns:
: MarkDown instructions on what to do after the deployment is
  complete.

#### provider *: ClassVar[[StackDeploymentProvider](zenml.md#zenml.enums.StackDeploymentProvider)]* *= 'aws'*

## zenml.stack_deployments.azure_stack_deployment module

Functionality to deploy a ZenML stack to Azure.

### *class* zenml.stack_deployments.azure_stack_deployment.AZUREZenMLCloudStackDeployment(\*, terraform: bool = False, stack_name: str, zenml_server_url: str, zenml_server_api_token: str, location: str | None = None)

Bases: [`ZenMLCloudStackDeployment`](#zenml.stack_deployments.stack_deployment.ZenMLCloudStackDeployment)

Azure ZenML Cloud Stack Deployment.

#### deployment *: ClassVar[str]* *= 'azure-cloud-shell'*

#### *classmethod* description() → str

Return a description of the ZenML Cloud Stack Deployment.

This will be displayed when the user is prompted to deploy
the ZenML stack.

Returns:
: A MarkDown description of the ZenML Cloud Stack Deployment.

#### get_deployment_config() → [StackDeploymentConfig](zenml.models.v2.misc.md#zenml.models.v2.misc.stack_deployment.StackDeploymentConfig)

Return the configuration to deploy the ZenML stack to the specified cloud provider.

The configuration should include:

* a cloud provider console URL where the user will be redirected to

deploy the ZenML stack. The URL should include as many pre-filled
URL query parameters as possible.
\* a textual description of the URL
\* some deployment providers may require additional configuration
parameters or scripts to be passed to the cloud provider in addition to
the deployment URL query parameters. Where that is the case, this method
should also return a string that the user can copy and paste into the
cloud provider console to deploy the ZenML stack (e.g. a set of
environment variables, YAML configuration snippet, bash or Terraform
script etc.).

Returns:
: The configuration or script to deploy the ZenML stack to the
  specified cloud provider.

#### *classmethod* instructions() → str

Return instructions on how to deploy the ZenML stack to the specified cloud provider.

This will be displayed before the user is prompted to deploy the ZenML
stack.

Returns:
: MarkDown instructions on how to deploy the ZenML stack to the
  specified cloud provider.

#### *classmethod* integrations() → List[str]

Return the ZenML integrations required for the stack.

Returns:
: The list of ZenML integrations that need to be installed for the
  stack to be usable.

#### *classmethod* locations() → Dict[str, str]

Return the locations where the ZenML stack can be deployed.

Returns:
: The regions where the ZenML stack can be deployed as a map of region
  names to region descriptions.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'location': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'stack_name': FieldInfo(annotation=str, required=True), 'terraform': FieldInfo(annotation=bool, required=False, default=False), 'zenml_server_api_token': FieldInfo(annotation=str, required=True), 'zenml_server_url': FieldInfo(annotation=str, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### *classmethod* permissions() → Dict[str, List[str]]

Return the permissions granted to ZenML to access the cloud resources.

Returns:
: The permissions granted to ZenML to access the cloud resources, as
  a dictionary grouping permissions by resource.

#### *classmethod* post_deploy_instructions() → str

Return instructions on what to do after the deployment is complete.

This will be displayed after the deployment is complete.

Returns:
: MarkDown instructions on what to do after the deployment is
  complete.

#### provider *: ClassVar[[StackDeploymentProvider](zenml.md#zenml.enums.StackDeploymentProvider)]* *= 'azure'*

#### *classmethod* skypilot_default_regions() → Dict[str, str]

Returns the regions supported by default for the Skypilot.

Returns:
: The regions supported by default for the Skypilot.

## zenml.stack_deployments.gcp_stack_deployment module

Functionality to deploy a ZenML stack to GCP.

### *class* zenml.stack_deployments.gcp_stack_deployment.GCPZenMLCloudStackDeployment(\*, terraform: bool = False, stack_name: str, zenml_server_url: str, zenml_server_api_token: str, location: str | None = None)

Bases: [`ZenMLCloudStackDeployment`](#zenml.stack_deployments.stack_deployment.ZenMLCloudStackDeployment)

GCP ZenML Cloud Stack Deployment.

#### deployment *: ClassVar[str]* *= 'deployment-manager'*

#### *classmethod* description() → str

Return a description of the ZenML Cloud Stack Deployment.

This will be displayed when the user is prompted to deploy
the ZenML stack.

Returns:
: A MarkDown description of the ZenML Cloud Stack Deployment.

#### get_deployment_config() → [StackDeploymentConfig](zenml.models.v2.misc.md#zenml.models.v2.misc.stack_deployment.StackDeploymentConfig)

Return the configuration to deploy the ZenML stack to the specified cloud provider.

The configuration should include:

* a cloud provider console URL where the user will be redirected to

deploy the ZenML stack. The URL should include as many pre-filled
URL query parameters as possible.
\* a textual description of the URL
\* some deployment providers may require additional configuration
parameters or scripts to be passed to the cloud provider in addition to
the deployment URL query parameters. Where that is the case, this method
should also return a string that the user can copy and paste into the
cloud provider console to deploy the ZenML stack (e.g. a set of
environment variables, YAML configuration snippet, bash or Terraform
script etc.).

Returns:
: The configuration or script to deploy the ZenML stack to the
  specified cloud provider.

#### *classmethod* instructions() → str

Return instructions on how to deploy the ZenML stack to the specified cloud provider.

This will be displayed before the user is prompted to deploy the ZenML
stack.

Returns:
: MarkDown instructions on how to deploy the ZenML stack to the
  specified cloud provider.

#### *classmethod* integrations() → List[str]

Return the ZenML integrations required for the stack.

Returns:
: The list of ZenML integrations that need to be installed for the
  stack to be usable.

#### *classmethod* locations() → Dict[str, str]

Return the locations where the ZenML stack can be deployed.

Returns:
: The regions where the ZenML stack can be deployed as a map of region
  names to region descriptions.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'location': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'stack_name': FieldInfo(annotation=str, required=True), 'terraform': FieldInfo(annotation=bool, required=False, default=False), 'zenml_server_api_token': FieldInfo(annotation=str, required=True), 'zenml_server_url': FieldInfo(annotation=str, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### *classmethod* permissions() → Dict[str, List[str]]

Return the permissions granted to ZenML to access the cloud resources.

Returns:
: The permissions granted to ZenML to access the cloud resources, as
  a dictionary grouping permissions by resource.

#### *classmethod* post_deploy_instructions() → str

Return instructions on what to do after the deployment is complete.

This will be displayed after the deployment is complete.

Returns:
: MarkDown instructions on what to do after the deployment is
  complete.

#### provider *: ClassVar[[StackDeploymentProvider](zenml.md#zenml.enums.StackDeploymentProvider)]* *= 'gcp'*

#### *classmethod* skypilot_default_regions() → Dict[str, str]

Returns the regions supported by default for the Skypilot.

Returns:
: The regions supported by default for the Skypilot.

## zenml.stack_deployments.stack_deployment module

Functionality to deploy a ZenML stack to a cloud provider.

### *class* zenml.stack_deployments.stack_deployment.ZenMLCloudStackDeployment(\*, terraform: bool = False, stack_name: str, zenml_server_url: str, zenml_server_api_token: str, location: str | None = None)

Bases: `BaseModel`

ZenML Cloud Stack CLI Deployment base class.

#### deployment *: ClassVar[str]*

#### *property* deployment_type *: str*

Return the type of deployment.

Returns:
: The type of deployment.

#### *abstract classmethod* description() → str

Return a description of the ZenML Cloud Stack Deployment.

This will be displayed when the user is prompted to deploy
the ZenML stack.

Returns:
: A MarkDown description of the ZenML Cloud Stack Deployment.

#### *abstract* get_deployment_config() → [StackDeploymentConfig](zenml.models.v2.misc.md#zenml.models.v2.misc.stack_deployment.StackDeploymentConfig)

Return the configuration to deploy the ZenML stack to the specified cloud provider.

The configuration should include:

* a cloud provider console URL where the user will be redirected to

deploy the ZenML stack. The URL should include as many pre-filled
URL query parameters as possible.
\* a textual description of the URL
\* some deployment providers may require additional configuration
parameters or scripts to be passed to the cloud provider in addition to
the deployment URL query parameters. Where that is the case, this method
should also return a string that the user can copy and paste into the
cloud provider console to deploy the ZenML stack (e.g. a set of
environment variables, YAML configuration snippet, bash or Terraform
script etc.).

Returns:
: The configuration or script to deploy the ZenML stack to the
  specified cloud provider.

#### *classmethod* get_deployment_info() → [StackDeploymentInfo](zenml.models.v2.misc.md#zenml.models.v2.misc.stack_deployment.StackDeploymentInfo)

Return information about the ZenML Cloud Stack Deployment.

Returns:
: Information about the ZenML Cloud Stack Deployment.

#### get_stack(date_start: datetime | None = None) → [DeployedStack](zenml.models.v2.misc.md#zenml.models.v2.misc.stack_deployment.DeployedStack) | None

Return the ZenML stack that was deployed and registered.

This method is called to retrieve a ZenML stack matching the deployment
provider.

Args:
: date_start: The date when the deployment started.

Returns:
: The ZenML stack that was deployed and registered or None if a
  matching stack was not found.

#### *abstract classmethod* instructions() → str

Return instructions on how to deploy the ZenML stack to the specified cloud provider.

This will be displayed before the user is prompted to deploy the ZenML
stack.

Returns:
: MarkDown instructions on how to deploy the ZenML stack to the
  specified cloud provider.

#### *abstract classmethod* integrations() → List[str]

Return the ZenML integrations required for the stack.

Returns:
: The list of ZenML integrations that need to be installed for the
  stack to be usable.

#### location *: str | None*

#### *abstract classmethod* locations() → Dict[str, str]

Return the locations where the ZenML stack can be deployed.

Returns:
: The regions where the ZenML stack can be deployed as a map of region
  names to region descriptions.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'location': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'stack_name': FieldInfo(annotation=str, required=True), 'terraform': FieldInfo(annotation=bool, required=False, default=False), 'zenml_server_api_token': FieldInfo(annotation=str, required=True), 'zenml_server_url': FieldInfo(annotation=str, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### *abstract classmethod* permissions() → Dict[str, List[str]]

Return the permissions granted to ZenML to access the cloud resources.

Returns:
: The permissions granted to ZenML to access the cloud resources, as
  a dictionary grouping permissions by resource.

#### *abstract classmethod* post_deploy_instructions() → str

Return instructions on what to do after the deployment is complete.

This will be displayed after the deployment is complete.

Returns:
: MarkDown instructions on what to do after the deployment is
  complete.

#### provider *: ClassVar[[StackDeploymentProvider](zenml.md#zenml.enums.StackDeploymentProvider)]*

#### *classmethod* skypilot_default_regions() → Dict[str, str]

Returns the regions supported by default for the Skypilot.

Returns:
: The regions supported by default for the Skypilot.

#### stack_name *: str*

#### terraform *: bool*

#### zenml_server_api_token *: str*

#### zenml_server_url *: str*

## zenml.stack_deployments.utils module

Functionality to deploy a ZenML stack to a cloud provider.

### zenml.stack_deployments.utils.get_stack_deployment_class(provider: [StackDeploymentProvider](zenml.md#zenml.enums.StackDeploymentProvider)) → Type[[ZenMLCloudStackDeployment](#zenml.stack_deployments.stack_deployment.ZenMLCloudStackDeployment)]

Get the ZenML Cloud Stack Deployment class for the specified provider.

Args:
: provider: The stack deployment provider.

Returns:
: The ZenML Cloud Stack Deployment class for the specified provider.

## Module contents

ZenML Stack Deployments.
