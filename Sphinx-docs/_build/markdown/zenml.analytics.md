# zenml.analytics package

## Submodules

## zenml.analytics.client module

The analytics client of ZenML.

### *class* zenml.analytics.client.Client(send: bool = True, timeout: int = 15)

Bases: `object`

The client class for ZenML analytics.

#### alias(user_id: UUID, previous_id: UUID) → Tuple[bool, str]

Method to alias user IDs.

Args:
: user_id: The user ID.
  previous_id: Previous ID for the alias.

Returns:
: Tuple (success flag, the original message).

#### group(user_id: UUID, group_id: UUID, traits: Dict[Any, Any] | None) → Tuple[bool, str]

Method to group users.

Args:
: user_id: The user ID.
  group_id: The group ID.
  traits: Traits to assign to the group.

Returns:
: Tuple (success flag, the original message).

#### identify(user_id: UUID, traits: Dict[Any, Any] | None) → Tuple[bool, str]

Method to identify a user with given traits.

Args:
: user_id: The user ID.
  traits: The traits for the identification process.

Returns:
: Tuple (success flag, the original message).

#### track(user_id: UUID, event: [AnalyticsEvent](#zenml.analytics.enums.AnalyticsEvent), properties: Dict[Any, Any] | None) → Tuple[bool, str]

Method to track events.

Args:
: user_id: The user ID.
  event: The type of the event.
  properties: Dict of additional properties for the event.

Returns:
: Tuple (success flag, the original message).

## zenml.analytics.context module

The analytics module of ZenML.

This module is based on the ‘analytics-python’ package created by Segment.
The base functionalities are adapted to work with the ZenML analytics server.

### *class* zenml.analytics.context.AnalyticsContext

Bases: `object`

Client class for ZenML Analytics v2.

#### alias(user_id: UUID, previous_id: UUID) → bool

Alias user IDs.

Args:
: user_id: The user ID.
  previous_id: Previous ID for the alias.

Returns:
: True if alias information was sent, False otherwise.

#### group(group_id: UUID, traits: Dict[str, Any] | None = None) → bool

Group the user.

Args:
: group_id: Group ID.
  traits: Traits of the group.

Returns:
: True if tracking information was sent, False otherwise.

#### identify(traits: Dict[str, Any] | None = None) → bool

Identify the user through segment.

Args:
: traits: Traits of the user.

Returns:
: True if tracking information was sent, False otherwise.

#### *property* in_server *: bool*

Flag to check whether the code is running in a ZenML server.

Returns:
: True if running in a server, False otherwise.

#### track(event: [AnalyticsEvent](#zenml.analytics.enums.AnalyticsEvent), properties: Dict[str, Any] | None = None) → bool

Track an event.

Args:
: event: Event to track.
  properties: Event properties.

Returns:
: True if tracking information was sent, False otherwise.

## zenml.analytics.enums module

Collection of analytics events for ZenML.

### *class* zenml.analytics.enums.AnalyticsEvent(value, names=None, \*, module=None, qualname=None, type=None, start=1, boundary=None)

Bases: `str`, `Enum`

Enum of events to track in segment.

#### BUILD_PIPELINE *= 'Pipeline built'*

#### CREATED_FLAVOR *= 'Flavor created'*

#### CREATED_MODEL *= 'Model created'*

#### CREATED_MODEL_VERSION *= 'Model Version created'*

#### CREATED_RUN_TEMPLATE *= 'Run template created'*

#### CREATED_SECRET *= 'Secret created'*

#### CREATED_SERVICE_ACCOUNT *= 'Service account created'*

#### CREATED_SERVICE_CONNECTOR *= 'Service connector created'*

#### CREATED_TAG *= 'Tag created'*

#### CREATED_TRIGGER *= 'Trigger created'*

#### CREATED_WORKSPACE *= 'Workspace created'*

#### CREATE_PIPELINE *= 'Pipeline created'*

#### DEPLOY_FULL_STACK *= 'Full stack deployed'*

#### DEPLOY_STACK *= 'Stack deployed'*

#### DEPLOY_STACK_COMPONENT *= 'Stack component deployed'*

#### DESTROY_STACK *= 'Stack destroyed'*

#### DESTROY_STACK_COMPONENT *= 'Stack component destroyed'*

#### DEVICE_VERIFIED *= 'Device verified'*

#### EXECUTED_RUN_TEMPLATE *= 'Run templated executed'*

#### GENERATE_TEMPLATE *= 'Template generated'*

#### MODEL_DEPLOYED *= 'Model deployed'*

#### OPT_IN_ANALYTICS *= 'Analytics opt-in'*

#### OPT_IN_OUT_EMAIL *= 'Response for Email prompt'*

#### OPT_OUT_ANALYTICS *= 'Analytics opt-out'*

#### REGISTERED_CODE_REPOSITORY *= 'Code repository registered'*

#### REGISTERED_STACK *= 'Stack registered'*

#### REGISTERED_STACK_COMPONENT *= 'Stack component registered'*

#### RUN_PIPELINE *= 'Pipeline run'*

#### RUN_PIPELINE_ENDED *= 'Pipeline run ended'*

#### RUN_STACK_RECIPE *= 'Stack recipe ran'*

#### RUN_ZENML_GO *= 'ZenML go'*

#### SERVER_SETTINGS_UPDATED *= 'Server Settings Updated'*

#### UPDATED_STACK *= 'Stack updated'*

#### UPDATED_TRIGGER *= 'Trigger updated'*

#### USER_ENRICHED *= 'User Enriched'*

#### ZENML_SERVER_DEPLOYED *= 'ZenML server deployed'*

#### ZENML_SERVER_DESTROYED *= 'ZenML server destroyed'*

## zenml.analytics.models module

Helper models for ZenML analytics.

### *class* zenml.analytics.models.AnalyticsTrackedModelMixin

Bases: `BaseModel`

Mixin for models that are tracked through analytics events.

Classes that have information tracked in analytics events can inherit
from this mixin and implement the abstract methods. The @track_method
decorator will detect function arguments and return values that inherit
from this class and will include the ANALYTICS_FIELDS attributes as
tracking metadata.

#### ANALYTICS_FIELDS *: ClassVar[List[str]]* *= []*

#### get_analytics_metadata() → Dict[str, Any]

Get the analytics metadata for the model.

Returns:
: Dict of analytics metadata.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

## zenml.analytics.request module

The ‘analytics’ module of ZenML.

This module is based on the ‘analytics-python’ package created by Segment.
The base functionalities are adapted to work with the ZenML analytics server.

### zenml.analytics.request.post(batch: List[str], timeout: int = 15) → Response

Post a batch of messages to the ZenML analytics server.

Args:
: batch: The messages to send.
  timeout: Timeout in seconds.

Returns:
: The response.

Raises:
: AnalyticsAPIError: If the post request has failed.

## zenml.analytics.utils module

Utility functions and classes for ZenML analytics.

### *exception* zenml.analytics.utils.AnalyticsAPIError(status: int, message: str)

Bases: `Exception`

Custom exception class for API-related errors.

### *class* zenml.analytics.utils.AnalyticsEncoder(\*, skipkeys=False, ensure_ascii=True, check_circular=True, allow_nan=True, sort_keys=False, indent=None, separators=None, default=None)

Bases: `JSONEncoder`

Helper encoder class for JSON serialization.

#### default(obj: Any) → Any

The default method to handle UUID and ‘AnalyticsEvent’ objects.

Args:
: obj: The object to encode.

Returns:
: The encoded object.

### *class* zenml.analytics.utils.analytics_disabler

Bases: `object`

Context manager which disables ZenML analytics.

### zenml.analytics.utils.email_opt_int(opted_in: bool, email: str | None, source: str) → None

Track the event of the users response to the email prompt, identify them.

Args:
: opted_in: Did the user decide to opt-in
  email: The email the user optionally provided
  source: Location when the user replied [“zenml go”, “zenml server”]

### zenml.analytics.utils.track_decorator(event: [AnalyticsEvent](#zenml.analytics.enums.AnalyticsEvent)) → Callable[[F], F]

Decorator to track event.

If the decorated function takes in a AnalyticsTrackedModelMixin object as
an argument or returns one, it will be called to track the event. The return
value takes precedence over the argument when determining which object is
called to track the event.

If the decorated function is a method of a class that inherits from
AnalyticsTrackerMixin, the parent object will be used to intermediate
tracking analytics.

Args:
: event: Event string to stamp with.

Returns:
: A decorator that applies the analytics tracking to a function.

### *class* zenml.analytics.utils.track_handler(event: [AnalyticsEvent](#zenml.analytics.enums.AnalyticsEvent), metadata: Dict[str, Any] | None = None)

Bases: `object`

Context handler to enable tracking the success status of an event.

## Module contents

The ‘analytics’ module of ZenML.

### zenml.analytics.alias(user_id: UUID, previous_id: UUID) → bool

Alias user IDs.

Args:
: user_id: The user ID.
  previous_id: Previous ID for the alias.

Returns:
: True if event is sent successfully, False is not.

### zenml.analytics.group(group_id: UUID, group_metadata: Dict[str, Any] | None = None) → bool

Attach metadata to a segment group.

Args:
: group_id: ID of the group.
  group_metadata: Metadata to attach to the group.

Returns:
: True if event is sent successfully, False if not.

### zenml.analytics.identify(metadata: Dict[str, Any] | None = None) → bool

Attach metadata to user directly.

Args:
: metadata: Dict of metadata to attach to the user.

Returns:
: True if event is sent successfully, False is not.

### zenml.analytics.track(event: [AnalyticsEvent](#zenml.analytics.enums.AnalyticsEvent), metadata: Dict[str, Any] | None = None) → bool

Track segment event if user opted-in.

Args:
: event: Name of event to track in segment.
  metadata: Dict of metadata to track.

Returns:
: True if event is sent successfully, False if not.
