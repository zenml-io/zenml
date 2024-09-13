# zenml.services package

## Subpackages

* [zenml.services.container package](zenml.services.container.md)
  * [Submodules](zenml.services.container.md#submodules)
  * [zenml.services.container.container_service module](zenml.services.container.md#module-zenml.services.container.container_service)
    * [`ContainerService`](zenml.services.container.md#zenml.services.container.container_service.ContainerService)
      * [`ContainerService.SERVICE_TYPE`](zenml.services.container.md#zenml.services.container.container_service.ContainerService.SERVICE_TYPE)
      * [`ContainerService.admin_state`](zenml.services.container.md#zenml.services.container.container_service.ContainerService.admin_state)
      * [`ContainerService.check_status()`](zenml.services.container.md#zenml.services.container.container_service.ContainerService.check_status)
      * [`ContainerService.config`](zenml.services.container.md#zenml.services.container.container_service.ContainerService.config)
      * [`ContainerService.container`](zenml.services.container.md#zenml.services.container.container_service.ContainerService.container)
      * [`ContainerService.container_id`](zenml.services.container.md#zenml.services.container.container_service.ContainerService.container_id)
      * [`ContainerService.deprovision()`](zenml.services.container.md#zenml.services.container.container_service.ContainerService.deprovision)
      * [`ContainerService.docker_client`](zenml.services.container.md#zenml.services.container.container_service.ContainerService.docker_client)
      * [`ContainerService.endpoint`](zenml.services.container.md#zenml.services.container.container_service.ContainerService.endpoint)
      * [`ContainerService.get_logs()`](zenml.services.container.md#zenml.services.container.container_service.ContainerService.get_logs)
      * [`ContainerService.get_service_status_message()`](zenml.services.container.md#zenml.services.container.container_service.ContainerService.get_service_status_message)
      * [`ContainerService.model_computed_fields`](zenml.services.container.md#zenml.services.container.container_service.ContainerService.model_computed_fields)
      * [`ContainerService.model_config`](zenml.services.container.md#zenml.services.container.container_service.ContainerService.model_config)
      * [`ContainerService.model_fields`](zenml.services.container.md#zenml.services.container.container_service.ContainerService.model_fields)
      * [`ContainerService.model_post_init()`](zenml.services.container.md#zenml.services.container.container_service.ContainerService.model_post_init)
      * [`ContainerService.provision()`](zenml.services.container.md#zenml.services.container.container_service.ContainerService.provision)
      * [`ContainerService.run()`](zenml.services.container.md#zenml.services.container.container_service.ContainerService.run)
      * [`ContainerService.status`](zenml.services.container.md#zenml.services.container.container_service.ContainerService.status)
      * [`ContainerService.type`](zenml.services.container.md#zenml.services.container.container_service.ContainerService.type)
      * [`ContainerService.uuid`](zenml.services.container.md#zenml.services.container.container_service.ContainerService.uuid)
    * [`ContainerServiceConfig`](zenml.services.container.md#zenml.services.container.container_service.ContainerServiceConfig)
      * [`ContainerServiceConfig.description`](zenml.services.container.md#zenml.services.container.container_service.ContainerServiceConfig.description)
      * [`ContainerServiceConfig.image`](zenml.services.container.md#zenml.services.container.container_service.ContainerServiceConfig.image)
      * [`ContainerServiceConfig.model_computed_fields`](zenml.services.container.md#zenml.services.container.container_service.ContainerServiceConfig.model_computed_fields)
      * [`ContainerServiceConfig.model_config`](zenml.services.container.md#zenml.services.container.container_service.ContainerServiceConfig.model_config)
      * [`ContainerServiceConfig.model_fields`](zenml.services.container.md#zenml.services.container.container_service.ContainerServiceConfig.model_fields)
      * [`ContainerServiceConfig.model_name`](zenml.services.container.md#zenml.services.container.container_service.ContainerServiceConfig.model_name)
      * [`ContainerServiceConfig.model_version`](zenml.services.container.md#zenml.services.container.container_service.ContainerServiceConfig.model_version)
      * [`ContainerServiceConfig.name`](zenml.services.container.md#zenml.services.container.container_service.ContainerServiceConfig.name)
      * [`ContainerServiceConfig.pipeline_name`](zenml.services.container.md#zenml.services.container.container_service.ContainerServiceConfig.pipeline_name)
      * [`ContainerServiceConfig.pipeline_step_name`](zenml.services.container.md#zenml.services.container.container_service.ContainerServiceConfig.pipeline_step_name)
      * [`ContainerServiceConfig.root_runtime_path`](zenml.services.container.md#zenml.services.container.container_service.ContainerServiceConfig.root_runtime_path)
      * [`ContainerServiceConfig.service_name`](zenml.services.container.md#zenml.services.container.container_service.ContainerServiceConfig.service_name)
      * [`ContainerServiceConfig.singleton`](zenml.services.container.md#zenml.services.container.container_service.ContainerServiceConfig.singleton)
      * [`ContainerServiceConfig.type`](zenml.services.container.md#zenml.services.container.container_service.ContainerServiceConfig.type)
    * [`ContainerServiceStatus`](zenml.services.container.md#zenml.services.container.container_service.ContainerServiceStatus)
      * [`ContainerServiceStatus.config_file`](zenml.services.container.md#zenml.services.container.container_service.ContainerServiceStatus.config_file)
      * [`ContainerServiceStatus.last_error`](zenml.services.container.md#zenml.services.container.container_service.ContainerServiceStatus.last_error)
      * [`ContainerServiceStatus.last_state`](zenml.services.container.md#zenml.services.container.container_service.ContainerServiceStatus.last_state)
      * [`ContainerServiceStatus.log_file`](zenml.services.container.md#zenml.services.container.container_service.ContainerServiceStatus.log_file)
      * [`ContainerServiceStatus.model_computed_fields`](zenml.services.container.md#zenml.services.container.container_service.ContainerServiceStatus.model_computed_fields)
      * [`ContainerServiceStatus.model_config`](zenml.services.container.md#zenml.services.container.container_service.ContainerServiceStatus.model_config)
      * [`ContainerServiceStatus.model_fields`](zenml.services.container.md#zenml.services.container.container_service.ContainerServiceStatus.model_fields)
      * [`ContainerServiceStatus.runtime_path`](zenml.services.container.md#zenml.services.container.container_service.ContainerServiceStatus.runtime_path)
      * [`ContainerServiceStatus.state`](zenml.services.container.md#zenml.services.container.container_service.ContainerServiceStatus.state)
      * [`ContainerServiceStatus.type`](zenml.services.container.md#zenml.services.container.container_service.ContainerServiceStatus.type)
  * [zenml.services.container.container_service_endpoint module](zenml.services.container.md#module-zenml.services.container.container_service_endpoint)
    * [`ContainerServiceEndpoint`](zenml.services.container.md#zenml.services.container.container_service_endpoint.ContainerServiceEndpoint)
      * [`ContainerServiceEndpoint.admin_state`](zenml.services.container.md#zenml.services.container.container_service_endpoint.ContainerServiceEndpoint.admin_state)
      * [`ContainerServiceEndpoint.config`](zenml.services.container.md#zenml.services.container.container_service_endpoint.ContainerServiceEndpoint.config)
      * [`ContainerServiceEndpoint.model_computed_fields`](zenml.services.container.md#zenml.services.container.container_service_endpoint.ContainerServiceEndpoint.model_computed_fields)
      * [`ContainerServiceEndpoint.model_config`](zenml.services.container.md#zenml.services.container.container_service_endpoint.ContainerServiceEndpoint.model_config)
      * [`ContainerServiceEndpoint.model_fields`](zenml.services.container.md#zenml.services.container.container_service_endpoint.ContainerServiceEndpoint.model_fields)
      * [`ContainerServiceEndpoint.monitor`](zenml.services.container.md#zenml.services.container.container_service_endpoint.ContainerServiceEndpoint.monitor)
      * [`ContainerServiceEndpoint.prepare_for_start()`](zenml.services.container.md#zenml.services.container.container_service_endpoint.ContainerServiceEndpoint.prepare_for_start)
      * [`ContainerServiceEndpoint.status`](zenml.services.container.md#zenml.services.container.container_service_endpoint.ContainerServiceEndpoint.status)
      * [`ContainerServiceEndpoint.type`](zenml.services.container.md#zenml.services.container.container_service_endpoint.ContainerServiceEndpoint.type)
    * [`ContainerServiceEndpointConfig`](zenml.services.container.md#zenml.services.container.container_service_endpoint.ContainerServiceEndpointConfig)
      * [`ContainerServiceEndpointConfig.allocate_port`](zenml.services.container.md#zenml.services.container.container_service_endpoint.ContainerServiceEndpointConfig.allocate_port)
      * [`ContainerServiceEndpointConfig.description`](zenml.services.container.md#zenml.services.container.container_service_endpoint.ContainerServiceEndpointConfig.description)
      * [`ContainerServiceEndpointConfig.model_computed_fields`](zenml.services.container.md#zenml.services.container.container_service_endpoint.ContainerServiceEndpointConfig.model_computed_fields)
      * [`ContainerServiceEndpointConfig.model_config`](zenml.services.container.md#zenml.services.container.container_service_endpoint.ContainerServiceEndpointConfig.model_config)
      * [`ContainerServiceEndpointConfig.model_fields`](zenml.services.container.md#zenml.services.container.container_service_endpoint.ContainerServiceEndpointConfig.model_fields)
      * [`ContainerServiceEndpointConfig.name`](zenml.services.container.md#zenml.services.container.container_service_endpoint.ContainerServiceEndpointConfig.name)
      * [`ContainerServiceEndpointConfig.port`](zenml.services.container.md#zenml.services.container.container_service_endpoint.ContainerServiceEndpointConfig.port)
      * [`ContainerServiceEndpointConfig.protocol`](zenml.services.container.md#zenml.services.container.container_service_endpoint.ContainerServiceEndpointConfig.protocol)
      * [`ContainerServiceEndpointConfig.type`](zenml.services.container.md#zenml.services.container.container_service_endpoint.ContainerServiceEndpointConfig.type)
    * [`ContainerServiceEndpointStatus`](zenml.services.container.md#zenml.services.container.container_service_endpoint.ContainerServiceEndpointStatus)
      * [`ContainerServiceEndpointStatus.hostname`](zenml.services.container.md#zenml.services.container.container_service_endpoint.ContainerServiceEndpointStatus.hostname)
      * [`ContainerServiceEndpointStatus.last_error`](zenml.services.container.md#zenml.services.container.container_service_endpoint.ContainerServiceEndpointStatus.last_error)
      * [`ContainerServiceEndpointStatus.last_state`](zenml.services.container.md#zenml.services.container.container_service_endpoint.ContainerServiceEndpointStatus.last_state)
      * [`ContainerServiceEndpointStatus.model_computed_fields`](zenml.services.container.md#zenml.services.container.container_service_endpoint.ContainerServiceEndpointStatus.model_computed_fields)
      * [`ContainerServiceEndpointStatus.model_config`](zenml.services.container.md#zenml.services.container.container_service_endpoint.ContainerServiceEndpointStatus.model_config)
      * [`ContainerServiceEndpointStatus.model_fields`](zenml.services.container.md#zenml.services.container.container_service_endpoint.ContainerServiceEndpointStatus.model_fields)
      * [`ContainerServiceEndpointStatus.port`](zenml.services.container.md#zenml.services.container.container_service_endpoint.ContainerServiceEndpointStatus.port)
      * [`ContainerServiceEndpointStatus.protocol`](zenml.services.container.md#zenml.services.container.container_service_endpoint.ContainerServiceEndpointStatus.protocol)
      * [`ContainerServiceEndpointStatus.state`](zenml.services.container.md#zenml.services.container.container_service_endpoint.ContainerServiceEndpointStatus.state)
      * [`ContainerServiceEndpointStatus.type`](zenml.services.container.md#zenml.services.container.container_service_endpoint.ContainerServiceEndpointStatus.type)
  * [zenml.services.container.entrypoint module](zenml.services.container.md#module-zenml.services.container.entrypoint)
    * [`launch_service()`](zenml.services.container.md#zenml.services.container.entrypoint.launch_service)
  * [Module contents](zenml.services.container.md#module-zenml.services.container)
* [zenml.services.local package](zenml.services.local.md)
  * [Submodules](zenml.services.local.md#submodules)
  * [zenml.services.local.local_daemon_entrypoint module](zenml.services.local.md#module-zenml.services.local.local_daemon_entrypoint)
  * [zenml.services.local.local_service module](zenml.services.local.md#module-zenml.services.local.local_service)
    * [`LocalDaemonService`](zenml.services.local.md#zenml.services.local.local_service.LocalDaemonService)
      * [`LocalDaemonService.SERVICE_TYPE`](zenml.services.local.md#zenml.services.local.local_service.LocalDaemonService.SERVICE_TYPE)
      * [`LocalDaemonService.admin_state`](zenml.services.local.md#zenml.services.local.local_service.LocalDaemonService.admin_state)
      * [`LocalDaemonService.check_status()`](zenml.services.local.md#zenml.services.local.local_service.LocalDaemonService.check_status)
      * [`LocalDaemonService.config`](zenml.services.local.md#zenml.services.local.local_service.LocalDaemonService.config)
      * [`LocalDaemonService.deprovision()`](zenml.services.local.md#zenml.services.local.local_service.LocalDaemonService.deprovision)
      * [`LocalDaemonService.endpoint`](zenml.services.local.md#zenml.services.local.local_service.LocalDaemonService.endpoint)
      * [`LocalDaemonService.get_logs()`](zenml.services.local.md#zenml.services.local.local_service.LocalDaemonService.get_logs)
      * [`LocalDaemonService.get_service_status_message()`](zenml.services.local.md#zenml.services.local.local_service.LocalDaemonService.get_service_status_message)
      * [`LocalDaemonService.model_computed_fields`](zenml.services.local.md#zenml.services.local.local_service.LocalDaemonService.model_computed_fields)
      * [`LocalDaemonService.model_config`](zenml.services.local.md#zenml.services.local.local_service.LocalDaemonService.model_config)
      * [`LocalDaemonService.model_fields`](zenml.services.local.md#zenml.services.local.local_service.LocalDaemonService.model_fields)
      * [`LocalDaemonService.provision()`](zenml.services.local.md#zenml.services.local.local_service.LocalDaemonService.provision)
      * [`LocalDaemonService.run()`](zenml.services.local.md#zenml.services.local.local_service.LocalDaemonService.run)
      * [`LocalDaemonService.start()`](zenml.services.local.md#zenml.services.local.local_service.LocalDaemonService.start)
      * [`LocalDaemonService.status`](zenml.services.local.md#zenml.services.local.local_service.LocalDaemonService.status)
      * [`LocalDaemonService.type`](zenml.services.local.md#zenml.services.local.local_service.LocalDaemonService.type)
      * [`LocalDaemonService.uuid`](zenml.services.local.md#zenml.services.local.local_service.LocalDaemonService.uuid)
    * [`LocalDaemonServiceConfig`](zenml.services.local.md#zenml.services.local.local_service.LocalDaemonServiceConfig)
      * [`LocalDaemonServiceConfig.blocking`](zenml.services.local.md#zenml.services.local.local_service.LocalDaemonServiceConfig.blocking)
      * [`LocalDaemonServiceConfig.description`](zenml.services.local.md#zenml.services.local.local_service.LocalDaemonServiceConfig.description)
      * [`LocalDaemonServiceConfig.model_computed_fields`](zenml.services.local.md#zenml.services.local.local_service.LocalDaemonServiceConfig.model_computed_fields)
      * [`LocalDaemonServiceConfig.model_config`](zenml.services.local.md#zenml.services.local.local_service.LocalDaemonServiceConfig.model_config)
      * [`LocalDaemonServiceConfig.model_fields`](zenml.services.local.md#zenml.services.local.local_service.LocalDaemonServiceConfig.model_fields)
      * [`LocalDaemonServiceConfig.model_name`](zenml.services.local.md#zenml.services.local.local_service.LocalDaemonServiceConfig.model_name)
      * [`LocalDaemonServiceConfig.model_version`](zenml.services.local.md#zenml.services.local.local_service.LocalDaemonServiceConfig.model_version)
      * [`LocalDaemonServiceConfig.name`](zenml.services.local.md#zenml.services.local.local_service.LocalDaemonServiceConfig.name)
      * [`LocalDaemonServiceConfig.pipeline_name`](zenml.services.local.md#zenml.services.local.local_service.LocalDaemonServiceConfig.pipeline_name)
      * [`LocalDaemonServiceConfig.pipeline_step_name`](zenml.services.local.md#zenml.services.local.local_service.LocalDaemonServiceConfig.pipeline_step_name)
      * [`LocalDaemonServiceConfig.root_runtime_path`](zenml.services.local.md#zenml.services.local.local_service.LocalDaemonServiceConfig.root_runtime_path)
      * [`LocalDaemonServiceConfig.service_name`](zenml.services.local.md#zenml.services.local.local_service.LocalDaemonServiceConfig.service_name)
      * [`LocalDaemonServiceConfig.silent_daemon`](zenml.services.local.md#zenml.services.local.local_service.LocalDaemonServiceConfig.silent_daemon)
      * [`LocalDaemonServiceConfig.singleton`](zenml.services.local.md#zenml.services.local.local_service.LocalDaemonServiceConfig.singleton)
      * [`LocalDaemonServiceConfig.type`](zenml.services.local.md#zenml.services.local.local_service.LocalDaemonServiceConfig.type)
    * [`LocalDaemonServiceStatus`](zenml.services.local.md#zenml.services.local.local_service.LocalDaemonServiceStatus)
      * [`LocalDaemonServiceStatus.config_file`](zenml.services.local.md#zenml.services.local.local_service.LocalDaemonServiceStatus.config_file)
      * [`LocalDaemonServiceStatus.last_error`](zenml.services.local.md#zenml.services.local.local_service.LocalDaemonServiceStatus.last_error)
      * [`LocalDaemonServiceStatus.last_state`](zenml.services.local.md#zenml.services.local.local_service.LocalDaemonServiceStatus.last_state)
      * [`LocalDaemonServiceStatus.log_file`](zenml.services.local.md#zenml.services.local.local_service.LocalDaemonServiceStatus.log_file)
      * [`LocalDaemonServiceStatus.model_computed_fields`](zenml.services.local.md#zenml.services.local.local_service.LocalDaemonServiceStatus.model_computed_fields)
      * [`LocalDaemonServiceStatus.model_config`](zenml.services.local.md#zenml.services.local.local_service.LocalDaemonServiceStatus.model_config)
      * [`LocalDaemonServiceStatus.model_fields`](zenml.services.local.md#zenml.services.local.local_service.LocalDaemonServiceStatus.model_fields)
      * [`LocalDaemonServiceStatus.pid`](zenml.services.local.md#zenml.services.local.local_service.LocalDaemonServiceStatus.pid)
      * [`LocalDaemonServiceStatus.pid_file`](zenml.services.local.md#zenml.services.local.local_service.LocalDaemonServiceStatus.pid_file)
      * [`LocalDaemonServiceStatus.runtime_path`](zenml.services.local.md#zenml.services.local.local_service.LocalDaemonServiceStatus.runtime_path)
      * [`LocalDaemonServiceStatus.silent_daemon`](zenml.services.local.md#zenml.services.local.local_service.LocalDaemonServiceStatus.silent_daemon)
      * [`LocalDaemonServiceStatus.state`](zenml.services.local.md#zenml.services.local.local_service.LocalDaemonServiceStatus.state)
      * [`LocalDaemonServiceStatus.type`](zenml.services.local.md#zenml.services.local.local_service.LocalDaemonServiceStatus.type)
  * [zenml.services.local.local_service_endpoint module](zenml.services.local.md#module-zenml.services.local.local_service_endpoint)
    * [`LocalDaemonServiceEndpoint`](zenml.services.local.md#zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpoint)
      * [`LocalDaemonServiceEndpoint.admin_state`](zenml.services.local.md#zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpoint.admin_state)
      * [`LocalDaemonServiceEndpoint.config`](zenml.services.local.md#zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpoint.config)
      * [`LocalDaemonServiceEndpoint.model_computed_fields`](zenml.services.local.md#zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpoint.model_computed_fields)
      * [`LocalDaemonServiceEndpoint.model_config`](zenml.services.local.md#zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpoint.model_config)
      * [`LocalDaemonServiceEndpoint.model_fields`](zenml.services.local.md#zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpoint.model_fields)
      * [`LocalDaemonServiceEndpoint.monitor`](zenml.services.local.md#zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpoint.monitor)
      * [`LocalDaemonServiceEndpoint.prepare_for_start()`](zenml.services.local.md#zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpoint.prepare_for_start)
      * [`LocalDaemonServiceEndpoint.status`](zenml.services.local.md#zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpoint.status)
      * [`LocalDaemonServiceEndpoint.type`](zenml.services.local.md#zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpoint.type)
    * [`LocalDaemonServiceEndpointConfig`](zenml.services.local.md#zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpointConfig)
      * [`LocalDaemonServiceEndpointConfig.allocate_port`](zenml.services.local.md#zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpointConfig.allocate_port)
      * [`LocalDaemonServiceEndpointConfig.description`](zenml.services.local.md#zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpointConfig.description)
      * [`LocalDaemonServiceEndpointConfig.ip_address`](zenml.services.local.md#zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpointConfig.ip_address)
      * [`LocalDaemonServiceEndpointConfig.model_computed_fields`](zenml.services.local.md#zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpointConfig.model_computed_fields)
      * [`LocalDaemonServiceEndpointConfig.model_config`](zenml.services.local.md#zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpointConfig.model_config)
      * [`LocalDaemonServiceEndpointConfig.model_fields`](zenml.services.local.md#zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpointConfig.model_fields)
      * [`LocalDaemonServiceEndpointConfig.name`](zenml.services.local.md#zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpointConfig.name)
      * [`LocalDaemonServiceEndpointConfig.port`](zenml.services.local.md#zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpointConfig.port)
      * [`LocalDaemonServiceEndpointConfig.protocol`](zenml.services.local.md#zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpointConfig.protocol)
      * [`LocalDaemonServiceEndpointConfig.type`](zenml.services.local.md#zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpointConfig.type)
    * [`LocalDaemonServiceEndpointStatus`](zenml.services.local.md#zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpointStatus)
      * [`LocalDaemonServiceEndpointStatus.hostname`](zenml.services.local.md#zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpointStatus.hostname)
      * [`LocalDaemonServiceEndpointStatus.last_error`](zenml.services.local.md#zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpointStatus.last_error)
      * [`LocalDaemonServiceEndpointStatus.last_state`](zenml.services.local.md#zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpointStatus.last_state)
      * [`LocalDaemonServiceEndpointStatus.model_computed_fields`](zenml.services.local.md#zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpointStatus.model_computed_fields)
      * [`LocalDaemonServiceEndpointStatus.model_config`](zenml.services.local.md#zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpointStatus.model_config)
      * [`LocalDaemonServiceEndpointStatus.model_fields`](zenml.services.local.md#zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpointStatus.model_fields)
      * [`LocalDaemonServiceEndpointStatus.port`](zenml.services.local.md#zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpointStatus.port)
      * [`LocalDaemonServiceEndpointStatus.protocol`](zenml.services.local.md#zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpointStatus.protocol)
      * [`LocalDaemonServiceEndpointStatus.state`](zenml.services.local.md#zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpointStatus.state)
      * [`LocalDaemonServiceEndpointStatus.type`](zenml.services.local.md#zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpointStatus.type)
  * [Module contents](zenml.services.local.md#module-zenml.services.local)
* [zenml.services.terraform package](zenml.services.terraform.md)
  * [Submodules](zenml.services.terraform.md#submodules)
  * [zenml.services.terraform.terraform_service module](zenml.services.terraform.md#zenml-services-terraform-terraform-service-module)
  * [Module contents](zenml.services.terraform.md#module-zenml.services.terraform)

## Submodules

## zenml.services.service module

Implementation of the ZenML Service class.

### *class* zenml.services.service.BaseDeploymentService(\*, type: Literal['zenml.services.service.BaseDeploymentService'] = 'zenml.services.service.BaseDeploymentService', uuid: UUID, admin_state: [ServiceState](#zenml.services.service_status.ServiceState) = ServiceState.INACTIVE, config: [ServiceConfig](#zenml.services.service.ServiceConfig), status: [ServiceStatus](#zenml.services.service_status.ServiceStatus), endpoint: [BaseServiceEndpoint](#zenml.services.service_endpoint.BaseServiceEndpoint) | None = None)

Bases: [`BaseService`](#zenml.services.service.BaseService)

Base class for deployment services.

#### *property* healthcheck_url *: str | None*

Gets the healthcheck URL for the endpoint.

Returns:
: the healthcheck URL for the endpoint

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'validate_assignment': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'admin_state': FieldInfo(annotation=ServiceState, required=False, default=<ServiceState.INACTIVE: 'inactive'>), 'config': FieldInfo(annotation=ServiceConfig, required=True), 'endpoint': FieldInfo(annotation=Union[BaseServiceEndpoint, NoneType], required=False, default=None), 'status': FieldInfo(annotation=ServiceStatus, required=True), 'type': FieldInfo(annotation=Literal['zenml.services.service.BaseDeploymentService'], required=False, default='zenml.services.service.BaseDeploymentService'), 'uuid': FieldInfo(annotation=UUID, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### *property* prediction_url *: str | None*

Gets the prediction URL for the endpoint.

Returns:
: the prediction URL for the endpoint

#### type *: Literal['zenml.services.service.BaseDeploymentService']*

### *class* zenml.services.service.BaseService(\*, type: Literal['zenml.services.service.BaseService'] = 'zenml.services.service.BaseService', uuid: UUID, admin_state: [ServiceState](#zenml.services.service_status.ServiceState) = ServiceState.INACTIVE, config: [ServiceConfig](#zenml.services.service.ServiceConfig), status: [ServiceStatus](#zenml.services.service_status.ServiceStatus), endpoint: [BaseServiceEndpoint](#zenml.services.service_endpoint.BaseServiceEndpoint) | None = None)

Bases: [`BaseTypedModel`](zenml.utils.md#zenml.utils.typed_model.BaseTypedModel)

Base service class.

This class implements generic functionality concerning the life-cycle
management and tracking of an external service (e.g. process, container,
Kubernetes deployment etc.).

Attributes:
: SERVICE_TYPE: a service type descriptor with information describing
  : the service class. Every concrete service class must define this.
  <br/>
  admin_state: the administrative state of the service.
  uuid: unique UUID identifier for the service instance.
  config: service configuration
  status: service status
  endpoint: optional service endpoint

#### SERVICE_TYPE *: ClassVar[[ServiceType](#zenml.services.service_type.ServiceType)]*

#### admin_state *: [ServiceState](#zenml.services.service_status.ServiceState)*

#### *abstract* check_status() → Tuple[[ServiceState](#zenml.services.service_status.ServiceState), str]

Check the the current operational state of the external service.

This method should be overridden by subclasses that implement
concrete service tracking functionality.

Returns:
: The operational state of the external service and a message
  providing additional information about that state (e.g. a
  description of the error if one is encountered while checking the
  service status).

#### config *: [ServiceConfig](#zenml.services.service.ServiceConfig)*

#### deprovision(force: bool = False) → None

Deprovisions all resources used by the service.

Args:
: force: if True, the service will be deprovisioned even if it is
  : in a failed state.

Raises:
: NotImplementedError: if the service does not implement
  : deprovisioning functionality.

#### endpoint *: [BaseServiceEndpoint](#zenml.services.service_endpoint.BaseServiceEndpoint) | None*

#### *classmethod* from_json(json_str: str) → [BaseTypedModel](zenml.utils.md#zenml.utils.typed_model.BaseTypedModel)

Loads a service from a JSON string.

Args:
: json_str: the JSON string to load from.

Returns:
: The loaded service object.

#### *classmethod* from_model(model: [ServiceResponse](zenml.models.md#zenml.models.ServiceResponse)) → [BaseService](#zenml.services.service.BaseService)

Loads a service from a model.

Args:
: model: The ServiceResponse to load from.

Returns:
: The loaded service object.

Raises:
: ValueError: if the service source is not found in the model.

#### get_healthcheck_url() → str | None

Gets the healthcheck URL for the endpoint.

Returns:
: the healthcheck URL for the endpoint

#### *abstract* get_logs(follow: bool = False, tail: int | None = None) → Generator[str, bool, None]

Retrieve the service logs.

This method should be overridden by subclasses that implement
concrete service tracking functionality.

Args:
: follow: if True, the logs will be streamed as they are written
  tail: only retrieve the last NUM lines of log output.

Returns:
: A generator that can be accessed to get the service logs.

#### get_prediction_url() → str | None

Gets the prediction URL for the endpoint.

Returns:
: the prediction URL for the endpoint

#### get_service_status_message() → str

Get a service status message.

Returns:
: A message providing information about the current operational
  state of the service.

#### *property* is_failed *: bool*

Check if the service is currently failed.

This method will actively poll the external service to get its status
and will return the result.

Returns:
: True if the service is in a failure state, otherwise False.

#### *property* is_running *: bool*

Check if the service is currently running.

This method will actively poll the external service to get its status
and will return the result.

Returns:
: True if the service is running and active (i.e. the endpoints are
  responsive, if any are configured), otherwise False.

#### *property* is_stopped *: bool*

Check if the service is currently stopped.

This method will actively poll the external service to get its status
and will return the result.

Returns:
: True if the service is stopped, otherwise False.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'validate_assignment': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'admin_state': FieldInfo(annotation=ServiceState, required=False, default=<ServiceState.INACTIVE: 'inactive'>), 'config': FieldInfo(annotation=ServiceConfig, required=True), 'endpoint': FieldInfo(annotation=Union[BaseServiceEndpoint, NoneType], required=False, default=None), 'status': FieldInfo(annotation=ServiceStatus, required=True), 'type': FieldInfo(annotation=Literal['zenml.services.service.BaseService'], required=False, default='zenml.services.service.BaseService'), 'uuid': FieldInfo(annotation=UUID, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### poll_service_status(timeout: int = 0) → bool

Polls the external service status.

It does this until the service operational state matches the
administrative state, the service enters a failed state, or the timeout
is reached.

Args:
: timeout: maximum time to wait for the service operational state
  : to match the administrative state, in seconds

Returns:
: True if the service operational state matches the administrative
  state, False otherwise.

#### provision() → None

Provisions resources to run the service.

Raises:
: NotImplementedError: if the service does not implement provisioning functionality

#### start(timeout: int = 0) → None

Start the service and optionally wait for it to become active.

Args:
: timeout: amount of time to wait for the service to become active.
  : If set to 0, the method will return immediately after checking
    the service status.

#### status *: [ServiceStatus](#zenml.services.service_status.ServiceStatus)*

#### stop(timeout: int = 0, force: bool = False) → None

Stop the service and optionally wait for it to shutdown.

Args:
: timeout: amount of time to wait for the service to shutdown.
  : If set to 0, the method will return immediately after checking
    the service status.
  <br/>
  force: if True, the service will be stopped even if it is not
  : currently running.

#### type *: Literal['zenml.services.service.BaseService']*

#### update(config: [ServiceConfig](#zenml.services.service.ServiceConfig)) → None

Update the service configuration.

Args:
: config: the new service configuration.

#### update_status() → None

Update the status of the service.

Check the current operational state of the external service
and update the local operational status information to reflect it.

This method should be overridden by subclasses that implement
concrete service status tracking functionality.

#### uuid *: UUID*

### *class* zenml.services.service.ServiceConfig(\*, type: Literal['zenml.services.service.ServiceConfig'] = 'zenml.services.service.ServiceConfig', name: str = '', description: str = '', pipeline_name: str = '', pipeline_step_name: str = '', model_name: str = '', model_version: str = '', service_name: str = '')

Bases: [`BaseTypedModel`](zenml.utils.md#zenml.utils.typed_model.BaseTypedModel)

Generic service configuration.

Concrete service classes should extend this class and add additional
attributes that they want to see reflected and used in the service
configuration.

Attributes:
: name: name for the service instance
  description: description of the service
  pipeline_name: name of the pipeline that spun up the service
  pipeline_step_name: name of the pipeline step that spun up the service
  run_name: name of the pipeline run that spun up the service.

#### description *: str*

#### get_service_labels() → Dict[str, str]

Get the service labels.

Returns:
: a dictionary of service labels.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'protected_namespaces': ()}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'description': FieldInfo(annotation=str, required=False, default=''), 'model_name': FieldInfo(annotation=str, required=False, default=''), 'model_version': FieldInfo(annotation=str, required=False, default=''), 'name': FieldInfo(annotation=str, required=False, default=''), 'pipeline_name': FieldInfo(annotation=str, required=False, default=''), 'pipeline_step_name': FieldInfo(annotation=str, required=False, default=''), 'service_name': FieldInfo(annotation=str, required=False, default=''), 'type': FieldInfo(annotation=Literal['zenml.services.service.ServiceConfig'], required=False, default='zenml.services.service.ServiceConfig')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_name *: str*

#### model_version *: str*

#### name *: str*

#### pipeline_name *: str*

#### pipeline_step_name *: str*

#### service_name *: str*

#### type *: Literal['zenml.services.service.ServiceConfig']*

### zenml.services.service.update_service_status(pre_status: [ServiceState](#zenml.services.service_status.ServiceState) | None = None, post_status: [ServiceState](#zenml.services.service_status.ServiceState) | None = None, error_status: [ServiceState](#zenml.services.service_status.ServiceState) = ServiceState.ERROR) → Callable[[T], T]

A decorator to update the service status before and after a method call.

This decorator is used to wrap service methods and update the service status
before and after the method call. If the method raises an exception, the
service status is updated to reflect the error state.

Args:
: pre_status: the status to update before the method call.
  post_status: the status to update after the method call.
  error_status: the status to update if the method raises an exception.

Returns:
: Callable[…, Any]: The wrapped method with exception handling.

## zenml.services.service_endpoint module

Implementation of a ZenML service endpoint.

### *class* zenml.services.service_endpoint.BaseServiceEndpoint(\*args: Any, type: Literal['zenml.services.service_endpoint.BaseServiceEndpoint'] = 'zenml.services.service_endpoint.BaseServiceEndpoint', admin_state: [ServiceState](#zenml.services.service_status.ServiceState) = ServiceState.INACTIVE, config: [ServiceEndpointConfig](#zenml.services.service_endpoint.ServiceEndpointConfig), status: [ServiceEndpointStatus](#zenml.services.service_endpoint.ServiceEndpointStatus), monitor: [BaseServiceEndpointHealthMonitor](#zenml.services.service_monitor.BaseServiceEndpointHealthMonitor) | None = None)

Bases: [`BaseTypedModel`](zenml.utils.md#zenml.utils.typed_model.BaseTypedModel)

Base service class.

This class implements generic functionality concerning the life-cycle
management and tracking of an external service endpoint (e.g. a HTTP/HTTPS
API or generic TCP endpoint exposed by a service).

Attributes:
: admin_state: the administrative state of the service endpoint
  config: service endpoint configuration
  status: service endpoint status
  monitor: optional service endpoint health monitor

#### admin_state *: [ServiceState](#zenml.services.service_status.ServiceState)*

#### check_status() → Tuple[[ServiceState](#zenml.services.service_status.ServiceState), str]

Check the the current operational state of the external service endpoint.

Returns:
: The operational state of the external service endpoint and a
  message providing additional information about that state
  (e.g. a description of the error, if one is encountered while
  checking the service status).

#### config *: [ServiceEndpointConfig](#zenml.services.service_endpoint.ServiceEndpointConfig)*

#### is_active() → bool

Check if the service endpoint is active.

This means that it is responsive and can receive requests). This method
will use the configured health monitor to actively check the endpoint
status and will return the result.

Returns:
: True if the service endpoint is active, otherwise False.

#### is_inactive() → bool

Check if the service endpoint is inactive.

This means that it is unresponsive and cannot receive requests. This
method will use the configured health monitor to actively check the
endpoint status and will return the result.

Returns:
: True if the service endpoint is inactive, otherwise False.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'admin_state': FieldInfo(annotation=ServiceState, required=False, default=<ServiceState.INACTIVE: 'inactive'>), 'config': FieldInfo(annotation=ServiceEndpointConfig, required=True), 'monitor': FieldInfo(annotation=Union[BaseServiceEndpointHealthMonitor, NoneType], required=False, default=None), 'status': FieldInfo(annotation=ServiceEndpointStatus, required=True), 'type': FieldInfo(annotation=Literal['zenml.services.service_endpoint.BaseServiceEndpoint'], required=False, default='zenml.services.service_endpoint.BaseServiceEndpoint')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### monitor *: [BaseServiceEndpointHealthMonitor](#zenml.services.service_monitor.BaseServiceEndpointHealthMonitor) | None*

#### status *: [ServiceEndpointStatus](#zenml.services.service_endpoint.ServiceEndpointStatus)*

#### type *: Literal['zenml.services.service_endpoint.BaseServiceEndpoint']*

#### update_status() → None

Check the the current operational state of the external service endpoint.

It updates the local operational status information accordingly.

### *class* zenml.services.service_endpoint.ServiceEndpointConfig(\*, type: Literal['zenml.services.service_endpoint.ServiceEndpointConfig'] = 'zenml.services.service_endpoint.ServiceEndpointConfig', name: str = '', description: str = '')

Bases: [`BaseTypedModel`](zenml.utils.md#zenml.utils.typed_model.BaseTypedModel)

Generic service endpoint configuration.

Concrete service classes should extend this class and add additional
attributes that they want to see reflected and use in the endpoint
configuration.

Attributes:
: name: unique name for the service endpoint
  description: description of the service endpoint

#### description *: str*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'description': FieldInfo(annotation=str, required=False, default=''), 'name': FieldInfo(annotation=str, required=False, default=''), 'type': FieldInfo(annotation=Literal['zenml.services.service_endpoint.ServiceEndpointConfig'], required=False, default='zenml.services.service_endpoint.ServiceEndpointConfig')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### type *: Literal['zenml.services.service_endpoint.ServiceEndpointConfig']*

### *class* zenml.services.service_endpoint.ServiceEndpointProtocol(value, names=None, \*, module=None, qualname=None, type=None, start=1, boundary=None)

Bases: [`StrEnum`](zenml.utils.md#zenml.utils.enum_utils.StrEnum)

Possible endpoint protocol values.

#### HTTP *= 'http'*

#### HTTPS *= 'https'*

#### TCP *= 'tcp'*

### *class* zenml.services.service_endpoint.ServiceEndpointStatus(\*, type: Literal['zenml.services.service_endpoint.ServiceEndpointStatus'] = 'zenml.services.service_endpoint.ServiceEndpointStatus', state: [ServiceState](#zenml.services.service_status.ServiceState) = ServiceState.INACTIVE, last_state: [ServiceState](#zenml.services.service_status.ServiceState) = ServiceState.INACTIVE, last_error: str = '', protocol: [ServiceEndpointProtocol](#zenml.services.service_endpoint.ServiceEndpointProtocol) = ServiceEndpointProtocol.TCP, hostname: str | None = None, port: int | None = None)

Bases: [`ServiceStatus`](#zenml.services.service_status.ServiceStatus)

Status information describing the operational state of a service endpoint.

For example, this could be a HTTP/HTTPS API or generic TCP endpoint exposed
by a service. Concrete service classes should extend this class and add
additional attributes that make up the operational state of the service
endpoint.

Attributes:
: protocol: the TCP protocol used by the service endpoint
  hostname: the hostname where the service endpoint is accessible
  port: the current TCP port where the service endpoint is accessible

#### hostname *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'hostname': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'last_error': FieldInfo(annotation=str, required=False, default=''), 'last_state': FieldInfo(annotation=ServiceState, required=False, default=<ServiceState.INACTIVE: 'inactive'>), 'port': FieldInfo(annotation=Union[int, NoneType], required=False, default=None), 'protocol': FieldInfo(annotation=ServiceEndpointProtocol, required=False, default=<ServiceEndpointProtocol.TCP: 'tcp'>), 'state': FieldInfo(annotation=ServiceState, required=False, default=<ServiceState.INACTIVE: 'inactive'>), 'type': FieldInfo(annotation=Literal['zenml.services.service_endpoint.ServiceEndpointStatus'], required=False, default='zenml.services.service_endpoint.ServiceEndpointStatus')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### port *: int | None*

#### protocol *: [ServiceEndpointProtocol](#zenml.services.service_endpoint.ServiceEndpointProtocol)*

#### type *: Literal['zenml.services.service_endpoint.ServiceEndpointStatus']*

#### *property* uri *: str | None*

Get the URI of the service endpoint.

Returns:
: The URI of the service endpoint or None, if the service endpoint
  operational status doesn’t have the required information.

## zenml.services.service_monitor module

Implementation of the service health monitor.

### *class* zenml.services.service_monitor.BaseServiceEndpointHealthMonitor(\*, type: Literal['zenml.services.service_monitor.BaseServiceEndpointHealthMonitor'] = 'zenml.services.service_monitor.BaseServiceEndpointHealthMonitor', config: [ServiceEndpointHealthMonitorConfig](#zenml.services.service_monitor.ServiceEndpointHealthMonitorConfig) = None)

Bases: [`BaseTypedModel`](zenml.utils.md#zenml.utils.typed_model.BaseTypedModel)

Base class used for service endpoint health monitors.

Attributes:
: config: health monitor configuration for endpoint

#### *abstract* check_endpoint_status(endpoint: [BaseServiceEndpoint](#zenml.services.service_endpoint.BaseServiceEndpoint)) → Tuple[[ServiceState](#zenml.services.service_status.ServiceState), str]

Check the the current operational state of the external service endpoint.

Args:
: endpoint: service endpoint to check

This method should be overridden by subclasses that implement
concrete service endpoint tracking functionality.

Returns:
: The operational state of the external service endpoint and an
  optional error message, if an error is encountered while checking
  the service endpoint status.

#### config *: [ServiceEndpointHealthMonitorConfig](#zenml.services.service_monitor.ServiceEndpointHealthMonitorConfig)*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'config': FieldInfo(annotation=ServiceEndpointHealthMonitorConfig, required=False, default_factory=ServiceEndpointHealthMonitorConfig), 'type': FieldInfo(annotation=Literal['zenml.services.service_monitor.BaseServiceEndpointHealthMonitor'], required=False, default='zenml.services.service_monitor.BaseServiceEndpointHealthMonitor')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### type *: Literal['zenml.services.service_monitor.BaseServiceEndpointHealthMonitor']*

### *class* zenml.services.service_monitor.HTTPEndpointHealthMonitor(\*, type: Literal['zenml.services.service_monitor.HTTPEndpointHealthMonitor'] = 'zenml.services.service_monitor.HTTPEndpointHealthMonitor', config: [HTTPEndpointHealthMonitorConfig](#zenml.services.service_monitor.HTTPEndpointHealthMonitorConfig) = None)

Bases: [`BaseServiceEndpointHealthMonitor`](#zenml.services.service_monitor.BaseServiceEndpointHealthMonitor)

HTTP service endpoint health monitor.

Attributes:
: config: health monitor configuration for HTTP endpoint

#### check_endpoint_status(endpoint: [BaseServiceEndpoint](#zenml.services.service_endpoint.BaseServiceEndpoint)) → Tuple[[ServiceState](#zenml.services.service_status.ServiceState), str]

Run a HTTP endpoint API healthcheck.

Args:
: endpoint: service endpoint to check.

Returns:
: The operational state of the external HTTP endpoint and an
  optional message describing that state (e.g. an error message,
  if an error is encountered while checking the HTTP endpoint
  status).

#### config *: [HTTPEndpointHealthMonitorConfig](#zenml.services.service_monitor.HTTPEndpointHealthMonitorConfig)*

#### get_healthcheck_uri(endpoint: [BaseServiceEndpoint](#zenml.services.service_endpoint.BaseServiceEndpoint)) → str | None

Get the healthcheck URI for the given service endpoint.

Args:
: endpoint: service endpoint to get the healthcheck URI for

Returns:
: The healthcheck URI for the given service endpoint or None, if
  the service endpoint doesn’t have a healthcheck URI.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'config': FieldInfo(annotation=HTTPEndpointHealthMonitorConfig, required=False, default_factory=HTTPEndpointHealthMonitorConfig), 'type': FieldInfo(annotation=Literal['zenml.services.service_monitor.HTTPEndpointHealthMonitor'], required=False, default='zenml.services.service_monitor.HTTPEndpointHealthMonitor')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### type *: Literal['zenml.services.service_monitor.HTTPEndpointHealthMonitor']*

### *class* zenml.services.service_monitor.HTTPEndpointHealthMonitorConfig(\*, type: Literal['zenml.services.service_monitor.HTTPEndpointHealthMonitorConfig'] = 'zenml.services.service_monitor.HTTPEndpointHealthMonitorConfig', healthcheck_uri_path: str = '', use_head_request: bool = False, http_status_code: int = 200, http_timeout: int = 5)

Bases: [`ServiceEndpointHealthMonitorConfig`](#zenml.services.service_monitor.ServiceEndpointHealthMonitorConfig)

HTTP service endpoint health monitor configuration.

Attributes:
: healthcheck_uri_path: URI subpath to use to perform service endpoint
  : healthchecks. If not set, the service endpoint URI will be used
    instead.
  <br/>
  use_head_request: set to True to use a HEAD request instead of a GET
  : when calling the healthcheck URI.
  <br/>
  http_status_code: HTTP status code to expect in the health check
  : response.
  <br/>
  http_timeout: HTTP health check request timeout in seconds.

#### healthcheck_uri_path *: str*

#### http_status_code *: int*

#### http_timeout *: int*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'healthcheck_uri_path': FieldInfo(annotation=str, required=False, default=''), 'http_status_code': FieldInfo(annotation=int, required=False, default=200), 'http_timeout': FieldInfo(annotation=int, required=False, default=5), 'type': FieldInfo(annotation=Literal['zenml.services.service_monitor.HTTPEndpointHealthMonitorConfig'], required=False, default='zenml.services.service_monitor.HTTPEndpointHealthMonitorConfig'), 'use_head_request': FieldInfo(annotation=bool, required=False, default=False)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### type *: Literal['zenml.services.service_monitor.HTTPEndpointHealthMonitorConfig']*

#### use_head_request *: bool*

### *class* zenml.services.service_monitor.ServiceEndpointHealthMonitorConfig(\*, type: Literal['zenml.services.service_monitor.ServiceEndpointHealthMonitorConfig'] = 'zenml.services.service_monitor.ServiceEndpointHealthMonitorConfig')

Bases: [`BaseTypedModel`](zenml.utils.md#zenml.utils.typed_model.BaseTypedModel)

Generic service health monitor configuration.

Concrete service classes should extend this class and add additional
attributes that they want to see reflected and use in the health monitor
configuration.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'type': FieldInfo(annotation=Literal['zenml.services.service_monitor.ServiceEndpointHealthMonitorConfig'], required=False, default='zenml.services.service_monitor.ServiceEndpointHealthMonitorConfig')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### type *: Literal['zenml.services.service_monitor.ServiceEndpointHealthMonitorConfig']*

### *class* zenml.services.service_monitor.TCPEndpointHealthMonitor(\*, type: Literal['zenml.services.service_monitor.TCPEndpointHealthMonitor'] = 'zenml.services.service_monitor.TCPEndpointHealthMonitor', config: [TCPEndpointHealthMonitorConfig](#zenml.services.service_monitor.TCPEndpointHealthMonitorConfig))

Bases: [`BaseServiceEndpointHealthMonitor`](#zenml.services.service_monitor.BaseServiceEndpointHealthMonitor)

TCP service endpoint health monitor.

Attributes:
: config: health monitor configuration for TCP endpoint

#### check_endpoint_status(endpoint: [BaseServiceEndpoint](#zenml.services.service_endpoint.BaseServiceEndpoint)) → Tuple[[ServiceState](#zenml.services.service_status.ServiceState), str]

Run a TCP endpoint healthcheck.

Args:
: endpoint: service endpoint to check.

Returns:
: The operational state of the external TCP endpoint and an
  optional message describing that state (e.g. an error message,
  if an error is encountered while checking the TCP endpoint
  status).

#### config *: [TCPEndpointHealthMonitorConfig](#zenml.services.service_monitor.TCPEndpointHealthMonitorConfig)*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'config': FieldInfo(annotation=TCPEndpointHealthMonitorConfig, required=True), 'type': FieldInfo(annotation=Literal['zenml.services.service_monitor.TCPEndpointHealthMonitor'], required=False, default='zenml.services.service_monitor.TCPEndpointHealthMonitor')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### type *: Literal['zenml.services.service_monitor.TCPEndpointHealthMonitor']*

### *class* zenml.services.service_monitor.TCPEndpointHealthMonitorConfig(\*, type: Literal['zenml.services.service_monitor.TCPEndpointHealthMonitorConfig'] = 'zenml.services.service_monitor.TCPEndpointHealthMonitorConfig')

Bases: [`ServiceEndpointHealthMonitorConfig`](#zenml.services.service_monitor.ServiceEndpointHealthMonitorConfig)

TCP service endpoint health monitor configuration.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'type': FieldInfo(annotation=Literal['zenml.services.service_monitor.TCPEndpointHealthMonitorConfig'], required=False, default='zenml.services.service_monitor.TCPEndpointHealthMonitorConfig')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### type *: Literal['zenml.services.service_monitor.TCPEndpointHealthMonitorConfig']*

## zenml.services.service_status module

Implementation of the ServiceStatus class.

### *class* zenml.services.service_status.ServiceState(value, names=None, \*, module=None, qualname=None, type=None, start=1, boundary=None)

Bases: [`StrEnum`](zenml.utils.md#zenml.utils.enum_utils.StrEnum)

Possible states for the service and service endpoint.

#### ACTIVE *= 'active'*

#### ERROR *= 'error'*

#### INACTIVE *= 'inactive'*

#### PENDING_SHUTDOWN *= 'pending_shutdown'*

#### PENDING_STARTUP *= 'pending_startup'*

#### SCALED_TO_ZERO *= 'scaled_to_zero'*

### *class* zenml.services.service_status.ServiceStatus(\*, type: Literal['zenml.services.service_status.ServiceStatus'] = 'zenml.services.service_status.ServiceStatus', state: [ServiceState](#zenml.services.service_status.ServiceState) = ServiceState.INACTIVE, last_state: [ServiceState](#zenml.services.service_status.ServiceState) = ServiceState.INACTIVE, last_error: str = '')

Bases: [`BaseTypedModel`](zenml.utils.md#zenml.utils.typed_model.BaseTypedModel)

Information about the status of a service or process.

This information describes the operational status of an external process or
service tracked by ZenML. This could be a process, container, Kubernetes
deployment etc.

Concrete service classes should extend this class and add additional
attributes that make up the operational state of the service.

Attributes:
: state: the current operational state
  last_state: the operational state prior to the last status update
  last_error: the error encountered during the last status update

#### clear_error() → None

Clear the last error message.

#### last_error *: str*

#### last_state *: [ServiceState](#zenml.services.service_status.ServiceState)*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'last_error': FieldInfo(annotation=str, required=False, default=''), 'last_state': FieldInfo(annotation=ServiceState, required=False, default=<ServiceState.INACTIVE: 'inactive'>), 'state': FieldInfo(annotation=ServiceState, required=False, default=<ServiceState.INACTIVE: 'inactive'>), 'type': FieldInfo(annotation=Literal['zenml.services.service_status.ServiceStatus'], required=False, default='zenml.services.service_status.ServiceStatus')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### state *: [ServiceState](#zenml.services.service_status.ServiceState)*

#### type *: Literal['zenml.services.service_status.ServiceStatus']*

#### update_state(new_state: [ServiceState](#zenml.services.service_status.ServiceState) | None = None, error: str = '') → None

Update the current operational state to reflect a new state value and/or error.

Args:
: new_state: new operational state discovered by the last service
  : status update
  <br/>
  error: error message describing an operational failure encountered
  : during the last service status update

## zenml.services.service_type module

Implementation of a ZenML ServiceType class.

### *class* zenml.services.service_type.ServiceType(\*, type: str, flavor: str, name: str = '', description: str = '', logo_url: str = '')

Bases: `BaseModel`

Service type descriptor.

Attributes:
: type: service type
  flavor: service flavor
  name: name of the service type
  description: description of the service type
  logo_url: logo of the service type

#### description *: str*

#### flavor *: str*

#### logo_url *: str*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'frozen': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'description': FieldInfo(annotation=str, required=False, default=''), 'flavor': FieldInfo(annotation=str, required=True), 'logo_url': FieldInfo(annotation=str, required=False, default=''), 'name': FieldInfo(annotation=str, required=False, default=''), 'type': FieldInfo(annotation=str, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### type *: str*

## Module contents

Initialization of the ZenML services module.

A service is a process or set of processes that outlive a pipeline run.

### *class* zenml.services.BaseService(\*, type: Literal['zenml.services.service.BaseService'] = 'zenml.services.service.BaseService', uuid: UUID, admin_state: [ServiceState](#zenml.services.service_status.ServiceState) = ServiceState.INACTIVE, config: [ServiceConfig](#zenml.services.service.ServiceConfig), status: [ServiceStatus](#zenml.services.service_status.ServiceStatus), endpoint: [BaseServiceEndpoint](#zenml.services.service_endpoint.BaseServiceEndpoint) | None = None)

Bases: [`BaseTypedModel`](zenml.utils.md#zenml.utils.typed_model.BaseTypedModel)

Base service class.

This class implements generic functionality concerning the life-cycle
management and tracking of an external service (e.g. process, container,
Kubernetes deployment etc.).

Attributes:
: SERVICE_TYPE: a service type descriptor with information describing
  : the service class. Every concrete service class must define this.
  <br/>
  admin_state: the administrative state of the service.
  uuid: unique UUID identifier for the service instance.
  config: service configuration
  status: service status
  endpoint: optional service endpoint

#### SERVICE_TYPE *: ClassVar[[ServiceType](#zenml.services.service_type.ServiceType)]*

#### admin_state *: [ServiceState](#zenml.services.service_status.ServiceState)*

#### *abstract* check_status() → Tuple[[ServiceState](#zenml.services.service_status.ServiceState), str]

Check the the current operational state of the external service.

This method should be overridden by subclasses that implement
concrete service tracking functionality.

Returns:
: The operational state of the external service and a message
  providing additional information about that state (e.g. a
  description of the error if one is encountered while checking the
  service status).

#### config *: [ServiceConfig](#zenml.services.service.ServiceConfig)*

#### deprovision(force: bool = False) → None

Deprovisions all resources used by the service.

Args:
: force: if True, the service will be deprovisioned even if it is
  : in a failed state.

Raises:
: NotImplementedError: if the service does not implement
  : deprovisioning functionality.

#### endpoint *: [BaseServiceEndpoint](#zenml.services.service_endpoint.BaseServiceEndpoint) | None*

#### *classmethod* from_json(json_str: str) → [BaseTypedModel](zenml.utils.md#zenml.utils.typed_model.BaseTypedModel)

Loads a service from a JSON string.

Args:
: json_str: the JSON string to load from.

Returns:
: The loaded service object.

#### *classmethod* from_model(model: [ServiceResponse](zenml.models.md#zenml.models.ServiceResponse)) → [BaseService](#zenml.services.BaseService)

Loads a service from a model.

Args:
: model: The ServiceResponse to load from.

Returns:
: The loaded service object.

Raises:
: ValueError: if the service source is not found in the model.

#### get_healthcheck_url() → str | None

Gets the healthcheck URL for the endpoint.

Returns:
: the healthcheck URL for the endpoint

#### *abstract* get_logs(follow: bool = False, tail: int | None = None) → Generator[str, bool, None]

Retrieve the service logs.

This method should be overridden by subclasses that implement
concrete service tracking functionality.

Args:
: follow: if True, the logs will be streamed as they are written
  tail: only retrieve the last NUM lines of log output.

Returns:
: A generator that can be accessed to get the service logs.

#### get_prediction_url() → str | None

Gets the prediction URL for the endpoint.

Returns:
: the prediction URL for the endpoint

#### get_service_status_message() → str

Get a service status message.

Returns:
: A message providing information about the current operational
  state of the service.

#### *property* is_failed *: bool*

Check if the service is currently failed.

This method will actively poll the external service to get its status
and will return the result.

Returns:
: True if the service is in a failure state, otherwise False.

#### *property* is_running *: bool*

Check if the service is currently running.

This method will actively poll the external service to get its status
and will return the result.

Returns:
: True if the service is running and active (i.e. the endpoints are
  responsive, if any are configured), otherwise False.

#### *property* is_stopped *: bool*

Check if the service is currently stopped.

This method will actively poll the external service to get its status
and will return the result.

Returns:
: True if the service is stopped, otherwise False.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'validate_assignment': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'admin_state': FieldInfo(annotation=ServiceState, required=False, default=<ServiceState.INACTIVE: 'inactive'>), 'config': FieldInfo(annotation=ServiceConfig, required=True), 'endpoint': FieldInfo(annotation=Union[BaseServiceEndpoint, NoneType], required=False, default=None), 'status': FieldInfo(annotation=ServiceStatus, required=True), 'type': FieldInfo(annotation=Literal['zenml.services.service.BaseService'], required=False, default='zenml.services.service.BaseService'), 'uuid': FieldInfo(annotation=UUID, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### poll_service_status(timeout: int = 0) → bool

Polls the external service status.

It does this until the service operational state matches the
administrative state, the service enters a failed state, or the timeout
is reached.

Args:
: timeout: maximum time to wait for the service operational state
  : to match the administrative state, in seconds

Returns:
: True if the service operational state matches the administrative
  state, False otherwise.

#### provision() → None

Provisions resources to run the service.

Raises:
: NotImplementedError: if the service does not implement provisioning functionality

#### start(timeout: int = 0) → None

Start the service and optionally wait for it to become active.

Args:
: timeout: amount of time to wait for the service to become active.
  : If set to 0, the method will return immediately after checking
    the service status.

#### status *: [ServiceStatus](#zenml.services.service_status.ServiceStatus)*

#### stop(timeout: int = 0, force: bool = False) → None

Stop the service and optionally wait for it to shutdown.

Args:
: timeout: amount of time to wait for the service to shutdown.
  : If set to 0, the method will return immediately after checking
    the service status.
  <br/>
  force: if True, the service will be stopped even if it is not
  : currently running.

#### type *: Literal['zenml.services.service.BaseService']*

#### update(config: [ServiceConfig](#zenml.services.service.ServiceConfig)) → None

Update the service configuration.

Args:
: config: the new service configuration.

#### update_status() → None

Update the status of the service.

Check the current operational state of the external service
and update the local operational status information to reflect it.

This method should be overridden by subclasses that implement
concrete service status tracking functionality.

#### uuid *: UUID*

### *class* zenml.services.BaseServiceEndpoint(\*args: Any, type: Literal['zenml.services.service_endpoint.BaseServiceEndpoint'] = 'zenml.services.service_endpoint.BaseServiceEndpoint', admin_state: [ServiceState](#zenml.services.service_status.ServiceState) = ServiceState.INACTIVE, config: [ServiceEndpointConfig](#zenml.services.service_endpoint.ServiceEndpointConfig), status: [ServiceEndpointStatus](#zenml.services.service_endpoint.ServiceEndpointStatus), monitor: [BaseServiceEndpointHealthMonitor](#zenml.services.service_monitor.BaseServiceEndpointHealthMonitor) | None = None)

Bases: [`BaseTypedModel`](zenml.utils.md#zenml.utils.typed_model.BaseTypedModel)

Base service class.

This class implements generic functionality concerning the life-cycle
management and tracking of an external service endpoint (e.g. a HTTP/HTTPS
API or generic TCP endpoint exposed by a service).

Attributes:
: admin_state: the administrative state of the service endpoint
  config: service endpoint configuration
  status: service endpoint status
  monitor: optional service endpoint health monitor

#### admin_state *: [ServiceState](#zenml.services.service_status.ServiceState)*

#### check_status() → Tuple[[ServiceState](#zenml.services.service_status.ServiceState), str]

Check the the current operational state of the external service endpoint.

Returns:
: The operational state of the external service endpoint and a
  message providing additional information about that state
  (e.g. a description of the error, if one is encountered while
  checking the service status).

#### config *: [ServiceEndpointConfig](#zenml.services.service_endpoint.ServiceEndpointConfig)*

#### is_active() → bool

Check if the service endpoint is active.

This means that it is responsive and can receive requests). This method
will use the configured health monitor to actively check the endpoint
status and will return the result.

Returns:
: True if the service endpoint is active, otherwise False.

#### is_inactive() → bool

Check if the service endpoint is inactive.

This means that it is unresponsive and cannot receive requests. This
method will use the configured health monitor to actively check the
endpoint status and will return the result.

Returns:
: True if the service endpoint is inactive, otherwise False.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'admin_state': FieldInfo(annotation=ServiceState, required=False, default=<ServiceState.INACTIVE: 'inactive'>), 'config': FieldInfo(annotation=ServiceEndpointConfig, required=True), 'monitor': FieldInfo(annotation=Union[BaseServiceEndpointHealthMonitor, NoneType], required=False, default=None), 'status': FieldInfo(annotation=ServiceEndpointStatus, required=True), 'type': FieldInfo(annotation=Literal['zenml.services.service_endpoint.BaseServiceEndpoint'], required=False, default='zenml.services.service_endpoint.BaseServiceEndpoint')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### monitor *: [BaseServiceEndpointHealthMonitor](#zenml.services.service_monitor.BaseServiceEndpointHealthMonitor) | None*

#### status *: [ServiceEndpointStatus](#zenml.services.service_endpoint.ServiceEndpointStatus)*

#### type *: Literal['zenml.services.service_endpoint.BaseServiceEndpoint']*

#### update_status() → None

Check the the current operational state of the external service endpoint.

It updates the local operational status information accordingly.

### *class* zenml.services.BaseServiceEndpointHealthMonitor(\*, type: Literal['zenml.services.service_monitor.BaseServiceEndpointHealthMonitor'] = 'zenml.services.service_monitor.BaseServiceEndpointHealthMonitor', config: [ServiceEndpointHealthMonitorConfig](#zenml.services.service_monitor.ServiceEndpointHealthMonitorConfig) = None)

Bases: [`BaseTypedModel`](zenml.utils.md#zenml.utils.typed_model.BaseTypedModel)

Base class used for service endpoint health monitors.

Attributes:
: config: health monitor configuration for endpoint

#### *abstract* check_endpoint_status(endpoint: [BaseServiceEndpoint](#zenml.services.BaseServiceEndpoint)) → Tuple[[ServiceState](#zenml.services.service_status.ServiceState), str]

Check the the current operational state of the external service endpoint.

Args:
: endpoint: service endpoint to check

This method should be overridden by subclasses that implement
concrete service endpoint tracking functionality.

Returns:
: The operational state of the external service endpoint and an
  optional error message, if an error is encountered while checking
  the service endpoint status.

#### config *: [ServiceEndpointHealthMonitorConfig](#zenml.services.service_monitor.ServiceEndpointHealthMonitorConfig)*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'config': FieldInfo(annotation=ServiceEndpointHealthMonitorConfig, required=False, default_factory=ServiceEndpointHealthMonitorConfig), 'type': FieldInfo(annotation=Literal['zenml.services.service_monitor.BaseServiceEndpointHealthMonitor'], required=False, default='zenml.services.service_monitor.BaseServiceEndpointHealthMonitor')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### type *: Literal['zenml.services.service_monitor.BaseServiceEndpointHealthMonitor']*

### *class* zenml.services.ContainerService(\*, type: Literal['zenml.services.container.container_service.ContainerService'] = 'zenml.services.container.container_service.ContainerService', uuid: UUID, admin_state: [ServiceState](#zenml.services.service_status.ServiceState) = ServiceState.INACTIVE, config: [ContainerServiceConfig](zenml.services.container.md#zenml.services.container.container_service.ContainerServiceConfig) = None, status: [ContainerServiceStatus](zenml.services.container.md#zenml.services.container.container_service.ContainerServiceStatus) = None, endpoint: [ContainerServiceEndpoint](zenml.services.container.md#zenml.services.container.container_service_endpoint.ContainerServiceEndpoint) | None = None)

Bases: [`BaseService`](#zenml.services.service.BaseService)

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

#### check_status() → Tuple[[ServiceState](#zenml.services.service_status.ServiceState), str]

Check the the current operational state of the docker container.

Returns:
: The operational state of the docker container and a message
  providing additional information about that state (e.g. a
  description of the error, if one is encountered).

#### config *: [ContainerServiceConfig](zenml.services.container.md#zenml.services.container.container_service.ContainerServiceConfig)*

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

#### endpoint *: [ContainerServiceEndpoint](zenml.services.container.md#zenml.services.container.container_service_endpoint.ContainerServiceEndpoint) | None*

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

#### status *: [ContainerServiceStatus](zenml.services.container.md#zenml.services.container.container_service.ContainerServiceStatus)*

#### type *: Literal['zenml.services.container.container_service.ContainerService']*

### *class* zenml.services.ContainerServiceConfig(\*, type: Literal['zenml.services.container.container_service.ContainerServiceConfig'] = 'zenml.services.container.container_service.ContainerServiceConfig', name: str = '', description: str = '', pipeline_name: str = '', pipeline_step_name: str = '', model_name: str = '', model_version: str = '', service_name: str = '', root_runtime_path: str | None = None, singleton: bool = False, image: str = 'zenmldocker/zenml')

Bases: [`ServiceConfig`](#zenml.services.service.ServiceConfig)

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

#### image *: str*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'protected_namespaces': ()}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'description': FieldInfo(annotation=str, required=False, default=''), 'image': FieldInfo(annotation=str, required=False, default='zenmldocker/zenml'), 'model_name': FieldInfo(annotation=str, required=False, default=''), 'model_version': FieldInfo(annotation=str, required=False, default=''), 'name': FieldInfo(annotation=str, required=False, default=''), 'pipeline_name': FieldInfo(annotation=str, required=False, default=''), 'pipeline_step_name': FieldInfo(annotation=str, required=False, default=''), 'root_runtime_path': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'service_name': FieldInfo(annotation=str, required=False, default=''), 'singleton': FieldInfo(annotation=bool, required=False, default=False), 'type': FieldInfo(annotation=Literal['zenml.services.container.container_service.ContainerServiceConfig'], required=False, default='zenml.services.container.container_service.ContainerServiceConfig')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### root_runtime_path *: str | None*

#### singleton *: bool*

#### type *: Literal['zenml.services.container.container_service.ContainerServiceConfig']*

### *class* zenml.services.ContainerServiceEndpoint(\*args: Any, type: Literal['zenml.services.container.container_service_endpoint.ContainerServiceEndpoint'] = 'zenml.services.container.container_service_endpoint.ContainerServiceEndpoint', admin_state: [ServiceState](#zenml.services.service_status.ServiceState) = ServiceState.INACTIVE, config: [ContainerServiceEndpointConfig](zenml.services.container.md#zenml.services.container.container_service_endpoint.ContainerServiceEndpointConfig) = None, status: [ContainerServiceEndpointStatus](zenml.services.container.md#zenml.services.container.container_service_endpoint.ContainerServiceEndpointStatus) = None, monitor: Annotated[[HTTPEndpointHealthMonitor](#zenml.services.service_monitor.HTTPEndpointHealthMonitor) | [TCPEndpointHealthMonitor](#zenml.services.service_monitor.TCPEndpointHealthMonitor) | None, \_PydanticGeneralMetadata(union_mode='left_to_right')])

Bases: [`BaseServiceEndpoint`](#zenml.services.service_endpoint.BaseServiceEndpoint)

A service endpoint exposed by a containerized process.

This class extends the base service endpoint class with functionality
concerning the life-cycle management and tracking of endpoints exposed
by external services implemented as containerized processes.

Attributes:
: config: service endpoint configuration
  status: service endpoint status
  monitor: optional service endpoint health monitor

#### config *: [ContainerServiceEndpointConfig](zenml.services.container.md#zenml.services.container.container_service_endpoint.ContainerServiceEndpointConfig)*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'admin_state': FieldInfo(annotation=ServiceState, required=False, default=<ServiceState.INACTIVE: 'inactive'>), 'config': FieldInfo(annotation=ContainerServiceEndpointConfig, required=False, default_factory=ContainerServiceEndpointConfig), 'monitor': FieldInfo(annotation=Union[HTTPEndpointHealthMonitor, TCPEndpointHealthMonitor, NoneType], required=True, discriminator='type', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'status': FieldInfo(annotation=ContainerServiceEndpointStatus, required=False, default_factory=ContainerServiceEndpointStatus), 'type': FieldInfo(annotation=Literal['zenml.services.container.container_service_endpoint.ContainerServiceEndpoint'], required=False, default='zenml.services.container.container_service_endpoint.ContainerServiceEndpoint')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### monitor *: [HTTPEndpointHealthMonitor](#zenml.services.service_monitor.HTTPEndpointHealthMonitor) | [TCPEndpointHealthMonitor](#zenml.services.service_monitor.TCPEndpointHealthMonitor) | None*

#### prepare_for_start() → None

Prepare the service endpoint for starting.

This method is called before the service is started.

#### status *: [ContainerServiceEndpointStatus](zenml.services.container.md#zenml.services.container.container_service_endpoint.ContainerServiceEndpointStatus)*

#### type *: Literal['zenml.services.container.container_service_endpoint.ContainerServiceEndpoint']*

### *class* zenml.services.ContainerServiceEndpointConfig(\*, type: Literal['zenml.services.container.container_service_endpoint.ContainerServiceEndpointConfig'] = 'zenml.services.container.container_service_endpoint.ContainerServiceEndpointConfig', name: str = '', description: str = '', protocol: [ServiceEndpointProtocol](#zenml.services.service_endpoint.ServiceEndpointProtocol) = ServiceEndpointProtocol.TCP, port: int | None = None, allocate_port: bool = True)

Bases: [`ServiceEndpointConfig`](#zenml.services.service_endpoint.ServiceEndpointConfig)

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

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'allocate_port': FieldInfo(annotation=bool, required=False, default=True), 'description': FieldInfo(annotation=str, required=False, default=''), 'name': FieldInfo(annotation=str, required=False, default=''), 'port': FieldInfo(annotation=Union[int, NoneType], required=False, default=None), 'protocol': FieldInfo(annotation=ServiceEndpointProtocol, required=False, default=<ServiceEndpointProtocol.TCP: 'tcp'>), 'type': FieldInfo(annotation=Literal['zenml.services.container.container_service_endpoint.ContainerServiceEndpointConfig'], required=False, default='zenml.services.container.container_service_endpoint.ContainerServiceEndpointConfig')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### port *: int | None*

#### protocol *: [ServiceEndpointProtocol](#zenml.services.service_endpoint.ServiceEndpointProtocol)*

#### type *: Literal['zenml.services.container.container_service_endpoint.ContainerServiceEndpointConfig']*

### *class* zenml.services.ContainerServiceEndpointStatus(\*, type: Literal['zenml.services.container.container_service_endpoint.ContainerServiceEndpointStatus'] = 'zenml.services.container.container_service_endpoint.ContainerServiceEndpointStatus', state: [ServiceState](#zenml.services.service_status.ServiceState) = ServiceState.INACTIVE, last_state: [ServiceState](#zenml.services.service_status.ServiceState) = ServiceState.INACTIVE, last_error: str = '', protocol: [ServiceEndpointProtocol](#zenml.services.service_endpoint.ServiceEndpointProtocol) = ServiceEndpointProtocol.TCP, hostname: str | None = None, port: int | None = None)

Bases: [`ServiceEndpointStatus`](#zenml.services.service_endpoint.ServiceEndpointStatus)

Local daemon service endpoint status.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'hostname': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'last_error': FieldInfo(annotation=str, required=False, default=''), 'last_state': FieldInfo(annotation=ServiceState, required=False, default=<ServiceState.INACTIVE: 'inactive'>), 'port': FieldInfo(annotation=Union[int, NoneType], required=False, default=None), 'protocol': FieldInfo(annotation=ServiceEndpointProtocol, required=False, default=<ServiceEndpointProtocol.TCP: 'tcp'>), 'state': FieldInfo(annotation=ServiceState, required=False, default=<ServiceState.INACTIVE: 'inactive'>), 'type': FieldInfo(annotation=Literal['zenml.services.container.container_service_endpoint.ContainerServiceEndpointStatus'], required=False, default='zenml.services.container.container_service_endpoint.ContainerServiceEndpointStatus')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### type *: Literal['zenml.services.container.container_service_endpoint.ContainerServiceEndpointStatus']*

### *class* zenml.services.ContainerServiceStatus(\*, type: Literal['zenml.services.container.container_service.ContainerServiceStatus'] = 'zenml.services.container.container_service.ContainerServiceStatus', state: [ServiceState](#zenml.services.service_status.ServiceState) = ServiceState.INACTIVE, last_state: [ServiceState](#zenml.services.service_status.ServiceState) = ServiceState.INACTIVE, last_error: str = '', runtime_path: str | None = None)

Bases: [`ServiceStatus`](#zenml.services.service_status.ServiceStatus)

containerized service status.

Attributes:
: runtime_path: the path where the service files (e.g. the configuration
  : file used to start the service daemon and the logfile) are located

#### *property* config_file *: str | None*

Get the path to the service configuration file.

Returns:
: The path to the configuration file, or None, if the
  service has never been started before.

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

#### type *: Literal['zenml.services.container.container_service.ContainerServiceStatus']*

### *class* zenml.services.HTTPEndpointHealthMonitor(\*, type: Literal['zenml.services.service_monitor.HTTPEndpointHealthMonitor'] = 'zenml.services.service_monitor.HTTPEndpointHealthMonitor', config: [HTTPEndpointHealthMonitorConfig](#zenml.services.service_monitor.HTTPEndpointHealthMonitorConfig) = None)

Bases: [`BaseServiceEndpointHealthMonitor`](#zenml.services.service_monitor.BaseServiceEndpointHealthMonitor)

HTTP service endpoint health monitor.

Attributes:
: config: health monitor configuration for HTTP endpoint

#### check_endpoint_status(endpoint: [BaseServiceEndpoint](#zenml.services.BaseServiceEndpoint)) → Tuple[[ServiceState](#zenml.services.service_status.ServiceState), str]

Run a HTTP endpoint API healthcheck.

Args:
: endpoint: service endpoint to check.

Returns:
: The operational state of the external HTTP endpoint and an
  optional message describing that state (e.g. an error message,
  if an error is encountered while checking the HTTP endpoint
  status).

#### config *: [HTTPEndpointHealthMonitorConfig](#zenml.services.service_monitor.HTTPEndpointHealthMonitorConfig)*

#### get_healthcheck_uri(endpoint: [BaseServiceEndpoint](#zenml.services.BaseServiceEndpoint)) → str | None

Get the healthcheck URI for the given service endpoint.

Args:
: endpoint: service endpoint to get the healthcheck URI for

Returns:
: The healthcheck URI for the given service endpoint or None, if
  the service endpoint doesn’t have a healthcheck URI.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'config': FieldInfo(annotation=HTTPEndpointHealthMonitorConfig, required=False, default_factory=HTTPEndpointHealthMonitorConfig), 'type': FieldInfo(annotation=Literal['zenml.services.service_monitor.HTTPEndpointHealthMonitor'], required=False, default='zenml.services.service_monitor.HTTPEndpointHealthMonitor')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### type *: Literal['zenml.services.service_monitor.HTTPEndpointHealthMonitor']*

### *class* zenml.services.HTTPEndpointHealthMonitorConfig(\*, type: Literal['zenml.services.service_monitor.HTTPEndpointHealthMonitorConfig'] = 'zenml.services.service_monitor.HTTPEndpointHealthMonitorConfig', healthcheck_uri_path: str = '', use_head_request: bool = False, http_status_code: int = 200, http_timeout: int = 5)

Bases: [`ServiceEndpointHealthMonitorConfig`](#zenml.services.service_monitor.ServiceEndpointHealthMonitorConfig)

HTTP service endpoint health monitor configuration.

Attributes:
: healthcheck_uri_path: URI subpath to use to perform service endpoint
  : healthchecks. If not set, the service endpoint URI will be used
    instead.
  <br/>
  use_head_request: set to True to use a HEAD request instead of a GET
  : when calling the healthcheck URI.
  <br/>
  http_status_code: HTTP status code to expect in the health check
  : response.
  <br/>
  http_timeout: HTTP health check request timeout in seconds.

#### healthcheck_uri_path *: str*

#### http_status_code *: int*

#### http_timeout *: int*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'healthcheck_uri_path': FieldInfo(annotation=str, required=False, default=''), 'http_status_code': FieldInfo(annotation=int, required=False, default=200), 'http_timeout': FieldInfo(annotation=int, required=False, default=5), 'type': FieldInfo(annotation=Literal['zenml.services.service_monitor.HTTPEndpointHealthMonitorConfig'], required=False, default='zenml.services.service_monitor.HTTPEndpointHealthMonitorConfig'), 'use_head_request': FieldInfo(annotation=bool, required=False, default=False)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### type *: Literal['zenml.services.service_monitor.HTTPEndpointHealthMonitorConfig']*

#### use_head_request *: bool*

### *class* zenml.services.LocalDaemonService(\*, type: Literal['zenml.services.local.local_service.LocalDaemonService'] = 'zenml.services.local.local_service.LocalDaemonService', uuid: UUID, admin_state: [ServiceState](#zenml.services.service_status.ServiceState) = ServiceState.INACTIVE, config: [LocalDaemonServiceConfig](zenml.services.local.md#zenml.services.local.local_service.LocalDaemonServiceConfig) = None, status: [LocalDaemonServiceStatus](zenml.services.local.md#zenml.services.local.local_service.LocalDaemonServiceStatus) = None, endpoint: [LocalDaemonServiceEndpoint](zenml.services.local.md#zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpoint) | None = None)

Bases: [`BaseService`](#zenml.services.service.BaseService)

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

#### check_status() → Tuple[[ServiceState](#zenml.services.service_status.ServiceState), str]

Check the the current operational state of the daemon process.

Returns:
: The operational state of the daemon process and a message
  providing additional information about that state (e.g. a
  description of the error, if one is encountered).

#### config *: [LocalDaemonServiceConfig](zenml.services.local.md#zenml.services.local.local_service.LocalDaemonServiceConfig)*

#### deprovision(force: bool = False) → None

Deprovision the service.

Args:
: force: if True, the service daemon will be forcefully stopped

#### endpoint *: [LocalDaemonServiceEndpoint](zenml.services.local.md#zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpoint) | None*

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

#### status *: [LocalDaemonServiceStatus](zenml.services.local.md#zenml.services.local.local_service.LocalDaemonServiceStatus)*

#### type *: Literal['zenml.services.local.local_service.LocalDaemonService']*

### *class* zenml.services.LocalDaemonServiceConfig(\*, type: Literal['zenml.services.local.local_service.LocalDaemonServiceConfig'] = 'zenml.services.local.local_service.LocalDaemonServiceConfig', name: str = '', description: str = '', pipeline_name: str = '', pipeline_step_name: str = '', model_name: str = '', model_version: str = '', service_name: str = '', silent_daemon: bool = False, root_runtime_path: str | None = None, singleton: bool = False, blocking: bool = False)

Bases: [`ServiceConfig`](#zenml.services.service.ServiceConfig)

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

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'protected_namespaces': ()}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'blocking': FieldInfo(annotation=bool, required=False, default=False), 'description': FieldInfo(annotation=str, required=False, default=''), 'model_name': FieldInfo(annotation=str, required=False, default=''), 'model_version': FieldInfo(annotation=str, required=False, default=''), 'name': FieldInfo(annotation=str, required=False, default=''), 'pipeline_name': FieldInfo(annotation=str, required=False, default=''), 'pipeline_step_name': FieldInfo(annotation=str, required=False, default=''), 'root_runtime_path': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'service_name': FieldInfo(annotation=str, required=False, default=''), 'silent_daemon': FieldInfo(annotation=bool, required=False, default=False), 'singleton': FieldInfo(annotation=bool, required=False, default=False), 'type': FieldInfo(annotation=Literal['zenml.services.local.local_service.LocalDaemonServiceConfig'], required=False, default='zenml.services.local.local_service.LocalDaemonServiceConfig')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### root_runtime_path *: str | None*

#### silent_daemon *: bool*

#### singleton *: bool*

#### type *: Literal['zenml.services.local.local_service.LocalDaemonServiceConfig']*

### *class* zenml.services.LocalDaemonServiceEndpoint(\*args: Any, type: Literal['zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpoint'] = 'zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpoint', admin_state: [ServiceState](#zenml.services.service_status.ServiceState) = ServiceState.INACTIVE, config: [LocalDaemonServiceEndpointConfig](zenml.services.local.md#zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpointConfig) = None, status: [LocalDaemonServiceEndpointStatus](zenml.services.local.md#zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpointStatus) = None, monitor: Annotated[[HTTPEndpointHealthMonitor](#zenml.services.service_monitor.HTTPEndpointHealthMonitor) | [TCPEndpointHealthMonitor](#zenml.services.service_monitor.TCPEndpointHealthMonitor) | None, \_PydanticGeneralMetadata(union_mode='left_to_right')])

Bases: [`BaseServiceEndpoint`](#zenml.services.service_endpoint.BaseServiceEndpoint)

A service endpoint exposed by a local daemon process.

This class extends the base service endpoint class with functionality
concerning the life-cycle management and tracking of endpoints exposed
by external services implemented as local daemon processes.

Attributes:
: config: service endpoint configuration
  status: service endpoint status
  monitor: optional service endpoint health monitor

#### config *: [LocalDaemonServiceEndpointConfig](zenml.services.local.md#zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpointConfig)*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'admin_state': FieldInfo(annotation=ServiceState, required=False, default=<ServiceState.INACTIVE: 'inactive'>), 'config': FieldInfo(annotation=LocalDaemonServiceEndpointConfig, required=False, default_factory=LocalDaemonServiceEndpointConfig), 'monitor': FieldInfo(annotation=Union[HTTPEndpointHealthMonitor, TCPEndpointHealthMonitor, NoneType], required=True, discriminator='type', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'status': FieldInfo(annotation=LocalDaemonServiceEndpointStatus, required=False, default_factory=LocalDaemonServiceEndpointStatus), 'type': FieldInfo(annotation=Literal['zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpoint'], required=False, default='zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpoint')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### monitor *: [HTTPEndpointHealthMonitor](#zenml.services.service_monitor.HTTPEndpointHealthMonitor) | [TCPEndpointHealthMonitor](#zenml.services.service_monitor.TCPEndpointHealthMonitor) | None*

#### prepare_for_start() → None

Prepare the service endpoint for starting.

This method is called before the service is started.

#### status *: [LocalDaemonServiceEndpointStatus](zenml.services.local.md#zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpointStatus)*

#### type *: Literal['zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpoint']*

### *class* zenml.services.LocalDaemonServiceEndpointConfig(\*, type: Literal['zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpointConfig'] = 'zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpointConfig', name: str = '', description: str = '', protocol: [ServiceEndpointProtocol](#zenml.services.service_endpoint.ServiceEndpointProtocol) = ServiceEndpointProtocol.TCP, port: int | None = None, ip_address: str = '127.0.0.1', allocate_port: bool = True)

Bases: [`ServiceEndpointConfig`](#zenml.services.service_endpoint.ServiceEndpointConfig)

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

#### ip_address *: str*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'allocate_port': FieldInfo(annotation=bool, required=False, default=True), 'description': FieldInfo(annotation=str, required=False, default=''), 'ip_address': FieldInfo(annotation=str, required=False, default='127.0.0.1'), 'name': FieldInfo(annotation=str, required=False, default=''), 'port': FieldInfo(annotation=Union[int, NoneType], required=False, default=None), 'protocol': FieldInfo(annotation=ServiceEndpointProtocol, required=False, default=<ServiceEndpointProtocol.TCP: 'tcp'>), 'type': FieldInfo(annotation=Literal['zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpointConfig'], required=False, default='zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpointConfig')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### port *: int | None*

#### protocol *: [ServiceEndpointProtocol](#zenml.services.service_endpoint.ServiceEndpointProtocol)*

#### type *: Literal['zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpointConfig']*

### *class* zenml.services.LocalDaemonServiceEndpointStatus(\*, type: Literal['zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpointStatus'] = 'zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpointStatus', state: [ServiceState](#zenml.services.service_status.ServiceState) = ServiceState.INACTIVE, last_state: [ServiceState](#zenml.services.service_status.ServiceState) = ServiceState.INACTIVE, last_error: str = '', protocol: [ServiceEndpointProtocol](#zenml.services.service_endpoint.ServiceEndpointProtocol) = ServiceEndpointProtocol.TCP, hostname: str | None = None, port: int | None = None)

Bases: [`ServiceEndpointStatus`](#zenml.services.service_endpoint.ServiceEndpointStatus)

Local daemon service endpoint status.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'hostname': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'last_error': FieldInfo(annotation=str, required=False, default=''), 'last_state': FieldInfo(annotation=ServiceState, required=False, default=<ServiceState.INACTIVE: 'inactive'>), 'port': FieldInfo(annotation=Union[int, NoneType], required=False, default=None), 'protocol': FieldInfo(annotation=ServiceEndpointProtocol, required=False, default=<ServiceEndpointProtocol.TCP: 'tcp'>), 'state': FieldInfo(annotation=ServiceState, required=False, default=<ServiceState.INACTIVE: 'inactive'>), 'type': FieldInfo(annotation=Literal['zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpointStatus'], required=False, default='zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpointStatus')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### type *: Literal['zenml.services.local.local_service_endpoint.LocalDaemonServiceEndpointStatus']*

### *class* zenml.services.LocalDaemonServiceStatus(\*, type: Literal['zenml.services.local.local_service.LocalDaemonServiceStatus'] = 'zenml.services.local.local_service.LocalDaemonServiceStatus', state: [ServiceState](#zenml.services.service_status.ServiceState) = ServiceState.INACTIVE, last_state: [ServiceState](#zenml.services.service_status.ServiceState) = ServiceState.INACTIVE, last_error: str = '', runtime_path: str | None = None, silent_daemon: bool = False)

Bases: [`ServiceStatus`](#zenml.services.service_status.ServiceStatus)

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

#### type *: Literal['zenml.services.local.local_service.LocalDaemonServiceStatus']*

### *class* zenml.services.ServiceConfig(\*, type: Literal['zenml.services.service.ServiceConfig'] = 'zenml.services.service.ServiceConfig', name: str = '', description: str = '', pipeline_name: str = '', pipeline_step_name: str = '', model_name: str = '', model_version: str = '', service_name: str = '')

Bases: [`BaseTypedModel`](zenml.utils.md#zenml.utils.typed_model.BaseTypedModel)

Generic service configuration.

Concrete service classes should extend this class and add additional
attributes that they want to see reflected and used in the service
configuration.

Attributes:
: name: name for the service instance
  description: description of the service
  pipeline_name: name of the pipeline that spun up the service
  pipeline_step_name: name of the pipeline step that spun up the service
  run_name: name of the pipeline run that spun up the service.

#### description *: str*

#### get_service_labels() → Dict[str, str]

Get the service labels.

Returns:
: a dictionary of service labels.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'protected_namespaces': ()}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'description': FieldInfo(annotation=str, required=False, default=''), 'model_name': FieldInfo(annotation=str, required=False, default=''), 'model_version': FieldInfo(annotation=str, required=False, default=''), 'name': FieldInfo(annotation=str, required=False, default=''), 'pipeline_name': FieldInfo(annotation=str, required=False, default=''), 'pipeline_step_name': FieldInfo(annotation=str, required=False, default=''), 'service_name': FieldInfo(annotation=str, required=False, default=''), 'type': FieldInfo(annotation=Literal['zenml.services.service.ServiceConfig'], required=False, default='zenml.services.service.ServiceConfig')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_name *: str*

#### model_version *: str*

#### name *: str*

#### pipeline_name *: str*

#### pipeline_step_name *: str*

#### service_name *: str*

#### type *: Literal['zenml.services.service.ServiceConfig']*

### *class* zenml.services.ServiceEndpointConfig(\*, type: Literal['zenml.services.service_endpoint.ServiceEndpointConfig'] = 'zenml.services.service_endpoint.ServiceEndpointConfig', name: str = '', description: str = '')

Bases: [`BaseTypedModel`](zenml.utils.md#zenml.utils.typed_model.BaseTypedModel)

Generic service endpoint configuration.

Concrete service classes should extend this class and add additional
attributes that they want to see reflected and use in the endpoint
configuration.

Attributes:
: name: unique name for the service endpoint
  description: description of the service endpoint

#### description *: str*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'description': FieldInfo(annotation=str, required=False, default=''), 'name': FieldInfo(annotation=str, required=False, default=''), 'type': FieldInfo(annotation=Literal['zenml.services.service_endpoint.ServiceEndpointConfig'], required=False, default='zenml.services.service_endpoint.ServiceEndpointConfig')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### type *: Literal['zenml.services.service_endpoint.ServiceEndpointConfig']*

### *class* zenml.services.ServiceEndpointHealthMonitorConfig(\*, type: Literal['zenml.services.service_monitor.ServiceEndpointHealthMonitorConfig'] = 'zenml.services.service_monitor.ServiceEndpointHealthMonitorConfig')

Bases: [`BaseTypedModel`](zenml.utils.md#zenml.utils.typed_model.BaseTypedModel)

Generic service health monitor configuration.

Concrete service classes should extend this class and add additional
attributes that they want to see reflected and use in the health monitor
configuration.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'type': FieldInfo(annotation=Literal['zenml.services.service_monitor.ServiceEndpointHealthMonitorConfig'], required=False, default='zenml.services.service_monitor.ServiceEndpointHealthMonitorConfig')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### type *: Literal['zenml.services.service_monitor.ServiceEndpointHealthMonitorConfig']*

### *class* zenml.services.ServiceEndpointProtocol(value, names=None, \*, module=None, qualname=None, type=None, start=1, boundary=None)

Bases: [`StrEnum`](zenml.utils.md#zenml.utils.enum_utils.StrEnum)

Possible endpoint protocol values.

#### HTTP *= 'http'*

#### HTTPS *= 'https'*

#### TCP *= 'tcp'*

### *class* zenml.services.ServiceEndpointStatus(\*, type: Literal['zenml.services.service_endpoint.ServiceEndpointStatus'] = 'zenml.services.service_endpoint.ServiceEndpointStatus', state: [ServiceState](#zenml.services.service_status.ServiceState) = ServiceState.INACTIVE, last_state: [ServiceState](#zenml.services.service_status.ServiceState) = ServiceState.INACTIVE, last_error: str = '', protocol: [ServiceEndpointProtocol](#zenml.services.service_endpoint.ServiceEndpointProtocol) = ServiceEndpointProtocol.TCP, hostname: str | None = None, port: int | None = None)

Bases: [`ServiceStatus`](#zenml.services.service_status.ServiceStatus)

Status information describing the operational state of a service endpoint.

For example, this could be a HTTP/HTTPS API or generic TCP endpoint exposed
by a service. Concrete service classes should extend this class and add
additional attributes that make up the operational state of the service
endpoint.

Attributes:
: protocol: the TCP protocol used by the service endpoint
  hostname: the hostname where the service endpoint is accessible
  port: the current TCP port where the service endpoint is accessible

#### hostname *: str | None*

#### last_error *: str*

#### last_state *: [ServiceState](#zenml.services.ServiceState)*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'hostname': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'last_error': FieldInfo(annotation=str, required=False, default=''), 'last_state': FieldInfo(annotation=ServiceState, required=False, default=<ServiceState.INACTIVE: 'inactive'>), 'port': FieldInfo(annotation=Union[int, NoneType], required=False, default=None), 'protocol': FieldInfo(annotation=ServiceEndpointProtocol, required=False, default=<ServiceEndpointProtocol.TCP: 'tcp'>), 'state': FieldInfo(annotation=ServiceState, required=False, default=<ServiceState.INACTIVE: 'inactive'>), 'type': FieldInfo(annotation=Literal['zenml.services.service_endpoint.ServiceEndpointStatus'], required=False, default='zenml.services.service_endpoint.ServiceEndpointStatus')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### port *: int | None*

#### protocol *: [ServiceEndpointProtocol](#zenml.services.service_endpoint.ServiceEndpointProtocol)*

#### state *: [ServiceState](#zenml.services.ServiceState)*

#### type *: Literal['zenml.services.service_endpoint.ServiceEndpointStatus']*

#### *property* uri *: str | None*

Get the URI of the service endpoint.

Returns:
: The URI of the service endpoint or None, if the service endpoint
  operational status doesn’t have the required information.

### *class* zenml.services.ServiceState(value, names=None, \*, module=None, qualname=None, type=None, start=1, boundary=None)

Bases: [`StrEnum`](zenml.utils.md#zenml.utils.enum_utils.StrEnum)

Possible states for the service and service endpoint.

#### ACTIVE *= 'active'*

#### ERROR *= 'error'*

#### INACTIVE *= 'inactive'*

#### PENDING_SHUTDOWN *= 'pending_shutdown'*

#### PENDING_STARTUP *= 'pending_startup'*

#### SCALED_TO_ZERO *= 'scaled_to_zero'*

### *class* zenml.services.ServiceStatus(\*, type: Literal['zenml.services.service_status.ServiceStatus'] = 'zenml.services.service_status.ServiceStatus', state: [ServiceState](#zenml.services.service_status.ServiceState) = ServiceState.INACTIVE, last_state: [ServiceState](#zenml.services.service_status.ServiceState) = ServiceState.INACTIVE, last_error: str = '')

Bases: [`BaseTypedModel`](zenml.utils.md#zenml.utils.typed_model.BaseTypedModel)

Information about the status of a service or process.

This information describes the operational status of an external process or
service tracked by ZenML. This could be a process, container, Kubernetes
deployment etc.

Concrete service classes should extend this class and add additional
attributes that make up the operational state of the service.

Attributes:
: state: the current operational state
  last_state: the operational state prior to the last status update
  last_error: the error encountered during the last status update

#### clear_error() → None

Clear the last error message.

#### last_error *: str*

#### last_state *: [ServiceState](#zenml.services.service_status.ServiceState)*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'last_error': FieldInfo(annotation=str, required=False, default=''), 'last_state': FieldInfo(annotation=ServiceState, required=False, default=<ServiceState.INACTIVE: 'inactive'>), 'state': FieldInfo(annotation=ServiceState, required=False, default=<ServiceState.INACTIVE: 'inactive'>), 'type': FieldInfo(annotation=Literal['zenml.services.service_status.ServiceStatus'], required=False, default='zenml.services.service_status.ServiceStatus')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### state *: [ServiceState](#zenml.services.service_status.ServiceState)*

#### type *: Literal['zenml.services.service_status.ServiceStatus']*

#### update_state(new_state: [ServiceState](#zenml.services.service_status.ServiceState) | None = None, error: str = '') → None

Update the current operational state to reflect a new state value and/or error.

Args:
: new_state: new operational state discovered by the last service
  : status update
  <br/>
  error: error message describing an operational failure encountered
  : during the last service status update

### *class* zenml.services.ServiceType(\*, type: str, flavor: str, name: str = '', description: str = '', logo_url: str = '')

Bases: `BaseModel`

Service type descriptor.

Attributes:
: type: service type
  flavor: service flavor
  name: name of the service type
  description: description of the service type
  logo_url: logo of the service type

#### description *: str*

#### flavor *: str*

#### logo_url *: str*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'frozen': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'description': FieldInfo(annotation=str, required=False, default=''), 'flavor': FieldInfo(annotation=str, required=True), 'logo_url': FieldInfo(annotation=str, required=False, default=''), 'name': FieldInfo(annotation=str, required=False, default=''), 'type': FieldInfo(annotation=str, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### type *: str*

### *class* zenml.services.TCPEndpointHealthMonitor(\*, type: Literal['zenml.services.service_monitor.TCPEndpointHealthMonitor'] = 'zenml.services.service_monitor.TCPEndpointHealthMonitor', config: [TCPEndpointHealthMonitorConfig](#zenml.services.service_monitor.TCPEndpointHealthMonitorConfig))

Bases: [`BaseServiceEndpointHealthMonitor`](#zenml.services.service_monitor.BaseServiceEndpointHealthMonitor)

TCP service endpoint health monitor.

Attributes:
: config: health monitor configuration for TCP endpoint

#### check_endpoint_status(endpoint: [BaseServiceEndpoint](#zenml.services.BaseServiceEndpoint)) → Tuple[[ServiceState](#zenml.services.service_status.ServiceState), str]

Run a TCP endpoint healthcheck.

Args:
: endpoint: service endpoint to check.

Returns:
: The operational state of the external TCP endpoint and an
  optional message describing that state (e.g. an error message,
  if an error is encountered while checking the TCP endpoint
  status).

#### config *: [TCPEndpointHealthMonitorConfig](#zenml.services.service_monitor.TCPEndpointHealthMonitorConfig)*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'config': FieldInfo(annotation=TCPEndpointHealthMonitorConfig, required=True), 'type': FieldInfo(annotation=Literal['zenml.services.service_monitor.TCPEndpointHealthMonitor'], required=False, default='zenml.services.service_monitor.TCPEndpointHealthMonitor')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### type *: Literal['zenml.services.service_monitor.TCPEndpointHealthMonitor']*

### *class* zenml.services.TCPEndpointHealthMonitorConfig(\*, type: Literal['zenml.services.service_monitor.TCPEndpointHealthMonitorConfig'] = 'zenml.services.service_monitor.TCPEndpointHealthMonitorConfig')

Bases: [`ServiceEndpointHealthMonitorConfig`](#zenml.services.service_monitor.ServiceEndpointHealthMonitorConfig)

TCP service endpoint health monitor configuration.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'type': FieldInfo(annotation=Literal['zenml.services.service_monitor.TCPEndpointHealthMonitorConfig'], required=False, default='zenml.services.service_monitor.TCPEndpointHealthMonitorConfig')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### type *: Literal['zenml.services.service_monitor.TCPEndpointHealthMonitorConfig']*
