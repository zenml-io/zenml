# zenml.experiment_trackers package

## Submodules

## zenml.experiment_trackers.base_experiment_tracker module

Base class for all ZenML experiment trackers.

### *class* zenml.experiment_trackers.base_experiment_tracker.BaseExperimentTracker(name: str, id: UUID, config: [StackComponentConfig](zenml.stack.md#zenml.stack.stack_component.StackComponentConfig), flavor: str, type: [StackComponentType](zenml.md#zenml.enums.StackComponentType), user: UUID | None, workspace: UUID, created: datetime, updated: datetime, labels: Dict[str, Any] | None = None, connector_requirements: [ServiceConnectorRequirements](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorRequirements) | None = None, connector: UUID | None = None, connector_resource_id: str | None = None, \*args: Any, \*\*kwargs: Any)

Bases: [`StackComponent`](zenml.stack.md#zenml.stack.stack_component.StackComponent), `ABC`

Base class for all ZenML experiment trackers.

#### *property* config *: [BaseExperimentTrackerConfig](#zenml.experiment_trackers.base_experiment_tracker.BaseExperimentTrackerConfig)*

Returns the config of the experiment tracker.

Returns:
: The config of the experiment tracker.

### *class* zenml.experiment_trackers.base_experiment_tracker.BaseExperimentTrackerConfig(warn_about_plain_text_secrets: bool = False)

Bases: [`StackComponentConfig`](zenml.stack.md#zenml.stack.stack_component.StackComponentConfig)

Base config for experiment trackers.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.experiment_trackers.base_experiment_tracker.BaseExperimentTrackerFlavor

Bases: [`Flavor`](zenml.stack.md#zenml.stack.flavor.Flavor)

Base class for all ZenML experiment tracker flavors.

#### *property* config_class *: Type[[BaseExperimentTrackerConfig](#zenml.experiment_trackers.base_experiment_tracker.BaseExperimentTrackerConfig)]*

Config class for this flavor.

Returns:
: The config class for this flavor.

#### *abstract property* implementation_class *: Type[[StackComponent](zenml.stack.md#zenml.stack.stack_component.StackComponent)]*

Returns the implementation class for this flavor.

Returns:
: The implementation class for this flavor.

#### *property* type *: [StackComponentType](zenml.md#zenml.enums.StackComponentType)*

Type of the flavor.

Returns:
: StackComponentType: The type of the flavor.

## Module contents

Experiment trackers let you track your ML experiments.

They log the parameters used and allow you to compare between runs. In the ZenML
world, every pipeline run is considered an experiment, and ZenML facilitates the
storage of experiment results through ExperimentTracker stack components. This
establishes a clear link between pipeline runs and experiments.

### *class* zenml.experiment_trackers.BaseExperimentTracker(name: str, id: UUID, config: [StackComponentConfig](zenml.stack.md#zenml.stack.stack_component.StackComponentConfig), flavor: str, type: [StackComponentType](zenml.md#zenml.enums.StackComponentType), user: UUID | None, workspace: UUID, created: datetime, updated: datetime, labels: Dict[str, Any] | None = None, connector_requirements: [ServiceConnectorRequirements](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorRequirements) | None = None, connector: UUID | None = None, connector_resource_id: str | None = None, \*args: Any, \*\*kwargs: Any)

Bases: [`StackComponent`](zenml.stack.md#zenml.stack.stack_component.StackComponent), `ABC`

Base class for all ZenML experiment trackers.

#### *property* config *: [BaseExperimentTrackerConfig](#zenml.experiment_trackers.base_experiment_tracker.BaseExperimentTrackerConfig)*

Returns the config of the experiment tracker.

Returns:
: The config of the experiment tracker.
