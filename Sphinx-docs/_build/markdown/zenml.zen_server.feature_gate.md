# zenml.zen_server.feature_gate package

## Submodules

## zenml.zen_server.feature_gate.endpoint_utils module

All endpoint utils for the feature gate implementations.

### zenml.zen_server.feature_gate.endpoint_utils.check_entitlement(resource_type: [ResourceType](zenml.zen_server.rbac.md#zenml.zen_server.rbac.models.ResourceType)) → None

Queries the feature gate to see if the operation falls within the tenants entitlements.

Raises an exception if the user is not entitled to create an instance of the
resource. Otherwise, simply returns.

Args:
: resource_type: The type of resource to check for.

### zenml.zen_server.feature_gate.endpoint_utils.report_decrement(resource_type: [ResourceType](zenml.zen_server.rbac.md#zenml.zen_server.rbac.models.ResourceType), resource_id: UUID) → None

Reports the deletion/deactivation of a feature/resource.

Args:
: resource_type: The type of resource to report a decrement in count for.
  resource_id: ID of the resource that was deleted.

### zenml.zen_server.feature_gate.endpoint_utils.report_usage(resource_type: [ResourceType](zenml.zen_server.rbac.md#zenml.zen_server.rbac.models.ResourceType), resource_id: UUID) → None

Reports the creation/usage of a feature/resource.

Args:
: resource_type: The type of resource to report a usage for
  resource_id: ID of the resource that was created.

## zenml.zen_server.feature_gate.feature_gate_interface module

Definition of the feature gate interface.

### *class* zenml.zen_server.feature_gate.feature_gate_interface.FeatureGateInterface

Bases: `ABC`

RBAC interface definition.

#### *abstract* check_entitlement(resource: [ResourceType](zenml.zen_server.rbac.md#zenml.zen_server.rbac.models.ResourceType)) → None

Checks if a user is entitled to create a resource.

Args:
: resource: The resource the user wants to create

Raises:
: UpgradeRequiredError in case a subscription limit is reached

#### *abstract* report_event(resource: [ResourceType](zenml.zen_server.rbac.md#zenml.zen_server.rbac.models.ResourceType), resource_id: UUID, is_decrement: bool = False) → None

Reports the usage of a feature to the aggregator backend.

Args:
: resource: The resource the user created
  resource_id: ID of the resource that was created/deleted.
  is_decrement: In case this event reports an actual decrement of usage

## zenml.zen_server.feature_gate.zenml_cloud_feature_gate module

ZenML Pro implementation of the feature gate.

### *class* zenml.zen_server.feature_gate.zenml_cloud_feature_gate.RawUsageEvent(\*, organization_id: str, feature: [ResourceType](zenml.zen_server.rbac.md#zenml.zen_server.rbac.models.ResourceType), total: int, metadata: Dict[str, Any] = {})

Bases: `BaseModel`

Model for reporting raw usage of a feature.

In case of consumables the UsageReport allows the Pricing Backend to
increment the usage per time-frame by 1.

#### feature *: [ResourceType](zenml.zen_server.rbac.md#zenml.zen_server.rbac.models.ResourceType)*

#### metadata *: Dict[str, Any]*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'feature': FieldInfo(annotation=ResourceType, required=True, description='The feature whose usage is being reported.'), 'metadata': FieldInfo(annotation=Dict[str, Any], required=False, default={}, description='Allows attaching additional metadata to events.'), 'organization_id': FieldInfo(annotation=str, required=True, description='The organization that this usage can be attributed to.'), 'total': FieldInfo(annotation=int, required=True, description='The total amount of entities of this type.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### organization_id *: str*

#### total *: int*

### *class* zenml.zen_server.feature_gate.zenml_cloud_feature_gate.ZenMLCloudFeatureGateInterface

Bases: [`FeatureGateInterface`](#zenml.zen_server.feature_gate.feature_gate_interface.FeatureGateInterface)

ZenML Cloud Feature Gate implementation.

#### check_entitlement(resource: [ResourceType](zenml.zen_server.rbac.md#zenml.zen_server.rbac.models.ResourceType)) → None

Checks if a user is entitled to create a resource.

Args:
: resource: The resource the user wants to create

Raises:
: SubscriptionUpgradeRequiredError: in case a subscription limit is reached

#### report_event(resource: [ResourceType](zenml.zen_server.rbac.md#zenml.zen_server.rbac.models.ResourceType), resource_id: UUID, is_decrement: bool = False) → None

Reports the usage of a feature to the aggregator backend.

Args:
: resource: The resource the user created
  resource_id: ID of the resource that was created/deleted.
  is_decrement: In case this event reports an actual decrement of usage

## Module contents
