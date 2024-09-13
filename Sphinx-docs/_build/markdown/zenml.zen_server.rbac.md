# zenml.zen_server.rbac package

## Submodules

## zenml.zen_server.rbac.endpoint_utils module

## zenml.zen_server.rbac.models module

RBAC model classes.

### *class* zenml.zen_server.rbac.models.Action(value, names=None, \*, module=None, qualname=None, type=None, start=1, boundary=None)

Bases: [`StrEnum`](zenml.utils.md#zenml.utils.enum_utils.StrEnum)

RBAC actions.

#### BACKUP_RESTORE *= 'backup_restore'*

#### CLIENT *= 'client'*

#### CREATE *= 'create'*

#### DELETE *= 'delete'*

#### PROMOTE *= 'promote'*

#### PRUNE *= 'prune'*

#### READ *= 'read'*

#### READ_SECRET_VALUE *= 'read_secret_value'*

#### SHARE *= 'share'*

#### UPDATE *= 'update'*

### *class* zenml.zen_server.rbac.models.Resource(\*, type: str, id: UUID | None = None)

Bases: `BaseModel`

RBAC resource model.

#### id *: UUID | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'frozen': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None), 'type': FieldInfo(annotation=str, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### type *: str*

### *class* zenml.zen_server.rbac.models.ResourceType(value, names=None, \*, module=None, qualname=None, type=None, start=1, boundary=None)

Bases: [`StrEnum`](zenml.utils.md#zenml.utils.enum_utils.StrEnum)

Resource types of the server API.

#### ACTION *= 'action'*

#### ARTIFACT *= 'artifact'*

#### ARTIFACT_VERSION *= 'artifact_version'*

#### CODE_REPOSITORY *= 'code_repository'*

#### EVENT_SOURCE *= 'event_source'*

#### FLAVOR *= 'flavor'*

#### MODEL *= 'model'*

#### MODEL_VERSION *= 'model_version'*

#### PIPELINE *= 'pipeline'*

#### PIPELINE_BUILD *= 'pipeline_build'*

#### PIPELINE_DEPLOYMENT *= 'pipeline_deployment'*

#### PIPELINE_RUN *= 'pipeline_run'*

#### RUN_METADATA *= 'run_metadata'*

#### RUN_TEMPLATE *= 'run_template'*

#### SECRET *= 'secret'*

#### SERVICE *= 'service'*

#### SERVICE_ACCOUNT *= 'service_account'*

#### SERVICE_CONNECTOR *= 'service_connector'*

#### STACK *= 'stack'*

#### STACK_COMPONENT *= 'stack_component'*

#### TAG *= 'tag'*

#### TRIGGER *= 'trigger'*

#### TRIGGER_EXECUTION *= 'trigger_execution'*

#### USER *= 'user'*

#### WORKSPACE *= 'workspace'*

## zenml.zen_server.rbac.rbac_interface module

RBAC interface definition.

### *class* zenml.zen_server.rbac.rbac_interface.RBACInterface

Bases: `ABC`

RBAC interface definition.

#### *abstract* check_permissions(user: [UserResponse](zenml.models.md#zenml.models.UserResponse), resources: Set[[Resource](#zenml.zen_server.rbac.models.Resource)], action: [Action](#zenml.zen_server.rbac.models.Action)) → Dict[[Resource](#zenml.zen_server.rbac.models.Resource), bool]

Checks if a user has permissions to perform an action on resources.

Args:
: user: User which wants to access a resource.
  resources: The resources the user wants to access.
  action: The action that the user wants to perform on the resources.

Returns:
: A dictionary mapping resources to a boolean which indicates whether
  the user has permissions to perform the action on that resource.

#### *abstract* list_allowed_resource_ids(user: [UserResponse](zenml.models.md#zenml.models.UserResponse), resource: [Resource](#zenml.zen_server.rbac.models.Resource), action: [Action](#zenml.zen_server.rbac.models.Action)) → Tuple[bool, List[str]]

Lists all resource IDs of a resource type that a user can access.

Args:
: user: User which wants to access a resource.
  resource: The resource the user wants to access.
  action: The action that the user wants to perform on the resource.

Returns:
: A tuple (full_resource_access, resource_ids).
  full_resource_access will be True if the user can perform the
  given action on any instance of the given resource type, False
  otherwise. If full_resource_access is False, resource_ids
  will contain the list of instance IDs that the user can perform
  the action on.

#### *abstract* update_resource_membership(user: [UserResponse](zenml.models.md#zenml.models.UserResponse), resource: [Resource](#zenml.zen_server.rbac.models.Resource), actions: List[[Action](#zenml.zen_server.rbac.models.Action)]) → None

Update the resource membership of a user.

Args:
: user: User for which the resource membership should be updated.
  resource: The resource.
  actions: The actions that the user should be able to perform on the
  <br/>
  > resource.

## zenml.zen_server.rbac.utils module

## zenml.zen_server.rbac.zenml_cloud_rbac module

Cloud RBAC implementation.

### *class* zenml.zen_server.rbac.zenml_cloud_rbac.ZenMLCloudRBAC

Bases: [`RBACInterface`](#zenml.zen_server.rbac.rbac_interface.RBACInterface)

RBAC implementation that uses the ZenML Pro Management Plane as a backend.

#### check_permissions(user: [UserResponse](zenml.models.md#zenml.models.UserResponse), resources: Set[[Resource](#zenml.zen_server.rbac.models.Resource)], action: [Action](#zenml.zen_server.rbac.models.Action)) → Dict[[Resource](#zenml.zen_server.rbac.models.Resource), bool]

Checks if a user has permissions to perform an action on resources.

Args:
: user: User which wants to access a resource.
  resources: The resources the user wants to access.
  action: The action that the user wants to perform on the resources.

Returns:
: A dictionary mapping resources to a boolean which indicates whether
  the user has permissions to perform the action on that resource.

#### list_allowed_resource_ids(user: [UserResponse](zenml.models.md#zenml.models.UserResponse), resource: [Resource](#zenml.zen_server.rbac.models.Resource), action: [Action](#zenml.zen_server.rbac.models.Action)) → Tuple[bool, List[str]]

Lists all resource IDs of a resource type that a user can access.

Args:
: user: User which wants to access a resource.
  resource: The resource the user wants to access.
  action: The action that the user wants to perform on the resource.

Returns:
: A tuple (full_resource_access, resource_ids).
  full_resource_access will be True if the user can perform the
  given action on any instance of the given resource type, False
  otherwise. If full_resource_access is False, resource_ids
  will contain the list of instance IDs that the user can perform
  the action on.

#### update_resource_membership(user: [UserResponse](zenml.models.md#zenml.models.UserResponse), resource: [Resource](#zenml.zen_server.rbac.models.Resource), actions: List[[Action](#zenml.zen_server.rbac.models.Action)]) → None

Update the resource membership of a user.

Args:
: user: User for which the resource membership should be updated.
  resource: The resource.
  actions: The actions that the user should be able to perform on the
  <br/>
  > resource.

## Module contents

RBAC definitions.
