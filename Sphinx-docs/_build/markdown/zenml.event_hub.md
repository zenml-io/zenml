# zenml.event_hub package

## Submodules

## zenml.event_hub.base_event_hub module

Base class for event hub implementations.

### *class* zenml.event_hub.base_event_hub.BaseEventHub

Bases: `ABC`

Base class for event hub implementations.

The event hub is responsible for relaying events from event sources to
action handlers. It functions similarly to a pub/sub system where
event source handlers publish events and action handlers subscribe to them.

The event hub also serves to decouple event sources from action handlers,
allowing them to be configured independently and their implementations to be
unaware of each other.

#### action_handlers *: Dict[Tuple[str, str], Callable[[Dict[str, Any], [TriggerExecutionResponse](zenml.models.v2.core.md#zenml.models.v2.core.trigger_execution.TriggerExecutionResponse), [AuthContext](zenml.zen_server.md#zenml.zen_server.auth.AuthContext)], None]]* *= {}*

#### *abstract* activate_trigger(trigger: [TriggerResponse](zenml.models.v2.core.md#zenml.models.v2.core.trigger.TriggerResponse)) → None

Add a trigger to the event hub.

Configure the event hub to trigger an action when an event is received.

Args:
: trigger: the trigger to activate.

#### *abstract* deactivate_trigger(trigger: [TriggerResponse](zenml.models.v2.core.md#zenml.models.v2.core.trigger.TriggerResponse)) → None

Remove a trigger from the event hub.

Configure the event hub to stop triggering an action when an event is
received.

Args:
: trigger: the trigger to deactivate.

#### *abstract* publish_event(event: [BaseEvent](zenml.event_sources.md#zenml.event_sources.base_event.BaseEvent), event_source: [EventSourceResponse](zenml.models.v2.core.md#zenml.models.v2.core.event_source.EventSourceResponse)) → None

Publish an event to the event hub.

Args:
: event: The event.
  event_source: The event source that produced the event.

#### subscribe_action_handler(action_flavor: str, action_subtype: str, callback: Callable[[Dict[str, Any], [TriggerExecutionResponse](zenml.models.v2.core.md#zenml.models.v2.core.trigger_execution.TriggerExecutionResponse), [AuthContext](zenml.zen_server.md#zenml.zen_server.auth.AuthContext)], None]) → None

Subscribe an action handler to the event hub.

Args:
: action_flavor: the flavor of the action to trigger.
  action_subtype: the subtype of the action to trigger.
  callback: the action to trigger when the trigger is activated.

#### trigger_action(event: [BaseEvent](zenml.event_sources.md#zenml.event_sources.base_event.BaseEvent), event_source: [EventSourceResponse](zenml.models.v2.core.md#zenml.models.v2.core.event_source.EventSourceResponse), trigger: [TriggerResponse](zenml.models.v2.core.md#zenml.models.v2.core.trigger.TriggerResponse), action_callback: Callable[[Dict[str, Any], [TriggerExecutionResponse](zenml.models.v2.core.md#zenml.models.v2.core.trigger_execution.TriggerExecutionResponse), [AuthContext](zenml.zen_server.md#zenml.zen_server.auth.AuthContext)], None]) → None

Trigger an action.

Args:
: event: The event.
  event_source: The event source that produced the event.
  trigger: The trigger that was activated.
  action_callback: The action to trigger.

#### unsubscribe_action_handler(action_flavor: str, action_subtype: str) → None

Unsubscribe an action handler from the event hub.

Args:
: action_flavor: the flavor of the action to trigger.
  action_subtype: the subtype of the action to trigger.

#### *property* zen_store *: [SqlZenStore](zenml.zen_stores.md#zenml.zen_stores.sql_zen_store.SqlZenStore)*

Returns the active zen store.

Returns:
: The active zen store.

Raises:
: ValueError: If the active zen store is not a SQL zen store.

## zenml.event_hub.event_hub module

Base class for all the Event Hub.

### *class* zenml.event_hub.event_hub.InternalEventHub

Bases: [`BaseEventHub`](#zenml.event_hub.base_event_hub.BaseEventHub)

Internal in-server event hub implementation.

The internal in-server event hub uses the database as a source of truth for
configured triggers and triggers actions by calling the action handlers
directly.

#### activate_trigger(trigger: [TriggerResponse](zenml.models.v2.core.md#zenml.models.v2.core.trigger.TriggerResponse)) → None

Add a trigger to the event hub.

Configure the event hub to trigger an action when an event is received.

Args:
: trigger: the trigger to activate.

#### deactivate_trigger(trigger: [TriggerResponse](zenml.models.v2.core.md#zenml.models.v2.core.trigger.TriggerResponse)) → None

Remove a trigger from the event hub.

Configure the event hub to stop triggering an action when an event is
received.

Args:
: trigger: the trigger to deactivate.

#### get_matching_active_triggers_for_event(event: [BaseEvent](zenml.event_sources.md#zenml.event_sources.base_event.BaseEvent), event_source: [EventSourceResponse](zenml.models.v2.core.md#zenml.models.v2.core.event_source.EventSourceResponse)) → List[[TriggerResponse](zenml.models.v2.core.md#zenml.models.v2.core.trigger.TriggerResponse)]

Get all triggers that match an incoming event.

Args:
: event: The inbound event.
  event_source: The event source which emitted the event.

Returns:
: The list of matching triggers.

#### publish_event(event: [BaseEvent](zenml.event_sources.md#zenml.event_sources.base_event.BaseEvent), event_source: [EventSourceResponse](zenml.models.v2.core.md#zenml.models.v2.core.event_source.EventSourceResponse)) → None

Process an incoming event and trigger all configured actions.

This will first check for any subscribers/triggers for this event,
then log the event for later reference and finally perform the
configured action(s).

Args:
: event: The event.
  event_source: The event source that produced the event.

## Module contents

ZenML Event Hub module.

The Event Hub is responsible for receiving all Events and dispatching them to
the relevant Subscribers/Triggers.
