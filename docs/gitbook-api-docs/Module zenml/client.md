---
description: API documentation for Client
---

# Module zenml.client

Client implementation.

<a id="zenml.client.AnyResponse"></a>

### zenml.client.AnyResponse

type: ignore[type-arg]

<a id="zenml.client.ClientConfiguration"></a>

## ClientConfiguration Objects

```python
class ClientConfiguration(FileSyncModel)
```

Pydantic object used for serializing client configuration options.

<a id="zenml.client.ClientConfiguration.active_workspace"></a>

### ClientConfiguration.active\_workspace

```python
 | @property
 | def active_workspace() -> "WorkspaceResponse"
```

Get the active workspace for the local client.

**Returns**:

  The active workspace.
  

**Raises**:

- `RuntimeError` - If no active workspace is set.

<a id="zenml.client.ClientConfiguration.set_active_workspace"></a>

### ClientConfiguration.set\_active\_workspace

```python
 | def set_active_workspace(workspace: "WorkspaceResponse") -> None
```

Set the workspace for the local client.

**Arguments**:

- `workspace` - The workspace to set active.

<a id="zenml.client.ClientConfiguration.set_active_stack"></a>

### ClientConfiguration.set\_active\_stack

```python
 | def set_active_stack(stack: "StackResponse") -> None
```

Set the stack for the local client.

**Arguments**:

- `stack` - The stack to set active.

<a id="zenml.client.ClientMetaClass"></a>

## ClientMetaClass Objects

```python
class ClientMetaClass(ABCMeta)
```

Client singleton metaclass.

This metaclass is used to enforce a singleton instance of the Client
class with the following additional properties:

* the singleton Client instance is created on first access to reflect
the global configuration and local client configuration.
* the Client shouldn't be accessed from within pipeline steps (a warning
is logged if this is attempted).

<a id="zenml.client.ClientMetaClass.__init__"></a>

### ClientMetaClass.\_\_init\_\_

```python
 | def __init__(cls, *args: Any, **kwargs: Any) -> None
```

Initialize the Client class.

**Arguments**:

- `*args` - Positional arguments.
- `**kwargs` - Keyword arguments.

<a id="zenml.client.ClientMetaClass.__call__"></a>

### ClientMetaClass.\_\_call\_\_

```python
 | def __call__(cls, *args: Any, **kwargs: Any) -> "Client"
```

Create or return the global Client instance.

If the Client constructor is called with custom arguments,
the singleton functionality of the metaclass is bypassed: a new
Client instance is created and returned immediately and without
saving it as the global Client singleton.

**Arguments**:

- `*args` - Positional arguments.
- `**kwargs` - Keyword arguments.
  

**Returns**:

- `Client` - The global Client instance.

<a id="zenml.client.Client"></a>

## Client Objects

```python
@evaluate_all_lazy_load_args_in_client_methods
class Client(metaclass=ClientMetaClass)
```

ZenML client class.

The ZenML client manages configuration options for ZenML stacks as well
as their components.

<a id="zenml.client.Client.__init__"></a>

### Client.\_\_init\_\_

```python
 | def __init__(root: Optional[Path] = None) -> None
```

Initializes the global client instance.

Client is a singleton class: only one instance can exist. Calling
this constructor multiple times will always yield the same instance (see
the exception below).

The `root` argument is only meant for internal use and testing purposes.
User code must never pass them to the constructor.
When a custom `root` value is passed, an anonymous Client instance
is created and returned independently of the Client singleton and
that will have no effect as far as the rest of the ZenML core code is
concerned.

Instead of creating a new Client instance to reflect a different
repository root, to change the active root in the global Client,
call `Client().activate_root(<new-root>)`.

**Arguments**:

- `root` - (internal use) custom root directory for the client. If
  no path is given, the repository root is determined using the
  environment variable `ZENML_REPOSITORY_PATH` (if set) and by
  recursively searching in the parent directories of the
  current working directory. Only used to initialize new
  clients internally.

<a id="zenml.client.Client.get_instance"></a>

### Client.get\_instance

```python
 | @classmethod
 | def get_instance(cls) -> Optional["Client"]
```

Return the Client singleton instance.

**Returns**:

  The Client singleton instance or None, if the Client hasn't
  been initialized yet.

<a id="zenml.client.Client.initialize"></a>

### Client.initialize

```python
 | @staticmethod
 | def initialize(root: Optional[Path] = None) -> None
```

Initializes a new ZenML repository at the given path.

**Arguments**:

- `root` - The root directory where the repository should be created.
  If None, the current working directory is used.
  

**Raises**:

- `InitializationException` - If the root directory already contains a
  ZenML repository.

<a id="zenml.client.Client.uses_local_configuration"></a>

### Client.uses\_local\_configuration

```python
 | @property
 | def uses_local_configuration() -> bool
```

Check if the client is using a local configuration.

**Returns**:

  True if the client is using a local configuration,
  False otherwise.

<a id="zenml.client.Client.is_repository_directory"></a>

### Client.is\_repository\_directory

```python
 | @staticmethod
 | def is_repository_directory(path: Path) -> bool
```

Checks whether a ZenML client exists at the given path.

**Arguments**:

- `path` - The path to check.
  

**Returns**:

  True if a ZenML client exists at the given path,
  False otherwise.

<a id="zenml.client.Client.find_repository"></a>

### Client.find\_repository

```python
 | @staticmethod
 | def find_repository(path: Optional[Path] = None,
 |                     enable_warnings: bool = False) -> Optional[Path]
```

Search for a ZenML repository directory.

**Arguments**:

- `path` - Optional path to look for the repository. If no path is
  given, this function tries to find the repository using the
  environment variable `ZENML_REPOSITORY_PATH` (if set) and
  recursively searching in the parent directories of the current
  working directory.
- `enable_warnings` - If `True`, warnings are printed if the repository
  root cannot be found.
  

**Returns**:

  Absolute path to a ZenML repository directory or None if no
  repository directory was found.

<a id="zenml.client.Client.is_inside_repository"></a>

### Client.is\_inside\_repository

```python
 | @staticmethod
 | def is_inside_repository(file_path: str) -> bool
```

Returns whether a file is inside the active ZenML repository.

**Arguments**:

- `file_path` - A file path.
  

**Returns**:

  True if the file is inside the active ZenML repository, False
  otherwise.

<a id="zenml.client.Client.zen_store"></a>

### Client.zen\_store

```python
 | @property
 | def zen_store() -> "BaseZenStore"
```

Shortcut to return the global zen store.

**Returns**:

  The global zen store.

<a id="zenml.client.Client.root"></a>

### Client.root

```python
 | @property
 | def root() -> Optional[Path]
```

The root directory of this client.

**Returns**:

  The root directory of this client, or None, if the client
  has not been initialized.

<a id="zenml.client.Client.config_directory"></a>

### Client.config\_directory

```python
 | @property
 | def config_directory() -> Optional[Path]
```

The configuration directory of this client.

**Returns**:

  The configuration directory of this client, or None, if the
  client doesn't have an active root.

<a id="zenml.client.Client.activate_root"></a>

### Client.activate\_root

```python
 | def activate_root(root: Optional[Path] = None) -> None
```

Set the active repository root directory.

**Arguments**:

- `root` - The path to set as the active repository root. If not set,
  the repository root is determined using the environment
  variable `ZENML_REPOSITORY_PATH` (if set) and by recursively
  searching in the parent directories of the current working
  directory.

<a id="zenml.client.Client.set_active_workspace"></a>

### Client.set\_active\_workspace

```python
 | def set_active_workspace(
 |         workspace_name_or_id: Union[str, UUID]) -> "WorkspaceResponse"
```

Set the workspace for the local client.

**Arguments**:

- `workspace_name_or_id` - The name or ID of the workspace to set active.
  

**Returns**:

  The model of the active workspace.

<a id="zenml.client.Client.get_settings"></a>

### Client.get\_settings

```python
 | def get_settings(hydrate: bool = True) -> ServerSettingsResponse
```

Get the server settings.

**Arguments**:

- `hydrate` - Flag deciding whether to hydrate the output model(s)
  by including metadata fields in the response.
  

**Returns**:

  The server settings.

<a id="zenml.client.Client.update_server_settings"></a>

### Client.update\_server\_settings

```python
 | def update_server_settings(
 |     updated_name: Optional[str] = None,
 |     updated_logo_url: Optional[str] = None,
 |     updated_enable_analytics: Optional[bool] = None,
 |     updated_enable_announcements: Optional[bool] = None,
 |     updated_enable_updates: Optional[bool] = None,
 |     updated_onboarding_state: Optional[Dict[str, Any]] = None
 | ) -> ServerSettingsResponse
```

Update the server settings.

**Arguments**:

- `updated_name` - Updated name for the server.
- `updated_logo_url` - Updated logo URL for the server.
- `updated_enable_analytics` - Updated value whether to enable
  analytics for the server.
- `updated_enable_announcements` - Updated value whether to display
  announcements about ZenML.
- `updated_enable_updates` - Updated value whether to display updates
  about ZenML.
- `updated_onboarding_state` - Updated onboarding state for the server.
  

**Returns**:

  The updated server settings.

<a id="zenml.client.Client.create_user"></a>

### Client.create\_user

```python
 | def create_user(name: str,
 |                 password: Optional[str] = None,
 |                 is_admin: bool = False) -> UserResponse
```

Create a new user.

**Arguments**:

- `name` - The name of the user.
- `password` - The password of the user. If not provided, the user will
  be created with empty password.
- `is_admin` - Whether the user should be an admin.
  

**Returns**:

  The model of the created user.

<a id="zenml.client.Client.get_user"></a>

### Client.get\_user

```python
 | def get_user(name_id_or_prefix: Union[str, UUID],
 |              allow_name_prefix_match: bool = True,
 |              hydrate: bool = True) -> UserResponse
```

Gets a user.

**Arguments**:

- `name_id_or_prefix` - The name or ID of the user.
- `allow_name_prefix_match` - If True, allow matching by name prefix.
- `hydrate` - Flag deciding whether to hydrate the output model(s)
  by including metadata fields in the response.
  

**Returns**:

  The User

<a id="zenml.client.Client.list_users"></a>

### Client.list\_users

```python
 | def list_users(sort_by: str = "created",
 |                page: int = PAGINATION_STARTING_PAGE,
 |                size: int = PAGE_SIZE_DEFAULT,
 |                logical_operator: LogicalOperators = LogicalOperators.AND,
 |                id: Optional[Union[UUID, str]] = None,
 |                external_user_id: Optional[str] = None,
 |                created: Optional[Union[datetime, str]] = None,
 |                updated: Optional[Union[datetime, str]] = None,
 |                name: Optional[str] = None,
 |                full_name: Optional[str] = None,
 |                email: Optional[str] = None,
 |                active: Optional[bool] = None,
 |                email_opted_in: Optional[bool] = None,
 |                hydrate: bool = False) -> Page[UserResponse]
```

List all users.

**Arguments**:

- `sort_by` - The column to sort by
- `page` - The page of items
- `size` - The maximum size of all pages
- `logical_operator` - Which logical operator to use [and, or]
- `id` - Use the id of stacks to filter by.
- `external_user_id` - Use the external user id for filtering.
- `created` - Use to filter by time of creation
- `updated` - Use the last updated date for filtering
- `name` - Use the username for filtering
- `full_name` - Use the user full name for filtering
- `email` - Use the user email for filtering
- `active` - User the user active status for filtering
- `email_opted_in` - Use the user opt in status for filtering
- `hydrate` - Flag deciding whether to hydrate the output model(s)
  by including metadata fields in the response.
  

**Returns**:

  The User

<a id="zenml.client.Client.update_user"></a>

### Client.update\_user

```python
 | def update_user(name_id_or_prefix: Union[str, UUID],
 |                 updated_name: Optional[str] = None,
 |                 updated_full_name: Optional[str] = None,
 |                 updated_email: Optional[str] = None,
 |                 updated_email_opt_in: Optional[bool] = None,
 |                 updated_password: Optional[str] = None,
 |                 old_password: Optional[str] = None,
 |                 updated_is_admin: Optional[bool] = None,
 |                 updated_metadata: Optional[Dict[str, Any]] = None,
 |                 active: Optional[bool] = None) -> UserResponse
```

Update a user.

**Arguments**:

- `name_id_or_prefix` - The name or ID of the user to update.
- `updated_name` - The new name of the user.
- `updated_full_name` - The new full name of the user.
- `updated_email` - The new email of the user.
- `updated_email_opt_in` - The new email opt-in status of the user.
- `updated_password` - The new password of the user.
- `old_password` - The old password of the user. Required for password
  update.
- `updated_is_admin` - Whether the user should be an admin.
- `updated_metadata` - The new metadata for the user.
- `active` - Use to activate or deactivate the user.
  

**Returns**:

  The updated user.
  

**Raises**:

- `ValidationError` - If the old password is not provided when updating
  the password.

<a id="zenml.client.Client.deactivate_user"></a>

### Client.deactivate\_user

```python
 | @_fail_for_sql_zen_store
 | def deactivate_user(name_id_or_prefix: str) -> "UserResponse"
```

Deactivate a user and generate an activation token.

**Arguments**:

- `name_id_or_prefix` - The name or ID of the user to reset.
  

**Returns**:

  The deactivated user.

<a id="zenml.client.Client.delete_user"></a>

### Client.delete\_user

```python
 | def delete_user(name_id_or_prefix: str) -> None
```

Delete a user.

**Arguments**:

- `name_id_or_prefix` - The name or ID of the user to delete.

<a id="zenml.client.Client.active_user"></a>

### Client.active\_user

```python
 | @property
 | def active_user() -> "UserResponse"
```

Get the user that is currently in use.

**Returns**:

  The active user.

<a id="zenml.client.Client.create_workspace"></a>

### Client.create\_workspace

```python
 | def create_workspace(name: str, description: str) -> WorkspaceResponse
```

Create a new workspace.

**Arguments**:

- `name` - Name of the workspace.
- `description` - Description of the workspace.
  

**Returns**:

  The created workspace.

<a id="zenml.client.Client.get_workspace"></a>

### Client.get\_workspace

```python
 | def get_workspace(name_id_or_prefix: Optional[Union[UUID, str]],
 |                   allow_name_prefix_match: bool = True,
 |                   hydrate: bool = True) -> WorkspaceResponse
```

Gets a workspace.

**Arguments**:

- `name_id_or_prefix` - The name or ID of the workspace.
- `allow_name_prefix_match` - If True, allow matching by name prefix.
- `hydrate` - Flag deciding whether to hydrate the output model(s)
  by including metadata fields in the response.
  

**Returns**:

  The workspace

<a id="zenml.client.Client.list_workspaces"></a>

### Client.list\_workspaces

```python
 | def list_workspaces(sort_by: str = "created",
 |                     page: int = PAGINATION_STARTING_PAGE,
 |                     size: int = PAGE_SIZE_DEFAULT,
 |                     logical_operator: LogicalOperators = LogicalOperators.AND,
 |                     id: Optional[Union[UUID, str]] = None,
 |                     created: Optional[Union[datetime, str]] = None,
 |                     updated: Optional[Union[datetime, str]] = None,
 |                     name: Optional[str] = None,
 |                     hydrate: bool = False) -> Page[WorkspaceResponse]
```

List all workspaces.

**Arguments**:

- `sort_by` - The column to sort by
- `page` - The page of items
- `size` - The maximum size of all pages
- `logical_operator` - Which logical operator to use [and, or]
- `id` - Use the workspace ID to filter by.
- `created` - Use to filter by time of creation
- `updated` - Use the last updated date for filtering
- `name` - Use the workspace name for filtering
- `hydrate` - Flag deciding whether to hydrate the output model(s)
  by including metadata fields in the response.
  

**Returns**:

  Page of workspaces

<a id="zenml.client.Client.update_workspace"></a>

### Client.update\_workspace

```python
 | def update_workspace(
 |         name_id_or_prefix: Optional[Union[UUID, str]],
 |         new_name: Optional[str] = None,
 |         new_description: Optional[str] = None) -> WorkspaceResponse
```

Update a workspace.

**Arguments**:

- `name_id_or_prefix` - Name, ID or prefix of the workspace to update.
- `new_name` - New name of the workspace.
- `new_description` - New description of the workspace.
  

**Returns**:

  The updated workspace.

<a id="zenml.client.Client.delete_workspace"></a>

### Client.delete\_workspace

```python
 | def delete_workspace(name_id_or_prefix: str) -> None
```

Delete a workspace.

**Arguments**:

- `name_id_or_prefix` - The name or ID of the workspace to delete.
  

**Raises**:

- `IllegalOperationError` - If the workspace to delete is the active
  workspace.

<a id="zenml.client.Client.active_workspace"></a>

### Client.active\_workspace

```python
 | @property
 | def active_workspace() -> WorkspaceResponse
```

Get the currently active workspace of the local client.

If no active workspace is configured locally for the client, the
active workspace in the global configuration is used instead.

**Returns**:

  The active workspace.
  

**Raises**:

- `RuntimeError` - If the active workspace is not set.

<a id="zenml.client.Client.create_stack"></a>

### Client.create\_stack

```python
 | def create_stack(name: str,
 |                  components: Mapping[StackComponentType, Union[str, UUID]],
 |                  stack_spec_file: Optional[str] = None,
 |                  labels: Optional[Dict[str, Any]] = None) -> StackResponse
```

Registers a stack and its components.

**Arguments**:

- `name` - The name of the stack to register.
- `components` - dictionary which maps component types to component names
- `stack_spec_file` - path to the stack spec file
- `labels` - The labels of the stack.
  

**Returns**:

  The model of the registered stack.

<a id="zenml.client.Client.get_stack"></a>

### Client.get\_stack

```python
 | def get_stack(name_id_or_prefix: Optional[Union[UUID, str]] = None,
 |               allow_name_prefix_match: bool = True,
 |               hydrate: bool = True) -> StackResponse
```

Get a stack by name, ID or prefix.

If no name, ID or prefix is provided, the active stack is returned.

**Arguments**:

- `name_id_or_prefix` - The name, ID or prefix of the stack.
- `allow_name_prefix_match` - If True, allow matching by name prefix.
- `hydrate` - Flag deciding whether to hydrate the output model(s)
  by including metadata fields in the response.
  

**Returns**:

  The stack.

<a id="zenml.client.Client.list_stacks"></a>

### Client.list\_stacks

```python
 | def list_stacks(sort_by: str = "created",
 |                 page: int = PAGINATION_STARTING_PAGE,
 |                 size: int = PAGE_SIZE_DEFAULT,
 |                 logical_operator: LogicalOperators = LogicalOperators.AND,
 |                 id: Optional[Union[UUID, str]] = None,
 |                 created: Optional[Union[datetime, str]] = None,
 |                 updated: Optional[Union[datetime, str]] = None,
 |                 name: Optional[str] = None,
 |                 description: Optional[str] = None,
 |                 component_id: Optional[Union[str, UUID]] = None,
 |                 user: Optional[Union[UUID, str]] = None,
 |                 component: Optional[Union[UUID, str]] = None,
 |                 hydrate: bool = False) -> Page[StackResponse]
```

Lists all stacks.

**Arguments**:

- `sort_by` - The column to sort by
- `page` - The page of items
- `size` - The maximum size of all pages
- `logical_operator` - Which logical operator to use [and, or]
- `id` - Use the id of stacks to filter by.
- `created` - Use to filter by time of creation
- `updated` - Use the last updated date for filtering
- `description` - Use the stack description for filtering
- `component_id` - The id of the component to filter by.
- `user` - The name/ID of the user to filter by.
- `component` - The name/ID of the component to filter by.
- `name` - The name of the stack to filter by.
- `hydrate` - Flag deciding whether to hydrate the output model(s)
  by including metadata fields in the response.
  

**Returns**:

  A page of stacks.

<a id="zenml.client.Client.update_stack"></a>

### Client.update\_stack

```python
 | def update_stack(
 |     name_id_or_prefix: Optional[Union[UUID, str]] = None,
 |     name: Optional[str] = None,
 |     stack_spec_file: Optional[str] = None,
 |     labels: Optional[Dict[str, Any]] = None,
 |     description: Optional[str] = None,
 |     component_updates: Optional[Dict[StackComponentType,
 |                                      List[Union[UUID, str]]]] = None
 | ) -> StackResponse
```

Updates a stack and its components.

**Arguments**:

- `name_id_or_prefix` - The name, id or prefix of the stack to update.
- `name` - the new name of the stack.
- `stack_spec_file` - path to the stack spec file.
- `labels` - The new labels of the stack component.
- `description` - the new description of the stack.
- `component_updates` - dictionary which maps stack component types to
  lists of new stack component names or ids.
  

**Returns**:

  The model of the updated stack.
  

**Raises**:

- `EntityExistsError` - If the stack name is already taken.

<a id="zenml.client.Client.delete_stack"></a>

### Client.delete\_stack

```python
 | def delete_stack(name_id_or_prefix: Union[str, UUID],
 |                  recursive: bool = False) -> None
```

Deregisters a stack.

**Arguments**:

- `name_id_or_prefix` - The name, id or prefix id of the stack
  to deregister.
- `recursive` - If `True`, all components of the stack which are not
  associated with any other stack will also be deleted.
  

**Raises**:

- `ValueError` - If the stack is the currently active stack for this
  client.

<a id="zenml.client.Client.active_stack"></a>

### Client.active\_stack

```python
 | @property
 | def active_stack() -> "Stack"
```

The active stack for this client.

**Returns**:

  The active stack for this client.

<a id="zenml.client.Client.active_stack_model"></a>

### Client.active\_stack\_model

```python
 | @property
 | def active_stack_model() -> StackResponse
```

The model of the active stack for this client.

If no active stack is configured locally for the client, the active
stack in the global configuration is used instead.

**Returns**:

  The model of the active stack for this client.
  

**Raises**:

- `RuntimeError` - If the active stack is not set.

<a id="zenml.client.Client.activate_stack"></a>

### Client.activate\_stack

```python
 | def activate_stack(stack_name_id_or_prefix: Union[str, UUID]) -> None
```

Sets the stack as active.

**Arguments**:

- `stack_name_id_or_prefix` - Model of the stack to activate.
  

**Raises**:

- `KeyError` - If the stack is not registered.

<a id="zenml.client.Client.create_service"></a>

### Client.create\_service

```python
 | def create_service(config: ServiceConfig,
 |                    service_type: ServiceType,
 |                    model_version_id: Optional[UUID] = None) -> ServiceResponse
```

Registers a service.

**Arguments**:

- `config` - The configuration of the service.
- `service_type` - The type of the service.
- `model_version_id` - The ID of the model version to associate with the
  service.
  

**Returns**:

  The registered service.

<a id="zenml.client.Client.get_service"></a>

### Client.get\_service

```python
 | def get_service(
 |         name_id_or_prefix: Union[str, UUID],
 |         allow_name_prefix_match: bool = True,
 |         hydrate: bool = True,
 |         type: Optional[str] = None,
 |         workspace: Optional[Union[str, UUID]] = None) -> ServiceResponse
```

Gets a service.

**Arguments**:

- `name_id_or_prefix` - The name or ID of the service.
- `allow_name_prefix_match` - If True, allow matching by name prefix.
- `hydrate` - Flag deciding whether to hydrate the output model(s)
  by including metadata fields in the response.
- `type` - The type of the service.
- `workspace` - The workspace name/ID to filter by.
  

**Returns**:

  The Service

<a id="zenml.client.Client.list_services"></a>

### Client.list\_services

```python
 | def list_services(
 |         sort_by: str = "created",
 |         page: int = PAGINATION_STARTING_PAGE,
 |         size: int = PAGE_SIZE_DEFAULT,
 |         logical_operator: LogicalOperators = LogicalOperators.AND,
 |         id: Optional[Union[UUID, str]] = None,
 |         created: Optional[datetime] = None,
 |         updated: Optional[datetime] = None,
 |         type: Optional[str] = None,
 |         flavor: Optional[str] = None,
 |         user: Optional[Union[UUID, str]] = None,
 |         workspace: Optional[Union[str, UUID]] = None,
 |         hydrate: bool = False,
 |         running: Optional[bool] = None,
 |         service_name: Optional[str] = None,
 |         pipeline_name: Optional[str] = None,
 |         pipeline_run_id: Optional[str] = None,
 |         pipeline_step_name: Optional[str] = None,
 |         model_version_id: Optional[Union[str, UUID]] = None,
 |         config: Optional[Dict[str, Any]] = None) -> Page[ServiceResponse]
```

List all services.

**Arguments**:

- `sort_by` - The column to sort by
- `page` - The page of items
- `size` - The maximum size of all pages
- `logical_operator` - Which logical operator to use [and, or]
- `id` - Use the id of services to filter by.
- `created` - Use to filter by time of creation
- `updated` - Use the last updated date for filtering
- `type` - Use the service type for filtering
- `flavor` - Use the service flavor for filtering
- `workspace` - The workspace name/ID to filter by.
- `user` - Filter by user name/ID.
- `hydrate` - Flag deciding whether to hydrate the output model(s)
  by including metadata fields in the response.
- `running` - Use the running status for filtering
- `pipeline_name` - Use the pipeline name for filtering
- `service_name` - Use the service name or model name
  for filtering
- `pipeline_step_name` - Use the pipeline step name for filtering
- `model_version_id` - Use the model version id for filtering
- `config` - Use the config for filtering
- `pipeline_run_id` - Use the pipeline run id for filtering
  

**Returns**:

  The Service response page.

<a id="zenml.client.Client.update_service"></a>

### Client.update\_service

```python
 | def update_service(id: UUID,
 |                    name: Optional[str] = None,
 |                    service_source: Optional[str] = None,
 |                    admin_state: Optional[ServiceState] = None,
 |                    status: Optional[Dict[str, Any]] = None,
 |                    endpoint: Optional[Dict[str, Any]] = None,
 |                    labels: Optional[Dict[str, str]] = None,
 |                    prediction_url: Optional[str] = None,
 |                    health_check_url: Optional[str] = None,
 |                    model_version_id: Optional[UUID] = None) -> ServiceResponse
```

Update a service.

**Arguments**:

- `id` - The ID of the service to update.
- `name` - The new name of the service.
- `admin_state` - The new admin state of the service.
- `status` - The new status of the service.
- `endpoint` - The new endpoint of the service.
- `service_source` - The new service source of the service.
- `labels` - The new labels of the service.
- `prediction_url` - The new prediction url of the service.
- `health_check_url` - The new health check url of the service.
- `model_version_id` - The new model version id of the service.
  

**Returns**:

  The updated service.

<a id="zenml.client.Client.delete_service"></a>

### Client.delete\_service

```python
 | def delete_service(name_id_or_prefix: UUID,
 |                    workspace: Optional[Union[str, UUID]] = None) -> None
```

Delete a service.

**Arguments**:

- `name_id_or_prefix` - The name or ID of the service to delete.
- `workspace` - The workspace name/ID to filter by.

<a id="zenml.client.Client.get_stack_component"></a>

### Client.get\_stack\_component

```python
 | def get_stack_component(component_type: StackComponentType,
 |                         name_id_or_prefix: Optional[Union[str, UUID]] = None,
 |                         allow_name_prefix_match: bool = True,
 |                         hydrate: bool = True) -> ComponentResponse
```

Fetches a registered stack component.

If the name_id_or_prefix is provided, it will try to fetch the component
with the corresponding identifier. If not, it will try to fetch the
active component of the given type.

**Arguments**:

- `component_type` - The type of the component to fetch
- `name_id_or_prefix` - The id of the component to fetch.
- `allow_name_prefix_match` - If True, allow matching by name prefix.
- `hydrate` - Flag deciding whether to hydrate the output model(s)
  by including metadata fields in the response.
  

**Returns**:

  The registered stack component.
  

**Raises**:

- `KeyError` - If no name_id_or_prefix is provided and no such component
  is part of the active stack.

<a id="zenml.client.Client.list_stack_components"></a>

### Client.list\_stack\_components

```python
 | def list_stack_components(
 |         sort_by: str = "created",
 |         page: int = PAGINATION_STARTING_PAGE,
 |         size: int = PAGE_SIZE_DEFAULT,
 |         logical_operator: LogicalOperators = LogicalOperators.AND,
 |         id: Optional[Union[UUID, str]] = None,
 |         created: Optional[datetime] = None,
 |         updated: Optional[datetime] = None,
 |         name: Optional[str] = None,
 |         flavor: Optional[str] = None,
 |         type: Optional[str] = None,
 |         connector_id: Optional[Union[str, UUID]] = None,
 |         stack_id: Optional[Union[str, UUID]] = None,
 |         user: Optional[Union[UUID, str]] = None,
 |         hydrate: bool = False) -> Page[ComponentResponse]
```

Lists all registered stack components.

**Arguments**:

- `sort_by` - The column to sort by
- `page` - The page of items
- `size` - The maximum size of all pages
- `logical_operator` - Which logical operator to use [and, or]
- `id` - Use the id of component to filter by.
- `created` - Use to component by time of creation
- `updated` - Use the last updated date for filtering
- `flavor` - Use the component flavor for filtering
- `type` - Use the component type for filtering
- `connector_id` - The id of the connector to filter by.
- `stack_id` - The id of the stack to filter by.
- `name` - The name of the component to filter by.
- `user` - The ID of name of the user to filter by.
- `hydrate` - Flag deciding whether to hydrate the output model(s)
  by including metadata fields in the response.
  

**Returns**:

  A page of stack components.

<a id="zenml.client.Client.create_stack_component"></a>

### Client.create\_stack\_component

```python
 | def create_stack_component(
 |         name: str,
 |         flavor: str,
 |         component_type: StackComponentType,
 |         configuration: Dict[str, str],
 |         labels: Optional[Dict[str, Any]] = None) -> "ComponentResponse"
```

Registers a stack component.

**Arguments**:

- `name` - The name of the stack component.
- `flavor` - The flavor of the stack component.
- `component_type` - The type of the stack component.
- `configuration` - The configuration of the stack component.
- `labels` - The labels of the stack component.
  

**Returns**:

  The model of the registered component.

<a id="zenml.client.Client.update_stack_component"></a>

### Client.update\_stack\_component

```python
 | def update_stack_component(
 |         name_id_or_prefix: Optional[Union[UUID, str]],
 |         component_type: StackComponentType,
 |         name: Optional[str] = None,
 |         configuration: Optional[Dict[str, Any]] = None,
 |         labels: Optional[Dict[str, Any]] = None,
 |         disconnect: Optional[bool] = None,
 |         connector_id: Optional[UUID] = None,
 |         connector_resource_id: Optional[str] = None) -> ComponentResponse
```

Updates a stack component.

**Arguments**:

- `name_id_or_prefix` - The name, id or prefix of the stack component to
  update.
- `component_type` - The type of the stack component to update.
- `name` - The new name of the stack component.
- `configuration` - The new configuration of the stack component.
- `labels` - The new labels of the stack component.
- `disconnect` - Whether to disconnect the stack component from its
  service connector.
- `connector_id` - The new connector id of the stack component.
- `connector_resource_id` - The new connector resource id of the
  stack component.
  

**Returns**:

  The updated stack component.
  

**Raises**:

- `EntityExistsError` - If the new name is already taken.

<a id="zenml.client.Client.delete_stack_component"></a>

### Client.delete\_stack\_component

```python
 | def delete_stack_component(name_id_or_prefix: Union[str, UUID],
 |                            component_type: StackComponentType) -> None
```

Deletes a registered stack component.

**Arguments**:

- `name_id_or_prefix` - The model of the component to delete.
- `component_type` - The type of the component to delete.

<a id="zenml.client.Client.create_flavor"></a>

### Client.create\_flavor

```python
 | def create_flavor(source: str,
 |                   component_type: StackComponentType) -> FlavorResponse
```

Creates a new flavor.

**Arguments**:

- `source` - The flavor to create.
- `component_type` - The type of the flavor.
  

**Returns**:

  The created flavor (in model form).
  

**Raises**:

- `ValueError` - in case the config_schema of the flavor is too large.

<a id="zenml.client.Client.get_flavor"></a>

### Client.get\_flavor

```python
 | def get_flavor(name_id_or_prefix: str,
 |                allow_name_prefix_match: bool = True,
 |                hydrate: bool = True) -> FlavorResponse
```

Get a stack component flavor.

**Arguments**:

- `name_id_or_prefix` - The name, ID or prefix to the id of the flavor
  to get.
- `allow_name_prefix_match` - If True, allow matching by name prefix.
- `hydrate` - Flag deciding whether to hydrate the output model(s)
  by including metadata fields in the response.
  

**Returns**:

  The stack component flavor.

<a id="zenml.client.Client.list_flavors"></a>

### Client.list\_flavors

```python
 | def list_flavors(sort_by: str = "created",
 |                  page: int = PAGINATION_STARTING_PAGE,
 |                  size: int = PAGE_SIZE_DEFAULT,
 |                  logical_operator: LogicalOperators = LogicalOperators.AND,
 |                  id: Optional[Union[UUID, str]] = None,
 |                  created: Optional[datetime] = None,
 |                  updated: Optional[datetime] = None,
 |                  name: Optional[str] = None,
 |                  type: Optional[str] = None,
 |                  integration: Optional[str] = None,
 |                  user: Optional[Union[UUID, str]] = None,
 |                  hydrate: bool = False) -> Page[FlavorResponse]
```

Fetches all the flavor models.

**Arguments**:

- `sort_by` - The column to sort by
- `page` - The page of items
- `size` - The maximum size of all pages
- `logical_operator` - Which logical operator to use [and, or]
- `id` - Use the id of flavors to filter by.
- `created` - Use to flavors by time of creation
- `updated` - Use the last updated date for filtering
- `user` - Filter by user name/ID.
- `name` - The name of the flavor to filter by.
- `type` - The type of the flavor to filter by.
- `integration` - The integration of the flavor to filter by.
- `hydrate` - Flag deciding whether to hydrate the output model(s)
  by including metadata fields in the response.
  

**Returns**:

  A list of all the flavor models.

<a id="zenml.client.Client.delete_flavor"></a>

### Client.delete\_flavor

```python
 | def delete_flavor(name_id_or_prefix: str) -> None
```

Deletes a flavor.

**Arguments**:

- `name_id_or_prefix` - The name, id or prefix of the id for the
  flavor to delete.

<a id="zenml.client.Client.get_flavors_by_type"></a>

### Client.get\_flavors\_by\_type

```python
 | def get_flavors_by_type(
 |         component_type: "StackComponentType") -> Page[FlavorResponse]
```

Fetches the list of flavor for a stack component type.

**Arguments**:

- `component_type` - The type of the component to fetch.
  

**Returns**:

  The list of flavors.

<a id="zenml.client.Client.get_flavor_by_name_and_type"></a>

### Client.get\_flavor\_by\_name\_and\_type

```python
 | def get_flavor_by_name_and_type(
 |         name: str, component_type: "StackComponentType") -> FlavorResponse
```

Fetches a registered flavor.

**Arguments**:

- `component_type` - The type of the component to fetch.
- `name` - The name of the flavor to fetch.
  

**Returns**:

  The registered flavor.
  

**Raises**:

- `KeyError` - If no flavor exists for the given type and name.

<a id="zenml.client.Client.list_pipelines"></a>

### Client.list\_pipelines

```python
 | def list_pipelines(sort_by: str = "created",
 |                    page: int = PAGINATION_STARTING_PAGE,
 |                    size: int = PAGE_SIZE_DEFAULT,
 |                    logical_operator: LogicalOperators = LogicalOperators.AND,
 |                    id: Optional[Union[UUID, str]] = None,
 |                    created: Optional[Union[datetime, str]] = None,
 |                    updated: Optional[Union[datetime, str]] = None,
 |                    name: Optional[str] = None,
 |                    latest_run_status: Optional[str] = None,
 |                    workspace: Optional[Union[str, UUID]] = None,
 |                    user: Optional[Union[UUID, str]] = None,
 |                    tag: Optional[str] = None,
 |                    tags: Optional[List[str]] = None,
 |                    hydrate: bool = False) -> Page[PipelineResponse]
```

List all pipelines.

**Arguments**:

- `sort_by` - The column to sort by
- `page` - The page of items
- `size` - The maximum size of all pages
- `logical_operator` - Which logical operator to use [and, or]
- `id` - Use the id of pipeline to filter by.
- `created` - Use to filter by time of creation
- `updated` - Use the last updated date for filtering
- `name` - The name of the pipeline to filter by.
- `latest_run_status` - Filter by the status of the latest run of a
  pipeline.
- `workspace` - The workspace name/ID to filter by.
- `user` - The name/ID of the user to filter by.
- `tag` - Tag to filter by.
- `tags` - Tags to filter by.
- `hydrate` - Flag deciding whether to hydrate the output model(s)
  by including metadata fields in the response.
  

**Returns**:

  A page with Pipeline fitting the filter description

<a id="zenml.client.Client.get_pipeline"></a>

### Client.get\_pipeline

```python
 | def get_pipeline(name_id_or_prefix: Union[str, UUID],
 |                  workspace: Optional[Union[str, UUID]] = None,
 |                  hydrate: bool = True) -> PipelineResponse
```

Get a pipeline by name, id or prefix.

**Arguments**:

- `name_id_or_prefix` - The name, ID or ID prefix of the pipeline.
- `workspace` - The workspace name/ID to filter by.
- `hydrate` - Flag deciding whether to hydrate the output model(s)
  by including metadata fields in the response.
  

**Returns**:

  The pipeline.

<a id="zenml.client.Client.delete_pipeline"></a>

### Client.delete\_pipeline

```python
 | def delete_pipeline(name_id_or_prefix: Union[str, UUID],
 |                     workspace: Optional[Union[str, UUID]] = None) -> None
```

Delete a pipeline.

**Arguments**:

- `name_id_or_prefix` - The name, ID or ID prefix of the pipeline.
- `workspace` - The workspace name/ID to filter by.

<a id="zenml.client.Client.trigger_pipeline"></a>

### Client.trigger\_pipeline

```python
 | @_fail_for_sql_zen_store
 | def trigger_pipeline(
 |         pipeline_name_or_id: Union[str, UUID, None] = None,
 |         run_configuration: Union[PipelineRunConfiguration, Dict[str, Any],
 |                                  None] = None,
 |         config_path: Optional[str] = None,
 |         template_id: Optional[UUID] = None,
 |         stack_name_or_id: Union[str, UUID, None] = None,
 |         synchronous: bool = False,
 |         workspace: Optional[Union[str, UUID]] = None) -> PipelineRunResponse
```

Trigger a pipeline from the server.

Usage examples:
* Run the latest runnable template for a pipeline:
* Run the latest runnable template for a pipeline on a specific stack:
* Run a specific template:

```python
Client().trigger_pipeline(pipeline_name_or_id=<NAME>)
```
```python
Client().trigger_pipeline(
    pipeline_name_or_id=<NAME>,
    stack_name_or_id=<STACK_NAME_OR_ID>
)
```
```python
Client().trigger_pipeline(template_id=<ID>)
```

**Arguments**:

- `pipeline_name_or_id` - Name or ID of the pipeline. If this is
  specified, the latest runnable template for this pipeline will
  be used for the run (Runnable here means that the build
  associated with the template is for a remote stack without any
  custom flavor stack components). If not given, a template ID
  that should be run needs to be specified.
- `run_configuration` - Configuration for the run. Either this or a
  path to a config file can be specified.
- `config_path` - Path to a YAML configuration file. This file will be
  parsed as a `PipelineRunConfiguration` object. Either this or
  the configuration in code can be specified.
- `template_id` - ID of the template to run. Either this or a pipeline
  can be specified.
- `stack_name_or_id` - Name or ID of the stack on which to run the
  pipeline. If not specified, this method will try to find a
  runnable template on any stack.
- `synchronous` - If `True`, this method will wait until the triggered
  run is finished.
- `workspace` - The workspace name/ID to filter by.
  

**Raises**:

- `RuntimeError` - If triggering the pipeline failed.
  

**Returns**:

  Model of the pipeline run.

<a id="zenml.client.Client.get_build"></a>

### Client.get\_build

```python
 | def get_build(id_or_prefix: Union[str, UUID],
 |               workspace: Optional[Union[str, UUID]] = None,
 |               hydrate: bool = True) -> PipelineBuildResponse
```

Get a build by id or prefix.

**Arguments**:

- `id_or_prefix` - The id or id prefix of the build.
- `workspace` - The workspace name/ID to filter by.
- `hydrate` - Flag deciding whether to hydrate the output model(s)
  by including metadata fields in the response.
  

**Returns**:

  The build.
  

**Raises**:

- `KeyError` - If no build was found for the given id or prefix.
- `ZenKeyError` - If multiple builds were found that match the given
  id or prefix.

<a id="zenml.client.Client.list_builds"></a>

### Client.list\_builds

```python
 | def list_builds(sort_by: str = "created",
 |                 page: int = PAGINATION_STARTING_PAGE,
 |                 size: int = PAGE_SIZE_DEFAULT,
 |                 logical_operator: LogicalOperators = LogicalOperators.AND,
 |                 id: Optional[Union[UUID, str]] = None,
 |                 created: Optional[Union[datetime, str]] = None,
 |                 updated: Optional[Union[datetime, str]] = None,
 |                 workspace: Optional[Union[str, UUID]] = None,
 |                 user: Optional[Union[UUID, str]] = None,
 |                 pipeline_id: Optional[Union[str, UUID]] = None,
 |                 stack_id: Optional[Union[str, UUID]] = None,
 |                 container_registry_id: Optional[Union[UUID, str]] = None,
 |                 is_local: Optional[bool] = None,
 |                 contains_code: Optional[bool] = None,
 |                 zenml_version: Optional[str] = None,
 |                 python_version: Optional[str] = None,
 |                 checksum: Optional[str] = None,
 |                 stack_checksum: Optional[str] = None,
 |                 duration: Optional[Union[int, str]] = None,
 |                 hydrate: bool = False) -> Page[PipelineBuildResponse]
```

List all builds.

**Arguments**:

- `sort_by` - The column to sort by
- `page` - The page of items
- `size` - The maximum size of all pages
- `logical_operator` - Which logical operator to use [and, or]
- `id` - Use the id of build to filter by.
- `created` - Use to filter by time of creation
- `updated` - Use the last updated date for filtering
- `workspace` - The workspace name/ID to filter by.
- `user` - Filter by user name/ID.
- `pipeline_id` - The id of the pipeline to filter by.
- `stack_id` - The id of the stack to filter by.
- `container_registry_id` - The id of the container registry to
  filter by.
- `is_local` - Use to filter local builds.
- `contains_code` - Use to filter builds that contain code.
- `zenml_version` - The version of ZenML to filter by.
- `python_version` - The Python version to filter by.
- `checksum` - The build checksum to filter by.
- `stack_checksum` - The stack checksum to filter by.
- `duration` - The duration of the build in seconds to filter by.
- `hydrate` - Flag deciding whether to hydrate the output model(s)
  by including metadata fields in the response.
  

**Returns**:

  A page with builds fitting the filter description

<a id="zenml.client.Client.delete_build"></a>

### Client.delete\_build

```python
 | def delete_build(id_or_prefix: str,
 |                  workspace: Optional[Union[str, UUID]] = None) -> None
```

Delete a build.

**Arguments**:

- `id_or_prefix` - The id or id prefix of the build.
- `workspace` - The workspace name/ID to filter by.

<a id="zenml.client.Client.create_event_source"></a>

### Client.create\_event\_source

```python
 | @_fail_for_sql_zen_store
 | def create_event_source(name: str,
 |                         configuration: Dict[str, Any],
 |                         flavor: str,
 |                         event_source_subtype: PluginSubType,
 |                         description: str = "") -> EventSourceResponse
```

Registers an event source.

**Arguments**:

- `name` - The name of the event source to create.
- `configuration` - Configuration for this event source.
- `flavor` - The flavor of event source.
- `event_source_subtype` - The event source subtype.
- `description` - The description of the event source.
  

**Returns**:

  The model of the registered event source.

<a id="zenml.client.Client.get_event_source"></a>

### Client.get\_event\_source

```python
 | @_fail_for_sql_zen_store
 | def get_event_source(name_id_or_prefix: Union[UUID, str],
 |                      allow_name_prefix_match: bool = True,
 |                      workspace: Optional[Union[str, UUID]] = None,
 |                      hydrate: bool = True) -> EventSourceResponse
```

Get an event source by name, ID or prefix.

**Arguments**:

- `name_id_or_prefix` - The name, ID or prefix of the stack.
- `allow_name_prefix_match` - If True, allow matching by name prefix.
- `workspace` - The workspace name/ID to filter by.
- `hydrate` - Flag deciding whether to hydrate the output model(s)
  by including metadata fields in the response.
  

**Returns**:

  The event_source.

<a id="zenml.client.Client.list_event_sources"></a>

### Client.list\_event\_sources

```python
 | def list_event_sources(
 |         sort_by: str = "created",
 |         page: int = PAGINATION_STARTING_PAGE,
 |         size: int = PAGE_SIZE_DEFAULT,
 |         logical_operator: LogicalOperators = LogicalOperators.AND,
 |         id: Optional[Union[UUID, str]] = None,
 |         created: Optional[datetime] = None,
 |         updated: Optional[datetime] = None,
 |         name: Optional[str] = None,
 |         flavor: Optional[str] = None,
 |         event_source_type: Optional[str] = None,
 |         workspace: Optional[Union[str, UUID]] = None,
 |         user: Optional[Union[UUID, str]] = None,
 |         hydrate: bool = False) -> Page[EventSourceResponse]
```

Lists all event_sources.

**Arguments**:

- `sort_by` - The column to sort by
- `page` - The page of items
- `size` - The maximum size of all pages
- `logical_operator` - Which logical operator to use [and, or]
- `id` - Use the id of event_sources to filter by.
- `created` - Use to filter by time of creation
- `updated` - Use the last updated date for filtering
- `workspace` - The workspace name/ID to filter by.
- `user` - Filter by user name/ID.
- `name` - The name of the event_source to filter by.
- `flavor` - The flavor of the event_source to filter by.
- `event_source_type` - The subtype of the event_source to filter by.
- `hydrate` - Flag deciding whether to hydrate the output model(s)
  by including metadata fields in the response.
  

**Returns**:

  A page of event_sources.

<a id="zenml.client.Client.update_event_source"></a>

### Client.update\_event\_source

```python
 | @_fail_for_sql_zen_store
 | def update_event_source(
 |         name_id_or_prefix: Union[UUID, str],
 |         name: Optional[str] = None,
 |         description: Optional[str] = None,
 |         configuration: Optional[Dict[str, Any]] = None,
 |         rotate_secret: Optional[bool] = None,
 |         is_active: Optional[bool] = None,
 |         workspace: Optional[Union[str, UUID]] = None) -> EventSourceResponse
```

Updates an event_source.

**Arguments**:

- `name_id_or_prefix` - The name, id or prefix of the event_source to update.
- `name` - the new name of the event_source.
- `description` - the new description of the event_source.
- `configuration` - The event source configuration.
- `rotate_secret` - Allows rotating of secret, if true, the response will
  contain the new secret value
- `is_active` - Optional[bool] = Allows for activation/deactivating the
  event source
- `workspace` - The workspace name/ID to filter by.
  

**Returns**:

  The model of the updated event_source.
  

**Raises**:

- `EntityExistsError` - If the event_source name is already taken.

<a id="zenml.client.Client.delete_event_source"></a>

### Client.delete\_event\_source

```python
 | @_fail_for_sql_zen_store
 | def delete_event_source(name_id_or_prefix: Union[str, UUID],
 |                         workspace: Optional[Union[str, UUID]] = None) -> None
```

Deletes an event_source.

**Arguments**:

- `name_id_or_prefix` - The name, id or prefix id of the event_source
  to deregister.
- `workspace` - The workspace name/ID to filter by.

<a id="zenml.client.Client.create_action"></a>

### Client.create\_action

```python
 | @_fail_for_sql_zen_store
 | def create_action(name: str,
 |                   flavor: str,
 |                   action_type: PluginSubType,
 |                   configuration: Dict[str, Any],
 |                   service_account_id: UUID,
 |                   auth_window: Optional[int] = None,
 |                   description: str = "") -> ActionResponse
```

Create an action.

**Arguments**:

- `name` - The name of the action.
- `flavor` - The flavor of the action,
- `action_type` - The action subtype.
- `configuration` - The action configuration.
- `service_account_id` - The service account that is used to execute the
  action.
- `auth_window` - The time window in minutes for which the service
  account is authorized to execute the action. Set this to 0 to
  authorize the service account indefinitely (not recommended).
- `description` - The description of the action.
  

**Returns**:

  The created action

<a id="zenml.client.Client.get_action"></a>

### Client.get\_action

```python
 | @_fail_for_sql_zen_store
 | def get_action(name_id_or_prefix: Union[UUID, str],
 |                allow_name_prefix_match: bool = True,
 |                workspace: Optional[Union[str, UUID]] = None,
 |                hydrate: bool = True) -> ActionResponse
```

Get an action by name, ID or prefix.

**Arguments**:

- `name_id_or_prefix` - The name, ID or prefix of the action.
- `allow_name_prefix_match` - If True, allow matching by name prefix.
- `workspace` - The workspace name/ID to filter by.
- `hydrate` - Flag deciding whether to hydrate the output model(s)
  by including metadata fields in the response.
  

**Returns**:

  The action.

<a id="zenml.client.Client.list_actions"></a>

### Client.list\_actions

```python
 | @_fail_for_sql_zen_store
 | def list_actions(sort_by: str = "created",
 |                  page: int = PAGINATION_STARTING_PAGE,
 |                  size: int = PAGE_SIZE_DEFAULT,
 |                  logical_operator: LogicalOperators = LogicalOperators.AND,
 |                  id: Optional[Union[UUID, str]] = None,
 |                  created: Optional[datetime] = None,
 |                  updated: Optional[datetime] = None,
 |                  name: Optional[str] = None,
 |                  flavor: Optional[str] = None,
 |                  action_type: Optional[str] = None,
 |                  workspace: Optional[Union[str, UUID]] = None,
 |                  user: Optional[Union[UUID, str]] = None,
 |                  hydrate: bool = False) -> Page[ActionResponse]
```

List actions.

**Arguments**:

- `sort_by` - The column to sort by
- `page` - The page of items
- `size` - The maximum size of all pages
- `logical_operator` - Which logical operator to use [and, or]
- `id` - Use the id of the action to filter by.
- `created` - Use to filter by time of creation
- `updated` - Use the last updated date for filtering
- `workspace` - The workspace name/ID to filter by.
- `user` - Filter by user name/ID.
- `name` - The name of the action to filter by.
- `flavor` - The flavor of the action to filter by.
- `action_type` - The type of the action to filter by.
- `hydrate` - Flag deciding whether to hydrate the output model(s)
  by including metadata fields in the response.
  

**Returns**:

  A page of actions.

<a id="zenml.client.Client.update_action"></a>

### Client.update\_action

```python
 | @_fail_for_sql_zen_store
 | def update_action(
 |         name_id_or_prefix: Union[UUID, str],
 |         name: Optional[str] = None,
 |         description: Optional[str] = None,
 |         configuration: Optional[Dict[str, Any]] = None,
 |         service_account_id: Optional[UUID] = None,
 |         auth_window: Optional[int] = None,
 |         workspace: Optional[Union[str, UUID]] = None) -> ActionResponse
```

Update an action.

**Arguments**:

- `name_id_or_prefix` - The name, id or prefix of the action to update.
- `name` - The new name of the action.
- `description` - The new description of the action.
- `configuration` - The new configuration of the action.
- `service_account_id` - The new service account that is used to execute
  the action.
- `auth_window` - The new time window in minutes for which the service
  account is authorized to execute the action. Set this to 0 to
  authorize the service account indefinitely (not recommended).
- `workspace` - The workspace name/ID to filter by.
  

**Returns**:

  The updated action.

<a id="zenml.client.Client.delete_action"></a>

### Client.delete\_action

```python
 | @_fail_for_sql_zen_store
 | def delete_action(name_id_or_prefix: Union[str, UUID],
 |                   workspace: Optional[Union[str, UUID]] = None) -> None
```

Delete an action.

**Arguments**:

- `name_id_or_prefix` - The name, id or prefix id of the action
  to delete.
- `workspace` - The workspace name/ID to filter by.

<a id="zenml.client.Client.create_trigger"></a>

### Client.create\_trigger

```python
 | @_fail_for_sql_zen_store
 | def create_trigger(name: str,
 |                    event_source_id: UUID,
 |                    event_filter: Dict[str, Any],
 |                    action_id: UUID,
 |                    description: str = "") -> TriggerResponse
```

Registers a trigger.

**Arguments**:

- `name` - The name of the trigger to create.
- `event_source_id` - The id of the event source id
- `event_filter` - The event filter
- `action_id` - The ID of the action that should be triggered.
- `description` - The description of the trigger
  

**Returns**:

  The created trigger.

<a id="zenml.client.Client.get_trigger"></a>

### Client.get\_trigger

```python
 | @_fail_for_sql_zen_store
 | def get_trigger(name_id_or_prefix: Union[UUID, str],
 |                 allow_name_prefix_match: bool = True,
 |                 workspace: Optional[Union[str, UUID]] = None,
 |                 hydrate: bool = True) -> TriggerResponse
```

Get a trigger by name, ID or prefix.

**Arguments**:

- `name_id_or_prefix` - The name, ID or prefix of the trigger.
- `allow_name_prefix_match` - If True, allow matching by name prefix.
- `workspace` - The workspace name/ID to filter by.
- `hydrate` - Flag deciding whether to hydrate the output model(s)
  by including metadata fields in the response.
  

**Returns**:

  The trigger.

<a id="zenml.client.Client.list_triggers"></a>

### Client.list\_triggers

```python
 | @_fail_for_sql_zen_store
 | def list_triggers(sort_by: str = "created",
 |                   page: int = PAGINATION_STARTING_PAGE,
 |                   size: int = PAGE_SIZE_DEFAULT,
 |                   logical_operator: LogicalOperators = LogicalOperators.AND,
 |                   id: Optional[Union[UUID, str]] = None,
 |                   created: Optional[datetime] = None,
 |                   updated: Optional[datetime] = None,
 |                   name: Optional[str] = None,
 |                   event_source_id: Optional[UUID] = None,
 |                   action_id: Optional[UUID] = None,
 |                   event_source_flavor: Optional[str] = None,
 |                   event_source_subtype: Optional[str] = None,
 |                   action_flavor: Optional[str] = None,
 |                   action_subtype: Optional[str] = None,
 |                   workspace: Optional[Union[str, UUID]] = None,
 |                   user: Optional[Union[UUID, str]] = None,
 |                   hydrate: bool = False) -> Page[TriggerResponse]
```

Lists all triggers.

**Arguments**:

- `sort_by` - The column to sort by
- `page` - The page of items
- `size` - The maximum size of all pages
- `logical_operator` - Which logical operator to use [and, or]
- `id` - Use the id of triggers to filter by.
- `created` - Use to filter by time of creation
- `updated` - Use the last updated date for filtering
- `workspace` - The workspace name/ID to filter by.
- `user` - Filter by user name/ID.
- `name` - The name of the trigger to filter by.
- `event_source_id` - The event source associated with the trigger.
- `action_id` - The action associated with the trigger.
- `event_source_flavor` - Flavor of the event source associated with the
  trigger.
- `event_source_subtype` - Type of the event source associated with the
  trigger.
- `action_flavor` - Flavor of the action associated with the trigger.
- `action_subtype` - Type of the action associated with the trigger.
- `hydrate` - Flag deciding whether to hydrate the output model(s)
  by including metadata fields in the response.
  

**Returns**:

  A page of triggers.

<a id="zenml.client.Client.update_trigger"></a>

### Client.update\_trigger

```python
 | @_fail_for_sql_zen_store
 | def update_trigger(
 |         name_id_or_prefix: Union[UUID, str],
 |         name: Optional[str] = None,
 |         description: Optional[str] = None,
 |         event_filter: Optional[Dict[str, Any]] = None,
 |         is_active: Optional[bool] = None,
 |         workspace: Optional[Union[str, UUID]] = None) -> TriggerResponse
```

Updates a trigger.

**Arguments**:

- `name_id_or_prefix` - The name, id or prefix of the trigger to update.
- `name` - the new name of the trigger.
- `description` - the new description of the trigger.
- `event_filter` - The event filter configuration.
- `is_active` - Whether the trigger is active or not.
- `workspace` - The workspace name/ID to filter by.
  

**Returns**:

  The model of the updated trigger.
  

**Raises**:

- `EntityExistsError` - If the trigger name is already taken.

<a id="zenml.client.Client.delete_trigger"></a>

### Client.delete\_trigger

```python
 | @_fail_for_sql_zen_store
 | def delete_trigger(name_id_or_prefix: Union[str, UUID],
 |                    workspace: Optional[Union[str, UUID]] = None) -> None
```

Deletes an trigger.

**Arguments**:

- `name_id_or_prefix` - The name, id or prefix id of the trigger
  to deregister.
- `workspace` - The workspace name/ID to filter by.

<a id="zenml.client.Client.get_deployment"></a>

### Client.get\_deployment

```python
 | def get_deployment(id_or_prefix: Union[str, UUID],
 |                    workspace: Optional[Union[str, UUID]] = None,
 |                    hydrate: bool = True) -> PipelineDeploymentResponse
```

Get a deployment by id or prefix.

**Arguments**:

- `id_or_prefix` - The id or id prefix of the deployment.
- `workspace` - The workspace name/ID to filter by.
- `hydrate` - Flag deciding whether to hydrate the output model(s)
  by including metadata fields in the response.
  

**Returns**:

  The deployment.
  

**Raises**:

- `KeyError` - If no deployment was found for the given id or prefix.
- `ZenKeyError` - If multiple deployments were found that match the given
  id or prefix.

<a id="zenml.client.Client.list_deployments"></a>

### Client.list\_deployments

```python
 | def list_deployments(
 |         sort_by: str = "created",
 |         page: int = PAGINATION_STARTING_PAGE,
 |         size: int = PAGE_SIZE_DEFAULT,
 |         logical_operator: LogicalOperators = LogicalOperators.AND,
 |         id: Optional[Union[UUID, str]] = None,
 |         created: Optional[Union[datetime, str]] = None,
 |         updated: Optional[Union[datetime, str]] = None,
 |         workspace: Optional[Union[str, UUID]] = None,
 |         user: Optional[Union[UUID, str]] = None,
 |         pipeline_id: Optional[Union[str, UUID]] = None,
 |         stack_id: Optional[Union[str, UUID]] = None,
 |         build_id: Optional[Union[str, UUID]] = None,
 |         template_id: Optional[Union[str, UUID]] = None,
 |         hydrate: bool = False) -> Page[PipelineDeploymentResponse]
```

List all deployments.

**Arguments**:

- `sort_by` - The column to sort by
- `page` - The page of items
- `size` - The maximum size of all pages
- `logical_operator` - Which logical operator to use [and, or]
- `id` - Use the id of build to filter by.
- `created` - Use to filter by time of creation
- `updated` - Use the last updated date for filtering
- `workspace` - The workspace name/ID to filter by.
- `user` - Filter by user name/ID.
- `pipeline_id` - The id of the pipeline to filter by.
- `stack_id` - The id of the stack to filter by.
- `build_id` - The id of the build to filter by.
- `template_id` - The ID of the template to filter by.
- `hydrate` - Flag deciding whether to hydrate the output model(s)
  by including metadata fields in the response.
  

**Returns**:

  A page with deployments fitting the filter description

<a id="zenml.client.Client.delete_deployment"></a>

### Client.delete\_deployment

```python
 | def delete_deployment(id_or_prefix: str,
 |                       workspace: Optional[Union[str, UUID]] = None) -> None
```

Delete a deployment.

**Arguments**:

- `id_or_prefix` - The id or id prefix of the deployment.
- `workspace` - The workspace name/ID to filter by.

<a id="zenml.client.Client.create_run_template"></a>

### Client.create\_run\_template

```python
 | def create_run_template(
 |         name: str,
 |         deployment_id: UUID,
 |         description: Optional[str] = None,
 |         tags: Optional[List[str]] = None) -> RunTemplateResponse
```

Create a run template.

**Arguments**:

- `name` - The name of the run template.
- `deployment_id` - ID of the deployment which this template should be
  based off of.
- `description` - The description of the run template.
- `tags` - Tags associated with the run template.
  

**Returns**:

  The created run template.

<a id="zenml.client.Client.get_run_template"></a>

### Client.get\_run\_template

```python
 | def get_run_template(name_id_or_prefix: Union[str, UUID],
 |                      workspace: Optional[Union[str, UUID]] = None,
 |                      hydrate: bool = True) -> RunTemplateResponse
```

Get a run template.

**Arguments**:

- `name_id_or_prefix` - Name/ID/ID prefix of the template to get.
- `workspace` - The workspace name/ID to filter by.
- `hydrate` - Flag deciding whether to hydrate the output model(s)
  by including metadata fields in the response.
  

**Returns**:

  The run template.

<a id="zenml.client.Client.list_run_templates"></a>

### Client.list\_run\_templates

```python
 | def list_run_templates(
 |         sort_by: str = "created",
 |         page: int = PAGINATION_STARTING_PAGE,
 |         size: int = PAGE_SIZE_DEFAULT,
 |         logical_operator: LogicalOperators = LogicalOperators.AND,
 |         created: Optional[Union[datetime, str]] = None,
 |         updated: Optional[Union[datetime, str]] = None,
 |         id: Optional[Union[UUID, str]] = None,
 |         name: Optional[str] = None,
 |         tag: Optional[str] = None,
 |         workspace: Optional[Union[str, UUID]] = None,
 |         pipeline_id: Optional[Union[str, UUID]] = None,
 |         build_id: Optional[Union[str, UUID]] = None,
 |         stack_id: Optional[Union[str, UUID]] = None,
 |         code_repository_id: Optional[Union[str, UUID]] = None,
 |         user: Optional[Union[UUID, str]] = None,
 |         pipeline: Optional[Union[UUID, str]] = None,
 |         stack: Optional[Union[UUID, str]] = None,
 |         hydrate: bool = False) -> Page[RunTemplateResponse]
```

Get a page of run templates.

**Arguments**:

- `sort_by` - The column to sort by.
- `page` - The page of items.
- `size` - The maximum size of all pages.
- `logical_operator` - Which logical operator to use [and, or].
- `created` - Filter by the creation date.
- `updated` - Filter by the last updated date.
- `id` - Filter by run template ID.
- `name` - Filter by run template name.
- `tag` - Filter by run template tags.
- `workspace` - Filter by workspace name/ID.
- `pipeline_id` - Filter by pipeline ID.
- `build_id` - Filter by build ID.
- `stack_id` - Filter by stack ID.
- `code_repository_id` - Filter by code repository ID.
- `user` - Filter by user name/ID.
- `pipeline` - Filter by pipeline name/ID.
- `stack` - Filter by stack name/ID.
- `hydrate` - Flag deciding whether to hydrate the output model(s)
  by including metadata fields in the response.
  

**Returns**:

  A page of run templates.

<a id="zenml.client.Client.update_run_template"></a>

### Client.update\_run\_template

```python
 | def update_run_template(
 |         name_id_or_prefix: Union[str, UUID],
 |         name: Optional[str] = None,
 |         description: Optional[str] = None,
 |         add_tags: Optional[List[str]] = None,
 |         remove_tags: Optional[List[str]] = None,
 |         workspace: Optional[Union[str, UUID]] = None) -> RunTemplateResponse
```

Update a run template.

**Arguments**:

- `name_id_or_prefix` - Name/ID/ID prefix of the template to update.
- `name` - The new name of the run template.
- `description` - The new description of the run template.
- `add_tags` - Tags to add to the run template.
- `remove_tags` - Tags to remove from the run template.
- `workspace` - The workspace name/ID to filter by.
  

**Returns**:

  The updated run template.

<a id="zenml.client.Client.delete_run_template"></a>

### Client.delete\_run\_template

```python
 | def delete_run_template(name_id_or_prefix: Union[str, UUID],
 |                         workspace: Optional[Union[str, UUID]] = None) -> None
```

Delete a run template.

**Arguments**:

- `name_id_or_prefix` - Name/ID/ID prefix of the template to delete.
- `workspace` - The workspace name/ID to filter by.

<a id="zenml.client.Client.get_schedule"></a>

### Client.get\_schedule

```python
 | def get_schedule(name_id_or_prefix: Union[str, UUID],
 |                  allow_name_prefix_match: bool = True,
 |                  workspace: Optional[Union[str, UUID]] = None,
 |                  hydrate: bool = True) -> ScheduleResponse
```

Get a schedule by name, id or prefix.

**Arguments**:

- `name_id_or_prefix` - The name, id or prefix of the schedule.
- `allow_name_prefix_match` - If True, allow matching by name prefix.
- `workspace` - The workspace name/ID to filter by.
- `hydrate` - Flag deciding whether to hydrate the output model(s)
  by including metadata fields in the response.
  

**Returns**:

  The schedule.

<a id="zenml.client.Client.list_schedules"></a>

### Client.list\_schedules

```python
 | def list_schedules(
 |     sort_by: str = "created",
 |     page: int = PAGINATION_STARTING_PAGE,
 |     size: int = PAGE_SIZE_DEFAULT,
 |     logical_operator: LogicalOperators = LogicalOperators.AND,
 |     id: Optional[Union[UUID, str]] = None,
 |     created: Optional[Union[datetime, str]] = None,
 |     updated: Optional[Union[datetime, str]] = None,
 |     name: Optional[str] = None,
 |     workspace: Optional[Union[str, UUID]] = None,
 |     user: Optional[Union[UUID, str]] = None,
 |     pipeline_id: Optional[Union[str, UUID]] = None,
 |     orchestrator_id: Optional[Union[str, UUID]] = None,
 |     active: Optional[Union[str, bool]] = None,
 |     cron_expression: Optional[str] = None,
 |     start_time: Optional[Union[datetime, str]] = None,
 |     end_time: Optional[Union[datetime, str]] = None,
 |     interval_second: Optional[int] = None,
 |     catchup: Optional[Union[str, bool]] = None,
 |     hydrate: bool = False,
 |     run_once_start_time: Optional[Union[datetime, str]] = None
 | ) -> Page[ScheduleResponse]
```

List schedules.

**Arguments**:

- `sort_by` - The column to sort by
- `page` - The page of items
- `size` - The maximum size of all pages
- `logical_operator` - Which logical operator to use [and, or]
- `id` - Use the id of stacks to filter by.
- `created` - Use to filter by time of creation
- `updated` - Use the last updated date for filtering
- `name` - The name of the stack to filter by.
- `workspace` - The workspace name/ID to filter by.
- `user` - Filter by user name/ID.
- `pipeline_id` - The id of the pipeline to filter by.
- `orchestrator_id` - The id of the orchestrator to filter by.
- `active` - Use to filter by active status.
- `cron_expression` - Use to filter by cron expression.
- `start_time` - Use to filter by start time.
- `end_time` - Use to filter by end time.
- `interval_second` - Use to filter by interval second.
- `catchup` - Use to filter by catchup.
- `hydrate` - Flag deciding whether to hydrate the output model(s)
  by including metadata fields in the response.
- `run_once_start_time` - Use to filter by run once start time.
  

**Returns**:

  A list of schedules.

<a id="zenml.client.Client.delete_schedule"></a>

### Client.delete\_schedule

```python
 | def delete_schedule(name_id_or_prefix: Union[str, UUID],
 |                     workspace: Optional[Union[str, UUID]] = None) -> None
```

Delete a schedule.

**Arguments**:

- `name_id_or_prefix` - The name, id or prefix id of the schedule
  to delete.
- `workspace` - The workspace name/ID to filter by.

<a id="zenml.client.Client.get_pipeline_run"></a>

### Client.get\_pipeline\_run

```python
 | def get_pipeline_run(name_id_or_prefix: Union[str, UUID],
 |                      allow_name_prefix_match: bool = True,
 |                      workspace: Optional[Union[str, UUID]] = None,
 |                      hydrate: bool = True) -> PipelineRunResponse
```

Gets a pipeline run by name, ID, or prefix.

**Arguments**:

- `name_id_or_prefix` - Name, ID, or prefix of the pipeline run.
- `allow_name_prefix_match` - If True, allow matching by name prefix.
- `workspace` - The workspace name/ID to filter by.
- `hydrate` - Flag deciding whether to hydrate the output model(s)
  by including metadata fields in the response.
  

**Returns**:

  The pipeline run.

<a id="zenml.client.Client.list_pipeline_runs"></a>

### Client.list\_pipeline\_runs

```python
 | def list_pipeline_runs(
 |         sort_by: str = "desc:created",
 |         page: int = PAGINATION_STARTING_PAGE,
 |         size: int = PAGE_SIZE_DEFAULT,
 |         logical_operator: LogicalOperators = LogicalOperators.AND,
 |         id: Optional[Union[UUID, str]] = None,
 |         created: Optional[Union[datetime, str]] = None,
 |         updated: Optional[Union[datetime, str]] = None,
 |         name: Optional[str] = None,
 |         workspace: Optional[Union[str, UUID]] = None,
 |         pipeline_id: Optional[Union[str, UUID]] = None,
 |         pipeline_name: Optional[str] = None,
 |         stack_id: Optional[Union[str, UUID]] = None,
 |         schedule_id: Optional[Union[str, UUID]] = None,
 |         build_id: Optional[Union[str, UUID]] = None,
 |         deployment_id: Optional[Union[str, UUID]] = None,
 |         code_repository_id: Optional[Union[str, UUID]] = None,
 |         template_id: Optional[Union[str, UUID]] = None,
 |         model_version_id: Optional[Union[str, UUID]] = None,
 |         orchestrator_run_id: Optional[str] = None,
 |         status: Optional[str] = None,
 |         start_time: Optional[Union[datetime, str]] = None,
 |         end_time: Optional[Union[datetime, str]] = None,
 |         unlisted: Optional[bool] = None,
 |         templatable: Optional[bool] = None,
 |         tag: Optional[str] = None,
 |         tags: Optional[List[str]] = None,
 |         user: Optional[Union[UUID, str]] = None,
 |         run_metadata: Optional[Dict[str, Any]] = None,
 |         pipeline: Optional[Union[UUID, str]] = None,
 |         code_repository: Optional[Union[UUID, str]] = None,
 |         model: Optional[Union[UUID, str]] = None,
 |         stack: Optional[Union[UUID, str]] = None,
 |         stack_component: Optional[Union[UUID, str]] = None,
 |         hydrate: bool = False) -> Page[PipelineRunResponse]
```

List all pipeline runs.

**Arguments**:

- `sort_by` - The column to sort by
- `page` - The page of items
- `size` - The maximum size of all pages
- `logical_operator` - Which logical operator to use [and, or]
- `id` - The id of the runs to filter by.
- `created` - Use to filter by time of creation
- `updated` - Use the last updated date for filtering
- `workspace` - The workspace name/ID to filter by.
- `pipeline_id` - The id of the pipeline to filter by.
- `pipeline_name` - DEPRECATED. Use `pipeline` instead to filter by
  pipeline name.
- `stack_id` - The id of the stack to filter by.
- `schedule_id` - The id of the schedule to filter by.
- `build_id` - The id of the build to filter by.
- `deployment_id` - The id of the deployment to filter by.
- `code_repository_id` - The id of the code repository to filter by.
- `template_id` - The ID of the template to filter by.
- `model_version_id` - The ID of the model version to filter by.
- `orchestrator_run_id` - The run id of the orchestrator to filter by.
- `name` - The name of the run to filter by.
- `status` - The status of the pipeline run
- `start_time` - The start_time for the pipeline run
- `end_time` - The end_time for the pipeline run
- `unlisted` - If the runs should be unlisted or not.
- `templatable` - If the runs should be templatable or not.
- `tag` - Tag to filter by.
- `tags` - Tags to filter by.
- `user` - The name/ID of the user to filter by.
- `run_metadata` - The run_metadata of the run to filter by.
- `pipeline` - The name/ID of the pipeline to filter by.
- `code_repository` - Filter by code repository name/ID.
- `model` - Filter by model name/ID.
- `stack` - Filter by stack name/ID.
- `stack_component` - Filter by stack component name/ID.
- `hydrate` - Flag deciding whether to hydrate the output model(s)
  by including metadata fields in the response.
  

**Returns**:

  A page with Pipeline Runs fitting the filter description

<a id="zenml.client.Client.delete_pipeline_run"></a>

### Client.delete\_pipeline\_run

```python
 | def delete_pipeline_run(name_id_or_prefix: Union[str, UUID],
 |                         workspace: Optional[Union[str, UUID]] = None) -> None
```

Deletes a pipeline run.

**Arguments**:

- `name_id_or_prefix` - Name, ID, or prefix of the pipeline run.
- `workspace` - The workspace name/ID to filter by.

<a id="zenml.client.Client.get_run_step"></a>

### Client.get\_run\_step

```python
 | def get_run_step(step_run_id: UUID, hydrate: bool = True) -> StepRunResponse
```

Get a step run by ID.

**Arguments**:

- `step_run_id` - The ID of the step run to get.
- `hydrate` - Flag deciding whether to hydrate the output model(s)
  by including metadata fields in the response.
  

**Returns**:

  The step run.

<a id="zenml.client.Client.list_run_steps"></a>

### Client.list\_run\_steps

```python
 | def list_run_steps(sort_by: str = "created",
 |                    page: int = PAGINATION_STARTING_PAGE,
 |                    size: int = PAGE_SIZE_DEFAULT,
 |                    logical_operator: LogicalOperators = LogicalOperators.AND,
 |                    id: Optional[Union[UUID, str]] = None,
 |                    created: Optional[Union[datetime, str]] = None,
 |                    updated: Optional[Union[datetime, str]] = None,
 |                    name: Optional[str] = None,
 |                    cache_key: Optional[str] = None,
 |                    code_hash: Optional[str] = None,
 |                    status: Optional[str] = None,
 |                    start_time: Optional[Union[datetime, str]] = None,
 |                    end_time: Optional[Union[datetime, str]] = None,
 |                    pipeline_run_id: Optional[Union[str, UUID]] = None,
 |                    deployment_id: Optional[Union[str, UUID]] = None,
 |                    original_step_run_id: Optional[Union[str, UUID]] = None,
 |                    workspace: Optional[Union[str, UUID]] = None,
 |                    user: Optional[Union[UUID, str]] = None,
 |                    model_version_id: Optional[Union[str, UUID]] = None,
 |                    model: Optional[Union[UUID, str]] = None,
 |                    run_metadata: Optional[Dict[str, Any]] = None,
 |                    hydrate: bool = False) -> Page[StepRunResponse]
```

List all pipelines.

**Arguments**:

- `sort_by` - The column to sort by
- `page` - The page of items
- `size` - The maximum size of all pages
- `logical_operator` - Which logical operator to use [and, or]
- `id` - Use the id of runs to filter by.
- `created` - Use to filter by time of creation
- `updated` - Use the last updated date for filtering
- `start_time` - Use to filter by the time when the step started running
- `end_time` - Use to filter by the time when the step finished running
- `workspace` - The workspace name/ID to filter by.
- `user` - Filter by user name/ID.
- `pipeline_run_id` - The id of the pipeline run to filter by.
- `deployment_id` - The id of the deployment to filter by.
- `original_step_run_id` - The id of the original step run to filter by.
- `model_version_id` - The ID of the model version to filter by.
- `model` - Filter by model name/ID.
- `name` - The name of the step run to filter by.
- `cache_key` - The cache key of the step run to filter by.
- `code_hash` - The code hash of the step run to filter by.
- `status` - The name of the run to filter by.
- `run_metadata` - Filter by run metadata.
- `hydrate` - Flag deciding whether to hydrate the output model(s)
  by including metadata fields in the response.
  

**Returns**:

  A page with Pipeline fitting the filter description

<a id="zenml.client.Client.get_artifact"></a>

### Client.get\_artifact

```python
 | def get_artifact(name_id_or_prefix: Union[str, UUID],
 |                  workspace: Optional[Union[str, UUID]] = None,
 |                  hydrate: bool = False) -> ArtifactResponse
```

Get an artifact by name, id or prefix.

**Arguments**:

- `name_id_or_prefix` - The name, ID or prefix of the artifact to get.
- `workspace` - The workspace name/ID to filter by.
- `hydrate` - Flag deciding whether to hydrate the output model(s)
  by including metadata fields in the response.
  

**Returns**:

  The artifact.

<a id="zenml.client.Client.list_artifacts"></a>

### Client.list\_artifacts

```python
 | def list_artifacts(sort_by: str = "created",
 |                    page: int = PAGINATION_STARTING_PAGE,
 |                    size: int = PAGE_SIZE_DEFAULT,
 |                    logical_operator: LogicalOperators = LogicalOperators.AND,
 |                    id: Optional[Union[UUID, str]] = None,
 |                    created: Optional[Union[datetime, str]] = None,
 |                    updated: Optional[Union[datetime, str]] = None,
 |                    name: Optional[str] = None,
 |                    has_custom_name: Optional[bool] = None,
 |                    user: Optional[Union[UUID, str]] = None,
 |                    workspace: Optional[Union[str, UUID]] = None,
 |                    hydrate: bool = False,
 |                    tag: Optional[str] = None,
 |                    tags: Optional[List[str]] = None) -> Page[ArtifactResponse]
```

Get a list of artifacts.

**Arguments**:

- `sort_by` - The column to sort by
- `page` - The page of items
- `size` - The maximum size of all pages
- `logical_operator` - Which logical operator to use [and, or]
- `id` - Use the id of artifact to filter by.
- `created` - Use to filter by time of creation
- `updated` - Use the last updated date for filtering
- `name` - The name of the artifact to filter by.
- `has_custom_name` - Filter artifacts with/without custom names.
- `user` - Filter by user name or ID.
- `workspace` - The workspace name/ID to filter by.
- `hydrate` - Flag deciding whether to hydrate the output model(s)
  by including metadata fields in the response.
- `tag` - Filter artifacts by tag.
- `tags` - Tags to filter by.
  

**Returns**:

  A list of artifacts.

<a id="zenml.client.Client.update_artifact"></a>

### Client.update\_artifact

```python
 | def update_artifact(
 |         name_id_or_prefix: Union[str, UUID],
 |         new_name: Optional[str] = None,
 |         add_tags: Optional[List[str]] = None,
 |         remove_tags: Optional[List[str]] = None,
 |         has_custom_name: Optional[bool] = None,
 |         workspace: Optional[Union[str, UUID]] = None) -> ArtifactResponse
```

Update an artifact.

**Arguments**:

- `name_id_or_prefix` - The name, ID or prefix of the artifact to update.
- `new_name` - The new name of the artifact.
- `add_tags` - Tags to add to the artifact.
- `remove_tags` - Tags to remove from the artifact.
- `has_custom_name` - Whether the artifact has a custom name.
- `workspace` - The workspace name/ID to filter by.
  

**Returns**:

  The updated artifact.

<a id="zenml.client.Client.delete_artifact"></a>

### Client.delete\_artifact

```python
 | def delete_artifact(name_id_or_prefix: Union[str, UUID],
 |                     workspace: Optional[Union[str, UUID]] = None) -> None
```

Delete an artifact.

**Arguments**:

- `name_id_or_prefix` - The name, ID or prefix of the artifact to delete.
- `workspace` - The workspace name/ID to filter by.

<a id="zenml.client.Client.prune_artifacts"></a>

### Client.prune\_artifacts

```python
 | def prune_artifacts(only_versions: bool = True,
 |                     delete_from_artifact_store: bool = False,
 |                     workspace: Optional[Union[str, UUID]] = None) -> None
```

Delete all unused artifacts and artifact versions.

**Arguments**:

- `only_versions` - Only delete artifact versions, keeping artifacts
- `delete_from_artifact_store` - Delete data from artifact metadata
- `workspace` - The workspace name/ID to filter by.

<a id="zenml.client.Client.get_artifact_version"></a>

### Client.get\_artifact\_version

```python
 | def get_artifact_version(name_id_or_prefix: Union[str, UUID],
 |                          version: Optional[str] = None,
 |                          workspace: Optional[Union[str, UUID]] = None,
 |                          hydrate: bool = True) -> ArtifactVersionResponse
```

Get an artifact version by ID or artifact name.

**Arguments**:

- `name_id_or_prefix` - Either the ID of the artifact version or the
  name of the artifact.
- `version` - The version of the artifact to get. Only used if
  `name_id_or_prefix` is the name of the artifact. If not
  specified, the latest version is returned.
- `workspace` - The workspace name/ID to filter by.
- `hydrate` - Flag deciding whether to hydrate the output model(s)
  by including metadata fields in the response.
  

**Returns**:

  The artifact version.

<a id="zenml.client.Client.list_artifact_versions"></a>

### Client.list\_artifact\_versions

```python
 | def list_artifact_versions(
 |         sort_by: str = "created",
 |         page: int = PAGINATION_STARTING_PAGE,
 |         size: int = PAGE_SIZE_DEFAULT,
 |         logical_operator: LogicalOperators = LogicalOperators.AND,
 |         id: Optional[Union[UUID, str]] = None,
 |         created: Optional[Union[datetime, str]] = None,
 |         updated: Optional[Union[datetime, str]] = None,
 |         artifact: Optional[Union[str, UUID]] = None,
 |         name: Optional[str] = None,
 |         version: Optional[Union[str, int]] = None,
 |         version_number: Optional[int] = None,
 |         artifact_store_id: Optional[Union[str, UUID]] = None,
 |         type: Optional[ArtifactType] = None,
 |         data_type: Optional[str] = None,
 |         uri: Optional[str] = None,
 |         materializer: Optional[str] = None,
 |         workspace: Optional[Union[str, UUID]] = None,
 |         model_version_id: Optional[Union[str, UUID]] = None,
 |         only_unused: Optional[bool] = False,
 |         has_custom_name: Optional[bool] = None,
 |         user: Optional[Union[UUID, str]] = None,
 |         model: Optional[Union[UUID, str]] = None,
 |         pipeline_run: Optional[Union[UUID, str]] = None,
 |         run_metadata: Optional[Dict[str, Any]] = None,
 |         tag: Optional[str] = None,
 |         tags: Optional[List[str]] = None,
 |         hydrate: bool = False) -> Page[ArtifactVersionResponse]
```

Get a list of artifact versions.

**Arguments**:

- `sort_by` - The column to sort by
- `page` - The page of items
- `size` - The maximum size of all pages
- `logical_operator` - Which logical operator to use [and, or]
- `id` - Use the id of artifact version to filter by.
- `created` - Use to filter by time of creation
- `updated` - Use the last updated date for filtering
- `artifact` - The name or ID of the artifact to filter by.
- `name` - The name of the artifact to filter by.
- `version` - The version of the artifact to filter by.
- `version_number` - The version number of the artifact to filter by.
- `artifact_store_id` - The id of the artifact store to filter by.
- `type` - The type of the artifact to filter by.
- `data_type` - The data type of the artifact to filter by.
- `uri` - The uri of the artifact to filter by.
- `materializer` - The materializer of the artifact to filter by.
- `workspace` - The workspace name/ID to filter by.
- `model_version_id` - Filter by model version ID.
- `only_unused` - Only return artifact versions that are not used in
  any pipeline runs.
- `has_custom_name` - Filter artifacts with/without custom names.
- `tag` - A tag to filter by.
- `tags` - Tags to filter by.
- `user` - Filter by user name or ID.
- `model` - Filter by model name or ID.
- `pipeline_run` - Filter by pipeline run name or ID.
- `run_metadata` - Filter by run metadata.
- `hydrate` - Flag deciding whether to hydrate the output model(s)
  by including metadata fields in the response.
  

**Returns**:

  A list of artifact versions.

<a id="zenml.client.Client.update_artifact_version"></a>

### Client.update\_artifact\_version

```python
 | def update_artifact_version(
 |         name_id_or_prefix: Union[str, UUID],
 |         version: Optional[str] = None,
 |         add_tags: Optional[List[str]] = None,
 |         remove_tags: Optional[List[str]] = None,
 |         workspace: Optional[Union[str,
 |                                   UUID]] = None) -> ArtifactVersionResponse
```

Update an artifact version.

**Arguments**:

- `name_id_or_prefix` - The name, ID or prefix of the artifact to update.
- `version` - The version of the artifact to update. Only used if
  `name_id_or_prefix` is the name of the artifact. If not
  specified, the latest version is updated.
- `add_tags` - Tags to add to the artifact version.
- `remove_tags` - Tags to remove from the artifact version.
- `workspace` - The workspace name/ID to filter by.
  

**Returns**:

  The updated artifact version.

<a id="zenml.client.Client.delete_artifact_version"></a>

### Client.delete\_artifact\_version

```python
 | def delete_artifact_version(
 |         name_id_or_prefix: Union[str, UUID],
 |         version: Optional[str] = None,
 |         delete_metadata: bool = True,
 |         delete_from_artifact_store: bool = False,
 |         workspace: Optional[Union[str, UUID]] = None) -> None
```

Delete an artifact version.

By default, this will delete only the metadata of the artifact from the
database, not the actual object stored in the artifact store.

**Arguments**:

- `name_id_or_prefix` - The ID of artifact version or name or prefix of the artifact to
  delete.
- `version` - The version of the artifact to delete.
- `delete_metadata` - If True, delete the metadata of the artifact
  version from the database.
- `delete_from_artifact_store` - If True, delete the artifact object
  itself from the artifact store.
- `workspace` - The workspace name/ID to filter by.

<a id="zenml.client.Client.create_run_metadata"></a>

### Client.create\_run\_metadata

```python
 | def create_run_metadata(metadata: Dict[str, "MetadataType"],
 |                         resources: List[RunMetadataResource],
 |                         stack_component_id: Optional[UUID] = None,
 |                         publisher_step_id: Optional[UUID] = None) -> None
```

Create run metadata.

**Arguments**:

- `metadata` - The metadata to create as a dictionary of key-value pairs.
- `resources` - The list of IDs and types of the resources for that the
  metadata was produced.
- `stack_component_id` - The ID of the stack component that produced
  the metadata.
- `publisher_step_id` - The ID of the step execution that publishes
  this metadata automatically.

<a id="zenml.client.Client.create_secret"></a>

### Client.create\_secret

```python
 | def create_secret(name: str,
 |                   values: Dict[str, str],
 |                   private: bool = False) -> SecretResponse
```

Creates a new secret.

**Arguments**:

- `name` - The name of the secret.
- `values` - The values of the secret.
- `private` - Whether the secret is private. A private secret is only
  accessible to the user who created it.
  

**Returns**:

  The created secret (in model form).
  

**Raises**:

- `NotImplementedError` - If centralized secrets management is not
  enabled.

<a id="zenml.client.Client.get_secret"></a>

### Client.get\_secret

```python
 | def get_secret(name_id_or_prefix: Union[str, UUID],
 |                private: Optional[bool] = None,
 |                allow_partial_name_match: bool = True,
 |                allow_partial_id_match: bool = True,
 |                hydrate: bool = True) -> SecretResponse
```

Get a secret.

Get a secret identified by a name, ID or prefix of the name or ID and
optionally a scope.

If a private status is not provided, privately scoped secrets will be
searched for first, followed by publicly scoped secrets. When a name or
prefix is used instead of a UUID value, each scope is first searched for
an exact match, then for a ID prefix or name substring match before
moving on to the next scope.

**Arguments**:

- `name_id_or_prefix` - The name, ID or prefix to the id of the secret
  to get.
- `private` - Whether the secret is private. If not set, all secrets will
  be searched for, prioritizing privately scoped secrets.
- `allow_partial_name_match` - If True, allow partial name matches.
- `allow_partial_id_match` - If True, allow partial ID matches.
- `hydrate` - Flag deciding whether to hydrate the output model(s)
  by including metadata fields in the response.
  

**Returns**:

  The secret.
  

**Raises**:

- `KeyError` - If no secret is found.
- `ZenKeyError` - If multiple secrets are found.
- `NotImplementedError` - If centralized secrets management is not
  enabled.

<a id="zenml.client.Client.list_secrets"></a>

### Client.list\_secrets

```python
 | def list_secrets(sort_by: str = "created",
 |                  page: int = PAGINATION_STARTING_PAGE,
 |                  size: int = PAGE_SIZE_DEFAULT,
 |                  logical_operator: LogicalOperators = LogicalOperators.AND,
 |                  id: Optional[Union[UUID, str]] = None,
 |                  created: Optional[datetime] = None,
 |                  updated: Optional[datetime] = None,
 |                  name: Optional[str] = None,
 |                  private: Optional[bool] = None,
 |                  user: Optional[Union[UUID, str]] = None,
 |                  hydrate: bool = False) -> Page[SecretResponse]
```

Fetches all the secret models.

The returned secrets do not contain the secret values. To get the
secret values, use `get_secret` individually for each secret.

**Arguments**:

- `sort_by` - The column to sort by
- `page` - The page of items
- `size` - The maximum size of all pages
- `logical_operator` - Which logical operator to use [and, or]
- `id` - Use the id of secrets to filter by.
- `created` - Use to secrets by time of creation
- `updated` - Use the last updated date for filtering
- `name` - The name of the secret to filter by.
- `private` - The private status of the secret to filter by.
- `user` - Filter by user name/ID.
- `hydrate` - Flag deciding whether to hydrate the output model(s)
  by including metadata fields in the response.
  

**Returns**:

  A list of all the secret models without the secret values.
  

**Raises**:

- `NotImplementedError` - If centralized secrets management is not
  enabled.

<a id="zenml.client.Client.update_secret"></a>

### Client.update\_secret

```python
 | def update_secret(name_id_or_prefix: Union[str, UUID],
 |                   private: Optional[bool] = None,
 |                   new_name: Optional[str] = None,
 |                   update_private: Optional[bool] = None,
 |                   add_or_update_values: Optional[Dict[str, str]] = None,
 |                   remove_values: Optional[List[str]] = None) -> SecretResponse
```

Updates a secret.

**Arguments**:

- `name_id_or_prefix` - The name, id or prefix of the id for the
  secret to update.
- `private` - The private status of the secret to update.
- `new_name` - The new name of the secret.
- `update_private` - New value used to update the private status of the
  secret.
- `add_or_update_values` - The values to add or update.
- `remove_values` - The values to remove.
  

**Returns**:

  The updated secret.
  

**Raises**:

- `KeyError` - If trying to remove a value that doesn't exist.
- `ValueError` - If a key is provided in both add_or_update_values and
  remove_values.

<a id="zenml.client.Client.delete_secret"></a>

### Client.delete\_secret

```python
 | def delete_secret(name_id_or_prefix: str,
 |                   private: Optional[bool] = None) -> None
```

Deletes a secret.

**Arguments**:

- `name_id_or_prefix` - The name or ID of the secret.
- `private` - The private status of the secret to delete.

<a id="zenml.client.Client.get_secret_by_name_and_private_status"></a>

### Client.get\_secret\_by\_name\_and\_private\_status

```python
 | def get_secret_by_name_and_private_status(
 |         name: str,
 |         private: Optional[bool] = None,
 |         hydrate: bool = True) -> SecretResponse
```

Fetches a registered secret with a given name and optional private status.

This is a version of get_secret that restricts the search to a given
name and an optional private status, without doing any prefix or UUID
matching.

If no private status is provided, the search will be done first for
private secrets, then for public secrets.

**Arguments**:

- `name` - The name of the secret to get.
- `private` - The private status of the secret to get.
- `hydrate` - Flag deciding whether to hydrate the output model(s)
  by including metadata fields in the response.
  

**Returns**:

  The registered secret.
  

**Raises**:

- `KeyError` - If no secret exists for the given name in the given scope.

<a id="zenml.client.Client.list_secrets_by_private_status"></a>

### Client.list\_secrets\_by\_private\_status

```python
 | def list_secrets_by_private_status(private: bool,
 |                                    hydrate: bool = False
 |                                    ) -> Page[SecretResponse]
```

Fetches the list of secrets with a given private status.

The returned secrets do not contain the secret values. To get the
secret values, use `get_secret` individually for each secret.

**Arguments**:

- `private` - The private status of the secrets to search for.
- `hydrate` - Flag deciding whether to hydrate the output model(s)
  by including metadata fields in the response.
  

**Returns**:

  The list of secrets in the given scope without the secret values.

<a id="zenml.client.Client.backup_secrets"></a>

### Client.backup\_secrets

```python
 | def backup_secrets(ignore_errors: bool = True,
 |                    delete_secrets: bool = False) -> None
```

Backs up all secrets to the configured backup secrets store.

**Arguments**:

- `ignore_errors` - Whether to ignore individual errors during the backup
  process and attempt to backup all secrets.
- `delete_secrets` - Whether to delete the secrets that have been
  successfully backed up from the primary secrets store. Setting
  this flag effectively moves all secrets from the primary secrets
  store to the backup secrets store.

<a id="zenml.client.Client.restore_secrets"></a>

### Client.restore\_secrets

```python
 | def restore_secrets(ignore_errors: bool = False,
 |                     delete_secrets: bool = False) -> None
```

Restore all secrets from the configured backup secrets store.

**Arguments**:

- `ignore_errors` - Whether to ignore individual errors during the
  restore process and attempt to restore all secrets.
- `delete_secrets` - Whether to delete the secrets that have been
  successfully restored from the backup secrets store. Setting
  this flag effectively moves all secrets from the backup secrets
  store to the primary secrets store.

<a id="zenml.client.Client.create_code_repository"></a>

### Client.create\_code\_repository

```python
 | def create_code_repository(
 |         name: str,
 |         config: Dict[str, Any],
 |         source: Source,
 |         description: Optional[str] = None,
 |         logo_url: Optional[str] = None) -> CodeRepositoryResponse
```

Create a new code repository.

**Arguments**:

- `name` - Name of the code repository.
- `config` - The configuration for the code repository.
- `source` - The code repository implementation source.
- `description` - The code repository description.
- `logo_url` - URL of a logo (png, jpg or svg) for the code repository.
  

**Returns**:

  The created code repository.

<a id="zenml.client.Client.get_code_repository"></a>

### Client.get\_code\_repository

```python
 | def get_code_repository(name_id_or_prefix: Union[str, UUID],
 |                         allow_name_prefix_match: bool = True,
 |                         workspace: Optional[Union[str, UUID]] = None,
 |                         hydrate: bool = True) -> CodeRepositoryResponse
```

Get a code repository by name, id or prefix.

**Arguments**:

- `name_id_or_prefix` - The name, ID or ID prefix of the code repository.
- `allow_name_prefix_match` - If True, allow matching by name prefix.
- `workspace` - The workspace name/ID to filter by.
- `hydrate` - Flag deciding whether to hydrate the output model(s)
  by including metadata fields in the response.
  

**Returns**:

  The code repository.

<a id="zenml.client.Client.list_code_repositories"></a>

### Client.list\_code\_repositories

```python
 | def list_code_repositories(
 |         sort_by: str = "created",
 |         page: int = PAGINATION_STARTING_PAGE,
 |         size: int = PAGE_SIZE_DEFAULT,
 |         logical_operator: LogicalOperators = LogicalOperators.AND,
 |         id: Optional[Union[UUID, str]] = None,
 |         created: Optional[Union[datetime, str]] = None,
 |         updated: Optional[Union[datetime, str]] = None,
 |         name: Optional[str] = None,
 |         workspace: Optional[Union[str, UUID]] = None,
 |         user: Optional[Union[UUID, str]] = None,
 |         hydrate: bool = False) -> Page[CodeRepositoryResponse]
```

List all code repositories.

**Arguments**:

- `sort_by` - The column to sort by.
- `page` - The page of items.
- `size` - The maximum size of all pages.
- `logical_operator` - Which logical operator to use [and, or].
- `id` - Use the id of the code repository to filter by.
- `created` - Use to filter by time of creation.
- `updated` - Use the last updated date for filtering.
- `name` - The name of the code repository to filter by.
- `workspace` - The workspace name/ID to filter by.
- `user` - Filter by user name/ID.
- `hydrate` - Flag deciding whether to hydrate the output model(s)
  by including metadata fields in the response.
  

**Returns**:

  A page of code repositories matching the filter description.

<a id="zenml.client.Client.update_code_repository"></a>

### Client.update\_code\_repository

```python
 | def update_code_repository(
 |         name_id_or_prefix: Union[UUID, str],
 |         name: Optional[str] = None,
 |         description: Optional[str] = None,
 |         logo_url: Optional[str] = None,
 |         config: Optional[Dict[str, Any]] = None,
 |         workspace: Optional[Union[str,
 |                                   UUID]] = None) -> CodeRepositoryResponse
```

Update a code repository.

**Arguments**:

- `name_id_or_prefix` - Name, ID or prefix of the code repository to
  update.
- `name` - New name of the code repository.
- `description` - New description of the code repository.
- `logo_url` - New logo URL of the code repository.
- `config` - New configuration options for the code repository. Will
  be used to update the existing configuration values. To remove
  values from the existing configuration, set the value for that
  key to `None`.
- `workspace` - The workspace name/ID to filter by.
  

**Returns**:

  The updated code repository.

<a id="zenml.client.Client.delete_code_repository"></a>

### Client.delete\_code\_repository

```python
 | def delete_code_repository(
 |         name_id_or_prefix: Union[str, UUID],
 |         workspace: Optional[Union[str, UUID]] = None) -> None
```

Delete a code repository.

**Arguments**:

- `name_id_or_prefix` - The name, ID or prefix of the code repository.
- `workspace` - The workspace name/ID to filter by.

<a id="zenml.client.Client.create_service_connector"></a>

### Client.create\_service\_connector

```python
 | def create_service_connector(
 |     name: str,
 |     connector_type: str,
 |     resource_type: Optional[str] = None,
 |     auth_method: Optional[str] = None,
 |     configuration: Optional[Dict[str, str]] = None,
 |     resource_id: Optional[str] = None,
 |     description: str = "",
 |     expiration_seconds: Optional[int] = None,
 |     expires_at: Optional[datetime] = None,
 |     expires_skew_tolerance: Optional[int] = None,
 |     labels: Optional[Dict[str, str]] = None,
 |     auto_configure: bool = False,
 |     verify: bool = True,
 |     list_resources: bool = True,
 |     register: bool = True
 | ) -> Tuple[
 |         Optional[Union[
 |             ServiceConnectorResponse,
 |             ServiceConnectorRequest,
 |         ]],
 |         Optional[ServiceConnectorResourcesModel],
 | ]
```

Create, validate and/or register a service connector.

**Arguments**:

- `name` - The name of the service connector.
- `connector_type` - The service connector type.
- `auth_method` - The authentication method of the service connector.
  May be omitted if auto-configuration is used.
- `resource_type` - The resource type for the service connector.
- `configuration` - The configuration of the service connector.
- `resource_id` - The resource id of the service connector.
- `description` - The description of the service connector.
- `expiration_seconds` - The expiration time of the service connector.
- `expires_at` - The expiration time of the service connector.
- `expires_skew_tolerance` - The allowed expiration skew for the service
  connector credentials.
- `labels` - The labels of the service connector.
- `auto_configure` - Whether to automatically configure the service
  connector from the local environment.
- `verify` - Whether to verify that the service connector configuration
  and credentials can be used to gain access to the resource.
- `list_resources` - Whether to also list the resources that the service
  connector can give access to (if verify is True).
- `register` - Whether to register the service connector or not.
  

**Returns**:

  The model of the registered service connector and the resources
  that the service connector can give access to (if verify is True).
  

**Raises**:

- `ValueError` - If the arguments are invalid.
- `KeyError` - If the service connector type is not found.
- `NotImplementedError` - If auto-configuration is not supported or
  not implemented for the service connector type.
- `AuthorizationException` - If the connector verification failed due
  to authorization issues.

<a id="zenml.client.Client.get_service_connector"></a>

### Client.get\_service\_connector

```python
 | def get_service_connector(name_id_or_prefix: Union[str, UUID],
 |                           allow_name_prefix_match: bool = True,
 |                           load_secrets: bool = False,
 |                           hydrate: bool = True) -> ServiceConnectorResponse
```

Fetches a registered service connector.

**Arguments**:

- `name_id_or_prefix` - The id of the service connector to fetch.
- `allow_name_prefix_match` - If True, allow matching by name prefix.
- `load_secrets` - If True, load the secrets for the service connector.
- `hydrate` - Flag deciding whether to hydrate the output model(s)
  by including metadata fields in the response.
  

**Returns**:

  The registered service connector.

<a id="zenml.client.Client.list_service_connectors"></a>

### Client.list\_service\_connectors

```python
 | def list_service_connectors(
 |         sort_by: str = "created",
 |         page: int = PAGINATION_STARTING_PAGE,
 |         size: int = PAGE_SIZE_DEFAULT,
 |         logical_operator: LogicalOperators = LogicalOperators.AND,
 |         id: Optional[Union[UUID, str]] = None,
 |         created: Optional[datetime] = None,
 |         updated: Optional[datetime] = None,
 |         name: Optional[str] = None,
 |         connector_type: Optional[str] = None,
 |         auth_method: Optional[str] = None,
 |         resource_type: Optional[str] = None,
 |         resource_id: Optional[str] = None,
 |         user: Optional[Union[UUID, str]] = None,
 |         labels: Optional[Dict[str, Optional[str]]] = None,
 |         secret_id: Optional[Union[str, UUID]] = None,
 |         hydrate: bool = False) -> Page[ServiceConnectorResponse]
```

Lists all registered service connectors.

**Arguments**:

- `sort_by` - The column to sort by
- `page` - The page of items
- `size` - The maximum size of all pages
- `logical_operator` - Which logical operator to use [and, or]
- `id` - The id of the service connector to filter by.
- `created` - Filter service connectors by time of creation
- `updated` - Use the last updated date for filtering
- `connector_type` - Use the service connector type for filtering
- `auth_method` - Use the service connector auth method for filtering
- `resource_type` - Filter service connectors by the resource type that
  they can give access to.
- `resource_id` - Filter service connectors by the resource id that
  they can give access to.
- `user` - Filter by user name/ID.
- `name` - The name of the service connector to filter by.
- `labels` - The labels of the service connector to filter by.
- `secret_id` - Filter by the id of the secret that is referenced by the
  service connector.
- `hydrate` - Flag deciding whether to hydrate the output model(s)
  by including metadata fields in the response.
  

**Returns**:

  A page of service connectors.

<a id="zenml.client.Client.update_service_connector"></a>

### Client.update\_service\_connector

```python
 | def update_service_connector(
 |     name_id_or_prefix: Union[UUID, str],
 |     name: Optional[str] = None,
 |     auth_method: Optional[str] = None,
 |     resource_type: Optional[str] = None,
 |     configuration: Optional[Dict[str, str]] = None,
 |     resource_id: Optional[str] = None,
 |     description: Optional[str] = None,
 |     expires_at: Optional[datetime] = None,
 |     expires_skew_tolerance: Optional[int] = None,
 |     expiration_seconds: Optional[int] = None,
 |     labels: Optional[Dict[str, Optional[str]]] = None,
 |     verify: bool = True,
 |     list_resources: bool = True,
 |     update: bool = True
 | ) -> Tuple[
 |         Optional[Union[
 |             ServiceConnectorResponse,
 |             ServiceConnectorUpdate,
 |         ]],
 |         Optional[ServiceConnectorResourcesModel],
 | ]
```

Validate and/or register an updated service connector.

If the `resource_type`, `resource_id` and `expiration_seconds`
parameters are set to their "empty" values (empty string for resource
type and resource ID, 0 for expiration seconds), the existing values
will be removed from the service connector. Setting them to None or
omitting them will not affect the existing values.

If supplied, the `configuration` parameter is a full replacement of the
existing configuration rather than a partial update.

Labels can be updated or removed by setting the label value to None.

**Arguments**:

- `name_id_or_prefix` - The name, id or prefix of the service connector
  to update.
- `name` - The new name of the service connector.
- `auth_method` - The new authentication method of the service connector.
- `resource_type` - The new resource type for the service connector.
  If set to the empty string, the existing resource type will be
  removed.
- `configuration` - The new configuration of the service connector. If
  set, this needs to be a full replacement of the existing
  configuration rather than a partial update.
- `resource_id` - The new resource id of the service connector.
  If set to the empty string, the existing resource ID will be
  removed.
- `description` - The description of the service connector.
- `expires_at` - The new UTC expiration time of the service connector.
- `expires_skew_tolerance` - The allowed expiration skew for the service
  connector credentials.
- `expiration_seconds` - The expiration time of the service connector.
  If set to 0, the existing expiration time will be removed.
- `labels` - The service connector to update or remove. If a label value
  is set to None, the label will be removed.
- `verify` - Whether to verify that the service connector configuration
  and credentials can be used to gain access to the resource.
- `list_resources` - Whether to also list the resources that the service
  connector can give access to (if verify is True).
- `update` - Whether to update the service connector or not.
  

**Returns**:

  The model of the registered service connector and the resources
  that the service connector can give access to (if verify is True).
  

**Raises**:

- `AuthorizationException` - If the service connector verification
  fails due to invalid credentials or insufficient permissions.

<a id="zenml.client.Client.delete_service_connector"></a>

### Client.delete\_service\_connector

```python
 | def delete_service_connector(name_id_or_prefix: Union[str, UUID]) -> None
```

Deletes a registered service connector.

**Arguments**:

- `name_id_or_prefix` - The ID or name of the service connector to delete.

<a id="zenml.client.Client.verify_service_connector"></a>

### Client.verify\_service\_connector

```python
 | def verify_service_connector(
 |         name_id_or_prefix: Union[UUID, str],
 |         resource_type: Optional[str] = None,
 |         resource_id: Optional[str] = None,
 |         list_resources: bool = True) -> "ServiceConnectorResourcesModel"
```

Verifies if a service connector has access to one or more resources.

**Arguments**:

- `name_id_or_prefix` - The name, id or prefix of the service connector
  to verify.
- `resource_type` - The type of the resource for which to verify access.
  If not provided, the resource type from the service connector
  configuration will be used.
- `resource_id` - The ID of the resource for which to verify access. If
  not provided, the resource ID from the service connector
  configuration will be used.
- `list_resources` - Whether to list the resources that the service
  connector has access to.
  

**Returns**:

  The list of resources that the service connector has access to,
  scoped to the supplied resource type and ID, if provided.
  

**Raises**:

- `AuthorizationException` - If the service connector does not have
  access to the resources.

<a id="zenml.client.Client.login_service_connector"></a>

### Client.login\_service\_connector

```python
 | def login_service_connector(name_id_or_prefix: Union[UUID, str],
 |                             resource_type: Optional[str] = None,
 |                             resource_id: Optional[str] = None,
 |                             **kwargs: Any) -> "ServiceConnector"
```

Use a service connector to authenticate a local client/SDK.

**Arguments**:

- `name_id_or_prefix` - The name, id or prefix of the service connector
  to use.
- `resource_type` - The type of the resource to connect to. If not
  provided, the resource type from the service connector
  configuration will be used.
- `resource_id` - The ID of a particular resource instance to configure
  the local client to connect to. If the connector instance is
  already configured with a resource ID that is not the same or
  equivalent to the one requested, a `ValueError` exception is
  raised. May be omitted for connectors and resource types that do
  not support multiple resource instances.
- `kwargs` - Additional implementation specific keyword arguments to use
  to configure the client.
  

**Returns**:

  The service connector client instance that was used to configure the
  local client.

<a id="zenml.client.Client.get_service_connector_client"></a>

### Client.get\_service\_connector\_client

```python
 | def get_service_connector_client(name_id_or_prefix: Union[UUID, str],
 |                                  resource_type: Optional[str] = None,
 |                                  resource_id: Optional[str] = None,
 |                                  verify: bool = False) -> "ServiceConnector"
```

Get the client side of a service connector instance to use with a local client.

**Arguments**:

- `name_id_or_prefix` - The name, id or prefix of the service connector
  to use.
- `resource_type` - The type of the resource to connect to. If not
  provided, the resource type from the service connector
  configuration will be used.
- `resource_id` - The ID of a particular resource instance to configure
  the local client to connect to. If the connector instance is
  already configured with a resource ID that is not the same or
  equivalent to the one requested, a `ValueError` exception is
  raised. May be omitted for connectors and resource types that do
  not support multiple resource instances.
- `verify` - Whether to verify that the service connector configuration
  and credentials can be used to gain access to the resource.
  

**Returns**:

  The client side of the indicated service connector instance that can
  be used to connect to the resource locally.

<a id="zenml.client.Client.list_service_connector_resources"></a>

### Client.list\_service\_connector\_resources

```python
 | def list_service_connector_resources(
 |     connector_type: Optional[str] = None,
 |     resource_type: Optional[str] = None,
 |     resource_id: Optional[str] = None,
 |     workspace_id: Optional[UUID] = None
 | ) -> List[ServiceConnectorResourcesModel]
```

List resources that can be accessed by service connectors.

**Arguments**:

- `connector_type` - The type of service connector to filter by.
- `resource_type` - The type of resource to filter by.
- `resource_id` - The ID of a particular resource instance to filter by.
- `workspace_id` - The ID of the workspace to filter by. If not provided,
  the active workspace will be used.
  

**Returns**:

  The matching list of resources that available service
  connectors have access to.

<a id="zenml.client.Client.list_service_connector_types"></a>

### Client.list\_service\_connector\_types

```python
 | def list_service_connector_types(
 |         connector_type: Optional[str] = None,
 |         resource_type: Optional[str] = None,
 |         auth_method: Optional[str] = None) -> List[ServiceConnectorTypeModel]
```

Get a list of service connector types.

**Arguments**:

- `connector_type` - Filter by connector type.
- `resource_type` - Filter by resource type.
- `auth_method` - Filter by authentication method.
  

**Returns**:

  List of service connector types.

<a id="zenml.client.Client.get_service_connector_type"></a>

### Client.get\_service\_connector\_type

```python
 | def get_service_connector_type(
 |         connector_type: str) -> ServiceConnectorTypeModel
```

Returns the requested service connector type.

**Arguments**:

- `connector_type` - the service connector type identifier.
  

**Returns**:

  The requested service connector type.

<a id="zenml.client.Client.create_model"></a>

### Client.create\_model

```python
 | def create_model(name: str,
 |                  license: Optional[str] = None,
 |                  description: Optional[str] = None,
 |                  audience: Optional[str] = None,
 |                  use_cases: Optional[str] = None,
 |                  limitations: Optional[str] = None,
 |                  trade_offs: Optional[str] = None,
 |                  ethics: Optional[str] = None,
 |                  tags: Optional[List[str]] = None,
 |                  save_models_to_registry: bool = True) -> ModelResponse
```

Creates a new model in Model Control Plane.

**Arguments**:

- `name` - The name of the model.
- `license` - The license under which the model is created.
- `description` - The description of the model.
- `audience` - The target audience of the model.
- `use_cases` - The use cases of the model.
- `limitations` - The known limitations of the model.
- `trade_offs` - The tradeoffs of the model.
- `ethics` - The ethical implications of the model.
- `tags` - Tags associated with the model.
- `save_models_to_registry` - Whether to save the model to the
  registry.
  

**Returns**:

  The newly created model.

<a id="zenml.client.Client.delete_model"></a>

### Client.delete\_model

```python
 | def delete_model(model_name_or_id: Union[str, UUID],
 |                  workspace: Optional[Union[str, UUID]] = None) -> None
```

Deletes a model from Model Control Plane.

**Arguments**:

- `model_name_or_id` - name or id of the model to be deleted.
- `workspace` - The workspace name/ID to filter by.

<a id="zenml.client.Client.update_model"></a>

### Client.update\_model

```python
 | def update_model(
 |         model_name_or_id: Union[str, UUID],
 |         name: Optional[str] = None,
 |         license: Optional[str] = None,
 |         description: Optional[str] = None,
 |         audience: Optional[str] = None,
 |         use_cases: Optional[str] = None,
 |         limitations: Optional[str] = None,
 |         trade_offs: Optional[str] = None,
 |         ethics: Optional[str] = None,
 |         add_tags: Optional[List[str]] = None,
 |         remove_tags: Optional[List[str]] = None,
 |         save_models_to_registry: Optional[bool] = None,
 |         workspace: Optional[Union[str, UUID]] = None) -> ModelResponse
```

Updates an existing model in Model Control Plane.

**Arguments**:

- `model_name_or_id` - name or id of the model to be deleted.
- `name` - The name of the model.
- `license` - The license under which the model is created.
- `description` - The description of the model.
- `audience` - The target audience of the model.
- `use_cases` - The use cases of the model.
- `limitations` - The known limitations of the model.
- `trade_offs` - The tradeoffs of the model.
- `ethics` - The ethical implications of the model.
- `add_tags` - Tags to add to the model.
- `remove_tags` - Tags to remove from to the model.
- `save_models_to_registry` - Whether to save the model to the
  registry.
- `workspace` - The workspace name/ID to filter by.
  

**Returns**:

  The updated model.

<a id="zenml.client.Client.get_model"></a>

### Client.get\_model

```python
 | def get_model(model_name_or_id: Union[str, UUID],
 |               workspace: Optional[Union[str, UUID]] = None,
 |               hydrate: bool = True,
 |               bypass_lazy_loader: bool = False) -> ModelResponse
```

Get an existing model from Model Control Plane.

**Arguments**:

- `model_name_or_id` - name or id of the model to be retrieved.
- `workspace` - The workspace name/ID to filter by.
- `hydrate` - Flag deciding whether to hydrate the output model(s)
  by including metadata fields in the response.
- `bypass_lazy_loader` - Whether to bypass the lazy loader.
  

**Returns**:

  The model of interest.

<a id="zenml.client.Client.list_models"></a>

### Client.list\_models

```python
 | def list_models(sort_by: str = "created",
 |                 page: int = PAGINATION_STARTING_PAGE,
 |                 size: int = PAGE_SIZE_DEFAULT,
 |                 logical_operator: LogicalOperators = LogicalOperators.AND,
 |                 created: Optional[Union[datetime, str]] = None,
 |                 updated: Optional[Union[datetime, str]] = None,
 |                 name: Optional[str] = None,
 |                 id: Optional[Union[UUID, str]] = None,
 |                 user: Optional[Union[UUID, str]] = None,
 |                 workspace: Optional[Union[str, UUID]] = None,
 |                 hydrate: bool = False,
 |                 tag: Optional[str] = None,
 |                 tags: Optional[List[str]] = None) -> Page[ModelResponse]
```

Get models by filter from Model Control Plane.

**Arguments**:

- `sort_by` - The column to sort by
- `page` - The page of items
- `size` - The maximum size of all pages
- `logical_operator` - Which logical operator to use [and, or]
- `created` - Use to filter by time of creation
- `updated` - Use the last updated date for filtering
- `name` - The name of the model to filter by.
- `id` - The id of the model to filter by.
- `user` - Filter by user name/ID.
- `workspace` - The workspace name/ID to filter by.
- `hydrate` - Flag deciding whether to hydrate the output model(s)
  by including metadata fields in the response.
- `tag` - The tag of the model to filter by.
- `tags` - Tags to filter by.
  

**Returns**:

  A page object with all models.

<a id="zenml.client.Client.create_model_version"></a>

### Client.create\_model\_version

```python
 | def create_model_version(
 |         model_name_or_id: Union[str, UUID],
 |         name: Optional[str] = None,
 |         description: Optional[str] = None,
 |         tags: Optional[List[str]] = None,
 |         workspace: Optional[Union[str, UUID]] = None) -> ModelVersionResponse
```

Creates a new model version in Model Control Plane.

**Arguments**:

- `model_name_or_id` - the name or id of the model to create model
  version in.
- `name` - the name of the Model Version to be created.
- `description` - the description of the Model Version to be created.
- `tags` - Tags associated with the model.
- `workspace` - The workspace name/ID to filter by.
  

**Returns**:

  The newly created model version.

<a id="zenml.client.Client.delete_model_version"></a>

### Client.delete\_model\_version

```python
 | def delete_model_version(model_version_id: UUID) -> None
```

Deletes a model version from Model Control Plane.

**Arguments**:

- `model_version_id` - Id of the model version to be deleted.

<a id="zenml.client.Client.get_model_version"></a>

### Client.get\_model\_version

```python
 | def get_model_version(model_name_or_id: Optional[Union[str, UUID]] = None,
 |                       model_version_name_or_number_or_id: Optional[Union[
 |                           str, int, ModelStages, UUID]] = None,
 |                       workspace: Optional[Union[str, UUID]] = None,
 |                       hydrate: bool = True) -> ModelVersionResponse
```

Get an existing model version from Model Control Plane.

**Arguments**:

- `model_name_or_id` - name or id of the model containing the model
  version.
- `model_version_name_or_number_or_id` - name, id, stage or number of
  the model version to be retrieved. If skipped - latest version
  is retrieved.
- `workspace` - The workspace name/ID to filter by.
- `hydrate` - Flag deciding whether to hydrate the output model(s)
  by including metadata fields in the response.
  

**Returns**:

  The model version of interest.
  

**Raises**:

- `RuntimeError` - In case method inputs don't adhere to restrictions.
- `KeyError` - In case no model version with the identifiers exists.
- `ValueError` - In case retrieval is attempted using non UUID model version
  identifier and no model identifier provided.

<a id="zenml.client.Client.list_model_versions"></a>

### Client.list\_model\_versions

```python
 | def list_model_versions(
 |     model_name_or_id: Union[str, UUID],
 |     sort_by: str = "number",
 |     page: int = PAGINATION_STARTING_PAGE,
 |     size: int = PAGE_SIZE_DEFAULT,
 |     logical_operator: LogicalOperators = LogicalOperators.AND,
 |     created: Optional[Union[datetime, str]] = None,
 |     updated: Optional[Union[datetime, str]] = None,
 |     name: Optional[str] = None,
 |     id: Optional[Union[UUID, str]] = None,
 |     number: Optional[int] = None,
 |     stage: Optional[Union[str, ModelStages]] = None,
 |     run_metadata: Optional[Dict[str, str]] = None,
 |     user: Optional[Union[UUID, str]] = None,
 |     hydrate: bool = False,
 |     tag: Optional[str] = None,
 |     tags: Optional[List[str]] = None,
 |     workspace: Optional[Union[str,
 |                               UUID]] = None) -> Page[ModelVersionResponse]
```

Get model versions by filter from Model Control Plane.

**Arguments**:

- `model_name_or_id` - name or id of the model containing the model
  version.
- `sort_by` - The column to sort by
- `page` - The page of items
- `size` - The maximum size of all pages
- `logical_operator` - Which logical operator to use [and, or]
- `created` - Use to filter by time of creation
- `updated` - Use the last updated date for filtering
- `name` - name or id of the model version.
- `id` - id of the model version.
- `number` - number of the model version.
- `stage` - stage of the model version.
- `run_metadata` - run metadata of the model version.
- `user` - Filter by user name/ID.
- `hydrate` - Flag deciding whether to hydrate the output model(s)
  by including metadata fields in the response.
- `tag` - The tag to filter by.
- `tags` - Tags to filter by.
- `workspace` - The workspace name/ID to filter by.
  

**Returns**:

  A page object with all model versions.

<a id="zenml.client.Client.update_model_version"></a>

### Client.update\_model\_version

```python
 | def update_model_version(
 |         model_name_or_id: Union[str, UUID],
 |         version_name_or_id: Union[str, UUID],
 |         stage: Optional[Union[str, ModelStages]] = None,
 |         force: bool = False,
 |         name: Optional[str] = None,
 |         description: Optional[str] = None,
 |         add_tags: Optional[List[str]] = None,
 |         remove_tags: Optional[List[str]] = None,
 |         workspace: Optional[Union[str, UUID]] = None) -> ModelVersionResponse
```

Get all model versions by filter.

**Arguments**:

- `model_name_or_id` - The name or ID of the model containing model version.
- `version_name_or_id` - The name or ID of model version to be updated.
- `stage` - Target model version stage to be set.
- `force` - Whether existing model version in target stage should be
  silently archived or an error should be raised.
- `name` - Target model version name to be set.
- `description` - Target model version description to be set.
- `add_tags` - Tags to add to the model version.
- `remove_tags` - Tags to remove from to the model version.
- `workspace` - The workspace name/ID to filter by.
  

**Returns**:

  An updated model version.

<a id="zenml.client.Client.list_model_version_artifact_links"></a>

### Client.list\_model\_version\_artifact\_links

```python
 | def list_model_version_artifact_links(
 |         sort_by: str = "created",
 |         page: int = PAGINATION_STARTING_PAGE,
 |         size: int = PAGE_SIZE_DEFAULT,
 |         logical_operator: LogicalOperators = LogicalOperators.AND,
 |         created: Optional[Union[datetime, str]] = None,
 |         updated: Optional[Union[datetime, str]] = None,
 |         model_version_id: Optional[Union[UUID, str]] = None,
 |         artifact_version_id: Optional[Union[UUID, str]] = None,
 |         artifact_name: Optional[str] = None,
 |         only_data_artifacts: Optional[bool] = None,
 |         only_model_artifacts: Optional[bool] = None,
 |         only_deployment_artifacts: Optional[bool] = None,
 |         has_custom_name: Optional[bool] = None,
 |         user: Optional[Union[UUID, str]] = None,
 |         hydrate: bool = False) -> Page[ModelVersionArtifactResponse]
```

Get model version to artifact links by filter in Model Control Plane.

**Arguments**:

- `sort_by` - The column to sort by
- `page` - The page of items
- `size` - The maximum size of all pages
- `logical_operator` - Which logical operator to use [and, or]
- `created` - Use to filter by time of creation
- `updated` - Use the last updated date for filtering
- `model_version_id` - Use the model version id for filtering
- `artifact_version_id` - Use the artifact id for filtering
- `artifact_name` - Use the artifact name for filtering
- `only_data_artifacts` - Use to filter by data artifacts
- `only_model_artifacts` - Use to filter by model artifacts
- `only_deployment_artifacts` - Use to filter by deployment artifacts
- `has_custom_name` - Filter artifacts with/without custom names.
- `user` - Filter by user name/ID.
- `hydrate` - Flag deciding whether to hydrate the output model(s)
  by including metadata fields in the response.
  

**Returns**:

  A page of all model version to artifact links.

<a id="zenml.client.Client.delete_model_version_artifact_link"></a>

### Client.delete\_model\_version\_artifact\_link

```python
 | def delete_model_version_artifact_link(model_version_id: UUID,
 |                                        artifact_version_id: UUID) -> None
```

Delete model version to artifact link in Model Control Plane.

**Arguments**:

- `model_version_id` - The id of the model version holding the link.
- `artifact_version_id` - The id of the artifact version to be deleted.
  

**Raises**:

- `RuntimeError` - If more than one artifact link is found for given filters.

<a id="zenml.client.Client.delete_all_model_version_artifact_links"></a>

### Client.delete\_all\_model\_version\_artifact\_links

```python
 | def delete_all_model_version_artifact_links(model_version_id: UUID,
 |                                             only_links: bool) -> None
```

Delete all model version to artifact links in Model Control Plane.

**Arguments**:

- `model_version_id` - The id of the model version holding the link.
- `only_links` - If true, only delete the link to the artifact.

<a id="zenml.client.Client.list_model_version_pipeline_run_links"></a>

### Client.list\_model\_version\_pipeline\_run\_links

```python
 | def list_model_version_pipeline_run_links(
 |         sort_by: str = "created",
 |         page: int = PAGINATION_STARTING_PAGE,
 |         size: int = PAGE_SIZE_DEFAULT,
 |         logical_operator: LogicalOperators = LogicalOperators.AND,
 |         created: Optional[Union[datetime, str]] = None,
 |         updated: Optional[Union[datetime, str]] = None,
 |         model_version_id: Optional[Union[UUID, str]] = None,
 |         pipeline_run_id: Optional[Union[UUID, str]] = None,
 |         pipeline_run_name: Optional[str] = None,
 |         user: Optional[Union[UUID, str]] = None,
 |         hydrate: bool = False) -> Page[ModelVersionPipelineRunResponse]
```

Get all model version to pipeline run links by filter.

**Arguments**:

- `sort_by` - The column to sort by
- `page` - The page of items
- `size` - The maximum size of all pages
- `logical_operator` - Which logical operator to use [and, or]
- `created` - Use to filter by time of creation
- `updated` - Use the last updated date for filtering
- `model_version_id` - Use the model version id for filtering
- `pipeline_run_id` - Use the pipeline run id for filtering
- `pipeline_run_name` - Use the pipeline run name for filtering
- `user` - Filter by user name or ID.
- `hydrate` - Flag deciding whether to hydrate the output model(s)
  by including metadata fields in the response
  

**Returns**:

  A page of all model version to pipeline run links.

<a id="zenml.client.Client.list_authorized_devices"></a>

### Client.list\_authorized\_devices

```python
 | def list_authorized_devices(
 |         sort_by: str = "created",
 |         page: int = PAGINATION_STARTING_PAGE,
 |         size: int = PAGE_SIZE_DEFAULT,
 |         logical_operator: LogicalOperators = LogicalOperators.AND,
 |         id: Optional[Union[UUID, str]] = None,
 |         created: Optional[Union[datetime, str]] = None,
 |         updated: Optional[Union[datetime, str]] = None,
 |         expires: Optional[Union[datetime, str]] = None,
 |         client_id: Union[UUID, str, None] = None,
 |         status: Union[OAuthDeviceStatus, str, None] = None,
 |         trusted_device: Union[bool, str, None] = None,
 |         user: Optional[Union[UUID, str]] = None,
 |         failed_auth_attempts: Union[int, str, None] = None,
 |         last_login: Optional[Union[datetime, str, None]] = None,
 |         hydrate: bool = False) -> Page[OAuthDeviceResponse]
```

List all authorized devices.

**Arguments**:

- `sort_by` - The column to sort by.
- `page` - The page of items.
- `size` - The maximum size of all pages.
- `logical_operator` - Which logical operator to use [and, or].
- `id` - Use the id of the code repository to filter by.
- `created` - Use to filter by time of creation.
- `updated` - Use the last updated date for filtering.
- `expires` - Use the expiration date for filtering.
- `client_id` - Use the client id for filtering.
- `status` - Use the status for filtering.
- `user` - Filter by user name/ID.
- `trusted_device` - Use the trusted device flag for filtering.
- `failed_auth_attempts` - Use the failed auth attempts for filtering.
- `last_login` - Use the last login date for filtering.
- `hydrate` - Flag deciding whether to hydrate the output model(s)
  by including metadata fields in the response.
  

**Returns**:

  A page of authorized devices matching the filter.

<a id="zenml.client.Client.get_authorized_device"></a>

### Client.get\_authorized\_device

```python
 | def get_authorized_device(id_or_prefix: Union[UUID, str],
 |                           allow_id_prefix_match: bool = True,
 |                           hydrate: bool = True) -> OAuthDeviceResponse
```

Get an authorized device by id or prefix.

**Arguments**:

- `id_or_prefix` - The ID or ID prefix of the authorized device.
- `allow_id_prefix_match` - If True, allow matching by ID prefix.
- `hydrate` - Flag deciding whether to hydrate the output model(s)
  by including metadata fields in the response.
  

**Returns**:

  The requested authorized device.
  

**Raises**:

- `KeyError` - If no authorized device is found with the given ID or
  prefix.

<a id="zenml.client.Client.update_authorized_device"></a>

### Client.update\_authorized\_device

```python
 | def update_authorized_device(
 |         id_or_prefix: Union[UUID, str],
 |         locked: Optional[bool] = None) -> OAuthDeviceResponse
```

Update an authorized device.

**Arguments**:

- `id_or_prefix` - The ID or ID prefix of the authorized device.
- `locked` - Whether to lock or unlock the authorized device.
  

**Returns**:

  The updated authorized device.

<a id="zenml.client.Client.delete_authorized_device"></a>

### Client.delete\_authorized\_device

```python
 | def delete_authorized_device(id_or_prefix: Union[str, UUID]) -> None
```

Delete an authorized device.

**Arguments**:

- `id_or_prefix` - The ID or ID prefix of the authorized device.

<a id="zenml.client.Client.get_trigger_execution"></a>

### Client.get\_trigger\_execution

```python
 | def get_trigger_execution(trigger_execution_id: UUID,
 |                           hydrate: bool = True) -> TriggerExecutionResponse
```

Get a trigger execution by ID.

**Arguments**:

- `trigger_execution_id` - The ID of the trigger execution to get.
- `hydrate` - Flag deciding whether to hydrate the output model(s)
  by including metadata fields in the response.
  

**Returns**:

  The trigger execution.

<a id="zenml.client.Client.list_trigger_executions"></a>

### Client.list\_trigger\_executions

```python
 | def list_trigger_executions(
 |         sort_by: str = "created",
 |         page: int = PAGINATION_STARTING_PAGE,
 |         size: int = PAGE_SIZE_DEFAULT,
 |         logical_operator: LogicalOperators = LogicalOperators.AND,
 |         trigger_id: Optional[UUID] = None,
 |         user: Optional[Union[UUID, str]] = None,
 |         workspace: Optional[Union[UUID, str]] = None,
 |         hydrate: bool = False) -> Page[TriggerExecutionResponse]
```

List all trigger executions matching the given filter criteria.

**Arguments**:

- `sort_by` - The column to sort by.
- `page` - The page of items.
- `size` - The maximum size of all pages.
- `logical_operator` - Which logical operator to use [and, or].
- `trigger_id` - ID of the trigger to filter by.
- `user` - Filter by user name/ID.
- `workspace` - Filter by workspace name/ID.
- `hydrate` - Flag deciding whether to hydrate the output model(s)
  by including metadata fields in the response.
  

**Returns**:

  A list of all trigger executions matching the filter criteria.

<a id="zenml.client.Client.delete_trigger_execution"></a>

### Client.delete\_trigger\_execution

```python
 | def delete_trigger_execution(trigger_execution_id: UUID) -> None
```

Delete a trigger execution.

**Arguments**:

- `trigger_execution_id` - The ID of the trigger execution to delete.

<a id="zenml.client.Client.create_service_account"></a>

### Client.create\_service\_account

```python
 | def create_service_account(name: str,
 |                            description: str = "") -> ServiceAccountResponse
```

Create a new service account.

**Arguments**:

- `name` - The name of the service account.
- `description` - The description of the service account.
  

**Returns**:

  The created service account.

<a id="zenml.client.Client.get_service_account"></a>

### Client.get\_service\_account

```python
 | def get_service_account(name_id_or_prefix: Union[str, UUID],
 |                         allow_name_prefix_match: bool = True,
 |                         hydrate: bool = True) -> ServiceAccountResponse
```

Gets a service account.

**Arguments**:

- `name_id_or_prefix` - The name or ID of the service account.
- `allow_name_prefix_match` - If True, allow matching by name prefix.
- `hydrate` - Flag deciding whether to hydrate the output model(s)
  by including metadata fields in the response.
  

**Returns**:

  The ServiceAccount

<a id="zenml.client.Client.list_service_accounts"></a>

### Client.list\_service\_accounts

```python
 | def list_service_accounts(
 |         sort_by: str = "created",
 |         page: int = PAGINATION_STARTING_PAGE,
 |         size: int = PAGE_SIZE_DEFAULT,
 |         logical_operator: LogicalOperators = LogicalOperators.AND,
 |         id: Optional[Union[UUID, str]] = None,
 |         created: Optional[Union[datetime, str]] = None,
 |         updated: Optional[Union[datetime, str]] = None,
 |         name: Optional[str] = None,
 |         description: Optional[str] = None,
 |         active: Optional[bool] = None,
 |         hydrate: bool = False) -> Page[ServiceAccountResponse]
```

List all service accounts.

**Arguments**:

- `sort_by` - The column to sort by
- `page` - The page of items
- `size` - The maximum size of all pages
- `logical_operator` - Which logical operator to use [and, or]
- `id` - Use the id of stacks to filter by.
- `created` - Use to filter by time of creation
- `updated` - Use the last updated date for filtering
- `name` - Use the service account name for filtering
- `description` - Use the service account description for filtering
- `active` - Use the service account active status for filtering
- `hydrate` - Flag deciding whether to hydrate the output model(s)
  by including metadata fields in the response.
  

**Returns**:

  The list of service accounts matching the filter description.

<a id="zenml.client.Client.update_service_account"></a>

### Client.update\_service\_account

```python
 | def update_service_account(
 |         name_id_or_prefix: Union[str, UUID],
 |         updated_name: Optional[str] = None,
 |         description: Optional[str] = None,
 |         active: Optional[bool] = None) -> ServiceAccountResponse
```

Update a service account.

**Arguments**:

- `name_id_or_prefix` - The name or ID of the service account to update.
- `updated_name` - The new name of the service account.
- `description` - The new description of the service account.
- `active` - The new active status of the service account.
  

**Returns**:

  The updated service account.

<a id="zenml.client.Client.delete_service_account"></a>

### Client.delete\_service\_account

```python
 | def delete_service_account(name_id_or_prefix: Union[str, UUID]) -> None
```

Delete a service account.

**Arguments**:

- `name_id_or_prefix` - The name or ID of the service account to delete.

<a id="zenml.client.Client.create_api_key"></a>

### Client.create\_api\_key

```python
 | def create_api_key(service_account_name_id_or_prefix: Union[str, UUID],
 |                    name: str,
 |                    description: str = "",
 |                    set_key: bool = False) -> APIKeyResponse
```

Create a new API key and optionally set it as the active API key.

**Arguments**:

- `service_account_name_id_or_prefix` - The name, ID or prefix of the
  service account to create the API key for.
- `name` - Name of the API key.
- `description` - The description of the API key.
- `set_key` - Whether to set the created API key as the active API key.
  

**Returns**:

  The created API key.

<a id="zenml.client.Client.set_api_key"></a>

### Client.set\_api\_key

```python
 | def set_api_key(key: str) -> None
```

Configure the client with an API key.

**Arguments**:

- `key` - The API key to use.
  

**Raises**:

- `NotImplementedError` - If the client is not connected to a ZenML
  server.

<a id="zenml.client.Client.list_api_keys"></a>

### Client.list\_api\_keys

```python
 | def list_api_keys(service_account_name_id_or_prefix: Union[str, UUID],
 |                   sort_by: str = "created",
 |                   page: int = PAGINATION_STARTING_PAGE,
 |                   size: int = PAGE_SIZE_DEFAULT,
 |                   logical_operator: LogicalOperators = LogicalOperators.AND,
 |                   id: Optional[Union[UUID, str]] = None,
 |                   created: Optional[Union[datetime, str]] = None,
 |                   updated: Optional[Union[datetime, str]] = None,
 |                   name: Optional[str] = None,
 |                   description: Optional[str] = None,
 |                   active: Optional[bool] = None,
 |                   last_login: Optional[Union[datetime, str]] = None,
 |                   last_rotated: Optional[Union[datetime, str]] = None,
 |                   hydrate: bool = False) -> Page[APIKeyResponse]
```

List all API keys.

**Arguments**:

- `service_account_name_id_or_prefix` - The name, ID or prefix of the
  service account to list the API keys for.
- `sort_by` - The column to sort by.
- `page` - The page of items.
- `size` - The maximum size of all pages.
- `logical_operator` - Which logical operator to use [and, or].
- `id` - Use the id of the API key to filter by.
- `created` - Use to filter by time of creation.
- `updated` - Use the last updated date for filtering.
- `name` - The name of the API key to filter by.
- `description` - The description of the API key to filter by.
- `active` - Whether the API key is active or not.
- `last_login` - The last time the API key was used.
- `last_rotated` - The last time the API key was rotated.
- `hydrate` - Flag deciding whether to hydrate the output model(s)
  by including metadata fields in the response.
  

**Returns**:

  A page of API keys matching the filter description.

<a id="zenml.client.Client.get_api_key"></a>

### Client.get\_api\_key

```python
 | def get_api_key(service_account_name_id_or_prefix: Union[str, UUID],
 |                 name_id_or_prefix: Union[str, UUID],
 |                 allow_name_prefix_match: bool = True,
 |                 hydrate: bool = True) -> APIKeyResponse
```

Get an API key by name, id or prefix.

**Arguments**:

- `service_account_name_id_or_prefix` - The name, ID or prefix of the
  service account to get the API key for.
- `name_id_or_prefix` - The name, ID or ID prefix of the API key.
- `allow_name_prefix_match` - If True, allow matching by name prefix.
- `hydrate` - Flag deciding whether to hydrate the output model(s)
  by including metadata fields in the response.
  

**Returns**:

  The API key.

<a id="zenml.client.Client.update_api_key"></a>

### Client.update\_api\_key

```python
 | def update_api_key(service_account_name_id_or_prefix: Union[str, UUID],
 |                    name_id_or_prefix: Union[UUID, str],
 |                    name: Optional[str] = None,
 |                    description: Optional[str] = None,
 |                    active: Optional[bool] = None) -> APIKeyResponse
```

Update an API key.

**Arguments**:

- `service_account_name_id_or_prefix` - The name, ID or prefix of the
  service account to update the API key for.
- `name_id_or_prefix` - Name, ID or prefix of the API key to update.
- `name` - New name of the API key.
- `description` - New description of the API key.
- `active` - Whether the API key is active or not.
  

**Returns**:

  The updated API key.

<a id="zenml.client.Client.rotate_api_key"></a>

### Client.rotate\_api\_key

```python
 | def rotate_api_key(service_account_name_id_or_prefix: Union[str, UUID],
 |                    name_id_or_prefix: Union[UUID, str],
 |                    retain_period_minutes: int = 0,
 |                    set_key: bool = False) -> APIKeyResponse
```

Rotate an API key.

**Arguments**:

- `service_account_name_id_or_prefix` - The name, ID or prefix of the
  service account to rotate the API key for.
- `name_id_or_prefix` - Name, ID or prefix of the API key to update.
- `retain_period_minutes` - The number of minutes to retain the old API
  key for. If set to 0, the old API key will be invalidated.
- `set_key` - Whether to set the rotated API key as the active API key.
  

**Returns**:

  The updated API key.

<a id="zenml.client.Client.delete_api_key"></a>

### Client.delete\_api\_key

```python
 | def delete_api_key(service_account_name_id_or_prefix: Union[str, UUID],
 |                    name_id_or_prefix: Union[str, UUID]) -> None
```

Delete an API key.

**Arguments**:

- `service_account_name_id_or_prefix` - The name, ID or prefix of the
  service account to delete the API key for.
- `name_id_or_prefix` - The name, ID or prefix of the API key.

<a id="zenml.client.Client.create_tag"></a>

### Client.create\_tag

```python
 | def create_tag(
 |         name: str,
 |         exclusive: bool = False,
 |         color: Optional[Union[str, ColorVariants]] = None) -> TagResponse
```

Creates a new tag.

**Arguments**:

- `name` - the name of the tag.
- `exclusive` - the boolean to decide whether the tag is an exclusive tag.
  An exclusive tag means that the tag can exist only for a single:
  - pipeline run within the scope of a pipeline
  - artifact version within the scope of an artifact
  - run template
- `color` - the color of the tag
  

**Returns**:

  The newly created tag.

<a id="zenml.client.Client.delete_tag"></a>

### Client.delete\_tag

```python
 | def delete_tag(tag_name_or_id: Union[str, UUID]) -> None
```

Deletes a tag.

**Arguments**:

- `tag_name_or_id` - name or id of the tag to be deleted.

<a id="zenml.client.Client.update_tag"></a>

### Client.update\_tag

```python
 | def update_tag(
 |         tag_name_or_id: Union[str, UUID],
 |         name: Optional[str] = None,
 |         exclusive: Optional[bool] = None,
 |         color: Optional[Union[str, ColorVariants]] = None) -> TagResponse
```

Updates an existing tag.

**Arguments**:

- `tag_name_or_id` - name or UUID of the tag to be updated.
- `name` - the name of the tag.
- `exclusive` - the boolean to decide whether the tag is an exclusive tag.
  An exclusive tag means that the tag can exist only for a single:
  - pipeline run within the scope of a pipeline
  - artifact version within the scope of an artifact
  - run template
- `color` - the color of the tag
  

**Returns**:

  The updated tag.

<a id="zenml.client.Client.get_tag"></a>

### Client.get\_tag

```python
 | def get_tag(tag_name_or_id: Union[str, UUID],
 |             hydrate: bool = True) -> TagResponse
```

Get an existing tag.

**Arguments**:

- `tag_name_or_id` - name or id of the tag to be retrieved.
- `hydrate` - Flag deciding whether to hydrate the output model(s)
  by including metadata fields in the response.
  

**Returns**:

  The tag of interest.

<a id="zenml.client.Client.list_tags"></a>

### Client.list\_tags

```python
 | def list_tags(sort_by: str = "created",
 |               page: int = PAGINATION_STARTING_PAGE,
 |               size: int = PAGE_SIZE_DEFAULT,
 |               logical_operator: LogicalOperators = LogicalOperators.AND,
 |               id: Optional[Union[UUID, str]] = None,
 |               user: Optional[Union[UUID, str]] = None,
 |               created: Optional[Union[datetime, str]] = None,
 |               updated: Optional[Union[datetime, str]] = None,
 |               name: Optional[str] = None,
 |               color: Optional[Union[str, ColorVariants]] = None,
 |               exclusive: Optional[bool] = None,
 |               hydrate: bool = False) -> Page[TagResponse]
```

Get tags by filter.

**Arguments**:

- `sort_by` - The column to sort by.
- `page` - The page of items.
- `size` - The maximum size of all pages.
- `logical_operator` - Which logical operator to use [and, or].
- `id` - Use the id of stacks to filter by.
- `user` - Use the user to filter by.
- `created` - Use to filter by time of creation.
- `updated` - Use the last updated date for filtering.
- `name` - The name of the tag.
- `color` - The color of the tag.
- `exclusive` - Flag indicating whether the tag is exclusive.
- `hydrate` - Flag deciding whether to hydrate the output model(s)
  by including metadata fields in the response.
  

**Returns**:

  A page of all tags.

<a id="zenml.client.Client.attach_tag"></a>

### Client.attach\_tag

```python
 | def attach_tag(tag_name_or_id: Union[str, UUID],
 |                resources: List[TagResource]) -> None
```

Attach a tag to resources.

**Arguments**:

- `tag_name_or_id` - name or id of the tag to be attached.
- `resources` - the resources to attach the tag to.

<a id="zenml.client.Client.detach_tag"></a>

### Client.detach\_tag

```python
 | def detach_tag(tag_name_or_id: Union[str, UUID],
 |                resources: List[TagResource]) -> None
```

Detach a tag from resources.

**Arguments**:

- `tag_name_or_id` - name or id of the tag to be detached.
- `resources` - the resources to detach the tag from.

