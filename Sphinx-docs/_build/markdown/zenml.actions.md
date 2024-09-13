# zenml.actions package

## Subpackages

* [zenml.actions.pipeline_run package](zenml.actions.pipeline_run.md)
  * [Submodules](zenml.actions.pipeline_run.md#submodules)
  * [zenml.actions.pipeline_run.pipeline_run_action module](zenml.actions.pipeline_run.md#zenml-actions-pipeline-run-pipeline-run-action-module)
  * [Module contents](zenml.actions.pipeline_run.md#module-zenml.actions.pipeline_run)

## Submodules

## zenml.actions.base_action module

Base implementation of actions.

### *class* zenml.actions.base_action.ActionConfig

Bases: [`BasePluginConfig`](zenml.plugins.md#zenml.plugins.base_plugin_flavor.BasePluginConfig)

Allows configuring the action configuration.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore', 'frozen': False}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.actions.base_action.BaseActionFlavor

Bases: [`BasePluginFlavor`](zenml.plugins.md#zenml.plugins.base_plugin_flavor.BasePluginFlavor), `ABC`

Base Action Flavor to register Action Configurations.

#### ACTION_CONFIG_CLASS *: ClassVar[Type[[ActionConfig](#zenml.actions.base_action.ActionConfig)]]*

#### TYPE *: ClassVar[[PluginType](zenml.md#zenml.enums.PluginType)]* *= 'action'*

#### *classmethod* get_action_config_schema() → Dict[str, Any]

The config schema for a flavor.

Returns:
: The config schema.

#### *classmethod* get_flavor_response_model(hydrate: bool) → [ActionFlavorResponse](zenml.models.v2.core.md#zenml.models.v2.core.action_flavor.ActionFlavorResponse)

Convert the Flavor into a Response Model.

Args:
: hydrate: Whether the model should be hydrated.

Returns:
: The response model.

### *class* zenml.actions.base_action.BaseActionHandler(event_hub: [BaseEventHub](zenml.event_hub.md#zenml.event_hub.base_event_hub.BaseEventHub) | None = None)

Bases: [`BasePlugin`](zenml.plugins.md#zenml.plugins.base_plugin_flavor.BasePlugin), `ABC`

Implementation for an action handler.

#### *abstract property* config_class *: Type[[ActionConfig](#zenml.actions.base_action.ActionConfig)]*

Returns the BasePluginConfig config.

Returns:
: The configuration.

#### create_action(action: [ActionRequest](zenml.models.v2.core.md#zenml.models.v2.core.action.ActionRequest)) → [ActionResponse](zenml.models.v2.core.md#zenml.models.v2.core.action.ActionResponse)

Process a action request and create the action in the database.

Args:
: action: Action request.

Raises:
: Exception: If the implementation specific processing before creating
  : the action fails.

Returns:
: The created action.

#### delete_action(action: [ActionResponse](zenml.models.v2.core.md#zenml.models.v2.core.action.ActionResponse), force: bool = False) → None

Process action delete request and delete the action in the database.

Args:
: action: The action to delete.
  force: Whether to force delete the action from the database
  <br/>
  > even if the action handler fails to delete the event
  > source.

Raises:
: Exception: If the implementation specific processing before deleting
  : the action fails.

#### *property* event_hub *: [BaseEventHub](zenml.event_hub.md#zenml.event_hub.base_event_hub.BaseEventHub)*

Get the event hub used to dispatch events.

Returns:
: The event hub.

Raises:
: RuntimeError: if an event hub isn’t configured.

#### event_hub_callback(config: Dict[str, Any], trigger_execution: [TriggerExecutionResponse](zenml.models.v2.core.md#zenml.models.v2.core.trigger_execution.TriggerExecutionResponse), auth_context: [AuthContext](zenml.zen_server.md#zenml.zen_server.auth.AuthContext)) → None

Callback to be used by the event hub to dispatch events to the action handler.

Args:
: config: The action configuration
  trigger_execution: The trigger execution
  auth_context: Authentication context with an API token that can be
  <br/>
  > used by external workloads to authenticate with the server
  > during the execution of the action. This API token is associated
  > with the service account that was configured for the trigger
  > that activated the action and has a validity defined by the
  > trigger’s authentication window.

#### extract_resources(action_config: [ActionConfig](#zenml.actions.base_action.ActionConfig), hydrate: bool = False) → Dict[[ResourceType](zenml.zen_server.rbac.md#zenml.zen_server.rbac.models.ResourceType), [BaseResponse](zenml.models.v2.base.md#id248)[Any, Any, Any]]

Extract related resources for this action.

Args:
: action_config: Action configuration from which to extract related
  : resources.
  <br/>
  hydrate: Whether to hydrate the resource models.

Returns:
: List of resources related to the action.

#### *abstract property* flavor_class *: Type[[BaseActionFlavor](#zenml.actions.base_action.BaseActionFlavor)]*

Returns the flavor class of the plugin.

Returns:
: The flavor class of the plugin.

#### get_action(action: [ActionResponse](zenml.models.v2.core.md#zenml.models.v2.core.action.ActionResponse), hydrate: bool = False) → [ActionResponse](zenml.models.v2.core.md#zenml.models.v2.core.action.ActionResponse)

Process a action response before it is returned to the user.

Args:
: action: The action fetched from the database.
  hydrate: Whether to hydrate the action.

Returns:
: The action.

#### *abstract* run(config: [ActionConfig](#zenml.actions.base_action.ActionConfig), trigger_execution: [TriggerExecutionResponse](zenml.models.v2.core.md#zenml.models.v2.core.trigger_execution.TriggerExecutionResponse), auth_context: [AuthContext](zenml.zen_server.md#zenml.zen_server.auth.AuthContext)) → None

Execute an action.

Args:
: config: The action configuration
  trigger_execution: The trigger execution
  auth_context: Authentication context with an API token that can be
  <br/>
  > used by external workloads to authenticate with the server
  > during the execution of the action. This API token is associated
  > with the service account that was configured for the trigger
  > that activated the action and has a validity defined by the
  > trigger’s authentication window.

#### set_event_hub(event_hub: [BaseEventHub](zenml.event_hub.md#zenml.event_hub.base_event_hub.BaseEventHub)) → None

Configure an event hub for this event source plugin.

Args:
: event_hub: Event hub to be used by this event handler to dispatch
  : events.

#### update_action(action: [ActionResponse](zenml.models.v2.core.md#zenml.models.v2.core.action.ActionResponse), action_update: [ActionUpdate](zenml.models.v2.core.md#zenml.models.v2.core.action.ActionUpdate)) → [ActionResponse](zenml.models.v2.core.md#zenml.models.v2.core.action.ActionResponse)

Process action update and update the action in the database.

Args:
: action: The action to update.
  action_update: The update to be applied to the action.

Raises:
: Exception: If the implementation specific processing before updating
  : the action fails.

Returns:
: The updated action.

#### validate_action_configuration(action_config: Dict[str, Any]) → [ActionConfig](#zenml.actions.base_action.ActionConfig)

Validate and return the action configuration.

Args:
: action_config: The action configuration to validate.

Returns:
: The validated action configuration.

Raises:
: ValueError: if the configuration is invalid.

## Module contents

Actions allow configuring a given action for later execution.
