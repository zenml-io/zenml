# zenml.integrations.gcp package

## Subpackages

* [zenml.integrations.gcp.artifact_stores package](zenml.integrations.gcp.artifact_stores.md)
  * [Submodules](zenml.integrations.gcp.artifact_stores.md#submodules)
  * [zenml.integrations.gcp.artifact_stores.gcp_artifact_store module](zenml.integrations.gcp.artifact_stores.md#zenml-integrations-gcp-artifact-stores-gcp-artifact-store-module)
  * [Module contents](zenml.integrations.gcp.artifact_stores.md#module-contents)
* [zenml.integrations.gcp.flavors package](zenml.integrations.gcp.flavors.md)
  * [Submodules](zenml.integrations.gcp.flavors.md#submodules)
  * [zenml.integrations.gcp.flavors.gcp_artifact_store_flavor module](zenml.integrations.gcp.flavors.md#zenml-integrations-gcp-flavors-gcp-artifact-store-flavor-module)
  * [zenml.integrations.gcp.flavors.gcp_image_builder_flavor module](zenml.integrations.gcp.flavors.md#zenml-integrations-gcp-flavors-gcp-image-builder-flavor-module)
  * [zenml.integrations.gcp.flavors.vertex_orchestrator_flavor module](zenml.integrations.gcp.flavors.md#zenml-integrations-gcp-flavors-vertex-orchestrator-flavor-module)
  * [zenml.integrations.gcp.flavors.vertex_step_operator_flavor module](zenml.integrations.gcp.flavors.md#zenml-integrations-gcp-flavors-vertex-step-operator-flavor-module)
  * [Module contents](zenml.integrations.gcp.flavors.md#module-contents)
* [zenml.integrations.gcp.image_builders package](zenml.integrations.gcp.image_builders.md)
  * [Submodules](zenml.integrations.gcp.image_builders.md#submodules)
  * [zenml.integrations.gcp.image_builders.gcp_image_builder module](zenml.integrations.gcp.image_builders.md#zenml-integrations-gcp-image-builders-gcp-image-builder-module)
  * [Module contents](zenml.integrations.gcp.image_builders.md#module-contents)
* [zenml.integrations.gcp.orchestrators package](zenml.integrations.gcp.orchestrators.md)
  * [Submodules](zenml.integrations.gcp.orchestrators.md#submodules)
  * [zenml.integrations.gcp.orchestrators.vertex_orchestrator module](zenml.integrations.gcp.orchestrators.md#zenml-integrations-gcp-orchestrators-vertex-orchestrator-module)
  * [Module contents](zenml.integrations.gcp.orchestrators.md#module-contents)
* [zenml.integrations.gcp.service_connectors package](zenml.integrations.gcp.service_connectors.md)
  * [Submodules](zenml.integrations.gcp.service_connectors.md#submodules)
  * [zenml.integrations.gcp.service_connectors.gcp_service_connector module](zenml.integrations.gcp.service_connectors.md#zenml-integrations-gcp-service-connectors-gcp-service-connector-module)
  * [Module contents](zenml.integrations.gcp.service_connectors.md#module-contents)
* [zenml.integrations.gcp.step_operators package](zenml.integrations.gcp.step_operators.md)
  * [Submodules](zenml.integrations.gcp.step_operators.md#submodules)
  * [zenml.integrations.gcp.step_operators.vertex_step_operator module](zenml.integrations.gcp.step_operators.md#zenml-integrations-gcp-step-operators-vertex-step-operator-module)
  * [Module contents](zenml.integrations.gcp.step_operators.md#module-contents)

## Submodules

## zenml.integrations.gcp.constants module

## zenml.integrations.gcp.google_credentials_mixin module

Implementation of the Google credentials mixin.

### *class* zenml.integrations.gcp.google_credentials_mixin.GoogleCredentialsConfigMixin(warn_about_plain_text_secrets: bool = False, \*, project: str | None = None, service_account_path: str | None = None)

Bases: [`StackComponentConfig`](zenml.stack.md#zenml.stack.stack_component.StackComponentConfig)

Config mixin for Google Cloud Platform credentials.

Attributes:
: project: GCP project name. If None, the project will be inferred from
  : the environment.
  <br/>
  service_account_path: path to the service account credentials file to be
  : used for authentication. If not provided, the default credentials
    will be used.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'project': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'service_account_path': FieldInfo(annotation=Union[str, NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### project *: str | None*

#### service_account_path *: str | None*

### *class* zenml.integrations.gcp.google_credentials_mixin.GoogleCredentialsMixin(name: str, id: UUID, config: [StackComponentConfig](zenml.stack.md#zenml.stack.stack_component.StackComponentConfig), flavor: str, type: [StackComponentType](zenml.md#zenml.enums.StackComponentType), user: UUID | None, workspace: UUID, created: datetime, updated: datetime, labels: Dict[str, Any] | None = None, connector_requirements: [ServiceConnectorRequirements](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorRequirements) | None = None, connector: UUID | None = None, connector_resource_id: str | None = None, \*args: Any, \*\*kwargs: Any)

Bases: [`StackComponent`](zenml.stack.md#zenml.stack.stack_component.StackComponent)

StackComponent mixin to get Google Cloud Platform credentials.

#### *property* config *: [GoogleCredentialsConfigMixin](#zenml.integrations.gcp.google_credentials_mixin.GoogleCredentialsConfigMixin)*

Returns the GoogleCredentialsConfigMixin config.

Returns:
: The configuration.

## Module contents

Initialization of the GCP ZenML integration.

The GCP integration submodule provides a way to run ZenML pipelines in a cloud
environment. Specifically, it allows the use of cloud artifact stores
and provides an io module to handle file operations on Google Cloud Storage
(GCS).

The Vertex AI integration submodule provides a way to run ZenML pipelines in a
Vertex AI environment.

### *class* zenml.integrations.gcp.GcpIntegration

Bases: [`Integration`](zenml.integrations.md#zenml.integrations.integration.Integration)

Definition of Google Cloud Platform integration for ZenML.

#### NAME *= 'gcp'*

#### REQUIREMENTS *: List[str]* *= ['kfp>=2.6.0', 'gcsfs', 'google-cloud-secret-manager', 'google-cloud-container>=2.21.0', 'google-cloud-artifact-registry>=1.11.3', 'google-cloud-storage>=2.9.0', 'google-cloud-aiplatform>=1.34.0', 'google-cloud-build>=3.11.0', 'kubernetes']*

#### REQUIREMENTS_IGNORED_ON_UNINSTALL *: List[str]* *= ['kubernetes', 'kfp']*

#### *classmethod* activate() → None

Activate the GCP integration.

#### *classmethod* flavors() → List[Type[[Flavor](zenml.stack.md#zenml.stack.flavor.Flavor)]]

Declare the stack component flavors for the GCP integration.

Returns:
: List of stack component flavors for this integration.
