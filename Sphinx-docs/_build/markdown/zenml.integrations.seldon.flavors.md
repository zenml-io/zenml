# zenml.integrations.seldon.flavors package

## Submodules

## zenml.integrations.seldon.flavors.seldon_model_deployer_flavor module

Seldon model deployer flavor.

### *class* zenml.integrations.seldon.flavors.seldon_model_deployer_flavor.SeldonModelDeployerConfig(warn_about_plain_text_secrets: bool = False, \*, kubernetes_context: str | None = None, kubernetes_namespace: str | None = None, base_url: str, secret: str | None, kubernetes_secret_name: str | None)

Bases: [`BaseModelDeployerConfig`](zenml.model_deployers.md#zenml.model_deployers.base_model_deployer.BaseModelDeployerConfig)

Config for the Seldon Model Deployer.

Attributes:
: kubernetes_context: the Kubernetes context to use to contact the remote
  : Seldon Core installation. If not specified, the current
    configuration is used. Depending on where the Seldon model deployer
    is being used, this can be either a locally active context or an
    in-cluster Kubernetes configuration (if running inside a pod).
    If the model deployer stack component is linked to a Kubernetes
    service connector, this field is ignored.
  <br/>
  kubernetes_namespace: the Kubernetes namespace where the Seldon Core
  : deployment servers are provisioned and managed by ZenML. If not
    specified, the namespace set in the current configuration is used.
    Depending on where the Seldon model deployer is being used, this can
    be either the current namespace configured in the locally active
    context or the namespace in the context of which the pod is running
    (if running inside a pod).
    If the model deployer stack component is linked to a Kubernetes
    service connector, this field is mandatory.
  <br/>
  base_url: the base URL of the Kubernetes ingress used to expose the
  : Seldon Core deployment servers.
  <br/>
  secret: the name of a ZenML secret containing the credentials used by
  : Seldon Core storage initializers to authenticate to the Artifact
    Store (i.e. the storage backend where models are stored - see
    [https://docs.seldon.io/projects/seldon-core/en/latest/servers/overview.html#handling-credentials](https://docs.seldon.io/projects/seldon-core/en/latest/servers/overview.html#handling-credentials)).
  <br/>
  kubernetes_secret_name: the name of the Kubernetes secret containing
  : the credentials used by Seldon Core storage initializers to
    authenticate to the Artifact Store (i.e. the storage backend where
    models are stored) - This is used when the secret is not managed by
    ZenML and is already present in the Kubernetes cluster.

#### base_url *: str*

#### kubernetes_context *: str | None*

#### kubernetes_namespace *: str | None*

#### kubernetes_secret_name *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'base_url': FieldInfo(annotation=str, required=True), 'kubernetes_context': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'kubernetes_namespace': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'kubernetes_secret_name': FieldInfo(annotation=Union[str, NoneType], required=True), 'secret': FieldInfo(annotation=Union[str, NoneType], required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### secret *: str | None*

### *class* zenml.integrations.seldon.flavors.seldon_model_deployer_flavor.SeldonModelDeployerFlavor

Bases: [`BaseModelDeployerFlavor`](zenml.model_deployers.md#zenml.model_deployers.base_model_deployer.BaseModelDeployerFlavor)

Seldon Core model deployer flavor.

#### *property* config_class *: Type[[SeldonModelDeployerConfig](#zenml.integrations.seldon.flavors.seldon_model_deployer_flavor.SeldonModelDeployerConfig)]*

Returns SeldonModelDeployerConfig config class.

Returns:
: The config class.

#### *property* docs_url *: str | None*

A url to point at docs explaining this flavor.

Returns:
: A flavor docs url.

#### *property* implementation_class *: Type[[SeldonModelDeployer](zenml.integrations.seldon.model_deployers.md#zenml.integrations.seldon.model_deployers.seldon_model_deployer.SeldonModelDeployer)]*

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

#### *property* service_connector_requirements *: [ServiceConnectorRequirements](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorRequirements) | None*

Service connector resource requirements for service connectors.

Specifies resource requirements that are used to filter the available
service connector types that are compatible with this flavor.

Returns:
: Requirements for compatible service connectors, if a service
  connector is required for this flavor.

## Module contents

Seldon integration flavors.

### *class* zenml.integrations.seldon.flavors.SeldonModelDeployerConfig(warn_about_plain_text_secrets: bool = False, \*, kubernetes_context: str | None = None, kubernetes_namespace: str | None = None, base_url: str, secret: str | None, kubernetes_secret_name: str | None)

Bases: [`BaseModelDeployerConfig`](zenml.model_deployers.md#zenml.model_deployers.base_model_deployer.BaseModelDeployerConfig)

Config for the Seldon Model Deployer.

Attributes:
: kubernetes_context: the Kubernetes context to use to contact the remote
  : Seldon Core installation. If not specified, the current
    configuration is used. Depending on where the Seldon model deployer
    is being used, this can be either a locally active context or an
    in-cluster Kubernetes configuration (if running inside a pod).
    If the model deployer stack component is linked to a Kubernetes
    service connector, this field is ignored.
  <br/>
  kubernetes_namespace: the Kubernetes namespace where the Seldon Core
  : deployment servers are provisioned and managed by ZenML. If not
    specified, the namespace set in the current configuration is used.
    Depending on where the Seldon model deployer is being used, this can
    be either the current namespace configured in the locally active
    context or the namespace in the context of which the pod is running
    (if running inside a pod).
    If the model deployer stack component is linked to a Kubernetes
    service connector, this field is mandatory.
  <br/>
  base_url: the base URL of the Kubernetes ingress used to expose the
  : Seldon Core deployment servers.
  <br/>
  secret: the name of a ZenML secret containing the credentials used by
  : Seldon Core storage initializers to authenticate to the Artifact
    Store (i.e. the storage backend where models are stored - see
    [https://docs.seldon.io/projects/seldon-core/en/latest/servers/overview.html#handling-credentials](https://docs.seldon.io/projects/seldon-core/en/latest/servers/overview.html#handling-credentials)).
  <br/>
  kubernetes_secret_name: the name of the Kubernetes secret containing
  : the credentials used by Seldon Core storage initializers to
    authenticate to the Artifact Store (i.e. the storage backend where
    models are stored) - This is used when the secret is not managed by
    ZenML and is already present in the Kubernetes cluster.

#### base_url *: str*

#### kubernetes_context *: str | None*

#### kubernetes_namespace *: str | None*

#### kubernetes_secret_name *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'base_url': FieldInfo(annotation=str, required=True), 'kubernetes_context': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'kubernetes_namespace': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'kubernetes_secret_name': FieldInfo(annotation=Union[str, NoneType], required=True), 'secret': FieldInfo(annotation=Union[str, NoneType], required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### secret *: str | None*

### *class* zenml.integrations.seldon.flavors.SeldonModelDeployerFlavor

Bases: [`BaseModelDeployerFlavor`](zenml.model_deployers.md#zenml.model_deployers.base_model_deployer.BaseModelDeployerFlavor)

Seldon Core model deployer flavor.

#### *property* config_class *: Type[[SeldonModelDeployerConfig](#zenml.integrations.seldon.flavors.seldon_model_deployer_flavor.SeldonModelDeployerConfig)]*

Returns SeldonModelDeployerConfig config class.

Returns:
: The config class.

#### *property* docs_url *: str | None*

A url to point at docs explaining this flavor.

Returns:
: A flavor docs url.

#### *property* implementation_class *: Type[[SeldonModelDeployer](zenml.integrations.seldon.model_deployers.md#zenml.integrations.seldon.model_deployers.seldon_model_deployer.SeldonModelDeployer)]*

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

#### *property* service_connector_requirements *: [ServiceConnectorRequirements](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorRequirements) | None*

Service connector resource requirements for service connectors.

Specifies resource requirements that are used to filter the available
service connector types that are compatible with this flavor.

Returns:
: Requirements for compatible service connectors, if a service
  connector is required for this flavor.
