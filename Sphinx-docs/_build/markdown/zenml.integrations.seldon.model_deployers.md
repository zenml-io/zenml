# zenml.integrations.seldon.model_deployers package

## Submodules

## zenml.integrations.seldon.model_deployers.seldon_model_deployer module

Implementation of the Seldon Model Deployer.

### *class* zenml.integrations.seldon.model_deployers.seldon_model_deployer.SeldonModelDeployer(name: str, id: UUID, config: [StackComponentConfig](zenml.stack.md#zenml.stack.stack_component.StackComponentConfig), flavor: str, type: [StackComponentType](zenml.md#zenml.enums.StackComponentType), user: UUID | None, workspace: UUID, created: datetime, updated: datetime, labels: Dict[str, Any] | None = None, connector_requirements: [ServiceConnectorRequirements](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorRequirements) | None = None, connector: UUID | None = None, connector_resource_id: str | None = None, \*args: Any, \*\*kwargs: Any)

Bases: [`BaseModelDeployer`](zenml.model_deployers.md#zenml.model_deployers.base_model_deployer.BaseModelDeployer)

Seldon Core model deployer stack component implementation.

#### FLAVOR

alias of [`SeldonModelDeployerFlavor`](zenml.integrations.seldon.flavors.md#zenml.integrations.seldon.flavors.seldon_model_deployer_flavor.SeldonModelDeployerFlavor)

#### NAME *: ClassVar[str]* *= 'Seldon Core'*

#### *property* config *: [SeldonModelDeployerConfig](zenml.integrations.seldon.flavors.md#zenml.integrations.seldon.flavors.seldon_model_deployer_flavor.SeldonModelDeployerConfig)*

Returns the SeldonModelDeployerConfig config.

Returns:
: The configuration.

#### get_docker_builds(deployment: [PipelineDeploymentBase](zenml.models.md#zenml.models.PipelineDeploymentBase)) → List[[BuildConfiguration](zenml.config.md#zenml.config.build_configuration.BuildConfiguration)]

Gets the Docker builds required for the component.

Args:
: deployment: The pipeline deployment for which to get the builds.

Returns:
: The required Docker builds.

#### *static* get_model_server_info(service_instance: [SeldonDeploymentService](zenml.integrations.seldon.services.md#zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentService)) → Dict[str, str | None]

Return implementation specific information that might be relevant to the user.

Args:
: service_instance: Instance of a SeldonDeploymentService

Returns:
: Model server information.

#### *property* kubernetes_secret_name *: str*

Get the Kubernetes secret name associated with this model deployer.

If a pre-existing Kubernetes secret is configured for this model
deployer, that name is returned to be used by all Seldon Core
deployments associated with this model deployer.

Otherwise, a Kubernetes secret name is generated based on the ID of
the active artifact store. The reason for this is that the same model
deployer may be used to deploy models in combination with different
artifact stores at the same time, and each artifact store may require
different credentials to be accessed.

Returns:
: The name of a Kubernetes secret to be used with Seldon Core
  deployments.

#### perform_delete_model(service: [BaseService](zenml.services.md#zenml.services.service.BaseService), timeout: int = 300, force: bool = False) → None

Delete a Seldon Core model deployment server.

Args:
: service: The service to delete.
  timeout: timeout in seconds to wait for the service to stop. If
  <br/>
  > set to 0, the method will return immediately after
  > deprovisioning the service, without waiting for it to stop.
  <br/>
  force: if True, force the service to stop.

#### perform_deploy_model(id: UUID, config: [ServiceConfig](zenml.services.md#zenml.services.service.ServiceConfig), timeout: int = 300) → [BaseService](zenml.services.md#zenml.services.service.BaseService)

Create a new Seldon Core deployment or update an existing one.

# noqa: DAR402

This should serve the supplied model and deployment configuration.

This method has two modes of operation, depending on the replace
argument value:

> * if replace is False, calling this method will create a new Seldon
>   Core deployment server to reflect the model and other configuration
>   parameters specified in the supplied Seldon deployment config.
> * if replace is True, this method will first attempt to find an
>   existing Seldon Core deployment that is *equivalent* to the supplied
>   configuration parameters. Two or more Seldon Core deployments are
>   considered equivalent if they have the same pipeline_name,
>   pipeline_step_name and model_name configuration parameters. To
>   put it differently, two Seldon Core deployments are equivalent if
>   they serve versions of the same model deployed by the same pipeline
>   step. If an equivalent Seldon Core deployment is found, it will be
>   updated in place to reflect the new configuration parameters. This
>   allows an existing Seldon Core deployment to retain its prediction
>   URL while performing a rolling update to serve a new model version.

Callers should set replace to True if they want a continuous model
deployment workflow that doesn’t spin up a new Seldon Core deployment
server for each new model version. If multiple equivalent Seldon Core
deployments are found, the most recently created deployment is selected
to be updated and the others are deleted.

Args:
: id: the UUID of the model server to deploy.
  config: the configuration of the model to be deployed with Seldon.
  <br/>
  > Core
  <br/>
  timeout: the timeout in seconds to wait for the Seldon Core server
  : to be provisioned and successfully started or updated. If set
    to 0, the method will return immediately after the Seldon Core
    server is provisioned, without waiting for it to fully start.

Returns:
: The ZenML Seldon Core deployment service object that can be used to
  interact with the remote Seldon Core server.

Raises:
: SeldonClientError: if a Seldon Core client error is encountered
  : while provisioning the Seldon Core deployment server.
  <br/>
  RuntimeError: if timeout is set to a positive value that is
  : exceeded while waiting for the Seldon Core deployment server
    to start, or if an operational failure is encountered before
    it reaches a ready state.

#### perform_start_model(service: [BaseService](zenml.services.md#zenml.services.service.BaseService), timeout: int = 300) → [BaseService](zenml.services.md#zenml.services.service.BaseService)

Start a Seldon Core model deployment server.

Args:
: service: The service to start.
  timeout: timeout in seconds to wait for the service to become
  <br/>
  > active. . If set to 0, the method will return immediately after
  > provisioning the service, without waiting for it to become
  > active.

Raises:
: NotImplementedError: since we don’t support starting Seldon Core
  : model servers

#### perform_stop_model(service: [BaseService](zenml.services.md#zenml.services.service.BaseService), timeout: int = 300, force: bool = False) → [BaseService](zenml.services.md#zenml.services.service.BaseService)

Stop a Seldon Core model server.

Args:
: service: The service to stop.
  timeout: timeout in seconds to wait for the service to stop.
  force: if True, force the service to stop.

Raises:
: NotImplementedError: stopping Seldon Core model servers is not
  : supported.

#### *property* seldon_client *: [SeldonClient](zenml.integrations.seldon.md#zenml.integrations.seldon.seldon_client.SeldonClient)*

Get the Seldon Core client associated with this model deployer.

Returns:
: The Seldon Core client.

Raises:
: RuntimeError: If the Kubernetes namespace is not configured when
  : using a service connector to deploy models with Seldon Core.

#### *property* validator *: [StackValidator](zenml.stack.md#zenml.stack.stack_validator.StackValidator) | None*

Ensures there is a container registry and image builder in the stack.

Returns:
: A StackValidator instance.

## Module contents

Initialization of the Seldon Model Deployer.

### *class* zenml.integrations.seldon.model_deployers.SeldonModelDeployer(name: str, id: UUID, config: [StackComponentConfig](zenml.stack.md#zenml.stack.stack_component.StackComponentConfig), flavor: str, type: [StackComponentType](zenml.md#zenml.enums.StackComponentType), user: UUID | None, workspace: UUID, created: datetime, updated: datetime, labels: Dict[str, Any] | None = None, connector_requirements: [ServiceConnectorRequirements](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorRequirements) | None = None, connector: UUID | None = None, connector_resource_id: str | None = None, \*args: Any, \*\*kwargs: Any)

Bases: [`BaseModelDeployer`](zenml.model_deployers.md#zenml.model_deployers.base_model_deployer.BaseModelDeployer)

Seldon Core model deployer stack component implementation.

#### FLAVOR

alias of [`SeldonModelDeployerFlavor`](zenml.integrations.seldon.flavors.md#zenml.integrations.seldon.flavors.seldon_model_deployer_flavor.SeldonModelDeployerFlavor)

#### NAME *: ClassVar[str]* *= 'Seldon Core'*

#### *property* config *: [SeldonModelDeployerConfig](zenml.integrations.seldon.flavors.md#zenml.integrations.seldon.flavors.seldon_model_deployer_flavor.SeldonModelDeployerConfig)*

Returns the SeldonModelDeployerConfig config.

Returns:
: The configuration.

#### get_docker_builds(deployment: [PipelineDeploymentBase](zenml.models.md#zenml.models.PipelineDeploymentBase)) → List[[BuildConfiguration](zenml.config.md#zenml.config.build_configuration.BuildConfiguration)]

Gets the Docker builds required for the component.

Args:
: deployment: The pipeline deployment for which to get the builds.

Returns:
: The required Docker builds.

#### *static* get_model_server_info(service_instance: [SeldonDeploymentService](zenml.integrations.seldon.services.md#zenml.integrations.seldon.services.seldon_deployment.SeldonDeploymentService)) → Dict[str, str | None]

Return implementation specific information that might be relevant to the user.

Args:
: service_instance: Instance of a SeldonDeploymentService

Returns:
: Model server information.

#### *property* kubernetes_secret_name *: str*

Get the Kubernetes secret name associated with this model deployer.

If a pre-existing Kubernetes secret is configured for this model
deployer, that name is returned to be used by all Seldon Core
deployments associated with this model deployer.

Otherwise, a Kubernetes secret name is generated based on the ID of
the active artifact store. The reason for this is that the same model
deployer may be used to deploy models in combination with different
artifact stores at the same time, and each artifact store may require
different credentials to be accessed.

Returns:
: The name of a Kubernetes secret to be used with Seldon Core
  deployments.

#### perform_delete_model(service: [BaseService](zenml.services.md#zenml.services.service.BaseService), timeout: int = 300, force: bool = False) → None

Delete a Seldon Core model deployment server.

Args:
: service: The service to delete.
  timeout: timeout in seconds to wait for the service to stop. If
  <br/>
  > set to 0, the method will return immediately after
  > deprovisioning the service, without waiting for it to stop.
  <br/>
  force: if True, force the service to stop.

#### perform_deploy_model(id: UUID, config: [ServiceConfig](zenml.services.md#zenml.services.service.ServiceConfig), timeout: int = 300) → [BaseService](zenml.services.md#zenml.services.service.BaseService)

Create a new Seldon Core deployment or update an existing one.

# noqa: DAR402

This should serve the supplied model and deployment configuration.

This method has two modes of operation, depending on the replace
argument value:

> * if replace is False, calling this method will create a new Seldon
>   Core deployment server to reflect the model and other configuration
>   parameters specified in the supplied Seldon deployment config.
> * if replace is True, this method will first attempt to find an
>   existing Seldon Core deployment that is *equivalent* to the supplied
>   configuration parameters. Two or more Seldon Core deployments are
>   considered equivalent if they have the same pipeline_name,
>   pipeline_step_name and model_name configuration parameters. To
>   put it differently, two Seldon Core deployments are equivalent if
>   they serve versions of the same model deployed by the same pipeline
>   step. If an equivalent Seldon Core deployment is found, it will be
>   updated in place to reflect the new configuration parameters. This
>   allows an existing Seldon Core deployment to retain its prediction
>   URL while performing a rolling update to serve a new model version.

Callers should set replace to True if they want a continuous model
deployment workflow that doesn’t spin up a new Seldon Core deployment
server for each new model version. If multiple equivalent Seldon Core
deployments are found, the most recently created deployment is selected
to be updated and the others are deleted.

Args:
: id: the UUID of the model server to deploy.
  config: the configuration of the model to be deployed with Seldon.
  <br/>
  > Core
  <br/>
  timeout: the timeout in seconds to wait for the Seldon Core server
  : to be provisioned and successfully started or updated. If set
    to 0, the method will return immediately after the Seldon Core
    server is provisioned, without waiting for it to fully start.

Returns:
: The ZenML Seldon Core deployment service object that can be used to
  interact with the remote Seldon Core server.

Raises:
: SeldonClientError: if a Seldon Core client error is encountered
  : while provisioning the Seldon Core deployment server.
  <br/>
  RuntimeError: if timeout is set to a positive value that is
  : exceeded while waiting for the Seldon Core deployment server
    to start, or if an operational failure is encountered before
    it reaches a ready state.

#### perform_start_model(service: [BaseService](zenml.services.md#zenml.services.service.BaseService), timeout: int = 300) → [BaseService](zenml.services.md#zenml.services.service.BaseService)

Start a Seldon Core model deployment server.

Args:
: service: The service to start.
  timeout: timeout in seconds to wait for the service to become
  <br/>
  > active. . If set to 0, the method will return immediately after
  > provisioning the service, without waiting for it to become
  > active.

Raises:
: NotImplementedError: since we don’t support starting Seldon Core
  : model servers

#### perform_stop_model(service: [BaseService](zenml.services.md#zenml.services.service.BaseService), timeout: int = 300, force: bool = False) → [BaseService](zenml.services.md#zenml.services.service.BaseService)

Stop a Seldon Core model server.

Args:
: service: The service to stop.
  timeout: timeout in seconds to wait for the service to stop.
  force: if True, force the service to stop.

Raises:
: NotImplementedError: stopping Seldon Core model servers is not
  : supported.

#### *property* seldon_client *: [SeldonClient](zenml.integrations.seldon.md#zenml.integrations.seldon.seldon_client.SeldonClient)*

Get the Seldon Core client associated with this model deployer.

Returns:
: The Seldon Core client.

Raises:
: RuntimeError: If the Kubernetes namespace is not configured when
  : using a service connector to deploy models with Seldon Core.

#### *property* validator *: [StackValidator](zenml.stack.md#zenml.stack.stack_validator.StackValidator) | None*

Ensures there is a container registry and image builder in the stack.

Returns:
: A StackValidator instance.
