# zenml.model_deployers package

## Submodules

## zenml.model_deployers.base_model_deployer module

Base class for all ZenML model deployers.

### *class* zenml.model_deployers.base_model_deployer.BaseModelDeployer(name: str, id: UUID, config: [StackComponentConfig](zenml.stack.md#zenml.stack.stack_component.StackComponentConfig), flavor: str, type: [StackComponentType](zenml.md#zenml.enums.StackComponentType), user: UUID | None, workspace: UUID, created: datetime, updated: datetime, labels: Dict[str, Any] | None = None, connector_requirements: [ServiceConnectorRequirements](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorRequirements) | None = None, connector: UUID | None = None, connector_resource_id: str | None = None, \*args: Any, \*\*kwargs: Any)

Bases: [`StackComponent`](zenml.stack.md#zenml.stack.stack_component.StackComponent), `ABC`

Base class for all ZenML model deployers.

The model deployer serves three major purposes:

1. It contains all the stack related configuration attributes required to
interact with the remote model serving tool, service or platform (e.g.
hostnames, URLs, references to credentials, other client related
configuration parameters).

2. It implements the continuous deployment logic necessary to deploy models
in a way that updates an existing model server that is already serving a
previous version of the same model instead of creating a new model server
for every new model version (see the deploy_model abstract method).
This functionality can be consumed directly from ZenML pipeline steps, but
it can also be used outside the pipeline to deploy ad hoc models. It is
also usually coupled with a standard model deployer step, implemented by
each integration, that hides the details of the deployment process away from
the user.

3. It acts as a ZenML BaseService registry, where every BaseService instance
is used as an internal representation of a remote model server (see the
find_model_server abstract method). To achieve this, it must be able to
re-create the configuration of a BaseService from information that is
persisted externally, alongside or even part of the remote model server
configuration itself. For example, for model servers that are implemented as
Kubernetes resources, the BaseService instances can be serialized and saved
as Kubernetes resource annotations. This allows the model deployer to keep
track of all externally running model servers and to re-create their
corresponding BaseService instance representations at any given time.
The model deployer also defines methods that implement basic life-cycle
management on remote model servers outside the coverage of a pipeline
(see stop_model_server, start_model_server and delete_model_server).

#### FLAVOR *: ClassVar[Type[[BaseModelDeployerFlavor](#zenml.model_deployers.base_model_deployer.BaseModelDeployerFlavor)]]*

#### NAME *: ClassVar[str]*

#### *property* config *: [BaseModelDeployerConfig](#zenml.model_deployers.base_model_deployer.BaseModelDeployerConfig)*

Returns the BaseModelDeployerConfig config.

Returns:
: The configuration.

#### delete_model_server(uuid: UUID, timeout: int = 300, force: bool = False) → None

Abstract method to delete a model server.

This operation is irreversible. A deleted model server must no longer
show up in the list of model servers returned by find_model_server.

Args:
: uuid: UUID of the model server to stop.
  timeout: timeout in seconds to wait for the service to stop. If
  <br/>
  > set to 0, the method will return immediately after
  > deprovisioning the service, without waiting for it to stop.
  <br/>
  force: if True, force the service to stop.

Raises:
: RuntimeError: if the model server is not found.

#### deploy_model(config: [ServiceConfig](zenml.services.md#zenml.services.service.ServiceConfig), service_type: [ServiceType](zenml.services.md#zenml.services.service_type.ServiceType), replace: bool = False, continuous_deployment_mode: bool = False, timeout: int = 300) → [BaseService](zenml.services.md#zenml.services.service.BaseService)

Deploy a model.

the deploy_model method is the main entry point for deploying models
using the model deployer. It is used to deploy a model to a model server
instance that is running on a remote serving platform or service. The
method is responsible for detecting if there is an existing model server
instance running serving one or more previous versions of the same model
and deploying the model to the serving platform or updating the existing
model server instance to include the new model version. The method
returns a Service object that is a representation of the external model
server instance. The Service object must implement basic operational
state tracking and lifecycle management operations for the model server
(e.g. start, stop, etc.).

Args:
: config: Custom Service configuration parameters for the model
  : deployer. Can include the pipeline name, the run id, the step
    name, the model name, the model uri, the model type etc.
  <br/>
  replace: If True, it will replace any existing model server instances
  : that serve the same model. If False, it does not replace any
    existing model server instance.
  <br/>
  continuous_deployment_mode: If True, it will replace any existing
  : model server instances that serve the same model, regardless of
    the configuration. If False, it will only replace existing model
    server instances that serve the same model if the configuration
    is exactly the same.
  <br/>
  timeout: The maximum time in seconds to wait for the model server
  : to start serving the model.
  <br/>
  service_type: The type of the service to deploy. If not provided,
  : the default service type of the model deployer will be used.

Raises:
: RuntimeError: if the model deployment fails.

Returns:
: The deployment Service object.

#### find_model_server(config: Dict[str, Any] | None = None, running: bool | None = None, service_uuid: UUID | None = None, pipeline_name: str | None = None, pipeline_step_name: str | None = None, service_name: str | None = None, model_name: str | None = None, model_version: str | None = None, service_type: [ServiceType](zenml.services.md#zenml.services.service_type.ServiceType) | None = None, type: str | None = None, flavor: str | None = None, pipeline_run_id: str | None = None) → List[[BaseService](zenml.services.md#zenml.services.service.BaseService)]

Abstract method to find one or more a model servers that match the given criteria.

Args:
: running: If true, only running services will be returned.
  service_uuid: The UUID of the service that was originally used
  <br/>
  > to deploy the model.
  <br/>
  pipeline_step_name: The name of the pipeline step that was originally used
  : to deploy the model.
  <br/>
  pipeline_name: The name of the pipeline that was originally used to deploy
  : the model from the model registry.
  <br/>
  model_name: The name of the model that was originally used to deploy
  : the model from the model registry.
  <br/>
  model_version: The version of the model that was originally used to
  : deploy the model from the model registry.
  <br/>
  service_type: The type of the service to find.
  type: The type of the service to find.
  flavor: The flavor of the service to find.
  pipeline_run_id: The UUID of the pipeline run that was originally used
  <br/>
  > to deploy the model.
  <br/>
  config: Custom Service configuration parameters for the model
  : deployer. Can include the pipeline name, the run id, the step
    name, the model name, the model uri, the model type etc.
  <br/>
  service_name: The name of the service to find.

Returns:
: One or more Service objects representing model servers that match
  the input search criteria.

#### *classmethod* get_active_model_deployer() → [BaseModelDeployer](#zenml.model_deployers.base_model_deployer.BaseModelDeployer)

Get the model deployer registered in the active stack.

Returns:
: The model deployer registered in the active stack.

Raises:
: TypeError: if a model deployer is not part of the
  : active stack.

#### *abstract static* get_model_server_info(service: [BaseService](zenml.services.md#zenml.services.service.BaseService)) → Dict[str, str | None]

Give implementation specific way to extract relevant model server properties for the user.

Args:
: service: Integration-specific service instance

Returns:
: A dictionary containing the relevant model server properties.

#### get_model_server_logs(uuid: UUID, follow: bool = False, tail: int | None = None) → Generator[str, bool, None]

Get the logs of a model server.

Args:
: uuid: UUID of the model server to get the logs of.
  follow: if True, the logs will be streamed as they are written
  tail: only retrieve the last NUM lines of log output.

Returns:
: A generator that yields the logs of the model server.

Raises:
: RuntimeError: if the model server is not found.

#### load_service(service_id: UUID) → [BaseService](zenml.services.md#zenml.services.service.BaseService)

Load a service from a URI.

Args:
: service_id: The ID of the service to load.

Returns:
: The loaded service.

#### *abstract* perform_delete_model(service: [BaseService](zenml.services.md#zenml.services.service.BaseService), timeout: int = 300, force: bool = False) → None

Abstract method to delete a model server.

This operation is irreversible. A deleted model server must no longer
show up in the list of model servers returned by find_model_server.

Args:
: service: The service to delete.
  timeout: timeout in seconds to wait for the service to stop. If
  <br/>
  > set to 0, the method will return immediately after
  > deprovisioning the service, without waiting for it to stop.
  <br/>
  force: if True, force the service to stop.

#### *abstract* perform_deploy_model(id: UUID, config: [ServiceConfig](zenml.services.md#zenml.services.service.ServiceConfig), timeout: int = 300) → [BaseService](zenml.services.md#zenml.services.service.BaseService)

Abstract method to deploy a model.

Concrete model deployer subclasses must implement the following
functionality in this method:
- Detect if there is an existing model server instance running serving
one or more previous versions of the same model
- Deploy the model to the serving platform or update the existing model
server instance to include the new model version
- Return a Service object that is a representation of the external model
server instance. The Service must implement basic operational state
tracking and lifecycle management operations for the model server (e.g.
start, stop, etc.)

Args:
: id: UUID of the service that was originally used to deploy the model.
  config: Custom Service configuration parameters for the model
  <br/>
  > deployer. Can include the pipeline name, the run id, the step
  > name, the model name, the model uri, the model type etc.
  <br/>
  timeout: The maximum time in seconds to wait for the model server
  : to start serving the model.

Returns:
: The deployment Service object.

#### *abstract* perform_start_model(service: [BaseService](zenml.services.md#zenml.services.service.BaseService), timeout: int = 300) → [BaseService](zenml.services.md#zenml.services.service.BaseService)

Abstract method to start a model server.

Args:
: service: The service to start.
  timeout: timeout in seconds to wait for the service to start. If
  <br/>
  > set to 0, the method will return immediately after
  > provisioning the service, without waiting for it to become
  > active.

#### *abstract* perform_stop_model(service: [BaseService](zenml.services.md#zenml.services.service.BaseService), timeout: int = 300, force: bool = False) → [BaseService](zenml.services.md#zenml.services.service.BaseService)

Abstract method to stop a model server.

This operation should be reversible. A stopped model server should still
show up in the list of model servers returned by find_model_server and
it should be possible to start it again by calling start_model_server.

Args:
: service: The service to stop.
  timeout: timeout in seconds to wait for the service to stop. If
  <br/>
  > set to 0, the method will return immediately after
  > deprovisioning the service, without waiting for it to stop.
  <br/>
  force: if True, force the service to stop.

#### start_model_server(uuid: UUID, timeout: int = 300) → None

Abstract method to start a model server.

Args:
: uuid: UUID of the model server to start.
  timeout: timeout in seconds to wait for the service to start. If
  <br/>
  > set to 0, the method will return immediately after
  > provisioning the service, without waiting for it to become
  > active.

Raises:
: RuntimeError: if the model server is not found.

#### stop_model_server(uuid: UUID, timeout: int = 300, force: bool = False) → None

Abstract method to stop a model server.

This operation should be reversible. A stopped model server should still
show up in the list of model servers returned by find_model_server and
it should be possible to start it again by calling start_model_server.

Args:
: uuid: UUID of the model server to stop.
  timeout: timeout in seconds to wait for the service to stop. If
  <br/>
  > set to 0, the method will return immediately after
  > deprovisioning the service, without waiting for it to stop.
  <br/>
  force: if True, force the service to stop.

Raises:
: RuntimeError: if the model server is not found.

### *class* zenml.model_deployers.base_model_deployer.BaseModelDeployerConfig(warn_about_plain_text_secrets: bool = False)

Bases: [`StackComponentConfig`](zenml.stack.md#zenml.stack.stack_component.StackComponentConfig)

Base config for all model deployers.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.model_deployers.base_model_deployer.BaseModelDeployerFlavor

Bases: [`Flavor`](zenml.stack.md#zenml.stack.flavor.Flavor)

Base class for model deployer flavors.

#### *property* config_class *: Type[[BaseModelDeployerConfig](#zenml.model_deployers.base_model_deployer.BaseModelDeployerConfig)]*

Returns BaseModelDeployerConfig config class.

Returns:
: The config class.

#### *abstract property* implementation_class *: Type[[BaseModelDeployer](#zenml.model_deployers.base_model_deployer.BaseModelDeployer)]*

The class that implements the model deployer.

#### *property* type *: [StackComponentType](zenml.md#zenml.enums.StackComponentType)*

Returns the flavor type.

Returns:
: The flavor type.

### zenml.model_deployers.base_model_deployer.get_model_version_id_if_exists(model_name: str | None, model_version: str | None) → UUID | None

Get the model version id if it exists.

Args:
: model_name: The name of the model.
  model_version: The version of the model.

Returns:
: The model version id if it exists.

## Module contents

Model deployers are stack components responsible for online model serving.

Online serving is the process of hosting and loading machine-learning models as
part of a managed web service and providing access to the models through an API
endpoint like HTTP or GRPC. Once deployed, you can send inference requests
to the model through the web service’s API and receive fast, low-latency
responses.

Add a model deployer to your ZenML stack to be able to implement continuous
model deployment pipelines that train models and continuously deploy them to a
model prediction web service.

When present in a stack, the model deployer also acts as a registry for models
that are served with ZenML. You can use the model deployer to list all models
that are currently deployed for online inference or filtered according
to a particular pipeline run or step, or to suspend, resume or delete
an external model server managed through ZenML.

### *class* zenml.model_deployers.BaseModelDeployer(name: str, id: UUID, config: [StackComponentConfig](zenml.stack.md#zenml.stack.stack_component.StackComponentConfig), flavor: str, type: [StackComponentType](zenml.md#zenml.enums.StackComponentType), user: UUID | None, workspace: UUID, created: datetime, updated: datetime, labels: Dict[str, Any] | None = None, connector_requirements: [ServiceConnectorRequirements](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorRequirements) | None = None, connector: UUID | None = None, connector_resource_id: str | None = None, \*args: Any, \*\*kwargs: Any)

Bases: [`StackComponent`](zenml.stack.md#zenml.stack.stack_component.StackComponent), `ABC`

Base class for all ZenML model deployers.

The model deployer serves three major purposes:

1. It contains all the stack related configuration attributes required to
interact with the remote model serving tool, service or platform (e.g.
hostnames, URLs, references to credentials, other client related
configuration parameters).

2. It implements the continuous deployment logic necessary to deploy models
in a way that updates an existing model server that is already serving a
previous version of the same model instead of creating a new model server
for every new model version (see the deploy_model abstract method).
This functionality can be consumed directly from ZenML pipeline steps, but
it can also be used outside the pipeline to deploy ad hoc models. It is
also usually coupled with a standard model deployer step, implemented by
each integration, that hides the details of the deployment process away from
the user.

3. It acts as a ZenML BaseService registry, where every BaseService instance
is used as an internal representation of a remote model server (see the
find_model_server abstract method). To achieve this, it must be able to
re-create the configuration of a BaseService from information that is
persisted externally, alongside or even part of the remote model server
configuration itself. For example, for model servers that are implemented as
Kubernetes resources, the BaseService instances can be serialized and saved
as Kubernetes resource annotations. This allows the model deployer to keep
track of all externally running model servers and to re-create their
corresponding BaseService instance representations at any given time.
The model deployer also defines methods that implement basic life-cycle
management on remote model servers outside the coverage of a pipeline
(see stop_model_server, start_model_server and delete_model_server).

#### FLAVOR *: ClassVar[Type[[BaseModelDeployerFlavor](#zenml.model_deployers.BaseModelDeployerFlavor)]]*

#### NAME *: ClassVar[str]*

#### *property* config *: [BaseModelDeployerConfig](#zenml.model_deployers.base_model_deployer.BaseModelDeployerConfig)*

Returns the BaseModelDeployerConfig config.

Returns:
: The configuration.

#### delete_model_server(uuid: UUID, timeout: int = 300, force: bool = False) → None

Abstract method to delete a model server.

This operation is irreversible. A deleted model server must no longer
show up in the list of model servers returned by find_model_server.

Args:
: uuid: UUID of the model server to stop.
  timeout: timeout in seconds to wait for the service to stop. If
  <br/>
  > set to 0, the method will return immediately after
  > deprovisioning the service, without waiting for it to stop.
  <br/>
  force: if True, force the service to stop.

Raises:
: RuntimeError: if the model server is not found.

#### deploy_model(config: [ServiceConfig](zenml.services.md#zenml.services.service.ServiceConfig), service_type: [ServiceType](zenml.services.md#zenml.services.service_type.ServiceType), replace: bool = False, continuous_deployment_mode: bool = False, timeout: int = 300) → [BaseService](zenml.services.md#zenml.services.service.BaseService)

Deploy a model.

the deploy_model method is the main entry point for deploying models
using the model deployer. It is used to deploy a model to a model server
instance that is running on a remote serving platform or service. The
method is responsible for detecting if there is an existing model server
instance running serving one or more previous versions of the same model
and deploying the model to the serving platform or updating the existing
model server instance to include the new model version. The method
returns a Service object that is a representation of the external model
server instance. The Service object must implement basic operational
state tracking and lifecycle management operations for the model server
(e.g. start, stop, etc.).

Args:
: config: Custom Service configuration parameters for the model
  : deployer. Can include the pipeline name, the run id, the step
    name, the model name, the model uri, the model type etc.
  <br/>
  replace: If True, it will replace any existing model server instances
  : that serve the same model. If False, it does not replace any
    existing model server instance.
  <br/>
  continuous_deployment_mode: If True, it will replace any existing
  : model server instances that serve the same model, regardless of
    the configuration. If False, it will only replace existing model
    server instances that serve the same model if the configuration
    is exactly the same.
  <br/>
  timeout: The maximum time in seconds to wait for the model server
  : to start serving the model.
  <br/>
  service_type: The type of the service to deploy. If not provided,
  : the default service type of the model deployer will be used.

Raises:
: RuntimeError: if the model deployment fails.

Returns:
: The deployment Service object.

#### find_model_server(config: Dict[str, Any] | None = None, running: bool | None = None, service_uuid: UUID | None = None, pipeline_name: str | None = None, pipeline_step_name: str | None = None, service_name: str | None = None, model_name: str | None = None, model_version: str | None = None, service_type: [ServiceType](zenml.services.md#zenml.services.service_type.ServiceType) | None = None, type: str | None = None, flavor: str | None = None, pipeline_run_id: str | None = None) → List[[BaseService](zenml.services.md#zenml.services.service.BaseService)]

Abstract method to find one or more a model servers that match the given criteria.

Args:
: running: If true, only running services will be returned.
  service_uuid: The UUID of the service that was originally used
  <br/>
  > to deploy the model.
  <br/>
  pipeline_step_name: The name of the pipeline step that was originally used
  : to deploy the model.
  <br/>
  pipeline_name: The name of the pipeline that was originally used to deploy
  : the model from the model registry.
  <br/>
  model_name: The name of the model that was originally used to deploy
  : the model from the model registry.
  <br/>
  model_version: The version of the model that was originally used to
  : deploy the model from the model registry.
  <br/>
  service_type: The type of the service to find.
  type: The type of the service to find.
  flavor: The flavor of the service to find.
  pipeline_run_id: The UUID of the pipeline run that was originally used
  <br/>
  > to deploy the model.
  <br/>
  config: Custom Service configuration parameters for the model
  : deployer. Can include the pipeline name, the run id, the step
    name, the model name, the model uri, the model type etc.
  <br/>
  service_name: The name of the service to find.

Returns:
: One or more Service objects representing model servers that match
  the input search criteria.

#### *classmethod* get_active_model_deployer() → [BaseModelDeployer](#zenml.model_deployers.base_model_deployer.BaseModelDeployer)

Get the model deployer registered in the active stack.

Returns:
: The model deployer registered in the active stack.

Raises:
: TypeError: if a model deployer is not part of the
  : active stack.

#### *abstract static* get_model_server_info(service: [BaseService](zenml.services.md#zenml.services.service.BaseService)) → Dict[str, str | None]

Give implementation specific way to extract relevant model server properties for the user.

Args:
: service: Integration-specific service instance

Returns:
: A dictionary containing the relevant model server properties.

#### get_model_server_logs(uuid: UUID, follow: bool = False, tail: int | None = None) → Generator[str, bool, None]

Get the logs of a model server.

Args:
: uuid: UUID of the model server to get the logs of.
  follow: if True, the logs will be streamed as they are written
  tail: only retrieve the last NUM lines of log output.

Returns:
: A generator that yields the logs of the model server.

Raises:
: RuntimeError: if the model server is not found.

#### load_service(service_id: UUID) → [BaseService](zenml.services.md#zenml.services.service.BaseService)

Load a service from a URI.

Args:
: service_id: The ID of the service to load.

Returns:
: The loaded service.

#### *abstract* perform_delete_model(service: [BaseService](zenml.services.md#zenml.services.service.BaseService), timeout: int = 300, force: bool = False) → None

Abstract method to delete a model server.

This operation is irreversible. A deleted model server must no longer
show up in the list of model servers returned by find_model_server.

Args:
: service: The service to delete.
  timeout: timeout in seconds to wait for the service to stop. If
  <br/>
  > set to 0, the method will return immediately after
  > deprovisioning the service, without waiting for it to stop.
  <br/>
  force: if True, force the service to stop.

#### *abstract* perform_deploy_model(id: UUID, config: [ServiceConfig](zenml.services.md#zenml.services.service.ServiceConfig), timeout: int = 300) → [BaseService](zenml.services.md#zenml.services.service.BaseService)

Abstract method to deploy a model.

Concrete model deployer subclasses must implement the following
functionality in this method:
- Detect if there is an existing model server instance running serving
one or more previous versions of the same model
- Deploy the model to the serving platform or update the existing model
server instance to include the new model version
- Return a Service object that is a representation of the external model
server instance. The Service must implement basic operational state
tracking and lifecycle management operations for the model server (e.g.
start, stop, etc.)

Args:
: id: UUID of the service that was originally used to deploy the model.
  config: Custom Service configuration parameters for the model
  <br/>
  > deployer. Can include the pipeline name, the run id, the step
  > name, the model name, the model uri, the model type etc.
  <br/>
  timeout: The maximum time in seconds to wait for the model server
  : to start serving the model.

Returns:
: The deployment Service object.

#### *abstract* perform_start_model(service: [BaseService](zenml.services.md#zenml.services.service.BaseService), timeout: int = 300) → [BaseService](zenml.services.md#zenml.services.service.BaseService)

Abstract method to start a model server.

Args:
: service: The service to start.
  timeout: timeout in seconds to wait for the service to start. If
  <br/>
  > set to 0, the method will return immediately after
  > provisioning the service, without waiting for it to become
  > active.

#### *abstract* perform_stop_model(service: [BaseService](zenml.services.md#zenml.services.service.BaseService), timeout: int = 300, force: bool = False) → [BaseService](zenml.services.md#zenml.services.service.BaseService)

Abstract method to stop a model server.

This operation should be reversible. A stopped model server should still
show up in the list of model servers returned by find_model_server and
it should be possible to start it again by calling start_model_server.

Args:
: service: The service to stop.
  timeout: timeout in seconds to wait for the service to stop. If
  <br/>
  > set to 0, the method will return immediately after
  > deprovisioning the service, without waiting for it to stop.
  <br/>
  force: if True, force the service to stop.

#### start_model_server(uuid: UUID, timeout: int = 300) → None

Abstract method to start a model server.

Args:
: uuid: UUID of the model server to start.
  timeout: timeout in seconds to wait for the service to start. If
  <br/>
  > set to 0, the method will return immediately after
  > provisioning the service, without waiting for it to become
  > active.

Raises:
: RuntimeError: if the model server is not found.

#### stop_model_server(uuid: UUID, timeout: int = 300, force: bool = False) → None

Abstract method to stop a model server.

This operation should be reversible. A stopped model server should still
show up in the list of model servers returned by find_model_server and
it should be possible to start it again by calling start_model_server.

Args:
: uuid: UUID of the model server to stop.
  timeout: timeout in seconds to wait for the service to stop. If
  <br/>
  > set to 0, the method will return immediately after
  > deprovisioning the service, without waiting for it to stop.
  <br/>
  force: if True, force the service to stop.

Raises:
: RuntimeError: if the model server is not found.

### *class* zenml.model_deployers.BaseModelDeployerFlavor

Bases: [`Flavor`](zenml.stack.md#zenml.stack.flavor.Flavor)

Base class for model deployer flavors.

#### *property* config_class *: Type[[BaseModelDeployerConfig](#zenml.model_deployers.base_model_deployer.BaseModelDeployerConfig)]*

Returns BaseModelDeployerConfig config class.

Returns:
: The config class.

#### *abstract property* implementation_class *: Type[[BaseModelDeployer](#zenml.model_deployers.base_model_deployer.BaseModelDeployer)]*

The class that implements the model deployer.

#### *property* type *: [StackComponentType](zenml.md#zenml.enums.StackComponentType)*

Returns the flavor type.

Returns:
: The flavor type.
