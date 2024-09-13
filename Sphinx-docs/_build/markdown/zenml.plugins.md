# zenml.plugins package

## Submodules

## zenml.plugins.base_plugin_flavor module

Base implementation for all Plugin Flavors.

### *class* zenml.plugins.base_plugin_flavor.BasePlugin

Bases: `ABC`

Base Class for all Plugins.

#### *abstract property* config_class *: Type[[BasePluginConfig](#zenml.plugins.base_plugin_flavor.BasePluginConfig)]*

Returns the BasePluginConfig config.

Returns:
: The configuration.

#### *abstract property* flavor_class *: Type[[BasePluginFlavor](#zenml.plugins.base_plugin_flavor.BasePluginFlavor)]*

Returns the flavor class of the plugin.

Returns:
: The flavor class of the plugin.

#### *property* zen_store *: [BaseZenStore](zenml.zen_stores.md#zenml.zen_stores.base_zen_store.BaseZenStore)*

Returns the active zen store.

Returns:
: The active zen store.

### *class* zenml.plugins.base_plugin_flavor.BasePluginConfig

Bases: `BaseModel`, `ABC`

Allows configuring of Event Source and Filter configuration.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore', 'frozen': False}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.plugins.base_plugin_flavor.BasePluginFlavor

Bases: `ABC`

Base Class for all PluginFlavors.

#### FLAVOR *: ClassVar[str]*

#### PLUGIN_CLASS *: ClassVar[Type[[BasePlugin](#zenml.plugins.base_plugin_flavor.BasePlugin)]]*

#### SUBTYPE *: ClassVar[[PluginSubType](zenml.md#zenml.enums.PluginSubType)]*

#### TYPE *: ClassVar[[PluginType](zenml.md#zenml.enums.PluginType)]*

#### *abstract classmethod* get_flavor_response_model(hydrate: bool) → [BasePluginFlavorResponse](zenml.models.v2.base.md#id272)[Any, Any, Any]

Convert the Flavor into a Response Model.

Args:
: hydrate: Whether the model should be hydrated.

## zenml.plugins.plugin_flavor_registry module

Registry for all plugins.

### *class* zenml.plugins.plugin_flavor_registry.PluginFlavorRegistry

Bases: `object`

Registry for plugin flavors.

#### get_flavor_class(\_type: [PluginType](zenml.md#zenml.enums.PluginType), subtype: [PluginSubType](zenml.md#zenml.enums.PluginSubType), name: str) → Type[[BasePluginFlavor](#zenml.plugins.base_plugin_flavor.BasePluginFlavor)]

Get a single event_source based on the key.

Args:
: \_type: The type of plugin.
  subtype: The subtype of plugin.
  name: Indicates the name of the plugin flavor.

Returns:
: BaseEventConfiguration subclass that was registered for this key.

Raises:
: KeyError: If there is no entry at this type, subtype, flavor

#### get_plugin(\_type: [PluginType](zenml.md#zenml.enums.PluginType), subtype: [PluginSubType](zenml.md#zenml.enums.PluginSubType), name: str) → [BasePlugin](#zenml.plugins.base_plugin_flavor.BasePlugin)

Get the plugin based on the flavor, type and subtype.

Args:
: name: The name of the plugin flavor.
  \_type: The type of plugin.
  subtype: The subtype of plugin.

Returns:
: Plugin instance associated with the flavor, type and subtype.

Raises:
: KeyError: If no plugin is found for the given flavor, type and
  : subtype.
  <br/>
  RuntimeError: If the plugin was not initialized.

#### initialize_plugins() → None

Initializes all registered plugins.

#### list_available_flavor_responses_for_type_and_subtype(\_type: [PluginType](zenml.md#zenml.enums.PluginType), subtype: [PluginSubType](zenml.md#zenml.enums.PluginSubType), page: int, size: int, hydrate: bool = False) → [Page](zenml.models.v2.base.md#id327)[[BasePluginFlavorResponse](zenml.models.md#zenml.models.BasePluginFlavorResponse)[Any, Any, Any]]

Get a list of all subtypes for a specific flavor and type.

Args:
: \_type: The type of Plugin
  subtype: The subtype of the plugin
  page: Page for pagination (offset +1)
  size: Page size for pagination
  hydrate: Whether to hydrate the response bodies

Returns:
: A page of flavors.

Raises:
: ValueError: If the page is out of range.

#### list_available_flavors_for_type_and_subtype(\_type: [PluginType](zenml.md#zenml.enums.PluginType), subtype: [PluginSubType](zenml.md#zenml.enums.PluginSubType)) → List[Type[[BasePluginFlavor](#zenml.plugins.base_plugin_flavor.BasePluginFlavor)]]

Get a list of all subtypes for a specific flavor and type.

Args:
: \_type: The type of Plugin
  subtype: The subtype of the plugin

Returns:
: List of flavors for the given type/subtype combination.

#### list_subtypes_within_type(\_type: [PluginType](zenml.md#zenml.enums.PluginType)) → List[[PluginSubType](zenml.md#zenml.enums.PluginSubType)]

Returns all available subtypes for a given type.

Args:
: \_type: The type of plugin

Returns:
: A list of available plugin subtypes for this plugin type.

#### register_plugin_flavor(flavor_class: Type[[BasePluginFlavor](#zenml.plugins.base_plugin_flavor.BasePluginFlavor)]) → None

Registers a new event_source.

Args:
: flavor_class: The flavor to register

#### register_plugin_flavors() → None

Registers all flavors.

### *class* zenml.plugins.plugin_flavor_registry.RegistryEntry(\*, flavor_class: Type[[BasePluginFlavor](#zenml.plugins.base_plugin_flavor.BasePluginFlavor)], plugin_instance: [BasePlugin](#zenml.plugins.base_plugin_flavor.BasePlugin) | None = None)

Bases: `BaseModel`

Registry Entry Class for the Plugin Registry.

#### flavor_class *: Type[[BasePluginFlavor](#zenml.plugins.base_plugin_flavor.BasePluginFlavor)]*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'arbitrary_types_allowed': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'flavor_class': FieldInfo(annotation=Type[BasePluginFlavor], required=True), 'plugin_instance': FieldInfo(annotation=Union[BasePlugin, NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### plugin_instance *: [BasePlugin](#zenml.plugins.base_plugin_flavor.BasePlugin) | None*

## Module contents
