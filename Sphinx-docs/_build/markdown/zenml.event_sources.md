# zenml.event_sources package

## Subpackages

* [zenml.event_sources.webhooks package](zenml.event_sources.webhooks.md)
  * [Submodules](zenml.event_sources.webhooks.md#submodules)
  * [zenml.event_sources.webhooks.base_webhook_event_source module](zenml.event_sources.webhooks.md#zenml-event-sources-webhooks-base-webhook-event-source-module)
  * [Module contents](zenml.event_sources.webhooks.md#module-zenml.event_sources.webhooks)

## Submodules

## zenml.event_sources.base_event module

Base implementation for events.

### *class* zenml.event_sources.base_event.BaseEvent

Bases: `BaseModel`

Base class for all inbound events.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

## zenml.event_sources.base_event_source module

Base implementation for event sources.

### *class* zenml.event_sources.base_event_source.BaseEventSourceFlavor

Bases: [`BasePluginFlavor`](zenml.plugins.md#zenml.plugins.base_plugin_flavor.BasePluginFlavor), `ABC`

Base Event Plugin Flavor to access an event plugin along with its configurations.

#### EVENT_FILTER_CONFIG_CLASS *: ClassVar[Type[[EventFilterConfig](#zenml.event_sources.base_event_source.EventFilterConfig)]]*

#### EVENT_SOURCE_CONFIG_CLASS *: ClassVar[Type[[EventSourceConfig](#zenml.event_sources.base_event_source.EventSourceConfig)]]*

#### TYPE *: ClassVar[[PluginType](zenml.md#zenml.enums.PluginType)]* *= 'event_source'*

#### *classmethod* get_event_filter_config_schema() → Dict[str, Any]

The config schema for a flavor.

Returns:
: The config schema.

#### *classmethod* get_event_source_config_schema() → Dict[str, Any]

The config schema for a flavor.

Returns:
: The config schema.

#### *classmethod* get_flavor_response_model(hydrate: bool) → [EventSourceFlavorResponse](zenml.models.v2.core.md#zenml.models.v2.core.event_source_flavor.EventSourceFlavorResponse)

Convert the Flavor into a Response Model.

Args:
: hydrate: Whether the model should be hydrated.

Returns:
: The Flavor Response model for the Event Source implementation

### *class* zenml.event_sources.base_event_source.BaseEventSourceHandler(event_hub: [BaseEventHub](zenml.event_hub.md#zenml.event_hub.base_event_hub.BaseEventHub) | None = None)

Bases: [`BasePlugin`](zenml.plugins.md#zenml.plugins.base_plugin_flavor.BasePlugin), `ABC`

Base event source handler implementation.

This class provides a base implementation for event source handlers.

The base event source handler acts as an intermediary between the REST API
endpoints and the ZenML store for all operations related to event sources.
It implements all operations related creating, updating, deleting, and
fetching event sources from the database. It also provides a set of methods
that can be overridden by concrete event source handlers that need to
react to or participate in the lifecycle of an event source:

* \_validate_event_source_request: validate and/or modify an event source

before it is created (before it is persisted in the database)
\* \_process_event_source_request: react to a new event source being created
(after it is persisted in the database)
\* \_validate_event_source_update: validate and/or modify an event source
update before it is applied (before the update is saved in the database)
\* \_process_event_source_update: react to an event source being updated
(after the update is saved in the database)
\* \_process_event_source_delete: react to an event source being deleted
(before it is deleted from the database)
\* \_process_event_source_response: modify an event source before it is
returned to the user

In addition to optionally overriding these methods, every event source
handler must define and provide configuration classes for the event source
and the event filter. These are used to validate and instantiate the
configuration from the user requests.

Finally, since event source handlers are also sources of events, the base
class provides methods that implementations can use to dispatch events to
the central event hub where they can be processed and eventually trigger
actions.

#### *abstract property* config_class *: Type[[EventSourceConfig](#zenml.event_sources.base_event_source.EventSourceConfig)]*

Returns the event source configuration class.

Returns:
: The configuration.

#### create_event_source(event_source: [EventSourceRequest](zenml.models.v2.core.md#zenml.models.v2.core.event_source.EventSourceRequest)) → [EventSourceResponse](zenml.models.v2.core.md#zenml.models.v2.core.event_source.EventSourceResponse)

Process an event source request and create the event source in the database.

Args:
: event_source: Event source request.

Returns:
: The created event source.

# noqa: DAR401

#### delete_event_source(event_source: [EventSourceResponse](zenml.models.v2.core.md#zenml.models.v2.core.event_source.EventSourceResponse), force: bool = False) → None

Process an event source delete request and delete the event source in the database.

Args:
: event_source: The event source to delete.
  force: Whether to force delete the event source from the database
  <br/>
  > even if the event source handler fails to delete the event
  > source.

# noqa: DAR401

#### dispatch_event(event: [BaseEvent](#zenml.event_sources.base_event.BaseEvent), event_source: [EventSourceResponse](zenml.models.v2.core.md#zenml.models.v2.core.event_source.EventSourceResponse)) → None

Dispatch an event to all active triggers that match the event.

Args:
: event: The event to dispatch.
  event_source: The event source that produced the event.

#### *property* event_hub *: [BaseEventHub](zenml.event_hub.md#zenml.event_hub.base_event_hub.BaseEventHub)*

Get the event hub used to dispatch events.

Returns:
: The event hub.

Raises:
: RuntimeError: if an event hub isn’t configured.

#### *abstract property* filter_class *: Type[[EventFilterConfig](#zenml.event_sources.base_event_source.EventFilterConfig)]*

Returns the event filter configuration class.

Returns:
: The event filter configuration class.

#### *abstract property* flavor_class *: Type[[BaseEventSourceFlavor](#zenml.event_sources.base_event_source.BaseEventSourceFlavor)]*

Returns the flavor class of the plugin.

Returns:
: The flavor class of the plugin.

#### get_event_source(event_source: [EventSourceResponse](zenml.models.v2.core.md#zenml.models.v2.core.event_source.EventSourceResponse), hydrate: bool = False) → [EventSourceResponse](zenml.models.v2.core.md#zenml.models.v2.core.event_source.EventSourceResponse)

Process an event source response before it is returned to the user.

Args:
: event_source: The event source fetched from the database.
  hydrate: Whether to hydrate the event source.

Returns:
: The event source.

#### set_event_hub(event_hub: [BaseEventHub](zenml.event_hub.md#zenml.event_hub.base_event_hub.BaseEventHub)) → None

Configure an event hub for this event source plugin.

Args:
: event_hub: Event hub to be used by this event handler to dispatch
  : events.

#### update_event_source(event_source: [EventSourceResponse](zenml.models.v2.core.md#zenml.models.v2.core.event_source.EventSourceResponse), event_source_update: [EventSourceUpdate](zenml.models.v2.core.md#zenml.models.v2.core.event_source.EventSourceUpdate)) → [EventSourceResponse](zenml.models.v2.core.md#zenml.models.v2.core.event_source.EventSourceResponse)

Process an event source update request and update the event source in the database.

Args:
: event_source: The event source to update.
  event_source_update: The update to be applied to the event source.

Returns:
: The updated event source.

# noqa: DAR401

#### validate_event_filter_configuration(configuration: Dict[str, Any]) → [EventFilterConfig](#zenml.event_sources.base_event_source.EventFilterConfig)

Validate and return the configuration of an event filter.

Args:
: configuration: The configuration to validate.

Returns:
: Instantiated event filter config.

Raises:
: ValueError: if the configuration is invalid.

#### validate_event_source_configuration(event_source_config: Dict[str, Any]) → [EventSourceConfig](#zenml.event_sources.base_event_source.EventSourceConfig)

Validate and return the event source configuration.

Args:
: event_source_config: The event source configuration to validate.

Returns:
: The validated event source configuration.

Raises:
: ValueError: if the configuration is invalid.

### *class* zenml.event_sources.base_event_source.EventFilterConfig

Bases: `BaseModel`, `ABC`

The Event Filter configuration.

#### *abstract* event_matches_filter(event: [BaseEvent](#zenml.event_sources.base_event.BaseEvent)) → bool

All implementations need to implement this check.

If the filter matches the inbound event instance, this should
return True, else False.

Args:
: event: The inbound event instance.

Returns:
: Whether the filter matches the event.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.event_sources.base_event_source.EventSourceConfig

Bases: [`BasePluginConfig`](zenml.plugins.md#zenml.plugins.base_plugin_flavor.BasePluginConfig)

The Event Source configuration.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore', 'frozen': False}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

## Module contents

Base Classes for Event Sources.
