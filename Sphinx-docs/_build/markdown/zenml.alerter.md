# zenml.alerter package

## Submodules

## zenml.alerter.base_alerter module

Base class for all ZenML alerters.

### *class* zenml.alerter.base_alerter.BaseAlerter(name: str, id: UUID, config: [StackComponentConfig](zenml.stack.md#zenml.stack.stack_component.StackComponentConfig), flavor: str, type: [StackComponentType](zenml.md#zenml.enums.StackComponentType), user: UUID | None, workspace: UUID, created: datetime, updated: datetime, labels: Dict[str, Any] | None = None, connector_requirements: [ServiceConnectorRequirements](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorRequirements) | None = None, connector: UUID | None = None, connector_resource_id: str | None = None, \*args: Any, \*\*kwargs: Any)

Bases: [`StackComponent`](zenml.stack.md#zenml.stack.stack_component.StackComponent), `ABC`

Base class for all ZenML alerters.

#### ask(question: str, params: [BaseAlerterStepParameters](#zenml.alerter.base_alerter.BaseAlerterStepParameters) | None = None) → bool

Post a message to a chat service and wait for approval.

This can be useful to easily get a human in the loop, e.g., when
deploying models.

Args:
: question: Question to ask (message to be posted).
  params: Optional parameters of this function.

Returns:
: bool: True if operation succeeded and was approved, else False.

#### *property* config *: [BaseAlerterConfig](#zenml.alerter.base_alerter.BaseAlerterConfig)*

Returns the BaseAlerterConfig config.

Returns:
: The configuration.

#### post(message: str, params: [BaseAlerterStepParameters](#zenml.alerter.base_alerter.BaseAlerterStepParameters) | None = None) → bool

Post a message to a chat service.

Args:
: message: Message to be posted.
  params: Optional parameters of this function.

Returns:
: bool: True if operation succeeded, else False.

### *class* zenml.alerter.base_alerter.BaseAlerterConfig(warn_about_plain_text_secrets: bool = False)

Bases: [`StackComponentConfig`](zenml.stack.md#zenml.stack.stack_component.StackComponentConfig)

Base config for alerters.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.alerter.base_alerter.BaseAlerterFlavor

Bases: [`Flavor`](zenml.stack.md#zenml.stack.flavor.Flavor), `ABC`

Base class for all ZenML alerter flavors.

#### *property* config_class *: Type[[BaseAlerterConfig](#zenml.alerter.base_alerter.BaseAlerterConfig)]*

Returns BaseAlerterConfig class.

Returns:
: The BaseAlerterConfig class.

#### *property* implementation_class *: Type[[BaseAlerter](#zenml.alerter.base_alerter.BaseAlerter)]*

Implementation class.

Returns:
: The implementation class.

#### *property* type *: [StackComponentType](zenml.md#zenml.enums.StackComponentType)*

Returns the flavor type.

Returns:
: The flavor type.

### *class* zenml.alerter.base_alerter.BaseAlerterStepParameters

Bases: `BaseModel`

Step parameters definition for all alerters.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

## Module contents

Alerters allow you to send alerts from within your pipeline.

This is useful to immediately get notified when failures happen,
and also for general monitoring / reporting.

### *class* zenml.alerter.BaseAlerter(name: str, id: UUID, config: [StackComponentConfig](zenml.stack.md#zenml.stack.stack_component.StackComponentConfig), flavor: str, type: [StackComponentType](zenml.md#zenml.enums.StackComponentType), user: UUID | None, workspace: UUID, created: datetime, updated: datetime, labels: Dict[str, Any] | None = None, connector_requirements: [ServiceConnectorRequirements](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorRequirements) | None = None, connector: UUID | None = None, connector_resource_id: str | None = None, \*args: Any, \*\*kwargs: Any)

Bases: [`StackComponent`](zenml.stack.md#zenml.stack.stack_component.StackComponent), `ABC`

Base class for all ZenML alerters.

#### ask(question: str, params: [BaseAlerterStepParameters](#zenml.alerter.base_alerter.BaseAlerterStepParameters) | None = None) → bool

Post a message to a chat service and wait for approval.

This can be useful to easily get a human in the loop, e.g., when
deploying models.

Args:
: question: Question to ask (message to be posted).
  params: Optional parameters of this function.

Returns:
: bool: True if operation succeeded and was approved, else False.

#### *property* config *: [BaseAlerterConfig](#zenml.alerter.base_alerter.BaseAlerterConfig)*

Returns the BaseAlerterConfig config.

Returns:
: The configuration.

#### post(message: str, params: [BaseAlerterStepParameters](#zenml.alerter.base_alerter.BaseAlerterStepParameters) | None = None) → bool

Post a message to a chat service.

Args:
: message: Message to be posted.
  params: Optional parameters of this function.

Returns:
: bool: True if operation succeeded, else False.

### *class* zenml.alerter.BaseAlerterConfig(warn_about_plain_text_secrets: bool = False)

Bases: [`StackComponentConfig`](zenml.stack.md#zenml.stack.stack_component.StackComponentConfig)

Base config for alerters.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.alerter.BaseAlerterFlavor

Bases: [`Flavor`](zenml.stack.md#zenml.stack.flavor.Flavor), `ABC`

Base class for all ZenML alerter flavors.

#### *property* config_class *: Type[[BaseAlerterConfig](#zenml.alerter.base_alerter.BaseAlerterConfig)]*

Returns BaseAlerterConfig class.

Returns:
: The BaseAlerterConfig class.

#### *property* implementation_class *: Type[[BaseAlerter](#zenml.alerter.base_alerter.BaseAlerter)]*

Implementation class.

Returns:
: The implementation class.

#### *property* type *: [StackComponentType](zenml.md#zenml.enums.StackComponentType)*

Returns the flavor type.

Returns:
: The flavor type.

### *class* zenml.alerter.BaseAlerterStepParameters

Bases: `BaseModel`

Step parameters definition for all alerters.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.
