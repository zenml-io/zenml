# zenml.services.local package

## Submodules

## zenml.services.local.local_daemon_entrypoint module

Implementation of a local daemon entrypoint.

This executable file is utilized as an entrypoint for all ZenML services
that are implemented as locally running daemon processes.

## zenml.services.local.local_service module

Implementation of a local ZenML service.

### *class* zenml.services.local.local_service.LocalDaemonService(\*, type: Literal['zenml.services.local.local_service.LocalDaemonService'] = 'zenml.services.local.local_service.LocalDaemonService', uuid: UUID, admin_state: [ServiceState](zenml.services.md#zenml.services.service_status.ServiceState) = ServiceState.INACTIVE, config: [LocalDaemonServiceConfig](#zenml.services.local.local_service.LocalDaemonServiceConfig) = None, status: [LocalDaemonServiceStatus](#zenml.services.local.local_service.LocalDaemonServiceStatus) = None, endpoint: [LocalDaemonServiceEndpoint](#zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpoint) | None = None)

Bases: [`BaseService`](zenml.services.md#zenml.services.service.BaseService)

A service represented by a local daemon process.

This class extends the base service class with functionality concerning
the life-cycle management and tracking of external services implemented as
local daemon processes.

To define a local daemon service, subclass this class and implement the
run method. Upon start, the service will spawn a daemon process that
ends up calling the run method.

For example,

```
``
```

```
`
```

python

from zenml.services import ServiceType, LocalDaemonService, LocalDaemonServiceConfig
import time

class SleepingDaemonConfig(LocalDaemonServiceConfig):

> wake_up_after: int

class SleepingDaemon(LocalDaemonService):

> SERVICE_TYPE = ServiceType(
> : name=”sleeper”,
>   description=”Sleeping daemon”,
>   type=”daemon”,
>   flavor=”sleeping”,

> )
> config: SleepingDaemonConfig

> def run(self) -> None:
> : time.sleep(self.config.wake_up_after)

daemon = SleepingDaemon(config=SleepingDaemonConfig(wake_up_after=10))
daemon.start()

```
``
```

```
`
```

NOTE: the SleepingDaemon class and its parent module have to be
discoverable as part of a ZenML Integration, otherwise the daemon will
fail with the following error:

``
TypeError: Cannot load service with unregistered service type:
name='sleeper' type='daemon' flavor='sleeping' description='Sleeping daemon'
``

Attributes:
: config: service configuration
  status: service status
  endpoint: optional service endpoint

#### SERVICE_TYPE *: ClassVar[[ServiceType](zenml.services.md#zenml.services.service_type.ServiceType)]*

#### admin_state *: [ServiceState](zenml.services.md#zenml.services.service_status.ServiceState)*

#### check_status() → Tuple[[ServiceState](zenml.services.md#zenml.services.service_status.ServiceState), str]

Check the the current operational state of the daemon process.

Returns:
: The operational state of the daemon process and a message
  providing additional information about that state (e.g. a
  description of the error, if one is encountered).

#### config *: [LocalDaemonServiceConfig](#zenml.services.local.local_service.LocalDaemonServiceConfig)*

#### deprovision(force: bool = False) → None

Deprovision the service.

Args:
: force: if True, the service daemon will be forcefully stopped

#### endpoint *: [LocalDaemonServiceEndpoint](#zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpoint) | None*

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

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'admin_state': FieldInfo(annotation=ServiceState, required=False, default=<ServiceState.INACTIVE: 'inactive'>), 'config': FieldInfo(annotation=LocalDaemonServiceConfig, required=False, default_factory=LocalDaemonServiceConfig), 'endpoint': FieldInfo(annotation=Union[LocalDaemonServiceEndpoint, NoneType], required=False, default=None), 'status': FieldInfo(annotation=LocalDaemonServiceStatus, required=False, default_factory=LocalDaemonServiceStatus), 'type': FieldInfo(annotation=Literal['zenml.services.local.local_service.LocalDaemonService'], required=False, default='zenml.services.local.local_service.LocalDaemonService'), 'uuid': FieldInfo(annotation=UUID, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### provision() → None

Provision the service.

#### *abstract* run() → None

Run the service daemon process associated with this service.

Subclasses must implement this method to provide the service daemon
functionality. This method will be executed in the context of the
running daemon, not in the context of the process that calls the
start method.

#### start(timeout: int = 0) → None

Start the service and optionally wait for it to become active.

Args:
: timeout: amount of time to wait for the service to become active.
  : If set to 0, the method will return immediately after checking
    the service status.

#### status *: [LocalDaemonServiceStatus](#zenml.services.local.local_service.LocalDaemonServiceStatus)*

#### type *: Literal['zenml.services.local.local_service.LocalDaemonService']*

#### uuid *: UUID*

### *class* zenml.services.local.local_service.LocalDaemonServiceConfig(\*, type: Literal['zenml.services.local.local_service.LocalDaemonServiceConfig'] = 'zenml.services.local.local_service.LocalDaemonServiceConfig', name: str = '', description: str = '', pipeline_name: str = '', pipeline_step_name: str = '', model_name: str = '', model_version: str = '', service_name: str = '', silent_daemon: bool = False, root_runtime_path: str | None = None, singleton: bool = False, blocking: bool = False)

Bases: [`ServiceConfig`](zenml.services.md#zenml.services.service.ServiceConfig)

Local daemon service configuration.

Attributes:
: silent_daemon: set to True to suppress the output of the daemon
  : (i.e. redirect stdout and stderr to /dev/null). If False, the
    daemon output will be redirected to a logfile.
  <br/>
  root_runtime_path: the root path where the service daemon will store
  : service configuration files
  <br/>
  singleton: set to True to store the service daemon configuration files
  : directly in the root_runtime_path directory instead of creating
    a subdirectory for each service instance. Only has effect if the
    root_runtime_path is also set.
  <br/>
  blocking: set to True to run the service the context of the current
  : process and block until the service is stopped instead of running
    the service as a daemon process. Useful for operating systems
    that do not support daemon processes.

#### blocking *: bool*

#### description *: str*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'protected_namespaces': ()}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'blocking': FieldInfo(annotation=bool, required=False, default=False), 'description': FieldInfo(annotation=str, required=False, default=''), 'model_name': FieldInfo(annotation=str, required=False, default=''), 'model_version': FieldInfo(annotation=str, required=False, default=''), 'name': FieldInfo(annotation=str, required=False, default=''), 'pipeline_name': FieldInfo(annotation=str, required=False, default=''), 'pipeline_step_name': FieldInfo(annotation=str, required=False, default=''), 'root_runtime_path': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'service_name': FieldInfo(annotation=str, required=False, default=''), 'silent_daemon': FieldInfo(annotation=bool, required=False, default=False), 'singleton': FieldInfo(annotation=bool, required=False, default=False), 'type': FieldInfo(annotation=Literal['zenml.services.local.local_service.LocalDaemonServiceConfig'], required=False, default='zenml.services.local.local_service.LocalDaemonServiceConfig')}*

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

#### silent_daemon *: bool*

#### singleton *: bool*

#### type *: Literal['zenml.services.local.local_service.LocalDaemonServiceConfig']*

### *class* zenml.services.local.local_service.LocalDaemonServiceStatus(\*, type: Literal['zenml.services.local.local_service.LocalDaemonServiceStatus'] = 'zenml.services.local.local_service.LocalDaemonServiceStatus', state: [ServiceState](zenml.services.md#zenml.services.service_status.ServiceState) = ServiceState.INACTIVE, last_state: [ServiceState](zenml.services.md#zenml.services.service_status.ServiceState) = ServiceState.INACTIVE, last_error: str = '', runtime_path: str | None = None, silent_daemon: bool = False)

Bases: [`ServiceStatus`](zenml.services.md#zenml.services.service_status.ServiceStatus)

Local daemon service status.

Attributes:
: runtime_path: the path where the service daemon runtime files (the
  : configuration file used to start the service daemon and the
    logfile) are located
  <br/>
  silent_daemon: flag indicating whether the output of the daemon
  : is suppressed (redirected to /dev/null).

#### *property* config_file *: str | None*

Get the path to the configuration file used to start the service daemon.

Returns:
: The path to the configuration file, or None, if the
  service has never been started before.

#### last_error *: str*

#### last_state *: [ServiceState](zenml.services.md#zenml.services.service_status.ServiceState)*

#### *property* log_file *: str | None*

Get the path to the log file where the service output is/has been logged.

Returns:
: The path to the log file, or None, if the service has never been
  started before, or if the service daemon output is suppressed.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'last_error': FieldInfo(annotation=str, required=False, default=''), 'last_state': FieldInfo(annotation=ServiceState, required=False, default=<ServiceState.INACTIVE: 'inactive'>), 'runtime_path': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'silent_daemon': FieldInfo(annotation=bool, required=False, default=False), 'state': FieldInfo(annotation=ServiceState, required=False, default=<ServiceState.INACTIVE: 'inactive'>), 'type': FieldInfo(annotation=Literal['zenml.services.local.local_service.LocalDaemonServiceStatus'], required=False, default='zenml.services.local.local_service.LocalDaemonServiceStatus')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### *property* pid *: int | None*

Return the PID of the currently running daemon.

Returns:
: The PID of the daemon, or None, if the service has never been
  started before.

#### *property* pid_file *: str | None*

Get the path to a daemon PID file.

This is where the last known PID of the daemon process is stored.

Returns:
: The path to the PID file, or None, if the service has never been
  started before.

#### runtime_path *: str | None*

#### silent_daemon *: bool*

#### state *: [ServiceState](zenml.services.md#zenml.services.service_status.ServiceState)*

#### type *: Literal['zenml.services.local.local_service.LocalDaemonServiceStatus']*

## zenml.services.local.local_service_endpoint module

Implementation of a local service endpoint.

### *class* zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpoint(\*args: Any, type: Literal['zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpoint'] = 'zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpoint', admin_state: [ServiceState](zenml.services.md#zenml.services.service_status.ServiceState) = ServiceState.INACTIVE, config: [LocalDaemonServiceEndpointConfig](#zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpointConfig) = None, status: [LocalDaemonServiceEndpointStatus](#zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpointStatus) = None, monitor: Annotated[[HTTPEndpointHealthMonitor](zenml.services.md#zenml.services.service_monitor.HTTPEndpointHealthMonitor) | [TCPEndpointHealthMonitor](zenml.services.md#zenml.services.service_monitor.TCPEndpointHealthMonitor) | None, \_PydanticGeneralMetadata(union_mode='left_to_right')])

Bases: [`BaseServiceEndpoint`](zenml.services.md#zenml.services.service_endpoint.BaseServiceEndpoint)

A service endpoint exposed by a local daemon process.

This class extends the base service endpoint class with functionality
concerning the life-cycle management and tracking of endpoints exposed
by external services implemented as local daemon processes.

Attributes:
: config: service endpoint configuration
  status: service endpoint status
  monitor: optional service endpoint health monitor

#### admin_state *: [ServiceState](zenml.services.md#zenml.services.service_status.ServiceState)*

#### config *: [LocalDaemonServiceEndpointConfig](#zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpointConfig)*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'admin_state': FieldInfo(annotation=ServiceState, required=False, default=<ServiceState.INACTIVE: 'inactive'>), 'config': FieldInfo(annotation=LocalDaemonServiceEndpointConfig, required=False, default_factory=LocalDaemonServiceEndpointConfig), 'monitor': FieldInfo(annotation=Union[HTTPEndpointHealthMonitor, TCPEndpointHealthMonitor, NoneType], required=True, discriminator='type', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'status': FieldInfo(annotation=LocalDaemonServiceEndpointStatus, required=False, default_factory=LocalDaemonServiceEndpointStatus), 'type': FieldInfo(annotation=Literal['zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpoint'], required=False, default='zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpoint')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### monitor *: [HTTPEndpointHealthMonitor](zenml.services.md#zenml.services.service_monitor.HTTPEndpointHealthMonitor) | [TCPEndpointHealthMonitor](zenml.services.md#zenml.services.service_monitor.TCPEndpointHealthMonitor) | None*

#### prepare_for_start() → None

Prepare the service endpoint for starting.

This method is called before the service is started.

#### status *: [LocalDaemonServiceEndpointStatus](#zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpointStatus)*

#### type *: Literal['zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpoint']*

### *class* zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpointConfig(\*, type: Literal['zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpointConfig'] = 'zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpointConfig', name: str = '', description: str = '', protocol: [ServiceEndpointProtocol](zenml.services.md#zenml.services.service_endpoint.ServiceEndpointProtocol) = ServiceEndpointProtocol.TCP, port: int | None = None, ip_address: str = '127.0.0.1', allocate_port: bool = True)

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
  ip_address: the IP address of the service endpoint. If not set, the
  : default localhost IP address will be used.
  <br/>
  allocate_port: set to True to allocate a free TCP port for the
  : service endpoint automatically.

#### allocate_port *: bool*

#### description *: str*

#### ip_address *: str*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'allocate_port': FieldInfo(annotation=bool, required=False, default=True), 'description': FieldInfo(annotation=str, required=False, default=''), 'ip_address': FieldInfo(annotation=str, required=False, default='127.0.0.1'), 'name': FieldInfo(annotation=str, required=False, default=''), 'port': FieldInfo(annotation=Union[int, NoneType], required=False, default=None), 'protocol': FieldInfo(annotation=ServiceEndpointProtocol, required=False, default=<ServiceEndpointProtocol.TCP: 'tcp'>), 'type': FieldInfo(annotation=Literal['zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpointConfig'], required=False, default='zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpointConfig')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### port *: int | None*

#### protocol *: [ServiceEndpointProtocol](zenml.services.md#zenml.services.service_endpoint.ServiceEndpointProtocol)*

#### type *: Literal['zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpointConfig']*

### *class* zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpointStatus(\*, type: Literal['zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpointStatus'] = 'zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpointStatus', state: [ServiceState](zenml.services.md#zenml.services.service_status.ServiceState) = ServiceState.INACTIVE, last_state: [ServiceState](zenml.services.md#zenml.services.service_status.ServiceState) = ServiceState.INACTIVE, last_error: str = '', protocol: [ServiceEndpointProtocol](zenml.services.md#zenml.services.service_endpoint.ServiceEndpointProtocol) = ServiceEndpointProtocol.TCP, hostname: str | None = None, port: int | None = None)

Bases: [`ServiceEndpointStatus`](zenml.services.md#zenml.services.service_endpoint.ServiceEndpointStatus)

Local daemon service endpoint status.

#### hostname *: str | None*

#### last_error *: str*

#### last_state *: [ServiceState](zenml.services.md#zenml.services.service_status.ServiceState)*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'hostname': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'last_error': FieldInfo(annotation=str, required=False, default=''), 'last_state': FieldInfo(annotation=ServiceState, required=False, default=<ServiceState.INACTIVE: 'inactive'>), 'port': FieldInfo(annotation=Union[int, NoneType], required=False, default=None), 'protocol': FieldInfo(annotation=ServiceEndpointProtocol, required=False, default=<ServiceEndpointProtocol.TCP: 'tcp'>), 'state': FieldInfo(annotation=ServiceState, required=False, default=<ServiceState.INACTIVE: 'inactive'>), 'type': FieldInfo(annotation=Literal['zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpointStatus'], required=False, default='zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpointStatus')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### port *: int | None*

#### protocol *: [ServiceEndpointProtocol](zenml.services.md#zenml.services.service_endpoint.ServiceEndpointProtocol)*

#### state *: [ServiceState](zenml.services.md#zenml.services.service_status.ServiceState)*

#### type *: Literal['zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpointStatus']*

## Module contents

Initialization of a local ZenML service.
