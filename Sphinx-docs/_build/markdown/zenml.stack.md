# zenml.stack package

## Submodules

## zenml.stack.authentication_mixin module

Stack component mixin for authentication.

### *class* zenml.stack.authentication_mixin.AuthenticationConfigMixin(warn_about_plain_text_secrets: bool = False, \*, authentication_secret: str | None = None)

Bases: [`StackComponentConfig`](#zenml.stack.stack_component.StackComponentConfig)

Base config for authentication mixins.

Any stack component that implements AuthenticationMixin should have a
config that inherits from this class.

Attributes:
: authentication_secret: Name of the secret that stores the
  : authentication credentials.

#### authentication_secret *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'authentication_secret': FieldInfo(annotation=Union[str, NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.stack.authentication_mixin.AuthenticationMixin(name: str, id: UUID, config: [StackComponentConfig](#zenml.stack.stack_component.StackComponentConfig), flavor: str, type: [StackComponentType](zenml.md#zenml.enums.StackComponentType), user: UUID | None, workspace: UUID, created: datetime, updated: datetime, labels: Dict[str, Any] | None = None, connector_requirements: [ServiceConnectorRequirements](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorRequirements) | None = None, connector: UUID | None = None, connector_resource_id: str | None = None, \*args: Any, \*\*kwargs: Any)

Bases: [`StackComponent`](#zenml.stack.stack_component.StackComponent)

Stack component mixin for authentication.

Any stack component that implements this mixin should have a config that
inherits from AuthenticationConfigMixin.

#### *property* config *: [AuthenticationConfigMixin](#zenml.stack.authentication_mixin.AuthenticationConfigMixin)*

Returns the AuthenticationConfigMixin config.

Returns:
: The configuration.

#### get_authentication_secret() → [SecretResponse](zenml.models.v2.core.md#zenml.models.v2.core.secret.SecretResponse) | None

Gets the secret referred to by the authentication secret attribute.

Returns:
: The secret if the authentication_secret attribute is set,
  None otherwise.

Raises:
: KeyError: If the secret does not exist.

#### get_typed_authentication_secret(expected_schema_type: Type[T]) → T | None

Gets a typed secret referred to by the authentication secret attribute.

Args:
: expected_schema_type: A Pydantic model class that represents the
  : expected schema type of the secret.

Returns:
: The secret values extracted from the secret and converted into the
  indicated Pydantic type, if the authentication_secret attribute is
  set, None otherwise.

Raises:
: TypeError: If the secret cannot be converted into the indicated
  : Pydantic type.

## zenml.stack.flavor module

Base ZenML Flavor implementation.

### *class* zenml.stack.flavor.Flavor

Bases: `object`

Class for ZenML Flavors.

#### *abstract property* config_class *: Type[[StackComponentConfig](#zenml.stack.stack_component.StackComponentConfig)]*

Returns StackComponentConfig config class.

Returns:
: The config class.

#### *property* config_schema *: Dict[str, Any]*

The config schema for a flavor.

Returns:
: The config schema.

#### *property* docs_url *: str | None*

A url to point at docs explaining this flavor.

Returns:
: A flavor docs url.

#### *classmethod* from_model(flavor_model: [FlavorResponse](zenml.models.v2.core.md#zenml.models.v2.core.flavor.FlavorResponse)) → [Flavor](#zenml.stack.flavor.Flavor)

Loads a flavor from a model.

Args:
: flavor_model: The model to load from.

Returns:
: The loaded flavor.

#### generate_default_docs_url() → str

Generate the doc urls for all inbuilt and integration flavors.

Note that this method is not going to be useful for custom flavors,
which do not have any docs in the main zenml docs.

Returns:
: The complete url to the zenml documentation

#### generate_default_sdk_docs_url() → str

Generate SDK docs url for a flavor.

Returns:
: The complete url to the zenml SDK docs

#### *abstract property* implementation_class *: Type[[StackComponent](#zenml.stack.stack_component.StackComponent)]*

Implementation class for this flavor.

Returns:
: The implementation class for this flavor.

#### *property* logo_url *: str | None*

A url to represent the flavor in the dashboard.

Returns:
: The flavor logo.

#### *abstract property* name *: str*

The flavor name.

Returns:
: The flavor name.

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

#### to_model(integration: str | None = None, is_custom: bool = True) → [FlavorRequest](zenml.models.v2.core.md#zenml.models.v2.core.flavor.FlavorRequest)

Converts a flavor to a model.

Args:
: integration: The integration to use for the model.
  is_custom: Whether the flavor is a custom flavor. Custom flavors
  <br/>
  > are then scoped by user and workspace

Returns:
: The model.

#### *abstract property* type *: [StackComponentType](zenml.md#zenml.enums.StackComponentType)*

The stack component type.

Returns:
: The stack component type.

### zenml.stack.flavor.validate_flavor_source(source: str, component_type: [StackComponentType](zenml.md#zenml.enums.StackComponentType)) → Type[[Flavor](#zenml.stack.flavor.Flavor)]

Import a StackComponent class from a given source and validate its type.

Args:
: source: source path of the implementation
  component_type: the type of the stack component

Returns:
: the imported class

Raises:
: ValueError: If ZenML cannot find the given module path
  TypeError: If the given module path does not point to a subclass of a
  <br/>
  > StackComponent which has the right component type.

## zenml.stack.flavor_registry module

Implementation of the ZenML flavor registry.

### *class* zenml.stack.flavor_registry.FlavorRegistry

Bases: `object`

Registry for stack component flavors.

The flavors defined by ZenML must be registered here.

#### *property* builtin_flavors *: List[Type[[Flavor](#zenml.stack.flavor.Flavor)]]*

A list of all default in-built flavors.

Returns:
: A list of builtin flavors.

#### *property* integration_flavors *: List[Type[[Flavor](#zenml.stack.flavor.Flavor)]]*

A list of all default integration flavors.

Returns:
: A list of integration flavors.

#### register_builtin_flavors(store: [BaseZenStore](zenml.zen_stores.md#zenml.zen_stores.base_zen_store.BaseZenStore)) → None

Registers the default built-in flavors.

Args:
: store: The instance of the zen_store to use

#### register_flavors(store: [BaseZenStore](zenml.zen_stores.md#zenml.zen_stores.base_zen_store.BaseZenStore)) → None

Register all flavors to the DB.

Args:
: store: The instance of a store to use for persistence

#### *static* register_integration_flavors(store: [BaseZenStore](zenml.zen_stores.md#zenml.zen_stores.base_zen_store.BaseZenStore)) → None

Registers the flavors implemented by integrations.

Args:
: store: The instance of the zen_store to use

## zenml.stack.stack module

Implementation of the ZenML Stack class.

### *class* zenml.stack.stack.Stack(id: UUID, name: str, \*, orchestrator: [BaseOrchestrator](zenml.orchestrators.md#zenml.orchestrators.base_orchestrator.BaseOrchestrator), artifact_store: [BaseArtifactStore](zenml.artifact_stores.md#zenml.artifact_stores.base_artifact_store.BaseArtifactStore), container_registry: [BaseContainerRegistry](zenml.container_registries.md#zenml.container_registries.base_container_registry.BaseContainerRegistry) | None = None, step_operator: [BaseStepOperator](zenml.step_operators.md#zenml.step_operators.base_step_operator.BaseStepOperator) | None = None, feature_store: [BaseFeatureStore](zenml.feature_stores.md#zenml.feature_stores.base_feature_store.BaseFeatureStore) | None = None, model_deployer: [BaseModelDeployer](zenml.model_deployers.md#zenml.model_deployers.base_model_deployer.BaseModelDeployer) | None = None, experiment_tracker: [BaseExperimentTracker](zenml.experiment_trackers.md#zenml.experiment_trackers.base_experiment_tracker.BaseExperimentTracker) | None = None, alerter: [BaseAlerter](zenml.alerter.md#zenml.alerter.base_alerter.BaseAlerter) | None = None, annotator: [BaseAnnotator](zenml.annotators.md#zenml.annotators.base_annotator.BaseAnnotator) | None = None, data_validator: [BaseDataValidator](zenml.data_validators.md#zenml.data_validators.base_data_validator.BaseDataValidator) | None = None, image_builder: [BaseImageBuilder](zenml.image_builders.md#zenml.image_builders.base_image_builder.BaseImageBuilder) | None = None, model_registry: [BaseModelRegistry](zenml.model_registries.md#zenml.model_registries.base_model_registry.BaseModelRegistry) | None = None)

Bases: `object`

ZenML stack class.

A ZenML stack is a collection of multiple stack components that are
required to run ZenML pipelines. Some of these components (orchestrator,
and artifact store) are required to run any kind of
pipeline, other components like the container registry are only required
if other stack components depend on them.

#### *property* alerter *: [BaseAlerter](zenml.alerter.md#zenml.alerter.base_alerter.BaseAlerter) | None*

The alerter of the stack.

Returns:
: The alerter of the stack.

#### *property* annotator *: [BaseAnnotator](zenml.annotators.md#zenml.annotators.base_annotator.BaseAnnotator) | None*

The annotator of the stack.

Returns:
: The annotator of the stack.

#### *property* apt_packages *: List[str]*

List of APT package requirements for the stack.

Returns:
: A list of APT package requirements for the stack.

#### *property* artifact_store *: [BaseArtifactStore](zenml.artifact_stores.md#zenml.artifact_stores.base_artifact_store.BaseArtifactStore)*

The artifact store of the stack.

Returns:
: The artifact store of the stack.

#### check_local_paths() → bool

Checks if the stack has local paths.

Returns:
: True if the stack has local paths, False otherwise.

Raises:
: ValueError: If the stack has local paths that do not conform to
  : the convention that all local path must be relative to the
    local stores directory.

#### cleanup_step_run(info: [StepRunInfo](zenml.config.md#zenml.config.step_run_info.StepRunInfo), step_failed: bool) → None

Cleans up resources after the step run is finished.

Args:
: info: Info about the step that was executed.
  step_failed: Whether the step failed.

#### *property* components *: Dict[[StackComponentType](zenml.md#zenml.enums.StackComponentType), [StackComponent](#zenml.stack.stack_component.StackComponent)]*

All components of the stack.

Returns:
: A dictionary of all components of the stack.

#### *property* container_registry *: [BaseContainerRegistry](zenml.container_registries.md#zenml.container_registries.base_container_registry.BaseContainerRegistry) | None*

The container registry of the stack.

Returns:
: The container registry of the stack or None if the stack does not
  have a container registry.

#### *property* data_validator *: [BaseDataValidator](zenml.data_validators.md#zenml.data_validators.base_data_validator.BaseDataValidator) | None*

The data validator of the stack.

Returns:
: The data validator of the stack.

#### deploy_pipeline(deployment: [PipelineDeploymentResponse](zenml.models.md#zenml.models.PipelineDeploymentResponse)) → Any

Deploys a pipeline on this stack.

Args:
: deployment: The pipeline deployment.

Returns:
: The return value of the call to orchestrator.run_pipeline(…).

#### deprovision() → None

Deprovisions all local resources of the stack.

#### dict() → Dict[str, str]

Converts the stack into a dictionary.

Returns:
: A dictionary containing the stack components.

#### *property* experiment_tracker *: [BaseExperimentTracker](zenml.experiment_trackers.md#zenml.experiment_trackers.base_experiment_tracker.BaseExperimentTracker) | None*

The experiment tracker of the stack.

Returns:
: The experiment tracker of the stack.

#### *property* feature_store *: [BaseFeatureStore](zenml.feature_stores.md#zenml.feature_stores.base_feature_store.BaseFeatureStore) | None*

The feature store of the stack.

Returns:
: The feature store of the stack.

#### *classmethod* from_components(id: UUID, name: str, components: Dict[[StackComponentType](zenml.md#zenml.enums.StackComponentType), [StackComponent](#zenml.stack.stack_component.StackComponent)]) → [Stack](#zenml.stack.stack.Stack)

Creates a stack instance from a dict of stack components.

# noqa: DAR402

Args:
: id: Unique ID of the stack.
  name: The name of the stack.
  components: The components of the stack.

Returns:
: A stack instance consisting of the given components.

Raises:
: TypeError: If a required component is missing or a component
  : doesn’t inherit from the expected base class.

#### *classmethod* from_model(stack_model: [StackResponse](zenml.models.v2.core.md#zenml.models.v2.core.stack.StackResponse)) → [Stack](#zenml.stack.stack.Stack)

Creates a Stack instance from a StackModel.

Args:
: stack_model: The StackModel to create the Stack from.

Returns:
: The created Stack instance.

#### get_docker_builds(deployment: [PipelineDeploymentBase](zenml.models.md#zenml.models.PipelineDeploymentBase)) → List[[BuildConfiguration](zenml.config.md#zenml.config.build_configuration.BuildConfiguration)]

Gets the Docker builds required for the stack.

Args:
: deployment: The pipeline deployment for which to get the builds.

Returns:
: The required Docker builds.

#### get_pipeline_run_metadata(run_id: UUID) → Dict[UUID, Dict[str, str | int | float | bool | Dict[Any, Any] | List[Any] | Set[Any] | Tuple[Any, ...] | [Uri](zenml.metadata.md#zenml.metadata.metadata_types.Uri) | [Path](zenml.metadata.md#zenml.metadata.metadata_types.Path) | [DType](zenml.metadata.md#zenml.metadata.metadata_types.DType) | [StorageSize](zenml.metadata.md#zenml.metadata.metadata_types.StorageSize)]]

Get general component-specific metadata for a pipeline run.

Args:
: run_id: ID of the pipeline run.

Returns:
: A dictionary mapping component IDs to the metadata they created.

#### get_step_run_metadata(info: [StepRunInfo](zenml.config.md#zenml.config.step_run_info.StepRunInfo)) → Dict[UUID, Dict[str, str | int | float | bool | Dict[Any, Any] | List[Any] | Set[Any] | Tuple[Any, ...] | [Uri](zenml.metadata.md#zenml.metadata.metadata_types.Uri) | [Path](zenml.metadata.md#zenml.metadata.metadata_types.Path) | [DType](zenml.metadata.md#zenml.metadata.metadata_types.DType) | [StorageSize](zenml.metadata.md#zenml.metadata.metadata_types.StorageSize)]]

Get component-specific metadata for a step run.

Args:
: info: Info about the step that was executed.

Returns:
: A dictionary mapping component IDs to the metadata they created.

#### *property* id *: UUID*

The ID of the stack.

Returns:
: The ID of the stack.

#### *property* image_builder *: [BaseImageBuilder](zenml.image_builders.md#zenml.image_builders.base_image_builder.BaseImageBuilder) | None*

The image builder of the stack.

Returns:
: The image builder of the stack.

#### *property* is_provisioned *: bool*

If the stack provisioned resources to run locally.

Returns:
: True if the stack provisioned resources to run locally.

#### *property* is_running *: bool*

If the stack is running locally.

Returns:
: True if the stack is running locally, False otherwise.

#### *property* model_deployer *: [BaseModelDeployer](zenml.model_deployers.md#zenml.model_deployers.base_model_deployer.BaseModelDeployer) | None*

The model deployer of the stack.

Returns:
: The model deployer of the stack.

#### *property* model_registry *: [BaseModelRegistry](zenml.model_registries.md#zenml.model_registries.base_model_registry.BaseModelRegistry) | None*

The model registry of the stack.

Returns:
: The model registry of the stack.

#### *property* name *: str*

The name of the stack.

Returns:
: str: The name of the stack.

#### *property* orchestrator *: [BaseOrchestrator](zenml.orchestrators.md#zenml.orchestrators.base_orchestrator.BaseOrchestrator)*

The orchestrator of the stack.

Returns:
: The orchestrator of the stack.

#### prepare_pipeline_deployment(deployment: [PipelineDeploymentResponse](zenml.models.md#zenml.models.PipelineDeploymentResponse)) → None

Prepares the stack for a pipeline deployment.

This method is called before a pipeline is deployed.

Args:
: deployment: The pipeline deployment

Raises:
: StackValidationError: If the stack component is not running.
  RuntimeError: If trying to deploy a pipeline that requires a remote
  <br/>
  > ZenML server with a local one.

#### prepare_step_run(info: [StepRunInfo](zenml.config.md#zenml.config.step_run_info.StepRunInfo)) → None

Prepares running a step.

Args:
: info: Info about the step that will be executed.

#### provision() → None

Provisions resources to run the stack locally.

#### *property* required_secrets *: Set[[secret_utils.SecretReference](zenml.utils.md#zenml.utils.secret_utils.SecretReference)]*

All required secrets for this stack.

Returns:
: The required secrets of this stack.

#### requirements(exclude_components: AbstractSet[[StackComponentType](zenml.md#zenml.enums.StackComponentType)] | None = None) → Set[str]

Set of PyPI requirements for the stack.

This method combines the requirements of all stack components (except
the ones specified in exclude_components).

Args:
: exclude_components: Set of component types for which the
  : requirements should not be included in the output.

Returns:
: Set of PyPI requirements.

#### *property* requires_remote_server *: bool*

If the stack requires a remote ZenServer to run.

This is the case if any code is getting executed remotely. This is the
case for both remote orchestrators as well as remote step operators.

Returns:
: If the stack requires a remote ZenServer to run.

#### resume() → None

Resumes the provisioned local resources of the stack.

Raises:
: ProvisioningError: If any stack component is missing provisioned
  : resources.

#### *property* setting_classes *: Dict[str, Type[[BaseSettings](zenml.config.md#zenml.config.base_settings.BaseSettings)]]*

Setting classes of all components of this stack.

Returns:
: All setting classes and their respective keys.

#### *property* step_operator *: [BaseStepOperator](zenml.step_operators.md#zenml.step_operators.base_step_operator.BaseStepOperator) | None*

The step operator of the stack.

Returns:
: The step operator of the stack.

#### suspend() → None

Suspends the provisioned local resources of the stack.

#### validate(fail_if_secrets_missing: bool = False) → None

Checks whether the stack configuration is valid.

To check if a stack configuration is valid, the following criteria must
be met:
- the stack must have an image builder if other components require it
- the StackValidator of each stack component has to validate the

> stack to make sure all the components are compatible with each other
- the required secrets of all components need to exist

Args:
: fail_if_secrets_missing: If this is True, an error will be raised
  : if a secret for a component is missing. Otherwise, only a
    warning will be logged.

#### validate_image_builder() → None

Validates that the stack has an image builder if required.

If the stack requires an image builder, but none is specified, a
local image builder will be created and assigned to the stack to
ensure backwards compatibility.

## zenml.stack.stack_component module

Implementation of the ZenML Stack Component class.

### *class* zenml.stack.stack_component.StackComponent(name: str, id: UUID, config: [StackComponentConfig](#zenml.stack.stack_component.StackComponentConfig), flavor: str, type: [StackComponentType](zenml.md#zenml.enums.StackComponentType), user: UUID | None, workspace: UUID, created: datetime, updated: datetime, labels: Dict[str, Any] | None = None, connector_requirements: [ServiceConnectorRequirements](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorRequirements) | None = None, connector: UUID | None = None, connector_resource_id: str | None = None, \*args: Any, \*\*kwargs: Any)

Bases: `object`

Abstract StackComponent class for all components of a ZenML stack.

#### *property* apt_packages *: List[str]*

List of APT package requirements for the component.

Returns:
: A list of APT package requirements for the component.

#### cleanup() → None

Cleans up the component after it has been used.

#### cleanup_step_run(info: [StepRunInfo](zenml.config.md#zenml.config.step_run_info.StepRunInfo), step_failed: bool) → None

Cleans up resources after the step run is finished.

Args:
: info: Info about the step that was executed.
  step_failed: Whether the step failed.

#### *property* config *: [StackComponentConfig](#zenml.stack.stack_component.StackComponentConfig)*

Returns the configuration of the stack component.

This should be overwritten by any subclasses that define custom configs
to return the correct config class.

Returns:
: The configuration of the stack component.

#### connector_has_expired() → bool

Checks whether the connector linked to this stack component has expired.

Returns:
: Whether the connector linked to this stack component has expired, or isn’t linked to a connector.

#### deprovision() → None

Deprovisions all resources of the component.

Raises:
: NotImplementedError: If the component does not implement this
  : method.

#### *classmethod* from_model(component_model: [ComponentResponse](zenml.models.md#zenml.models.ComponentResponse)) → [StackComponent](#zenml.stack.stack_component.StackComponent)

Creates a StackComponent from a ComponentModel.

Args:
: component_model: The ComponentModel to create the StackComponent

Returns:
: The created StackComponent.

Raises:
: ImportError: If the flavor can’t be imported.

#### get_connector() → [ServiceConnector](zenml.service_connectors.md#zenml.service_connectors.service_connector.ServiceConnector) | None

Returns the connector linked to this stack component.

Returns:
: The connector linked to this stack component.

Raises:
: RuntimeError: If the stack component does not specify connector
  : requirements or if the connector linked to the component is not
    compatible or not found.

#### get_docker_builds(deployment: [PipelineDeploymentBase](zenml.models.md#zenml.models.PipelineDeploymentBase)) → List[[BuildConfiguration](zenml.config.md#zenml.config.build_configuration.BuildConfiguration)]

Gets the Docker builds required for the component.

Args:
: deployment: The pipeline deployment for which to get the builds.

Returns:
: The required Docker builds.

#### get_pipeline_run_metadata(run_id: UUID) → Dict[str, MetadataType]

Get general component-specific metadata for a pipeline run.

Args:
: run_id: The ID of the pipeline run.

Returns:
: A dictionary of metadata.

#### get_settings(container: [Step](zenml.config.md#zenml.config.step_configurations.Step) | [StepRunResponse](zenml.models.md#zenml.models.StepRunResponse) | [StepRunInfo](zenml.config.md#zenml.config.step_run_info.StepRunInfo) | [PipelineDeploymentBase](zenml.models.md#zenml.models.PipelineDeploymentBase) | [PipelineDeploymentResponse](zenml.models.md#zenml.models.PipelineDeploymentResponse)) → [BaseSettings](zenml.config.md#zenml.config.base_settings.BaseSettings)

Gets settings for this stack component.

This will return None if the stack component doesn’t specify a
settings class or the container doesn’t contain runtime
options for this component.

Args:
: container: The Step, StepRunInfo or PipelineDeployment from
  : which to get the settings.

Returns:
: Settings for this stack component.

Raises:
: RuntimeError: If the stack component does not specify a settings
  : class.

#### get_step_run_metadata(info: [StepRunInfo](zenml.config.md#zenml.config.step_run_info.StepRunInfo)) → Dict[str, MetadataType]

Get component- and step-specific metadata after a step ran.

Args:
: info: Info about the step that was executed.

Returns:
: A dictionary of metadata.

#### *property* is_provisioned *: bool*

If the component provisioned resources to run.

Returns:
: True if the component provisioned resources to run.

#### *property* is_running *: bool*

If the component is running.

Returns:
: True if the component is running.

#### *property* is_suspended *: bool*

If the component is suspended.

Returns:
: True if the component is suspended.

#### *property* local_path *: str | None*

Path to a local directory to store persistent information.

This property should only be implemented by components that need to
store persistent information in a directory on the local machine and
also need that information to be available during pipeline runs.

IMPORTANT: the path returned by this property must always be a path
that is relative to the ZenML local store’s directory. The local
orchestrators rely on this convention to correctly mount the
local folders in the containers. This is an example of a valid
path:

```
``
```

```
`
```

python
from zenml.config.global_config import GlobalConfiguration

…

@property
def local_path(self) -> Optional[str]:

> return os.path.join(
> : GlobalConfiguration().local_stores_path,
>   str(self.uuid),

> )

```
``
```

```
`
```

Returns:
: A path to a local directory used by the component to store
  persistent information.

#### *property* log_file *: str | None*

Optional path to a log file for the stack component.

Returns:
: Optional path to a log file for the stack component.

#### *property* post_registration_message *: str | None*

Optional message printed after the stack component is registered.

Returns:
: An optional message.

#### prepare_pipeline_deployment(deployment: [PipelineDeploymentResponse](zenml.models.md#zenml.models.PipelineDeploymentResponse), stack: [Stack](#zenml.stack.stack.Stack)) → None

Prepares deploying the pipeline.

This method gets called immediately before a pipeline is deployed.
Subclasses should override it if they require runtime configuration
options or if they need to run code before the pipeline deployment.

Args:
: deployment: The pipeline deployment configuration.
  stack: The stack on which the pipeline will be deployed.

#### prepare_step_run(info: [StepRunInfo](zenml.config.md#zenml.config.step_run_info.StepRunInfo)) → None

Prepares running a step.

Args:
: info: Info about the step that will be executed.

#### provision() → None

Provisions resources to run the component.

Raises:
: NotImplementedError: If the component does not implement this
  : method.

#### *property* requirements *: Set[str]*

Set of PyPI requirements for the component.

Returns:
: A set of PyPI requirements for the component.

#### resume() → None

Resumes the provisioned resources of the component.

Raises:
: NotImplementedError: If the component does not implement this
  : method.

#### *property* settings_class *: Type[[BaseSettings](zenml.config.md#zenml.config.base_settings.BaseSettings)] | None*

Class specifying available settings for this component.

Returns:
: Optional settings class.

#### suspend() → None

Suspends the provisioned resources of the component.

Raises:
: NotImplementedError: If the component does not implement this
  : method.

#### *property* validator *: [StackValidator](#zenml.stack.stack_validator.StackValidator) | None*

The optional validator of the stack component.

This validator will be called each time a stack with the stack
component is initialized. Subclasses should override this property
and return a StackValidator that makes sure they’re not included in
any stack that they’re not compatible with.

Returns:
: An optional StackValidator instance.

### *class* zenml.stack.stack_component.StackComponentConfig(warn_about_plain_text_secrets: bool = False)

Bases: `BaseModel`, `ABC`

Base class for all ZenML stack component configs.

#### *property* is_local *: bool*

Checks if this stack component is running locally.

Concrete stack component configuration classes should override this
method to return True if the stack component is relying on local
resources or capabilities (e.g. local filesystem, local database or
other services).

Examples:
: * Artifact Stores that store artifacts in the local filesystem
  * Orchestrators that are connected to local orchestration runtime
  <br/>
  services (e.g. local Kubernetes clusters, Docker containers etc).

Returns:
: True if this config is for a local component, False otherwise.

#### *property* is_remote *: bool*

Checks if this stack component is running remotely.

Concrete stack component configuration classes should override this
method to return True if the stack component is running in a remote
location, and it needs to access the ZenML database.

This designation is used to determine if the stack component can be
used with a local ZenML database or if it requires a remote ZenML
server.

Examples:
: * Orchestrators that are running pipelines in the cloud or in a
  <br/>
  location other than the local host
  \* Step Operators that are running steps in the cloud or in a location
  other than the local host

Returns:
: True if this config is for a remote component, False otherwise.

#### *property* is_valid *: bool*

Checks if the stack component configurations are valid.

Concrete stack component configuration classes should override this
method to return False if the stack component configurations are invalid.

Returns:
: True if the stack component config is valid, False otherwise.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### *property* required_secrets *: Set[[SecretReference](zenml.utils.md#zenml.utils.secret_utils.SecretReference)]*

All required secrets for this stack component.

Returns:
: The required secrets of this stack component.

## zenml.stack.stack_validator module

Implementation of the ZenML Stack Validator.

### *class* zenml.stack.stack_validator.StackValidator(required_components: AbstractSet[[StackComponentType](zenml.md#zenml.enums.StackComponentType)] | None = None, custom_validation_function: Callable[[[Stack](#zenml.stack.stack.Stack)], Tuple[bool, str]] | None = None)

Bases: `object`

A StackValidator is used to validate a stack configuration.

Each StackComponent can provide a StackValidator to make sure it is
compatible with all components of the stack. The KubeflowOrchestrator
for example will always require the stack to have a container registry
in order to push the docker images that are required to run a pipeline
in Kubeflow Pipelines.

#### validate(stack: [Stack](#zenml.stack.stack.Stack)) → None

Validates the given stack.

Checks if the stack contains all the required components and passes
the custom validation function of the validator.

Args:
: stack: The stack to validate.

Raises:
: StackValidationError: If the stack does not meet all the
  : validation criteria.

## zenml.stack.utils module

Util functions for handling stacks, components, and flavors.

### zenml.stack.utils.get_flavor_by_name_and_type_from_zen_store(zen_store: [BaseZenStore](zenml.zen_stores.md#zenml.zen_stores.base_zen_store.BaseZenStore), flavor_name: str, component_type: [StackComponentType](zenml.md#zenml.enums.StackComponentType)) → [FlavorResponse](zenml.models.v2.core.md#zenml.models.v2.core.flavor.FlavorResponse)

Get a stack component flavor by name and type from a ZenStore.

Args:
: zen_store: The ZenStore to query.
  flavor_name: The name of a stack component flavor.
  component_type: The type of the stack component.

Returns:
: The flavor model.

Raises:
: KeyError: If no flavor with the given name and type exists.

### zenml.stack.utils.validate_stack_component_config(configuration_dict: Dict[str, Any], flavor_name: str, component_type: [StackComponentType](zenml.md#zenml.enums.StackComponentType), zen_store: [BaseZenStore](zenml.zen_stores.md#zenml.zen_stores.base_zen_store.BaseZenStore) | None = None, validate_custom_flavors: bool = True) → [StackComponentConfig](#zenml.stack.stack_component.StackComponentConfig) | None

Validate the configuration of a stack component.

Args:
: configuration_dict: The stack component configuration to validate.
  flavor_name: The name of the flavor of the stack component.
  component_type: The type of the stack component.
  zen_store: An optional ZenStore in which to look for the flavor. If not
  <br/>
  > provided, the flavor will be fetched via the regular ZenML Client.
  > This is mainly useful for checks running inside the ZenML server.
  <br/>
  validate_custom_flavors: When loading custom flavors from the local
  : environment, this flag decides whether the import failures are
    raised or an empty value is returned.

Returns:
: The validated stack component configuration or None, if the
  flavor is a custom flavor that could not be imported from the local
  environment and the validate_custom_flavors flag is set to False.

Raises:
: ValueError: If the configuration is invalid.
  ImportError: If the flavor class could not be imported.
  ModuleNotFoundError: If the flavor class could not be imported.

### zenml.stack.utils.warn_if_config_server_mismatch(configuration: [StackComponentConfig](#zenml.stack.stack_component.StackComponentConfig)) → None

Warn if a component configuration is mismatched with the ZenML server.

Args:
: configuration: The component configuration to check.

## Module contents

Initialization of the ZenML Stack.

The stack is essentially all the configuration for the infrastructure of your
MLOps platform.

A stack is made up of multiple components. Some examples are:

- An Artifact Store
- An Orchestrator
- A Step Operator (Optional)
- A Container Registry (Optional)

### *class* zenml.stack.Flavor

Bases: `object`

Class for ZenML Flavors.

#### *abstract property* config_class *: Type[[StackComponentConfig](#zenml.stack.stack_component.StackComponentConfig)]*

Returns StackComponentConfig config class.

Returns:
: The config class.

#### *property* config_schema *: Dict[str, Any]*

The config schema for a flavor.

Returns:
: The config schema.

#### *property* docs_url *: str | None*

A url to point at docs explaining this flavor.

Returns:
: A flavor docs url.

#### *classmethod* from_model(flavor_model: [FlavorResponse](zenml.models.v2.core.md#zenml.models.v2.core.flavor.FlavorResponse)) → [Flavor](#zenml.stack.flavor.Flavor)

Loads a flavor from a model.

Args:
: flavor_model: The model to load from.

Returns:
: The loaded flavor.

#### generate_default_docs_url() → str

Generate the doc urls for all inbuilt and integration flavors.

Note that this method is not going to be useful for custom flavors,
which do not have any docs in the main zenml docs.

Returns:
: The complete url to the zenml documentation

#### generate_default_sdk_docs_url() → str

Generate SDK docs url for a flavor.

Returns:
: The complete url to the zenml SDK docs

#### *abstract property* implementation_class *: Type[[StackComponent](#zenml.stack.stack_component.StackComponent)]*

Implementation class for this flavor.

Returns:
: The implementation class for this flavor.

#### *property* logo_url *: str | None*

A url to represent the flavor in the dashboard.

Returns:
: The flavor logo.

#### *abstract property* name *: str*

The flavor name.

Returns:
: The flavor name.

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

#### to_model(integration: str | None = None, is_custom: bool = True) → [FlavorRequest](zenml.models.v2.core.md#zenml.models.v2.core.flavor.FlavorRequest)

Converts a flavor to a model.

Args:
: integration: The integration to use for the model.
  is_custom: Whether the flavor is a custom flavor. Custom flavors
  <br/>
  > are then scoped by user and workspace

Returns:
: The model.

#### *abstract property* type *: [StackComponentType](zenml.md#zenml.enums.StackComponentType)*

The stack component type.

Returns:
: The stack component type.

### *class* zenml.stack.Stack(id: UUID, name: str, \*, orchestrator: [BaseOrchestrator](zenml.orchestrators.md#zenml.orchestrators.base_orchestrator.BaseOrchestrator), artifact_store: [BaseArtifactStore](zenml.artifact_stores.md#zenml.artifact_stores.base_artifact_store.BaseArtifactStore), container_registry: [BaseContainerRegistry](zenml.container_registries.md#zenml.container_registries.base_container_registry.BaseContainerRegistry) | None = None, step_operator: [BaseStepOperator](zenml.step_operators.md#zenml.step_operators.base_step_operator.BaseStepOperator) | None = None, feature_store: [BaseFeatureStore](zenml.feature_stores.md#zenml.feature_stores.base_feature_store.BaseFeatureStore) | None = None, model_deployer: [BaseModelDeployer](zenml.model_deployers.md#zenml.model_deployers.base_model_deployer.BaseModelDeployer) | None = None, experiment_tracker: [BaseExperimentTracker](zenml.experiment_trackers.md#zenml.experiment_trackers.base_experiment_tracker.BaseExperimentTracker) | None = None, alerter: [BaseAlerter](zenml.alerter.md#zenml.alerter.base_alerter.BaseAlerter) | None = None, annotator: [BaseAnnotator](zenml.annotators.md#zenml.annotators.base_annotator.BaseAnnotator) | None = None, data_validator: [BaseDataValidator](zenml.data_validators.md#zenml.data_validators.base_data_validator.BaseDataValidator) | None = None, image_builder: [BaseImageBuilder](zenml.image_builders.md#zenml.image_builders.base_image_builder.BaseImageBuilder) | None = None, model_registry: [BaseModelRegistry](zenml.model_registries.md#zenml.model_registries.base_model_registry.BaseModelRegistry) | None = None)

Bases: `object`

ZenML stack class.

A ZenML stack is a collection of multiple stack components that are
required to run ZenML pipelines. Some of these components (orchestrator,
and artifact store) are required to run any kind of
pipeline, other components like the container registry are only required
if other stack components depend on them.

#### *property* alerter *: [BaseAlerter](zenml.alerter.md#zenml.alerter.base_alerter.BaseAlerter) | None*

The alerter of the stack.

Returns:
: The alerter of the stack.

#### *property* annotator *: [BaseAnnotator](zenml.annotators.md#zenml.annotators.base_annotator.BaseAnnotator) | None*

The annotator of the stack.

Returns:
: The annotator of the stack.

#### *property* apt_packages *: List[str]*

List of APT package requirements for the stack.

Returns:
: A list of APT package requirements for the stack.

#### *property* artifact_store *: [BaseArtifactStore](zenml.artifact_stores.md#zenml.artifact_stores.base_artifact_store.BaseArtifactStore)*

The artifact store of the stack.

Returns:
: The artifact store of the stack.

#### check_local_paths() → bool

Checks if the stack has local paths.

Returns:
: True if the stack has local paths, False otherwise.

Raises:
: ValueError: If the stack has local paths that do not conform to
  : the convention that all local path must be relative to the
    local stores directory.

#### cleanup_step_run(info: [StepRunInfo](zenml.config.md#zenml.config.step_run_info.StepRunInfo), step_failed: bool) → None

Cleans up resources after the step run is finished.

Args:
: info: Info about the step that was executed.
  step_failed: Whether the step failed.

#### *property* components *: Dict[[StackComponentType](zenml.md#zenml.enums.StackComponentType), [StackComponent](#zenml.stack.StackComponent)]*

All components of the stack.

Returns:
: A dictionary of all components of the stack.

#### *property* container_registry *: [BaseContainerRegistry](zenml.container_registries.md#zenml.container_registries.base_container_registry.BaseContainerRegistry) | None*

The container registry of the stack.

Returns:
: The container registry of the stack or None if the stack does not
  have a container registry.

#### *property* data_validator *: [BaseDataValidator](zenml.data_validators.md#zenml.data_validators.base_data_validator.BaseDataValidator) | None*

The data validator of the stack.

Returns:
: The data validator of the stack.

#### deploy_pipeline(deployment: [PipelineDeploymentResponse](zenml.models.md#zenml.models.PipelineDeploymentResponse)) → Any

Deploys a pipeline on this stack.

Args:
: deployment: The pipeline deployment.

Returns:
: The return value of the call to orchestrator.run_pipeline(…).

#### deprovision() → None

Deprovisions all local resources of the stack.

#### dict() → Dict[str, str]

Converts the stack into a dictionary.

Returns:
: A dictionary containing the stack components.

#### *property* experiment_tracker *: [BaseExperimentTracker](zenml.experiment_trackers.md#zenml.experiment_trackers.base_experiment_tracker.BaseExperimentTracker) | None*

The experiment tracker of the stack.

Returns:
: The experiment tracker of the stack.

#### *property* feature_store *: [BaseFeatureStore](zenml.feature_stores.md#zenml.feature_stores.base_feature_store.BaseFeatureStore) | None*

The feature store of the stack.

Returns:
: The feature store of the stack.

#### *classmethod* from_components(id: UUID, name: str, components: Dict[[StackComponentType](zenml.md#zenml.enums.StackComponentType), [StackComponent](#zenml.stack.StackComponent)]) → [Stack](#zenml.stack.Stack)

Creates a stack instance from a dict of stack components.

# noqa: DAR402

Args:
: id: Unique ID of the stack.
  name: The name of the stack.
  components: The components of the stack.

Returns:
: A stack instance consisting of the given components.

Raises:
: TypeError: If a required component is missing or a component
  : doesn’t inherit from the expected base class.

#### *classmethod* from_model(stack_model: [StackResponse](zenml.models.v2.core.md#zenml.models.v2.core.stack.StackResponse)) → [Stack](#zenml.stack.stack.Stack)

Creates a Stack instance from a StackModel.

Args:
: stack_model: The StackModel to create the Stack from.

Returns:
: The created Stack instance.

#### get_docker_builds(deployment: [PipelineDeploymentBase](zenml.models.md#zenml.models.PipelineDeploymentBase)) → List[[BuildConfiguration](zenml.config.md#zenml.config.build_configuration.BuildConfiguration)]

Gets the Docker builds required for the stack.

Args:
: deployment: The pipeline deployment for which to get the builds.

Returns:
: The required Docker builds.

#### get_pipeline_run_metadata(run_id: UUID) → Dict[UUID, Dict[str, str | int | float | bool | Dict[Any, Any] | List[Any] | Set[Any] | Tuple[Any, ...] | [Uri](zenml.metadata.md#zenml.metadata.metadata_types.Uri) | [Path](zenml.metadata.md#zenml.metadata.metadata_types.Path) | [DType](zenml.metadata.md#zenml.metadata.metadata_types.DType) | [StorageSize](zenml.metadata.md#zenml.metadata.metadata_types.StorageSize)]]

Get general component-specific metadata for a pipeline run.

Args:
: run_id: ID of the pipeline run.

Returns:
: A dictionary mapping component IDs to the metadata they created.

#### get_step_run_metadata(info: [StepRunInfo](zenml.config.md#zenml.config.step_run_info.StepRunInfo)) → Dict[UUID, Dict[str, str | int | float | bool | Dict[Any, Any] | List[Any] | Set[Any] | Tuple[Any, ...] | [Uri](zenml.metadata.md#zenml.metadata.metadata_types.Uri) | [Path](zenml.metadata.md#zenml.metadata.metadata_types.Path) | [DType](zenml.metadata.md#zenml.metadata.metadata_types.DType) | [StorageSize](zenml.metadata.md#zenml.metadata.metadata_types.StorageSize)]]

Get component-specific metadata for a step run.

Args:
: info: Info about the step that was executed.

Returns:
: A dictionary mapping component IDs to the metadata they created.

#### *property* id *: UUID*

The ID of the stack.

Returns:
: The ID of the stack.

#### *property* image_builder *: [BaseImageBuilder](zenml.image_builders.md#zenml.image_builders.base_image_builder.BaseImageBuilder) | None*

The image builder of the stack.

Returns:
: The image builder of the stack.

#### *property* is_provisioned *: bool*

If the stack provisioned resources to run locally.

Returns:
: True if the stack provisioned resources to run locally.

#### *property* is_running *: bool*

If the stack is running locally.

Returns:
: True if the stack is running locally, False otherwise.

#### *property* model_deployer *: [BaseModelDeployer](zenml.model_deployers.md#zenml.model_deployers.base_model_deployer.BaseModelDeployer) | None*

The model deployer of the stack.

Returns:
: The model deployer of the stack.

#### *property* model_registry *: [BaseModelRegistry](zenml.model_registries.md#zenml.model_registries.base_model_registry.BaseModelRegistry) | None*

The model registry of the stack.

Returns:
: The model registry of the stack.

#### *property* name *: str*

The name of the stack.

Returns:
: str: The name of the stack.

#### *property* orchestrator *: [BaseOrchestrator](zenml.orchestrators.md#zenml.orchestrators.base_orchestrator.BaseOrchestrator)*

The orchestrator of the stack.

Returns:
: The orchestrator of the stack.

#### prepare_pipeline_deployment(deployment: [PipelineDeploymentResponse](zenml.models.md#zenml.models.PipelineDeploymentResponse)) → None

Prepares the stack for a pipeline deployment.

This method is called before a pipeline is deployed.

Args:
: deployment: The pipeline deployment

Raises:
: StackValidationError: If the stack component is not running.
  RuntimeError: If trying to deploy a pipeline that requires a remote
  <br/>
  > ZenML server with a local one.

#### prepare_step_run(info: [StepRunInfo](zenml.config.md#zenml.config.step_run_info.StepRunInfo)) → None

Prepares running a step.

Args:
: info: Info about the step that will be executed.

#### provision() → None

Provisions resources to run the stack locally.

#### *property* required_secrets *: Set[[secret_utils.SecretReference](zenml.utils.md#zenml.utils.secret_utils.SecretReference)]*

All required secrets for this stack.

Returns:
: The required secrets of this stack.

#### requirements(exclude_components: AbstractSet[[StackComponentType](zenml.md#zenml.enums.StackComponentType)] | None = None) → Set[str]

Set of PyPI requirements for the stack.

This method combines the requirements of all stack components (except
the ones specified in exclude_components).

Args:
: exclude_components: Set of component types for which the
  : requirements should not be included in the output.

Returns:
: Set of PyPI requirements.

#### *property* requires_remote_server *: bool*

If the stack requires a remote ZenServer to run.

This is the case if any code is getting executed remotely. This is the
case for both remote orchestrators as well as remote step operators.

Returns:
: If the stack requires a remote ZenServer to run.

#### resume() → None

Resumes the provisioned local resources of the stack.

Raises:
: ProvisioningError: If any stack component is missing provisioned
  : resources.

#### *property* setting_classes *: Dict[str, Type[[BaseSettings](zenml.config.md#zenml.config.base_settings.BaseSettings)]]*

Setting classes of all components of this stack.

Returns:
: All setting classes and their respective keys.

#### *property* step_operator *: [BaseStepOperator](zenml.step_operators.md#zenml.step_operators.base_step_operator.BaseStepOperator) | None*

The step operator of the stack.

Returns:
: The step operator of the stack.

#### suspend() → None

Suspends the provisioned local resources of the stack.

#### validate(fail_if_secrets_missing: bool = False) → None

Checks whether the stack configuration is valid.

To check if a stack configuration is valid, the following criteria must
be met:
- the stack must have an image builder if other components require it
- the StackValidator of each stack component has to validate the

> stack to make sure all the components are compatible with each other
- the required secrets of all components need to exist

Args:
: fail_if_secrets_missing: If this is True, an error will be raised
  : if a secret for a component is missing. Otherwise, only a
    warning will be logged.

#### validate_image_builder() → None

Validates that the stack has an image builder if required.

If the stack requires an image builder, but none is specified, a
local image builder will be created and assigned to the stack to
ensure backwards compatibility.

### *class* zenml.stack.StackComponent(name: str, id: UUID, config: [StackComponentConfig](#zenml.stack.stack_component.StackComponentConfig), flavor: str, type: [StackComponentType](zenml.md#zenml.enums.StackComponentType), user: UUID | None, workspace: UUID, created: datetime, updated: datetime, labels: Dict[str, Any] | None = None, connector_requirements: [ServiceConnectorRequirements](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorRequirements) | None = None, connector: UUID | None = None, connector_resource_id: str | None = None, \*args: Any, \*\*kwargs: Any)

Bases: `object`

Abstract StackComponent class for all components of a ZenML stack.

#### *property* apt_packages *: List[str]*

List of APT package requirements for the component.

Returns:
: A list of APT package requirements for the component.

#### cleanup() → None

Cleans up the component after it has been used.

#### cleanup_step_run(info: [StepRunInfo](zenml.config.md#zenml.config.step_run_info.StepRunInfo), step_failed: bool) → None

Cleans up resources after the step run is finished.

Args:
: info: Info about the step that was executed.
  step_failed: Whether the step failed.

#### *property* config *: [StackComponentConfig](#zenml.stack.stack_component.StackComponentConfig)*

Returns the configuration of the stack component.

This should be overwritten by any subclasses that define custom configs
to return the correct config class.

Returns:
: The configuration of the stack component.

#### connector_has_expired() → bool

Checks whether the connector linked to this stack component has expired.

Returns:
: Whether the connector linked to this stack component has expired, or isn’t linked to a connector.

#### deprovision() → None

Deprovisions all resources of the component.

Raises:
: NotImplementedError: If the component does not implement this
  : method.

#### *classmethod* from_model(component_model: [ComponentResponse](zenml.models.md#zenml.models.ComponentResponse)) → [StackComponent](#zenml.stack.StackComponent)

Creates a StackComponent from a ComponentModel.

Args:
: component_model: The ComponentModel to create the StackComponent

Returns:
: The created StackComponent.

Raises:
: ImportError: If the flavor can’t be imported.

#### get_connector() → [ServiceConnector](zenml.service_connectors.md#zenml.service_connectors.service_connector.ServiceConnector) | None

Returns the connector linked to this stack component.

Returns:
: The connector linked to this stack component.

Raises:
: RuntimeError: If the stack component does not specify connector
  : requirements or if the connector linked to the component is not
    compatible or not found.

#### get_docker_builds(deployment: [PipelineDeploymentBase](zenml.models.md#zenml.models.PipelineDeploymentBase)) → List[[BuildConfiguration](zenml.config.md#zenml.config.build_configuration.BuildConfiguration)]

Gets the Docker builds required for the component.

Args:
: deployment: The pipeline deployment for which to get the builds.

Returns:
: The required Docker builds.

#### get_pipeline_run_metadata(run_id: UUID) → Dict[str, MetadataType]

Get general component-specific metadata for a pipeline run.

Args:
: run_id: The ID of the pipeline run.

Returns:
: A dictionary of metadata.

#### get_settings(container: [Step](zenml.config.md#zenml.config.step_configurations.Step) | [StepRunResponse](zenml.models.md#zenml.models.StepRunResponse) | [StepRunInfo](zenml.config.md#zenml.config.step_run_info.StepRunInfo) | [PipelineDeploymentBase](zenml.models.md#zenml.models.PipelineDeploymentBase) | [PipelineDeploymentResponse](zenml.models.md#zenml.models.PipelineDeploymentResponse)) → [BaseSettings](zenml.config.md#zenml.config.base_settings.BaseSettings)

Gets settings for this stack component.

This will return None if the stack component doesn’t specify a
settings class or the container doesn’t contain runtime
options for this component.

Args:
: container: The Step, StepRunInfo or PipelineDeployment from
  : which to get the settings.

Returns:
: Settings for this stack component.

Raises:
: RuntimeError: If the stack component does not specify a settings
  : class.

#### get_step_run_metadata(info: [StepRunInfo](zenml.config.md#zenml.config.step_run_info.StepRunInfo)) → Dict[str, MetadataType]

Get component- and step-specific metadata after a step ran.

Args:
: info: Info about the step that was executed.

Returns:
: A dictionary of metadata.

#### *property* is_provisioned *: bool*

If the component provisioned resources to run.

Returns:
: True if the component provisioned resources to run.

#### *property* is_running *: bool*

If the component is running.

Returns:
: True if the component is running.

#### *property* is_suspended *: bool*

If the component is suspended.

Returns:
: True if the component is suspended.

#### *property* local_path *: str | None*

Path to a local directory to store persistent information.

This property should only be implemented by components that need to
store persistent information in a directory on the local machine and
also need that information to be available during pipeline runs.

IMPORTANT: the path returned by this property must always be a path
that is relative to the ZenML local store’s directory. The local
orchestrators rely on this convention to correctly mount the
local folders in the containers. This is an example of a valid
path:

```
``
```

```
`
```

python
from zenml.config.global_config import GlobalConfiguration

…

@property
def local_path(self) -> Optional[str]:

> return os.path.join(
> : GlobalConfiguration().local_stores_path,
>   str(self.uuid),

> )

```
``
```

```
`
```

Returns:
: A path to a local directory used by the component to store
  persistent information.

#### *property* log_file *: str | None*

Optional path to a log file for the stack component.

Returns:
: Optional path to a log file for the stack component.

#### *property* post_registration_message *: str | None*

Optional message printed after the stack component is registered.

Returns:
: An optional message.

#### prepare_pipeline_deployment(deployment: [PipelineDeploymentResponse](zenml.models.md#zenml.models.PipelineDeploymentResponse), stack: [Stack](#zenml.stack.Stack)) → None

Prepares deploying the pipeline.

This method gets called immediately before a pipeline is deployed.
Subclasses should override it if they require runtime configuration
options or if they need to run code before the pipeline deployment.

Args:
: deployment: The pipeline deployment configuration.
  stack: The stack on which the pipeline will be deployed.

#### prepare_step_run(info: [StepRunInfo](zenml.config.md#zenml.config.step_run_info.StepRunInfo)) → None

Prepares running a step.

Args:
: info: Info about the step that will be executed.

#### provision() → None

Provisions resources to run the component.

Raises:
: NotImplementedError: If the component does not implement this
  : method.

#### *property* requirements *: Set[str]*

Set of PyPI requirements for the component.

Returns:
: A set of PyPI requirements for the component.

#### resume() → None

Resumes the provisioned resources of the component.

Raises:
: NotImplementedError: If the component does not implement this
  : method.

#### *property* settings_class *: Type[[BaseSettings](zenml.config.md#zenml.config.base_settings.BaseSettings)] | None*

Class specifying available settings for this component.

Returns:
: Optional settings class.

#### suspend() → None

Suspends the provisioned resources of the component.

Raises:
: NotImplementedError: If the component does not implement this
  : method.

#### *property* validator *: [StackValidator](#zenml.stack.StackValidator) | None*

The optional validator of the stack component.

This validator will be called each time a stack with the stack
component is initialized. Subclasses should override this property
and return a StackValidator that makes sure they’re not included in
any stack that they’re not compatible with.

Returns:
: An optional StackValidator instance.

### *class* zenml.stack.StackComponentConfig(warn_about_plain_text_secrets: bool = False)

Bases: `BaseModel`, `ABC`

Base class for all ZenML stack component configs.

#### *property* is_local *: bool*

Checks if this stack component is running locally.

Concrete stack component configuration classes should override this
method to return True if the stack component is relying on local
resources or capabilities (e.g. local filesystem, local database or
other services).

Examples:
: * Artifact Stores that store artifacts in the local filesystem
  * Orchestrators that are connected to local orchestration runtime
  <br/>
  services (e.g. local Kubernetes clusters, Docker containers etc).

Returns:
: True if this config is for a local component, False otherwise.

#### *property* is_remote *: bool*

Checks if this stack component is running remotely.

Concrete stack component configuration classes should override this
method to return True if the stack component is running in a remote
location, and it needs to access the ZenML database.

This designation is used to determine if the stack component can be
used with a local ZenML database or if it requires a remote ZenML
server.

Examples:
: * Orchestrators that are running pipelines in the cloud or in a
  <br/>
  location other than the local host
  \* Step Operators that are running steps in the cloud or in a location
  other than the local host

Returns:
: True if this config is for a remote component, False otherwise.

#### *property* is_valid *: bool*

Checks if the stack component configurations are valid.

Concrete stack component configuration classes should override this
method to return False if the stack component configurations are invalid.

Returns:
: True if the stack component config is valid, False otherwise.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### *property* required_secrets *: Set[[SecretReference](zenml.utils.md#zenml.utils.secret_utils.SecretReference)]*

All required secrets for this stack component.

Returns:
: The required secrets of this stack component.

### *class* zenml.stack.StackValidator(required_components: AbstractSet[[StackComponentType](zenml.md#zenml.enums.StackComponentType)] | None = None, custom_validation_function: Callable[[[Stack](#zenml.stack.Stack)], Tuple[bool, str]] | None = None)

Bases: `object`

A StackValidator is used to validate a stack configuration.

Each StackComponent can provide a StackValidator to make sure it is
compatible with all components of the stack. The KubeflowOrchestrator
for example will always require the stack to have a container registry
in order to push the docker images that are required to run a pipeline
in Kubeflow Pipelines.

#### validate(stack: [Stack](#zenml.stack.Stack)) → None

Validates the given stack.

Checks if the stack contains all the required components and passes
the custom validation function of the validator.

Args:
: stack: The stack to validate.

Raises:
: StackValidationError: If the stack does not meet all the
  : validation criteria.
