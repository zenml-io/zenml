# zenml.integrations.seldon.services package

## Submodules

## zenml.integrations.seldon.services.seldon_deployment module

Implementation for the Seldon Deployment step.

### *class* zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentConfig(\*, type: Literal['zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentConfig'] = 'zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentConfig', name: str = '', description: str = '', pipeline_name: str = '', pipeline_step_name: str = '', model_name: str = 'default', model_version: str = '', service_name: str = '', model_uri: str = '', implementation: str, parameters: List[[SeldonDeploymentPredictorParameter](zenml.integrations.seldon.md#zenml.integrations.seldon.seldon_client.SeldonDeploymentPredictorParameter)] | None, resources: [SeldonResourceRequirements](zenml.integrations.seldon.md#zenml.integrations.seldon.seldon_client.SeldonResourceRequirements) | None, replicas: int = 1, secret_name: str | None, model_metadata: Dict[str, Any] = None, extra_args: Dict[str, Any] = None, is_custom_deployment: bool | None = False, spec: Dict[Any, Any] | None = None, serviceAccountName: str | None = None)

Bases: [`ServiceConfig`](zenml.services.md#zenml.services.service.ServiceConfig)

Seldon Core deployment service configuration.

Attributes:
: model_uri: URI of the model (or models) to serve.
  model_name: the name of the model. Multiple versions of the same model
  <br/>
  > should use the same model name.
  <br/>
  implementation: the Seldon Core implementation used to serve the model.
  : The implementation type can be one of the following: TENSORFLOW_SERVER,
    SKLEARN_SERVER, XGBOOST_SERVER, custom.
  <br/>
  replicas: number of replicas to use for the prediction service.
  secret_name: the name of a Kubernetes secret containing additional
  <br/>
  > configuration parameters for the Seldon Core deployment (e.g.
  > credentials to access the Artifact Store).
  <br/>
  model_metadata: optional model metadata information (see
  : [https://docs.seldon.io/projects/seldon-core/en/latest/reference/apis/metadata.html](https://docs.seldon.io/projects/seldon-core/en/latest/reference/apis/metadata.html)).
  <br/>
  extra_args: additional arguments to pass to the Seldon Core deployment
  : resource configuration.
  <br/>
  is_custom_deployment: whether the deployment is a custom deployment
  spec: custom Kubernetes resource specification for the Seldon Core
  serviceAccountName: The name of the Service Account applied to the deployment.

#### *classmethod* create_from_deployment(deployment: [SeldonDeployment](zenml.integrations.seldon.md#zenml.integrations.seldon.seldon_client.SeldonDeployment)) → [SeldonDeploymentConfig](#zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentConfig)

Recreate the configuration of a Seldon Core Service from a deployed instance.

Args:
: deployment: the Seldon Core deployment resource.

Returns:
: The Seldon Core service configuration corresponding to the given
  Seldon Core deployment resource.

Raises:
: ValueError: if the given deployment resource does not contain
  : the expected annotations, or it contains an invalid or
    incompatible Seldon Core service configuration.

#### extra_args *: Dict[str, Any]*

#### get_seldon_deployment_annotations() → Dict[str, str]

Generate annotations for the Seldon Core deployment from the service configuration.

The annotations are used to store additional information about the
Seldon Core service that is associated with the deployment that is
not available in the labels. One annotation particularly important
is the serialized Service configuration itself, which is used to
recreate the service configuration from a remote Seldon deployment.

Returns:
: The annotations for the Seldon Core deployment.

#### get_seldon_deployment_labels() → Dict[str, str]

Generate labels for the Seldon Core deployment from the service configuration.

These labels are attached to the Seldon Core deployment resource
and may be used as label selectors in lookup operations.

Returns:
: The labels for the Seldon Core deployment.

#### implementation *: str*

#### is_custom_deployment *: bool | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'protected_namespaces': ()}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'description': FieldInfo(annotation=str, required=False, default=''), 'extra_args': FieldInfo(annotation=Dict[str, Any], required=False, default_factory=dict), 'implementation': FieldInfo(annotation=str, required=True), 'is_custom_deployment': FieldInfo(annotation=Union[bool, NoneType], required=False, default=False), 'model_metadata': FieldInfo(annotation=Dict[str, Any], required=False, default_factory=dict), 'model_name': FieldInfo(annotation=str, required=False, default='default'), 'model_uri': FieldInfo(annotation=str, required=False, default=''), 'model_version': FieldInfo(annotation=str, required=False, default=''), 'name': FieldInfo(annotation=str, required=False, default=''), 'parameters': FieldInfo(annotation=Union[List[SeldonDeploymentPredictorParameter], NoneType], required=True), 'pipeline_name': FieldInfo(annotation=str, required=False, default=''), 'pipeline_step_name': FieldInfo(annotation=str, required=False, default=''), 'replicas': FieldInfo(annotation=int, required=False, default=1), 'resources': FieldInfo(annotation=Union[SeldonResourceRequirements, NoneType], required=True), 'secret_name': FieldInfo(annotation=Union[str, NoneType], required=True), 'serviceAccountName': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'service_name': FieldInfo(annotation=str, required=False, default=''), 'spec': FieldInfo(annotation=Union[Dict[Any, Any], NoneType], required=False, default_factory=dict), 'type': FieldInfo(annotation=Literal['zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentConfig'], required=False, default='zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentConfig')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_metadata *: Dict[str, Any]*

#### model_name *: str*

#### model_uri *: str*

#### parameters *: List[[SeldonDeploymentPredictorParameter](zenml.integrations.seldon.md#zenml.integrations.seldon.seldon_client.SeldonDeploymentPredictorParameter)] | None*

#### replicas *: int*

#### resources *: [SeldonResourceRequirements](zenml.integrations.seldon.md#zenml.integrations.seldon.seldon_client.SeldonResourceRequirements) | None*

#### secret_name *: str | None*

#### serviceAccountName *: str | None*

#### spec *: Dict[Any, Any] | None*

#### type *: Literal['zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentConfig']*

### *class* zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentService(\*, type: Literal['zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentService'] = 'zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentService', uuid: UUID, admin_state: [ServiceState](zenml.services.md#zenml.services.service_status.ServiceState) = ServiceState.INACTIVE, config: [SeldonDeploymentConfig](#zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentConfig), status: [SeldonDeploymentServiceStatus](#zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentServiceStatus) = None, endpoint: [BaseServiceEndpoint](zenml.services.md#zenml.services.service_endpoint.BaseServiceEndpoint) | None = None)

Bases: [`BaseDeploymentService`](zenml.services.md#zenml.services.service.BaseDeploymentService)

A service that represents a Seldon Core deployment server.

Attributes:
: config: service configuration.
  status: service status.

#### SERVICE_TYPE *: ClassVar[[ServiceType](zenml.services.md#zenml.services.service_type.ServiceType)]* *= ServiceType(type='model-serving', flavor='seldon', name='seldon-deployment', description='Seldon Core prediction service', logo_url='https://public-flavor-logos.s3.eu-central-1.amazonaws.com/model_deployer/seldon.png')*

#### check_status() → Tuple[[ServiceState](zenml.services.md#zenml.services.service_status.ServiceState), str]

Check the the current operational state of the Seldon Core deployment.

Returns:
: The operational state of the Seldon Core deployment and a message
  providing additional information about that state (e.g. a
  description of the error, if one is encountered).

#### config *: [SeldonDeploymentConfig](#zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentConfig)*

#### *classmethod* create_from_deployment(deployment: [SeldonDeployment](zenml.integrations.seldon.md#zenml.integrations.seldon.seldon_client.SeldonDeployment)) → [SeldonDeploymentService](#zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentService)

Recreate a Seldon Core service from a Seldon Core deployment resource.

It should then update their operational status.

Args:
: deployment: the Seldon Core deployment resource.

Returns:
: The Seldon Core service corresponding to the given
  Seldon Core deployment resource.

Raises:
: ValueError: if the given deployment resource does not contain
  : the expected service_uuid label.

#### deprovision(force: bool = False) → None

Deprovision the remote Seldon Core deployment instance.

Args:
: force: if True, the remote deployment instance will be
  : forcefully deprovisioned.

#### get_logs(follow: bool = False, tail: int | None = None) → Generator[str, bool, None]

Get the logs of a Seldon Core model deployment.

Args:
: follow: if True, the logs will be streamed as they are written
  tail: only retrieve the last NUM lines of log output.

Returns:
: A generator that can be accessed to get the service logs.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'validate_assignment': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'admin_state': FieldInfo(annotation=ServiceState, required=False, default=<ServiceState.INACTIVE: 'inactive'>), 'config': FieldInfo(annotation=SeldonDeploymentConfig, required=True), 'endpoint': FieldInfo(annotation=Union[BaseServiceEndpoint, NoneType], required=False, default=None), 'status': FieldInfo(annotation=SeldonDeploymentServiceStatus, required=False, default_factory=<lambda>), 'type': FieldInfo(annotation=Literal['zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentService'], required=False, default='zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentService'), 'uuid': FieldInfo(annotation=UUID, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### predict(request: str) → Any

Make a prediction using the service.

Args:
: request: a numpy array representing the request

Returns:
: A numpy array representing the prediction returned by the service.

Raises:
: Exception: if the service is not yet ready.
  ValueError: if the prediction_url is not set.

#### *property* prediction_url *: str | None*

The prediction URI exposed by the prediction service.

Returns:
: The prediction URI exposed by the prediction service, or None if
  the service is not yet ready.

#### provision() → None

Provision or update remote Seldon Core deployment instance.

This should then match the current configuration.

#### *property* seldon_deployment_name *: str*

Get the name of the Seldon Core deployment.

It should return the one that uniquely corresponds to this service instance.

Returns:
: The name of the Seldon Core deployment.

#### status *: [SeldonDeploymentServiceStatus](#zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentServiceStatus)*

#### type *: Literal['zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentService']*

### *class* zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentServiceStatus(\*, type: Literal['zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentServiceStatus'] = 'zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentServiceStatus', state: [ServiceState](zenml.services.md#zenml.services.service_status.ServiceState) = ServiceState.INACTIVE, last_state: [ServiceState](zenml.services.md#zenml.services.service_status.ServiceState) = ServiceState.INACTIVE, last_error: str = '')

Bases: [`ServiceStatus`](zenml.services.md#zenml.services.service_status.ServiceStatus)

Seldon Core deployment service status.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'last_error': FieldInfo(annotation=str, required=False, default=''), 'last_state': FieldInfo(annotation=ServiceState, required=False, default=<ServiceState.INACTIVE: 'inactive'>), 'state': FieldInfo(annotation=ServiceState, required=False, default=<ServiceState.INACTIVE: 'inactive'>), 'type': FieldInfo(annotation=Literal['zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentServiceStatus'], required=False, default='zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentServiceStatus')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### type *: Literal['zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentServiceStatus']*

## Module contents

Initialization for Seldon services.
