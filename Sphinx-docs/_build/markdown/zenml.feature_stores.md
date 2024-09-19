# zenml.feature_stores package

## Submodules

## zenml.feature_stores.base_feature_store module

The base class for feature stores.

### *class* zenml.feature_stores.base_feature_store.BaseFeatureStore(name: str, id: UUID, config: [StackComponentConfig](zenml.stack.md#zenml.stack.stack_component.StackComponentConfig), flavor: str, type: [StackComponentType](zenml.md#zenml.enums.StackComponentType), user: UUID | None, workspace: UUID, created: datetime, updated: datetime, labels: Dict[str, Any] | None = None, connector_requirements: [ServiceConnectorRequirements](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorRequirements) | None = None, connector: UUID | None = None, connector_resource_id: str | None = None, \*args: Any, \*\*kwargs: Any)

Bases: [`StackComponent`](zenml.stack.md#zenml.stack.stack_component.StackComponent), `ABC`

Base class for all ZenML feature stores.

#### *property* config *: [BaseFeatureStoreConfig](#zenml.feature_stores.base_feature_store.BaseFeatureStoreConfig)*

Returns the BaseFeatureStoreConfig config.

Returns:
: The configuration.

#### *abstract* get_historical_features(entity_df: Any, features: List[str], full_feature_names: bool = False) → Any

Returns the historical features for training or batch scoring.

Args:
: entity_df: The entity DataFrame or entity name.
  features: The features to retrieve.
  full_feature_names: Whether to return the full feature names.

Returns:
: The historical features.

#### *abstract* get_online_features(entity_rows: List[Dict[str, Any]], features: List[str], full_feature_names: bool = False) → Dict[str, Any]

Returns the latest online feature data.

Args:
: entity_rows: The entity rows to retrieve.
  features: The features to retrieve.
  full_feature_names: Whether to return the full feature names.

Returns:
: The latest online feature data as a dictionary.

### *class* zenml.feature_stores.base_feature_store.BaseFeatureStoreConfig(warn_about_plain_text_secrets: bool = False)

Bases: [`StackComponentConfig`](zenml.stack.md#zenml.stack.stack_component.StackComponentConfig)

Base config for feature stores.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.feature_stores.base_feature_store.BaseFeatureStoreFlavor

Bases: [`Flavor`](zenml.stack.md#zenml.stack.flavor.Flavor)

Base class for all ZenML feature store flavors.

#### *property* config_class *: Type[[BaseFeatureStoreConfig](#zenml.feature_stores.base_feature_store.BaseFeatureStoreConfig)]*

Config class for this flavor.

Returns:
: The config class.

#### *abstract property* implementation_class *: Type[[BaseFeatureStore](#zenml.feature_stores.base_feature_store.BaseFeatureStore)]*

Implementation class.

Returns:
: The implementation class.

#### *property* type *: [StackComponentType](zenml.md#zenml.enums.StackComponentType)*

Returns the flavor type.

Returns:
: The flavor type.

## Module contents

A feature store enables an offline and online serving of feature data.

Feature stores allow data teams to serve data via an offline store and an online
low-latency store where data is kept in sync between the two. It also offers a
centralized registry where features (and feature schemas) are stored for use
within a team or wider organization.

As a data scientist working on training your model, your requirements for how
you access your batch / ‘offline’ data will almost certainly be different from
how you access that data as part of a real-time or online inference setting.
Feast solves the problem of developing train-serve skew where those two sources
of data diverge from each other.

### *class* zenml.feature_stores.BaseFeatureStore(name: str, id: UUID, config: [StackComponentConfig](zenml.stack.md#zenml.stack.stack_component.StackComponentConfig), flavor: str, type: [StackComponentType](zenml.md#zenml.enums.StackComponentType), user: UUID | None, workspace: UUID, created: datetime, updated: datetime, labels: Dict[str, Any] | None = None, connector_requirements: [ServiceConnectorRequirements](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorRequirements) | None = None, connector: UUID | None = None, connector_resource_id: str | None = None, \*args: Any, \*\*kwargs: Any)

Bases: [`StackComponent`](zenml.stack.md#zenml.stack.stack_component.StackComponent), `ABC`

Base class for all ZenML feature stores.

#### *property* config *: [BaseFeatureStoreConfig](#zenml.feature_stores.base_feature_store.BaseFeatureStoreConfig)*

Returns the BaseFeatureStoreConfig config.

Returns:
: The configuration.

#### *abstract* get_historical_features(entity_df: Any, features: List[str], full_feature_names: bool = False) → Any

Returns the historical features for training or batch scoring.

Args:
: entity_df: The entity DataFrame or entity name.
  features: The features to retrieve.
  full_feature_names: Whether to return the full feature names.

Returns:
: The historical features.

#### *abstract* get_online_features(entity_rows: List[Dict[str, Any]], features: List[str], full_feature_names: bool = False) → Dict[str, Any]

Returns the latest online feature data.

Args:
: entity_rows: The entity rows to retrieve.
  features: The features to retrieve.
  full_feature_names: Whether to return the full feature names.

Returns:
: The latest online feature data as a dictionary.
