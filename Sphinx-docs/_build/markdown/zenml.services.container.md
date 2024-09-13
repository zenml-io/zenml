# zenml.services.container package

## Submodules

## zenml.services.container.container_service module

Implementation of a containerized ZenML service.

### *class* zenml.services.container.container_service.ContainerService(\*, type: Literal['zenml.services.container.container_service.ContainerService'] = 'zenml.services.container.container_service.ContainerService', uuid: UUID, admin_state: [ServiceState](zenml.services.md#zenml.services.service_status.ServiceState) = ServiceState.INACTIVE, config: [ContainerServiceConfig](#zenml.services.container.container_service.ContainerServiceConfig) = None, status: [ContainerServiceStatus](#zenml.services.container.container_service.ContainerServiceStatus) = None, endpoint: [ContainerServiceEndpoint](#zenml.services.container.container_service_endpoint.ContainerServiceEndpoint) | None = None)

Bases: [`BaseService`](zenml.services.md#zenml.services.service.BaseService)

A service represented by a containerized process.

This class extends the base service class with functionality concerning
the life-cycle management and tracking of external services implemented as
docker containers.

To define a containerized service, subclass this class and implement the
run method. Upon start, the service will spawn a container that
ends up calling the run method.

For example,

```
``
```

```
`
```

python

from zenml.services import ServiceType, ContainerService, ContainerServiceConfig
import time

class SleepingServiceConfig(ContainerServiceConfig):

> wake_up_after: int

class SleepingService(ContainerService):

> SERVICE_TYPE = ServiceType(
> : name=”sleeper”,
>   description=”Sleeping container”,
>   type=”container”,
>   flavor=”sleeping”,

> )
> config: SleepingServiceConfig

> def run(self) -> None:
> : time.sleep(self.config.wake_up_after)

service = SleepingService(config=SleepingServiceConfig(wake_up_after=10))
service.start()

```
``
```

```
`
```

NOTE: the SleepingService class and its parent module have to be
discoverable as part of a ZenML Integration, otherwise the daemon will
fail with the following error:

``
TypeError: Cannot load service with unregistered service type:
name='sleeper' type='container' flavor='sleeping' description='Sleeping container'
``

Attributes:
: config: service configuration
  status: service status
  endpoint: optional service endpoint

#### SERVICE_TYPE *: ClassVar[[ServiceType](zenml.services.md#zenml.services.service_type.ServiceType)]*

#### admin_state *: [ServiceState](zenml.services.md#zenml.services.service_status.ServiceState)*

#### check_status() → Tuple[[ServiceState](zenml.services.md#zenml.services.service_status.ServiceState), str]

Check the the current operational state of the docker container.

Returns:
: The operational state of the docker container and a message
  providing additional information about that state (e.g. a
  description of the error, if one is encountered).

#### config *: [ContainerServiceConfig](#zenml.services.container.container_service.ContainerServiceConfig)*

#### *property* container *: Container | None*

Get the docker container for the service.

Returns:
: The docker container for the service, or None if the container
  does not exist.

#### *property* container_id *: str*

Get the ID of the docker container for a service.

Returns:
: The ID of the docker container for the service.

#### deprovision(force: bool = False) → None

Deprovision the service.

Args:
: force: if True, the service container will be forcefully stopped

#### *property* docker_client *: DockerClient*

Initialize and/or return the docker client.

Returns:
: The docker client.

#### endpoint *: [ContainerServiceEndpoint](#zenml.services.container.container_service_endpoint.ContainerServiceEndpoint) | None*

#### get_logs(follow: bool = False, tail: int | None = None) → Generator[str, bool, None]

Retrieve the service logs.

Args:
: follow: if True, the logs will be streamed as they are written
  tail: only retrieve the last NUM lines of log output.

Yields:
: A generator that can be accessed to get the service logs.

#### get_service_status_message() → str

Get a message about the current operational state of the service.

Returns:
: A message providing information about the current operational
  state of the service.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'validate_assignment': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'admin_state': FieldInfo(annotation=ServiceState, required=False, default=<ServiceState.INACTIVE: 'inactive'>), 'config': FieldInfo(annotation=ContainerServiceConfig, required=False, default_factory=ContainerServiceConfig), 'endpoint': FieldInfo(annotation=Union[ContainerServiceEndpoint, NoneType], required=False, default=None), 'status': FieldInfo(annotation=ContainerServiceStatus, required=False, default_factory=ContainerServiceStatus), 'type': FieldInfo(annotation=Literal['zenml.services.container.container_service.ContainerService'], required=False, default='zenml.services.container.container_service.ContainerService'), 'uuid': FieldInfo(annotation=UUID, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

This function is meant to behave like a BaseModel method to initialise private attributes.

It takes context as an argument since that’s what pydantic-core passes when calling it.

Args:
: self: The BaseModel instance.
  context: The context.

#### provision() → None

Provision the service.

#### *abstract* run() → None

Run the containerized service logic associated with this service.

Subclasses must implement this method to provide the containerized
service functionality. This method will be executed in the context of
the running container, not in the context of the process that calls the
start method.

#### status *: [ContainerServiceStatus](#zenml.services.container.container_service.ContainerServiceStatus)*

#### type *: Literal['zenml.services.container.container_service.ContainerService']*

#### uuid *: UUID*

### *class* zenml.services.container.container_service.ContainerServiceConfig(\*, type: Literal['zenml.services.container.container_service.ContainerServiceConfig'] = 'zenml.services.container.container_service.ContainerServiceConfig', name: str = '', description: str = '', pipeline_name: str = '', pipeline_step_name: str = '', model_name: str = '', model_version: str = '', service_name: str = '', root_runtime_path: str | None = None, singleton: bool = False, image: str = 'zenmldocker/zenml')

Bases: [`ServiceConfig`](zenml.services.md#zenml.services.service.ServiceConfig)

containerized service configuration.

Attributes:
: root_runtime_path: the root path where the service stores its files.
  singleton: set to True to store the service files directly in the
  <br/>
  > root_runtime_path directory instead of creating a subdirectory for
  > each service instance. Only has effect if the root_runtime_path is
  > also set.
  <br/>
  image: the container image to use for the service.

#### description *: str*

#### image *: str*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'protected_namespaces': ()}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'description': FieldInfo(annotation=str, required=False, default=''), 'image': FieldInfo(annotation=str, required=False, default='zenmldocker/zenml'), 'model_name': FieldInfo(annotation=str, required=False, default=''), 'model_version': FieldInfo(annotation=str, required=False, default=''), 'name': FieldInfo(annotation=str, required=False, default=''), 'pipeline_name': FieldInfo(annotation=str, required=False, default=''), 'pipeline_step_name': FieldInfo(annotation=str, required=False, default=''), 'root_runtime_path': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'service_name': FieldInfo(annotation=str, required=False, default=''), 'singleton': FieldInfo(annotation=bool, required=False, default=False), 'type': FieldInfo(annotation=Literal['zenml.services.container.container_service.ContainerServiceConfig'], required=False, default='zenml.services.container.container_service.ContainerServiceConfig')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_name *: str*

#### model_version *: str*

#### name *: str*

#### pipeline_name *: str*

#### pipeline_step_name *: str*

#### root_runtime_path *: str | None*

#### service_name *: str*

#### singleton *: bool*

#### type *: Literal['zenml.services.container.container_service.ContainerServiceConfig']*

### *class* zenml.services.container.container_service.ContainerServiceStatus(\*, type: Literal['zenml.services.container.container_service.ContainerServiceStatus'] = 'zenml.services.container.container_service.ContainerServiceStatus', state: [ServiceState](zenml.services.md#zenml.services.service_status.ServiceState) = ServiceState.INACTIVE, last_state: [ServiceState](zenml.services.md#zenml.services.service_status.ServiceState) = ServiceState.INACTIVE, last_error: str = '', runtime_path: str | None = None)

Bases: [`ServiceStatus`](zenml.services.md#zenml.services.service_status.ServiceStatus)

containerized service status.

Attributes:
: runtime_path: the path where the service files (e.g. the configuration
  : file used to start the service daemon and the logfile) are located

#### *property* config_file *: str | None*

Get the path to the service configuration file.

Returns:
: The path to the configuration file, or None, if the
  service has never been started before.

#### last_error *: str*

#### last_state *: [ServiceState](zenml.services.md#zenml.services.service_status.ServiceState)*

#### *property* log_file *: str | None*

Get the path to the log file where the service output is/has been logged.

Returns:
: The path to the log file, or None, if the service has never been
  started before.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'last_error': FieldInfo(annotation=str, required=False, default=''), 'last_state': FieldInfo(annotation=ServiceState, required=False, default=<ServiceState.INACTIVE: 'inactive'>), 'runtime_path': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'state': FieldInfo(annotation=ServiceState, required=False, default=<ServiceState.INACTIVE: 'inactive'>), 'type': FieldInfo(annotation=Literal['zenml.services.container.container_service.ContainerServiceStatus'], required=False, default='zenml.services.container.container_service.ContainerServiceStatus')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### runtime_path *: str | None*

#### state *: [ServiceState](zenml.services.md#zenml.services.service_status.ServiceState)*

#### type *: Literal['zenml.services.container.container_service.ContainerServiceStatus']*

## zenml.services.container.container_service_endpoint module

Implementation of a containerized service endpoint.

### *class* zenml.services.container.container_service_endpoint.ContainerServiceEndpoint(\*args: Any, type: Literal['zenml.services.container.container_service_endpoint.ContainerServiceEndpoint'] = 'zenml.services.container.container_service_endpoint.ContainerServiceEndpoint', admin_state: [ServiceState](zenml.services.md#zenml.services.service_status.ServiceState) = ServiceState.INACTIVE, config: [ContainerServiceEndpointConfig](#zenml.services.container.container_service_endpoint.ContainerServiceEndpointConfig) = None, status: [ContainerServiceEndpointStatus](#zenml.services.container.container_service_endpoint.ContainerServiceEndpointStatus) = None, monitor: Annotated[[HTTPEndpointHealthMonitor](zenml.services.md#zenml.services.service_monitor.HTTPEndpointHealthMonitor) | [TCPEndpointHealthMonitor](zenml.services.md#zenml.services.service_monitor.TCPEndpointHealthMonitor) | None, \_PydanticGeneralMetadata(union_mode='left_to_right')])

Bases: [`BaseServiceEndpoint`](zenml.services.md#zenml.services.service_endpoint.BaseServiceEndpoint)

A service endpoint exposed by a containerized process.

This class extends the base service endpoint class with functionality
concerning the life-cycle management and tracking of endpoints exposed
by external services implemented as containerized processes.

Attributes:
: config: service endpoint configuration
  status: service endpoint status
  monitor: optional service endpoint health monitor

#### admin_state *: [ServiceState](zenml.services.md#zenml.services.service_status.ServiceState)*

#### config *: [ContainerServiceEndpointConfig](#zenml.services.container.container_service_endpoint.ContainerServiceEndpointConfig)*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'admin_state': FieldInfo(annotation=ServiceState, required=False, default=<ServiceState.INACTIVE: 'inactive'>), 'config': FieldInfo(annotation=ContainerServiceEndpointConfig, required=False, default_factory=ContainerServiceEndpointConfig), 'monitor': FieldInfo(annotation=Union[HTTPEndpointHealthMonitor, TCPEndpointHealthMonitor, NoneType], required=True, discriminator='type', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'status': FieldInfo(annotation=ContainerServiceEndpointStatus, required=False, default_factory=ContainerServiceEndpointStatus), 'type': FieldInfo(annotation=Literal['zenml.services.container.container_service_endpoint.ContainerServiceEndpoint'], required=False, default='zenml.services.container.container_service_endpoint.ContainerServiceEndpoint')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### monitor *: [HTTPEndpointHealthMonitor](zenml.services.md#zenml.services.service_monitor.HTTPEndpointHealthMonitor) | [TCPEndpointHealthMonitor](zenml.services.md#zenml.services.service_monitor.TCPEndpointHealthMonitor) | None*

#### prepare_for_start() → None

Prepare the service endpoint for starting.

This method is called before the service is started.

#### status *: [ContainerServiceEndpointStatus](#zenml.services.container.container_service_endpoint.ContainerServiceEndpointStatus)*

#### type *: Literal['zenml.services.container.container_service_endpoint.ContainerServiceEndpoint']*

### *class* zenml.services.container.container_service_endpoint.ContainerServiceEndpointConfig(\*, type: Literal['zenml.services.container.container_service_endpoint.ContainerServiceEndpointConfig'] = 'zenml.services.container.container_service_endpoint.ContainerServiceEndpointConfig', name: str = '', description: str = '', protocol: [ServiceEndpointProtocol](zenml.services.md#zenml.services.service_endpoint.ServiceEndpointProtocol) = ServiceEndpointProtocol.TCP, port: int | None = None, allocate_port: bool = True)

Bases: [`ServiceEndpointConfig`](zenml.services.md#zenml.services.service_endpoint.ServiceEndpointConfig)

Local daemon service endpoint configuration.

Attributes:
: protocol: the TCP protocol implemented by the service endpoint
  port: preferred TCP port value for the service endpoint. If the port
  <br/>
  > is in use when the service is started, setting allocate_port to
  > True will also try to allocate a new port value, otherwise an
  > exception will be raised.
  <br/>
  allocate_port: set to True to allocate a free TCP port for the
  : service endpoint automatically.

#### allocate_port *: bool*

#### description *: str*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'allocate_port': FieldInfo(annotation=bool, required=False, default=True), 'description': FieldInfo(annotation=str, required=False, default=''), 'name': FieldInfo(annotation=str, required=False, default=''), 'port': FieldInfo(annotation=Union[int, NoneType], required=False, default=None), 'protocol': FieldInfo(annotation=ServiceEndpointProtocol, required=False, default=<ServiceEndpointProtocol.TCP: 'tcp'>), 'type': FieldInfo(annotation=Literal['zenml.services.container.container_service_endpoint.ContainerServiceEndpointConfig'], required=False, default='zenml.services.container.container_service_endpoint.ContainerServiceEndpointConfig')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### port *: int | None*

#### protocol *: [ServiceEndpointProtocol](zenml.services.md#zenml.services.service_endpoint.ServiceEndpointProtocol)*

#### type *: Literal['zenml.services.container.container_service_endpoint.ContainerServiceEndpointConfig']*

### *class* zenml.services.container.container_service_endpoint.ContainerServiceEndpointStatus(\*, type: Literal['zenml.services.container.container_service_endpoint.ContainerServiceEndpointStatus'] = 'zenml.services.container.container_service_endpoint.ContainerServiceEndpointStatus', state: [ServiceState](zenml.services.md#zenml.services.service_status.ServiceState) = ServiceState.INACTIVE, last_state: [ServiceState](zenml.services.md#zenml.services.service_status.ServiceState) = ServiceState.INACTIVE, last_error: str = '', protocol: [ServiceEndpointProtocol](zenml.services.md#zenml.services.service_endpoint.ServiceEndpointProtocol) = ServiceEndpointProtocol.TCP, hostname: str | None = None, port: int | None = None)

Bases: [`ServiceEndpointStatus`](zenml.services.md#zenml.services.service_endpoint.ServiceEndpointStatus)

Local daemon service endpoint status.

#### hostname *: str | None*

#### last_error *: str*

#### last_state *: [ServiceState](zenml.services.md#zenml.services.service_status.ServiceState)*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'hostname': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'last_error': FieldInfo(annotation=str, required=False, default=''), 'last_state': FieldInfo(annotation=ServiceState, required=False, default=<ServiceState.INACTIVE: 'inactive'>), 'port': FieldInfo(annotation=Union[int, NoneType], required=False, default=None), 'protocol': FieldInfo(annotation=ServiceEndpointProtocol, required=False, default=<ServiceEndpointProtocol.TCP: 'tcp'>), 'state': FieldInfo(annotation=ServiceState, required=False, default=<ServiceState.INACTIVE: 'inactive'>), 'type': FieldInfo(annotation=Literal['zenml.services.container.container_service_endpoint.ContainerServiceEndpointStatus'], required=False, default='zenml.services.container.container_service_endpoint.ContainerServiceEndpointStatus')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### port *: int | None*

#### protocol *: [ServiceEndpointProtocol](zenml.services.md#zenml.services.service_endpoint.ServiceEndpointProtocol)*

#### state *: [ServiceState](zenml.services.md#zenml.services.service_status.ServiceState)*

#### type *: Literal['zenml.services.container.container_service_endpoint.ContainerServiceEndpointStatus']*

## zenml.services.container.entrypoint module

Implementation of a containerized service entrypoint.

This executable file is utilized as an entrypoint for all ZenML services
that are implemented as locally running docker containers.

### zenml.services.container.entrypoint.launch_service(service_config_file: str) → None

Instantiate and launch a ZenML local service from its configuration file.

Args:
: service_config_file: the path to the service configuration file.

Raises:
: TypeError: if the service configuration file is the wrong type.

## Module contents

Initialization of a containerized ZenML service.
