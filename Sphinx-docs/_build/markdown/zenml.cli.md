# zenml.cli package

## Submodules

## zenml.cli.annotator module

Functionality for annotator CLI subcommands.

### zenml.cli.annotator.register_annotator_subcommands() → None

Registers CLI subcommands for the annotator.

## zenml.cli.artifact module

CLI functionality to interact with artifacts.

## zenml.cli.authorized_device module

CLI functionality to interact with authorized devices.

## zenml.cli.base module

Base functionality for the CLI.

### *class* zenml.cli.base.ZenMLProjectTemplateLocation(\*, github_url: str, github_tag: str)

Bases: `BaseModel`

A ZenML project template location.

#### *property* copier_github_url *: str*

Get the GitHub URL for the copier.

Returns:
: A GitHub URL in copier format.

#### github_tag *: str*

#### github_url *: str*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'github_tag': FieldInfo(annotation=str, required=True), 'github_url': FieldInfo(annotation=str, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

## zenml.cli.cli module

Core CLI functionality.

### *class* zenml.cli.cli.TagGroup(name: str | None = None, tag: [CliCategories](zenml.md#zenml.enums.CliCategories) | None = None, commands: Dict[str, Command] | Sequence[Command] | None = None, \*\*kwargs: Dict[str, Any])

Bases: `Group`

Override the default click Group to add a tag.

The tag is used to group commands and groups of
commands in the help output.

### *class* zenml.cli.cli.ZenContext(command: Command, parent: Context | None = None, info_name: str | None = None, obj: Any | None = None, auto_envvar_prefix: str | None = None, default_map: Dict[str, Any] | None = None, terminal_width: int | None = None, max_content_width: int | None = None, resilient_parsing: bool = False, allow_extra_args: bool | None = None, allow_interspersed_args: bool | None = None, ignore_unknown_options: bool | None = None, help_option_names: List[str] | None = None, token_normalize_func: Callable[[str], str] | None = None, color: bool | None = None, show_default: bool | None = None)

Bases: `Context`

Override the default click Context to add the new Formatter.

#### formatter_class

alias of [`ZenFormatter`](#zenml.cli.formatter.ZenFormatter)

### *class* zenml.cli.cli.ZenMLCLI(name: str | None = None, commands: Dict[str, Command] | Sequence[Command] | None = None, \*\*attrs: Any)

Bases: `Group`

Custom click Group to create a custom format command help output.

#### context_class

alias of [`ZenContext`](#zenml.cli.cli.ZenContext)

#### format_commands(ctx: Context, formatter: HelpFormatter) → None

Multi methods that adds all the commands after the options.

This custom format_commands method is used to retrieve the commands and
groups of commands with a tag. In order to call the new custom format
method, the command must be added to the ZenML CLI class.

Args:
: ctx: The click context.
  formatter: The click formatter.

#### get_help(ctx: Context) → str

Formats the help into a string and returns it.

Calls `format_help()` internally.

Args:
: ctx: The click context.

Returns:
: The formatted help string.

## zenml.cli.code_repository module

CLI functionality to interact with code repositories.

## zenml.cli.config module

CLI for manipulating ZenML local and global config file.

## zenml.cli.downgrade module

CLI command to downgrade the ZenML Global Configuration version.

## zenml.cli.feature module

Functionality to generate stack component CLI commands.

### zenml.cli.feature.register_feature_store_subcommands() → None

Registers CLI subcommands for the Feature Store.

## zenml.cli.formatter module

Helper functions to format output for CLI.

### *class* zenml.cli.formatter.ZenFormatter(indent_increment: int = 2, width: int | None = None, max_width: int | None = None)

Bases: `HelpFormatter`

Override the default HelpFormatter to add a custom format for the help command output.

#### write_dl(rows: Sequence[Tuple[str, ...]], col_max: int = 30, col_spacing: int = 2) → None

Writes a definition list into the buffer.

This is how options and commands are usually formatted.

Arguments:
: rows: a list of items as tuples for the terms and values.
  col_max: the maximum width of the first column.
  col_spacing: the number of spaces between the first and
  <br/>
  > second column (and third).

The default behavior is to format the rows in a definition list
with rows of 2 columns following the format `(term, value)`.
But for new CLI commands, we want to format the rows in a definition
list with rows of 3 columns following the format
`(term, value, description)`.

Raises:
: TypeError: if the number of columns is not 2 or 3.

### zenml.cli.formatter.iter_rows(rows: Iterable[Tuple[str, ...]], col_count: int) → Iterator[Tuple[str, ...]]

Iterate over rows of a table.

Args:
: rows: The rows of the table.
  col_count: The number of columns in the table.

Yields:
: An iterator over the rows of the table.

### zenml.cli.formatter.measure_table(rows: Iterable[Tuple[str, ...]]) → Tuple[int, ...]

Measure the width of each column in a table.

Args:
: rows: The rows of the table.

Returns:
: A tuple of the width of each column.

## zenml.cli.integration module

Functionality to install or uninstall ZenML integrations via the CLI.

## zenml.cli.model module

CLI functionality to interact with Model Control Plane.

## zenml.cli.model_registry module

Functionality for model deployer CLI subcommands.

### zenml.cli.model_registry.register_model_registry_subcommands() → None

Registers CLI subcommands for the Model Registry.

## zenml.cli.pipeline module

CLI functionality to interact with pipelines.

## zenml.cli.secret module

Functionality to generate stack component CLI commands.

## zenml.cli.served_model module

Functionality for model-deployer CLI subcommands.

### zenml.cli.served_model.register_model_deployer_subcommands() → None

Registers CLI subcommands for the Model Deployer.

## zenml.cli.server module

CLI for managing ZenML server deployments.

## zenml.cli.service_accounts module

CLI functionality to interact with API keys.

## zenml.cli.service_connectors module

Service connector CLI commands.

### zenml.cli.service_connectors.prompt_connector_name(default_name: str | None = None, connector: UUID | None = None) → str

Prompt the user for a service connector name.

Args:
: default_name: The default name to use if the user doesn’t provide one.
  connector: The UUID of a service connector being renamed.

Returns:
: The name provided by the user.

### zenml.cli.service_connectors.prompt_expiration_time(min: int | None = None, max: int | None = None, default: int | None = None) → int

Prompt the user for an expiration time.

Args:
: min: The minimum allowed expiration time.
  max: The maximum allowed expiration time.
  default: The default expiration time.

Returns:
: The expiration time provided by the user.

### zenml.cli.service_connectors.prompt_expires_at(default: datetime | None = None) → datetime | None

Prompt the user for an expiration timestamp.

Args:
: default: The default expiration time.

Returns:
: The expiration time provided by the user.

### zenml.cli.service_connectors.prompt_resource_id(resource_name: str, resource_ids: List[str]) → str | None

Prompt the user for a resource ID.

Args:
: resource_name: The name of the resource.
  resource_ids: The list of available resource IDs.

Returns:
: The resource ID provided by the user.

### zenml.cli.service_connectors.prompt_resource_type(available_resource_types: List[str]) → str | None

Prompt the user for a resource type.

Args:
: available_resource_types: The list of available resource types.

Returns:
: The resource type provided by the user.

## zenml.cli.stack module

CLI for manipulating ZenML local and global config file.

### zenml.cli.stack.validate_name(ctx: Context, param: str, value: str) → str

Validate the name of the stack.

Args:
: ctx: The click context.
  param: The parameter name.
  value: The value of the parameter.

Returns:
: The validated value.

Raises:
: BadParameter: If the name is invalid.

## zenml.cli.stack_components module

Functionality to generate stack component CLI commands.

### zenml.cli.stack_components.connect_stack_component_with_service_connector(component_type: [StackComponentType](zenml.md#zenml.enums.StackComponentType), name_id_or_prefix: str | None = None, connector: str | None = None, resource_id: str | None = None, interactive: bool = False, no_verify: bool = False) → None

Connect the stack component to a resource through a service connector.

Args:
: component_type: Type of the component to generate the command for.
  name_id_or_prefix: The name of the stack component to connect.
  connector: The name, ID or prefix of the connector to use.
  resource_id: The resource ID to use connect to. Only
  <br/>
  > required for multi-instance connectors that are not already
  > configured with a particular resource ID.
  <br/>
  interactive: Configure a service connector resource interactively.
  no_verify: Do not verify whether the resource is accessible.

### zenml.cli.stack_components.generate_stack_component_connect_command(component_type: [StackComponentType](zenml.md#zenml.enums.StackComponentType)) → Callable[[str, str], None]

Generates a connect command for the specific stack component type.

Args:
: component_type: Type of the component to generate the command for.

Returns:
: A function that can be used as a click command.

### zenml.cli.stack_components.generate_stack_component_copy_command(component_type: [StackComponentType](zenml.md#zenml.enums.StackComponentType)) → Callable[[str, str], None]

Generates a copy command for the specific stack component type.

Args:
: component_type: Type of the component to generate the command for.

Returns:
: A function that can be used as a click command.

### zenml.cli.stack_components.generate_stack_component_delete_command(component_type: [StackComponentType](zenml.md#zenml.enums.StackComponentType)) → Callable[[str], None]

Generates a delete command for the specific stack component type.

Args:
: component_type: Type of the component to generate the command for.

Returns:
: A function that can be used as a click command.

### zenml.cli.stack_components.generate_stack_component_deploy_command(component_type: [StackComponentType](zenml.md#zenml.enums.StackComponentType)) → Callable[[str, str, str, str, bool, List[str] | None, List[str]], None]

Generates a deploy command for the stack component type.

Args:
: component_type: Type of the component to generate the command for.

Returns:
: A function that can be used as a click command.

### zenml.cli.stack_components.generate_stack_component_describe_command(component_type: [StackComponentType](zenml.md#zenml.enums.StackComponentType)) → Callable[[str], None]

Generates a describe command for the specific stack component type.

Args:
: component_type: Type of the component to generate the command for.

Returns:
: A function that can be used as a click command.

### zenml.cli.stack_components.generate_stack_component_destroy_command(component_type: [StackComponentType](zenml.md#zenml.enums.StackComponentType)) → Callable[[str, str, bool], None]

Generates a destroy command for the stack component type.

Args:
: component_type: Type of the component to generate the command for.

Returns:
: A function that can be used as a click command.

### zenml.cli.stack_components.generate_stack_component_disconnect_command(component_type: [StackComponentType](zenml.md#zenml.enums.StackComponentType)) → Callable[[str], None]

Generates a disconnect command for the specific stack component type.

Args:
: component_type: Type of the component to generate the command for.

Returns:
: A function that can be used as a click command.

### zenml.cli.stack_components.generate_stack_component_down_command(component_type: [StackComponentType](zenml.md#zenml.enums.StackComponentType)) → Callable[[str, bool], None]

Generates a down command for the specific stack component type.

Args:
: component_type: Type of the component to generate the command for.

Returns:
: A function that can be used as a click command.

### zenml.cli.stack_components.generate_stack_component_explain_command(component_type: [StackComponentType](zenml.md#zenml.enums.StackComponentType)) → Callable[[], None]

Generates an explain command for the specific stack component type.

Args:
: component_type: Type of the component to generate the command for.

Returns:
: A function that can be used as a click command.

### zenml.cli.stack_components.generate_stack_component_flavor_delete_command(component_type: [StackComponentType](zenml.md#zenml.enums.StackComponentType)) → Callable[[str], None]

Generates a delete command for a single flavor of a component.

Args:
: component_type: Type of the component to generate the command for.

Returns:
: A function that can be used as a click command.

### zenml.cli.stack_components.generate_stack_component_flavor_describe_command(component_type: [StackComponentType](zenml.md#zenml.enums.StackComponentType)) → Callable[[str], None]

Generates a describe command for a single flavor of a component.

Args:
: component_type: Type of the component to generate the command for.

Returns:
: A function that can be used as a click command.

### zenml.cli.stack_components.generate_stack_component_flavor_list_command(component_type: [StackComponentType](zenml.md#zenml.enums.StackComponentType)) → Callable[[], None]

Generates a list command for the flavors of a stack component.

Args:
: component_type: Type of the component to generate the command for.

Returns:
: A function that can be used as a click command.

### zenml.cli.stack_components.generate_stack_component_flavor_register_command(component_type: [StackComponentType](zenml.md#zenml.enums.StackComponentType)) → Callable[[str], None]

Generates a register command for the flavors of a stack component.

Args:
: component_type: Type of the component to generate the command for.

Returns:
: A function that can be used as a click command.

### zenml.cli.stack_components.generate_stack_component_get_command(component_type: [StackComponentType](zenml.md#zenml.enums.StackComponentType)) → Callable[[], None]

Generates a get command for the specific stack component type.

Args:
: component_type: Type of the component to generate the command for.

Returns:
: A function that can be used as a click command.

### zenml.cli.stack_components.generate_stack_component_list_command(component_type: [StackComponentType](zenml.md#zenml.enums.StackComponentType)) → Callable[[...], None]

Generates a list command for the specific stack component type.

Args:
: component_type: Type of the component to generate the command for.

Returns:
: A function that can be used as a click command.

### zenml.cli.stack_components.generate_stack_component_logs_command(component_type: [StackComponentType](zenml.md#zenml.enums.StackComponentType)) → Callable[[str, bool], None]

Generates a logs command for the specific stack component type.

Args:
: component_type: Type of the component to generate the command for.

Returns:
: A function that can be used as a click command.

### zenml.cli.stack_components.generate_stack_component_register_command(component_type: [StackComponentType](zenml.md#zenml.enums.StackComponentType)) → Callable[[str, str, List[str]], None]

Generates a register command for the specific stack component type.

Args:
: component_type: Type of the component to generate the command for.

Returns:
: A function that can be used as a click command.

### zenml.cli.stack_components.generate_stack_component_remove_attribute_command(component_type: [StackComponentType](zenml.md#zenml.enums.StackComponentType)) → Callable[[str, List[str]], None]

Generates remove_attribute command for a specific stack component type.

Args:
: component_type: Type of the component to generate the command for.

Returns:
: A function that can be used as a click command.

### zenml.cli.stack_components.generate_stack_component_rename_command(component_type: [StackComponentType](zenml.md#zenml.enums.StackComponentType)) → Callable[[str, str], None]

Generates a rename command for the specific stack component type.

Args:
: component_type: Type of the component to generate the command for.

Returns:
: A function that can be used as a click command.

### zenml.cli.stack_components.generate_stack_component_up_command(component_type: [StackComponentType](zenml.md#zenml.enums.StackComponentType)) → Callable[[str], None]

Generates a up command for the specific stack component type.

Args:
: component_type: Type of the component to generate the command for.

Returns:
: A function that can be used as a click command.

### zenml.cli.stack_components.generate_stack_component_update_command(component_type: [StackComponentType](zenml.md#zenml.enums.StackComponentType)) → Callable[[str, List[str]], None]

Generates an update command for the specific stack component type.

Args:
: component_type: Type of the component to generate the command for.

Returns:
: A function that can be used as a click command.

### zenml.cli.stack_components.prompt_select_resource(resource_list: List[[ServiceConnectorResourcesModel](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorResourcesModel)]) → Tuple[UUID, str]

Prompts the user to select a resource ID from a list of resources.

Args:
: resource_list: List of resources to select from.

Returns:
: The ID of a selected connector and the ID of the selected resource
  instance.

### zenml.cli.stack_components.prompt_select_resource_id(resource_ids: List[str], resource_name: str, interactive: bool = True) → str

Prompts the user to select a resource ID from a list of available IDs.

Args:
: resource_ids: A list of available resource IDs.
  resource_name: The name of the resource type to select.
  interactive: Whether to prompt the user for input or error out if
  <br/>
  > user input is required.

Returns:
: The selected resource ID.

### zenml.cli.stack_components.register_all_stack_component_cli_commands() → None

Registers CLI commands for all stack components.

### zenml.cli.stack_components.register_single_stack_component_cli_commands(component_type: [StackComponentType](zenml.md#zenml.enums.StackComponentType), parent_group: Group) → None

Registers all basic stack component CLI commands.

Args:
: component_type: Type of the component to generate the command for.
  parent_group: The parent group to register the commands to.

## zenml.cli.stack_recipes module

Functionality to handle downloading ZenML stacks via the CLI.

## zenml.cli.tag module

CLI functionality to interact with tags.

## zenml.cli.text_utils module

Utilities for CLI output.

### *class* zenml.cli.text_utils.OldSchoolMarkdownHeading(tag: str)

Bases: `Heading`

A traditional markdown heading.

### zenml.cli.text_utils.zenml_go_notebook_tutorial_message(ipynb_files: List[str]) → Markdown

Outputs a message to the user about the zenml go tutorial.

Args:
: ipynb_files: A list of IPython Notebook files.

Returns:
: A Markdown object.

## zenml.cli.user_management module

Functionality to administer users of the ZenML CLI and server.

## zenml.cli.utils module

Utility functions for the CLI.

### zenml.cli.utils.confirmation(text: str, \*args: Any, \*\*kwargs: Any) → bool

Echo a confirmation string on the CLI.

Args:
: text: Input text string.
  <br/>
  ```
  *
  ```
  <br/>
  args: Args to be passed to click.confirm().
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Kwargs to be passed to click.confirm().

Returns:
: Boolean based on user response.

### zenml.cli.utils.convert_structured_str_to_dict(string: str) → Dict[str, str]

Convert a structured string (JSON or YAML) into a dict.

Examples:
: ```pycon
  >>> convert_structured_str_to_dict('{"location": "Nevada", "aliens":"many"}')
  {'location': 'Nevada', 'aliens': 'many'}
  >>> convert_structured_str_to_dict('location: Nevada \naliens: many')
  {'location': 'Nevada', 'aliens': 'many'}
  >>> convert_structured_str_to_dict("{'location': 'Nevada', 'aliens': 'many'}")
  {'location': 'Nevada', 'aliens': 'many'}
  ```

Args:
: string: JSON or YAML string value

Returns:
: ```
  dict_
  ```
  <br/>
  : dict from structured JSON or YAML str

### zenml.cli.utils.create_data_type_help_text(filter_model: Type[[BaseFilter](zenml.models.v2.base.md#zenml.models.v2.base.filter.BaseFilter)], field: str) → str

Create a general help text for a fields datatype.

Args:
: filter_model: The filter model to use
  field: The field within that filter model

Returns:
: The help text.

### zenml.cli.utils.create_filter_help_text(filter_model: Type[[BaseFilter](zenml.models.v2.base.md#zenml.models.v2.base.filter.BaseFilter)], field: str) → str

Create the help text used in the click option help text.

Args:
: filter_model: The filter model to use
  field: The field within that filter model

Returns:
: The help text.

### zenml.cli.utils.declare(text: str | Text, bold: bool | None = None, italic: bool | None = None, \*\*kwargs: Any) → None

Echo a declaration on the CLI.

Args:
: text: Input text string.
  bold: Optional boolean to bold the text.
  italic: Optional boolean to italicize the text.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Optional kwargs to be passed to console.print().

### zenml.cli.utils.describe_pydantic_object(schema_json: Dict[str, Any]) → None

Describes a Pydantic object based on the dict-representation of its schema.

Args:
: schema_json: str, represents the schema of a Pydantic object, which
  : can be obtained through BaseModelClass.schema_json()

### zenml.cli.utils.error(text: str) → NoReturn

Echo an error string on the CLI.

Args:
: text: Input text string.

Raises:
: ClickException: when called.

### zenml.cli.utils.expand_argument_value_from_file(name: str, value: str) → str

Expands the value of an argument pointing to a file into the contents of that file.

Args:
: name: Name of the argument. Used solely for logging purposes.
  value: The value of the argument. This is to be interpreted as a
  <br/>
  > filename if it begins with a @ character.

Returns:
: The argument value expanded into the contents of the file, if the
  argument value begins with a @ character. Otherwise, the argument
  value is returned unchanged.

Raises:
: ValueError: If the argument value points to a file that doesn’t exist,
  : that cannot be read, or is too long(i.e. exceeds
    MAX_ARGUMENT_VALUE_SIZE bytes).

### zenml.cli.utils.expires_in(expires_at: datetime, expired_str: str, skew_tolerance: int | None = None) → str

Returns a human-readable string of the time until the token expires.

Args:
: expires_at: Datetime object of the token expiration.
  expired_str: String to return if the token is expired.
  skew_tolerance: Seconds of skew tolerance to subtract from the
  <br/>
  > expiration time. If the token expires within this time, it will be
  > considered expired.

Returns:
: Human readable string.

### zenml.cli.utils.format_integration_list(integrations: List[Tuple[str, Type[[Integration](zenml.integrations.md#zenml.integrations.integration.Integration)]]]) → List[Dict[str, str]]

Formats a list of integrations into a List of Dicts.

This list of dicts can then be printed in a table style using
cli_utils.print_table.

Args:
: integrations: List of tuples containing the name of the integration and
  : the integration metadata.

Returns:
: List of Dicts containing the name of the integration and the integration

### zenml.cli.utils.get_boolean_emoji(value: bool) → str

Returns the emoji for displaying a boolean.

Args:
: value: The boolean value to display

Returns:
: The emoji for the boolean

### zenml.cli.utils.get_execution_status_emoji(status: [ExecutionStatus](zenml.md#zenml.enums.ExecutionStatus)) → str

Returns an emoji representing the given execution status.

Args:
: status: The execution status to get the emoji for.

Returns:
: An emoji representing the given execution status.

Raises:
: RuntimeError: If the given execution status is not supported.

### zenml.cli.utils.get_package_information(package_names: List[str] | None = None) → Dict[str, str]

Get a dictionary of installed packages.

Args:
: package_names: Specific package names to get the information for.

Returns:
: A dictionary of the name:version for the package names passed in or
  : all packages and their respective versions.

### zenml.cli.utils.get_parsed_labels(labels: List[str] | None, allow_label_only: bool = False) → Dict[str, str | None]

Parse labels into a dictionary.

Args:
: labels: The labels to parse.
  allow_label_only: Whether to allow labels without values.

Returns:
: A dictionary of the metadata.

Raises:
: ValueError: If the labels are not in the correct format.

### zenml.cli.utils.get_service_state_emoji(state: [ServiceState](zenml.services.md#zenml.services.service_status.ServiceState)) → str

Get the rich emoji representing the operational state of a Service.

Args:
: state: Service state to get emoji for.

Returns:
: String representing the emoji.

### zenml.cli.utils.install_packages(packages: List[str], upgrade: bool = False, use_uv: bool = False) → None

Installs pypi packages into the current environment with pip or uv.

When using with uv, a virtual environment is required.

Args:
: packages: List of packages to install.
  upgrade: Whether to upgrade the packages if they are already installed.
  use_uv: Whether to use uv for package installation.

Raises:
: e: If the package installation fails.

### zenml.cli.utils.is_jupyter_installed() → bool

Checks if Jupyter notebook is installed.

Returns:
: bool: True if Jupyter notebook is installed, False otherwise.

### zenml.cli.utils.is_pip_installed() → bool

Check if pip is installed in the current environment.

Returns:
: True if pip is installed, False otherwise.

### zenml.cli.utils.is_sorted_or_filtered(ctx: Context) → bool

Decides whether any filtering/sorting happens during a ‘list’ CLI call.

Args:
: ctx: the Click context of the CLI call.

Returns:
: a boolean indicating whether any sorting or filtering parameters were
  used during the list CLI call.

### zenml.cli.utils.is_uv_installed() → bool

Check if uv is installed in the current environment.

Returns:
: True if uv is installed, False otherwise.

### zenml.cli.utils.list_options(filter_model: Type[[BaseFilter](zenml.models.v2.base.md#zenml.models.v2.base.filter.BaseFilter)]) → Callable[[F], F]

Create a decorator to generate the correct list of filter parameters.

The Outer decorator (list_options) is responsible for creating the inner
decorator. This is necessary so that the type of FilterModel can be passed
in as a parameter.

Based on the filter model, the inner decorator extracts all the click
options that should be added to the decorated function (wrapper).

Args:
: filter_model: The filter model based on which to decorate the function.

Returns:
: The inner decorator.

### zenml.cli.utils.multi_choice_prompt(object_type: str, choices: List[List[Any]], headers: List[str], prompt_text: str, allow_zero_be_a_new_object: bool = False, default_choice: str | None = None) → int | None

Prompts the user to select a choice from a list of choices.

Args:
: object_type: The type of the object
  choices: The list of choices
  prompt_text: The prompt text
  headers: The list of headers.
  allow_zero_be_a_new_object: Whether to allow zero as a new object
  default_choice: The default choice

Returns:
: The selected choice index or None for new object

Raises:
: RuntimeError: If no choice is made.

### zenml.cli.utils.parse_name_and_extra_arguments(args: List[str], expand_args: bool = False, name_mandatory: bool = True) → Tuple[str | None, Dict[str, str]]

Parse a name and extra arguments from the CLI.

This is a utility function used to parse a variable list of optional CLI
arguments of the form –key=value that must also include one mandatory
free-form name argument. There is no restriction as to the order of the
arguments.

Examples:
: ```pycon
  >>> parse_name_and_extra_arguments(['foo']])
  ('foo', {})
  >>> parse_name_and_extra_arguments(['foo', '--bar=1'])
  ('foo', {'bar': '1'})
  >>> parse_name_and_extra_arguments(['--bar=1', 'foo', '--baz=2'])
  ('foo', {'bar': '1', 'baz': '2'})
  >>> parse_name_and_extra_arguments(['--bar=1'])
  Traceback (most recent call last):
      ...
      ValueError: Missing required argument: name
  ```

Args:
: args: A list of command line arguments from the CLI.
  expand_args: Whether to expand argument values into the contents of the
  <br/>
  > files they may be pointing at using the special @ character.
  <br/>
  name_mandatory: Whether the name argument is mandatory.

Returns:
: The name and a dict of parsed args.

### zenml.cli.utils.parse_unknown_component_attributes(args: List[str]) → List[str]

Parse unknown options from the CLI.

Args:
: args: A list of strings from the CLI.

Returns:
: List of parsed args.

### zenml.cli.utils.pretty_print_model_deployer(model_services: List[[BaseService](zenml.services.md#zenml.services.service.BaseService)], model_deployer: [BaseModelDeployer](zenml.model_deployers.md#zenml.model_deployers.base_model_deployer.BaseModelDeployer)) → None

Given a list of served_models, print all associated key-value pairs.

Args:
: model_services: list of model deployment services
  model_deployer: Active model deployer

### zenml.cli.utils.pretty_print_model_version_details(model_version: [RegistryModelVersion](zenml.model_registries.md#zenml.model_registries.base_model_registry.RegistryModelVersion)) → None

Given a model_version, print all associated key-value pairs.

Args:
: model_version: model version

### zenml.cli.utils.pretty_print_model_version_table(model_versions: List[[RegistryModelVersion](zenml.model_registries.md#zenml.model_registries.base_model_registry.RegistryModelVersion)]) → None

Given a list of model_versions, print all associated key-value pairs.

Args:
: model_versions: list of model versions

### zenml.cli.utils.pretty_print_registered_model_table(registered_models: List[[RegisteredModel](zenml.model_registries.md#zenml.model_registries.base_model_registry.RegisteredModel)]) → None

Given a list of registered_models, print all associated key-value pairs.

Args:
: registered_models: list of registered models

### zenml.cli.utils.pretty_print_secret(secret: Dict[str, str], hide_secret: bool = True) → None

Print all key-value pairs associated with a secret.

Args:
: secret: Secret values to print.
  hide_secret: boolean that configures if the secret values are shown
  <br/>
  > on the CLI

### zenml.cli.utils.print_components_table(client: [Client](zenml.md#zenml.client.Client), component_type: [StackComponentType](zenml.md#zenml.enums.StackComponentType), components: Sequence[[ComponentResponse](zenml.models.md#zenml.models.ComponentResponse)], show_active: bool = False) → None

Prints a table with configuration options for a list of stack components.

If a component is active (its name matches the active_component_name),
it will be highlighted in a separate table column.

Args:
: client: Instance of the Repository singleton
  component_type: Type of stack component
  components: List of stack components to print.
  show_active: Flag to decide whether to append the active stack component
  <br/>
  > on the top of the list.

### zenml.cli.utils.print_debug_stack() → None

Print active stack and components for debugging purposes.

### zenml.cli.utils.print_flavor_list(flavors: [Page](zenml.models.v2.base.md#id327)[[FlavorResponse](zenml.models.md#zenml.models.FlavorResponse)]) → None

Prints the list of flavors.

Args:
: flavors: List of flavors to print.

### zenml.cli.utils.print_list_items(list_items: List[str], column_title: str) → None

Prints the configuration options of a stack.

Args:
: list_items: List of items
  column_title: Title of the column

### zenml.cli.utils.print_markdown(text: str) → None

Prints a string as markdown.

Args:
: text: Markdown string to be printed.

### zenml.cli.utils.print_markdown_with_pager(text: str) → None

Prints a string as markdown with a pager.

Args:
: text: Markdown string to be printed.

### zenml.cli.utils.print_model_url(url: str | None) → None

Pretty prints a given URL on the CLI.

Args:
: url: optional str, the URL to display.

### zenml.cli.utils.print_page_info(page: [Page](zenml.models.v2.base.md#id327)[T]) → None

Print all page information showing the number of items and pages.

Args:
: page: The page to print the information for.

### zenml.cli.utils.print_pipeline_runs_table(pipeline_runs: Sequence[[PipelineRunResponse](zenml.models.md#zenml.models.PipelineRunResponse)]) → None

Print a prettified list of all pipeline runs supplied to this method.

Args:
: pipeline_runs: List of pipeline runs

### zenml.cli.utils.print_pydantic_model(title: str, model: BaseModel, exclude_columns: AbstractSet[str] | None = None, columns: AbstractSet[str] | None = None) → None

Prints a single Pydantic model in a table.

Args:
: title: Title of the table.
  model: Pydantic model that will be represented as a row in the table.
  exclude_columns: Optionally specify columns to exclude.
  columns: Optionally specify subset and order of columns to display.

### zenml.cli.utils.print_pydantic_models(models: [Page](zenml.models.v2.base.md#id327)[T] | List[T], columns: List[str] | None = None, exclude_columns: List[str] | None = None, active_models: List[T] | None = None, show_active: bool = False) → None

Prints the list of Pydantic models in a table.

Args:
: models: List of Pydantic models that will be represented as a row in
  : the table.
  <br/>
  columns: Optionally specify subset and order of columns to display.
  exclude_columns: Optionally specify columns to exclude. (Note: columns
  <br/>
  > takes precedence over exclude_columns.)
  <br/>
  active_models: Optional list of active models of the given type T.
  show_active: Flag to decide whether to append the active model on the
  <br/>
  > top of the list.

### zenml.cli.utils.print_served_model_configuration(model_service: [BaseService](zenml.services.md#zenml.services.service.BaseService), model_deployer: [BaseModelDeployer](zenml.model_deployers.md#zenml.model_deployers.base_model_deployer.BaseModelDeployer)) → None

Prints the configuration of a model_service.

Args:
: model_service: Specific service instance to
  model_deployer: Active model deployer

### zenml.cli.utils.print_server_deployment(server: [ServerDeployment](zenml.zen_server.deploy.md#zenml.zen_server.deploy.deployment.ServerDeployment)) → None

Prints the configuration and status of a ZenML server deployment.

Args:
: server: Server deployment to print

### zenml.cli.utils.print_server_deployment_list(servers: List[[ServerDeployment](zenml.zen_server.deploy.md#zenml.zen_server.deploy.deployment.ServerDeployment)]) → None

Print a table with a list of ZenML server deployments.

Args:
: servers: list of ZenML server deployments

### zenml.cli.utils.print_service_connector_auth_method(auth_method: [AuthenticationMethodModel](zenml.models.md#zenml.models.AuthenticationMethodModel), title: str = '', heading: str = '#', footer: str = '---', print: bool = True) → str

Prints details for a service connector authentication method.

Args:
: auth_method: Service connector authentication method to print.
  title: Markdown title to use for the authentication method details.
  heading: Markdown heading to use for the authentication method title.
  footer: Markdown footer to use for the authentication method description.
  print: Whether to print the authentication method details to the console
  <br/>
  > or just return the message as a string.

Returns:
: The MarkDown authentication method details as a string.

### zenml.cli.utils.print_service_connector_configuration(connector: [ServiceConnectorResponse](zenml.models.md#zenml.models.ServiceConnectorResponse) | [ServiceConnectorRequest](zenml.models.md#zenml.models.ServiceConnectorRequest), active_status: bool, show_secrets: bool) → None

Prints the configuration options of a service connector.

Args:
: connector: The service connector to print.
  active_status: Whether the connector is active.
  show_secrets: Whether to show secrets.

### zenml.cli.utils.print_service_connector_resource_table(resources: List[[ServiceConnectorResourcesModel](zenml.models.md#zenml.models.ServiceConnectorResourcesModel)], show_resources_only: bool = False) → None

Prints a table with details for a list of service connector resources.

Args:
: resources: List of service connector resources to print.
  show_resources_only: If True, only the resources will be printed.

### zenml.cli.utils.print_service_connector_resource_type(resource_type: [ResourceTypeModel](zenml.models.md#zenml.models.ResourceTypeModel), title: str = '', heading: str = '#', footer: str = '---', print: bool = True) → str

Prints details for a service connector resource type.

Args:
: resource_type: Service connector resource type to print.
  title: Markdown title to use for the resource type details.
  heading: Markdown heading to use for the resource type title.
  footer: Markdown footer to use for the resource type description.
  print: Whether to print the resource type details to the console or
  <br/>
  > just return the message as a string.

Returns:
: The MarkDown resource type details as a string.

### zenml.cli.utils.print_service_connector_type(connector_type: [ServiceConnectorTypeModel](zenml.models.md#zenml.models.ServiceConnectorTypeModel), title: str = '', heading: str = '#', footer: str = '---', include_resource_types: bool = True, include_auth_methods: bool = True, print: bool = True) → str

Prints details for a service connector type.

Args:
: connector_type: Service connector type to print.
  title: Markdown title to use for the service connector type details.
  heading: Markdown heading to use for the service connector type title.
  footer: Markdown footer to use for the service connector type
  <br/>
  > description.
  <br/>
  include_resource_types: Whether to include the resource types for the
  : service connector type.
  <br/>
  include_auth_methods: Whether to include the authentication methods for
  : the service connector type.
  <br/>
  print: Whether to print the service connector type details to the
  : console or just return the message as a string.

Returns:
: The MarkDown service connector type details as a string.

### zenml.cli.utils.print_service_connector_types_table(connector_types: Sequence[[ServiceConnectorTypeModel](zenml.models.md#zenml.models.ServiceConnectorTypeModel)]) → None

Prints a table with details for a list of service connectors types.

Args:
: connector_types: List of service connector types to print.

### zenml.cli.utils.print_service_connectors_table(client: [Client](zenml.md#zenml.client.Client), connectors: Sequence[[ServiceConnectorResponse](zenml.models.md#zenml.models.ServiceConnectorResponse)], show_active: bool = False) → None

Prints a table with details for a list of service connectors.

Args:
: client: Instance of the Repository singleton
  connectors: List of service connectors to print.
  show_active: lag to decide whether to append the active connectors
  <br/>
  > on the top of the list.

### zenml.cli.utils.print_stack_component_configuration(component: [ComponentResponse](zenml.models.md#zenml.models.ComponentResponse), active_status: bool, connector_requirements: [ServiceConnectorRequirements](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorRequirements) | None = None) → None

Prints the configuration options of a stack component.

Args:
: component: The stack component to print.
  active_status: Whether the stack component is active.
  connector_requirements: Connector requirements for the component, taken
  <br/>
  > from the component flavor. Only needed if the component has a
  > connector.

### zenml.cli.utils.print_stack_configuration(stack: [StackResponse](zenml.models.md#zenml.models.StackResponse), active: bool) → None

Prints the configuration options of a stack.

Args:
: stack: Instance of a stack model.
  active: Whether the stack is active.

### zenml.cli.utils.print_stack_outputs(stack: [StackResponse](zenml.models.md#zenml.models.StackResponse)) → None

Prints outputs for stacks deployed with mlstacks.

Args:
: stack: Instance of a stack model.

### zenml.cli.utils.print_stacks_table(client: [Client](zenml.md#zenml.client.Client), stacks: Sequence[[StackResponse](zenml.models.md#zenml.models.StackResponse)], show_active: bool = False) → None

Print a prettified list of all stacks supplied to this method.

Args:
: client: Repository instance
  stacks: List of stacks
  show_active: Flag to decide whether to append the active stack on the
  <br/>
  > top of the list.

### zenml.cli.utils.print_table(obj: List[Dict[str, Any]], title: str | None = None, caption: str | None = None, \*\*columns: Column) → None

Prints the list of dicts in a table format.

The input object should be a List of Dicts. Each item in that list represent
a line in the Table. Each dict should have the same keys. The keys of the
dict will be used as headers of the resulting table.

Args:
: obj: A List containing dictionaries.
  title: Title of the table.
  caption: Caption of the table.
  columns: Optional column configurations to be used in the table.

### zenml.cli.utils.print_user_info(info: Dict[str, Any]) → None

Print user information to the terminal.

Args:
: info: The information to print.

### zenml.cli.utils.prompt_configuration(config_schema: Dict[str, Any], show_secrets: bool = False, existing_config: Dict[str, str] | None = None) → Dict[str, str]

Prompt the user for configuration values using the provided schema.

Args:
: config_schema: The configuration schema.
  show_secrets: Whether to show secrets in the terminal.
  existing_config: The existing configuration values.

Returns:
: The configuration values provided by the user.

### zenml.cli.utils.replace_emojis(text: str) → str

Replaces emoji shortcuts with their unicode equivalent.

Args:
: text: Text to expand.

Returns:
: Text with expanded emojis.

### zenml.cli.utils.requires_mac_env_var_warning() → bool

Checks if a warning needs to be shown for a local Mac server.

This is for the case where a user is on a macOS system, trying to run a
local server but is missing the OBJC_DISABLE_INITIALIZE_FORK_SAFETY
environment variable.

Returns:
: bool: True if a warning needs to be shown, False otherwise.

### zenml.cli.utils.seconds_to_human_readable(time_seconds: int) → str

Converts seconds to human-readable format.

Args:
: time_seconds: Seconds to convert.

Returns:
: Human readable string.

### zenml.cli.utils.temporary_active_stack(stack_name_or_id: UUID | str | None = None) → Iterator[[Stack](zenml.stack.md#zenml.stack.stack.Stack)]

Contextmanager to temporarily activate a stack.

Args:
: stack_name_or_id: The name or ID of the stack to activate. If not given,
  : this contextmanager will not do anything.

Yields:
: The active stack.

### zenml.cli.utils.title(text: str) → None

Echo a title formatted string on the CLI.

Args:
: text: Input text string.

### zenml.cli.utils.uninstall_package(package: str, use_uv: bool = False) → None

Uninstalls pypi package from the current environment with pip or uv.

Args:
: package: The package to uninstall.
  use_uv: Whether to use uv for package uninstallation.

### zenml.cli.utils.validate_keys(key: str) → None

Validates key if it is a valid python string.

Args:
: key: key to validate

### zenml.cli.utils.verify_mlstacks_prerequisites_installation() → None

Checks if the mlstacks package is installed.

### zenml.cli.utils.warn_deprecated_example_subcommand() → None

Warning for deprecating example subcommand.

### zenml.cli.utils.warn_unsupported_non_default_workspace() → None

Warning for unsupported non-default workspace.

### zenml.cli.utils.warning(text: str, bold: bool | None = None, italic: bool | None = None, \*\*kwargs: Any) → None

Echo a warning string on the CLI.

Args:
: text: Input text string.
  bold: Optional boolean to bold the text.
  italic: Optional boolean to italicize the text.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Optional kwargs to be passed to console.print().

## zenml.cli.version module

CLI command to show installed ZenML version.

## zenml.cli.web_login module

Web login CLI support.

### zenml.cli.web_login.web_login(url: str, verify_ssl: str | bool) → str

Implements the OAuth2 Device Authorization Grant flow.

This function implements the client side of the OAuth2 Device Authorization
Grant flow as defined in [https://tools.ietf.org/html/rfc8628](https://tools.ietf.org/html/rfc8628), with the
following customizations:

* the unique ZenML client ID (user_id in the global config) is used

as the OAuth2 client ID value
\* additional information is added to the user agent header to be used by
users to identify the ZenML client

Args:
: url: The URL of the OAuth2 server.
  verify_ssl: Whether to verify the SSL certificate of the OAuth2 server.
  <br/>
  > If a string is passed, it is interpreted as the path to a CA bundle
  > file.

Returns:
: The access token returned by the OAuth2 server.

Raises:
: AuthorizationException: If an error occurred during the authorization
  : process.

## zenml.cli.workspace module

Functionality to administer workspaces of the ZenML CLI and server.

## Module contents

ZenML CLI.

The ZenML CLI tool is usually downloaded and installed via PyPI and a
`pip install zenml` command. Please see the Installation & Setup
section above for more information about that process.

### How to use the CLI

Our CLI behaves similarly to many other CLIs for basic features. In
order to find out which version of ZenML you are running, type:

```
``
```

```
`
```

bash
: zenml version

```
``
```

```
`
```

If you ever need more information on exactly what a certain command will
do, use the `--help` flag attached to the end of your command string.

For example, to get a sense of all the commands available to you
while using the `zenml` command, type:

```
``
```

```
`
```

bash
: zenml –help

```
``
```

```
`
```

If you were instead looking to know more about a specific command, you
can type something like this:

```
``
```

```
`
```

bash
: zenml artifact-store register –help

```
``
```

```
`
```

This will give you information about how to register an artifact store.
(See below for more on that).

If you want to instead understand what the concept behind a group is, you 
can use the explain sub-command. For example, to see more details behind 
what a artifact-store is, you can type:

``bash
zenml artifact-store explain
``

This will give you an explanation of that concept in more detail.

### Beginning a Project

In order to start working on your project, initialize a ZenML repository
within your current directory with ZenML’s own config and resource management
tools:

``bash
zenml init
``

This is all you need to begin using all the MLOps goodness that ZenML
provides!

By default, `zenml init` will install its own hidden `.zen` folder
inside the current directory from which you are running the command.
You can also pass in a directory path manually using the
`--path` option:

``bash
zenml init --path /path/to/dir
``

If you wish to use one of [the available ZenML project templates]([https://docs.zenml.io/how-to/setting-up-a-project-repository/using-project-templates#list-of-zenml-project-templates](https://docs.zenml.io/how-to/setting-up-a-project-repository/using-project-templates#list-of-zenml-project-templates))
to generate a ready-to-use project scaffold in your repository, you can do so by
passing the `--template` option:

``bash
zenml init --template <name_of_template>
``

Running the above command will result in input prompts being shown to you. If 
you would like to rely on default values for the ZenML project template - 
you can add `--template-with-defaults` to the same command, like this:

``bash
zenml init --template <name_of_template> --template-with-defaults
``

In a similar fashion, if you would like to quickly explore the capabilities
of ZenML through a notebook, you can also use:

``bash
zenml go
``

### Cleaning up

If you wish to delete all data relating to your workspace from the
directory, use the `zenml clean` command. This will:

- delete all pipelines, pipeline runs and associated metadata
- delete all artifacts

### Using Integrations

Integrations are the different pieces of a project stack that enable custom
functionality. This ranges from bigger libraries like
[kubeflow]([https://www.kubeflow.org/](https://www.kubeflow.org/)) for orchestration down to smaller
visualization tools like [facets]([https://pair-code.github.io/facets/](https://pair-code.github.io/facets/)). Our
CLI is an easy way to get started with these integrations.

To list all the integrations available to you, type:

``bash
zenml integration list
``

To see the requirements for a specific integration, use the requirements
command:

``bash
zenml integration requirements INTEGRATION_NAME
``

If you wish to install the integration, using the requirements listed in the
previous command, install allows you to do this for your local environment:

``bash
zenml integration install INTEGRATION_NAME
``

Note that if you don’t specify a specific integration to be installed, the
ZenML CLI will install **all** available integrations.

If you want to install all integrations apart from one or multiple integrations,
use the following syntax, for example, which will install all integrations
except feast and aws:

``shell
zenml integration install -i feast -i aws
``

Uninstalling a specific integration is as simple as typing:

``bash
zenml integration uninstall INTEGRATION_NAME
``

For all these zenml integration commands, you can pass the –uv flag and we
will use uv as the package manager instead of pip. This will resolve and
install much faster than with pip, but note that it requires uv to be
installed on your machine. This is an experimental feature and may not work on
all systems. In particular, note that installing onto machines with GPU
acceleration may not work as expected.

If you would like to export the requirements of all ZenML integrations, you can
use the command:

``bash
zenml integration export-requirements
``

Here, you can also select a list of integrations and write the result into and
output file:

``bash
zenml integration export-requirements gcp kubeflow -o OUTPUT_FILE
``

### Filtering when listing

Certain CLI list commands allow you to filter their output. For example, all
stack components allow you to pass custom parameters to the list command that
will filter the output. To learn more about the available filters, a good quick
reference is to use the –help command, as in the following example:

``shell
zenml orchestrator list --help
``

You will see a list of all the available filters for the list command along
with examples of how to use them.

The –sort_by option allows you to sort the output by a specific field and
takes an asc or desc argument to specify the order. For example, to sort the
output of the list command by the name field in ascending order, you would
type:

``shell
zenml orchestrator list --sort_by "asc:name"
``

For fields marked as being of type TEXT or UUID, you can use the contains,
startswith and endswith keywords along with their particular identifier. For
example, for the orchestrator list command, you can use the following filter
to find all orchestrators that contain the string sagemaker in their name:

``shell
zenml orchestrator list --name "contains:sagemaker"
``

For fields marked as being of type BOOL, you can use the ‘True’ or ‘False’
values to filter the output.

Finally, for fields marked as being of type DATETIME, you can pass in datetime
values in the %Y-%m-%d %H:%M:%S format. These can be combined with the gte,
lte, gt and lt keywords (greater than or equal, less than or equal,
greater than and less than respectively) to specify the range of the filter. For
example, if I wanted to find all orchestrators that were created after the 1st
of January 2021, I would type:

``shell
zenml orchestrator list --created "gt:2021-01-01 00:00:00"
``

This syntax can also be combined to create more complex filters using the or
and and keywords.

### Artifact Stores

In ZenML, [the artifact store]([https://docs.zenml.io/stack-components/artifact-stores](https://docs.zenml.io/stack-components/artifact-stores))
is where all the inputs and outputs of your pipeline steps are stored. By
default, ZenML initializes your repository with an artifact store with
everything kept on your local machine. You can get a better understanding
about the concept of artifact stores by executing:

``bash
zenml artifact-store explain
``

If you wish to register a new artifact store, do so with the `register`
command:

``bash
zenml artifact-store register ARTIFACT_STORE_NAME --flavor=ARTIFACT_STORE_FLAVOR [--OPTIONS]
``

You can also add any labels to your stack component using the –label or -l flag:

``bash
zenml artifact-store register ARTIFACT_STORE_NAME --flavor=ARTIFACT_STORE_FLAVOR -l key1=value1 -l key2=value2
``

As you can see from the command above, when you register a new artifact store,
you have to choose a flavor. To see the full list of available artifact
store flavors, you can use the command:

``bash
zenml artifact-store flavor list
``

This list will show you which integration these flavors belong to and which
service connectors they are adaptable with. If you would like to get additional
information regarding a specific flavor, you can utilize the command:

``bash
zenml artifact-store flavor describe FLAVOR_NAME
``

If you wish to list the artifact stores that have already been registered
within your ZenML:

``bash
zenml artifact-store list
``

If you want the name of the artifact store in the active stack, you can
also use the get command:

``bash
zenml artifact-store get
``

For details about a particular artifact store, use the describe command.
By default, (without a specific artifact store name passed in) it will describe
the active or currently used artifact store:

``bash
zenml artifact-store describe ARTIFACT_STORE_NAME
``

If you wish to update/rename an artifact store, you can use the following
commands respectively:

``bash
zenml artifact-store update ARTIFACT_STORE_NAME --property_to_update=new_value
zenml artifact-store rename ARTIFACT_STORE_OLD_NAME ARTIFACT_STORE_NEW_NAME
``

If you wish to delete a particular artifact store, pass the name of the
artifact store into the CLI with the following command:

``bash
zenml artifact-store delete ARTIFACT_STORE_NAME
``

If you would like to connect/disconnect your artifact store to/from a service
connector, you can use the following commands:

``bash
zenml artifact-store connect ARTIFACT_STORE_NAME -c CONNECTOR_NAME
zenml artifact-store disconnect
``

The ZenML CLI provides a few more utility functions for you to manage your
artifact stores. In order to get a full list of available functions, use
the command:

``bash
zenml artifact-store --help
``

### Orchestrators

An [orchestrator]([https://docs.zenml.io/stack-components/orchestrators](https://docs.zenml.io/stack-components/orchestrators))
is a special kind of backend that manages the running of each step of the
pipeline. Orchestrators administer the actual pipeline runs. By default,
ZenML initializes your repository with an orchestrator that runs everything
on your local machine. In order to get a more detailed explanation, you can use
the command:

``bash
zenml orchestrator explain
``

If you wish to register a new orchestrator, do so with the `register`
command:

``bash
zenml orchestrator register ORCHESTRATOR_NAME --flavor=ORCHESTRATOR_FLAVOR [--ORCHESTRATOR_OPTIONS]
``

You can also add any label to your stack component using the –label or -l flag:

``bash
zenml orchestrator register ORCHESTRATOR_NAME --flavor=ORCHESTRATOR_FLAVOR -l key1=value1 -l key2=value2
``

As you can see from the command above, when you register a new orchestrator,
you have to choose a flavor. To see the full list of available orchestrator
flavors, you can use the command:

``bash
zenml orchestrator flavor list
``

This list will show you which integration these flavors belong to and which
service connectors they are adaptable with. If you would like to get additional
information regarding a specific flavor, you can utilize the command:

``bash
zenml orchestrator flavor describe FLAVOR_NAME
``

If you wish to list the orchestrators that have already been registered
within your ZenML workspace / repository, type:

``bash
zenml orchestrator list
``

If you want the name of the orchestrator in the active stack, you can
also use the get command:

``bash
zenml orchestrator get
``

For details about a particular orchestrator, use the describe command.
By default, (without a specific orchestrator name passed in) it will describe
the active or currently used orchestrator:

``bash
zenml orchestrator describe [ORCHESTRATOR_NAME]
``

If you wish to update/rename an orchestrator, you can use the following
commands respectively:

``bash
zenml orchestrator update ORCHESTRATOR_NAME --property_to_update=new_value
zenml orchestrator rename ORCHESTRATOR_OLD_NAME ORCHESTRATOR_NEW_NAME
``

If you wish to delete a particular orchestrator, pass the name of the
orchestrator into the CLI with the following command:

``bash
zenml orchestrator delete ORCHESTRATOR_NAME
``

If you would like to connect/disconnect your orchestrator to/from a service
connector, you can use the following commands:

``bash
zenml orchestrator connect ORCHESTRATOR_NAME -c CONNECTOR_NAME
zenml orchestrator disconnect
``

The ZenML CLI provides a few more utility functions for you to manage your
orchestrators. In order to get a full list of available functions, use
the command:

``bash
zenml orchestrators --help
``

### Container Registries

[The container registry]([https://docs.zenml.io/stack-components/container-registries](https://docs.zenml.io/stack-components/container-registries))
is where all the images that are used by a container-based orchestrator are
stored. To get a better understanding regarding container registries, use
the command:

``bash
zenml container-registry explain
``

By default, a default ZenML local stack will not register a container registry.
If you wish to register a new container registry, do so with the register
command:

``bash
zenml container-registry register REGISTRY_NAME --flavor=REGISTRY_FLAVOR [--REGISTRY_OPTIONS]
``

You can also add any label to your stack component using the –label or -l flag:

``bash
zenml container-registry register REGISTRY_NAME --flavor=REGISTRY_FLAVOR -l key1=value1 -l key2=value2
``

As you can see from the command above, when you register a new container
registry, you have to choose a flavor. To see the full list of available
container registry flavors, you can use the command:

``bash
zenml container-registry flavor list
``

This list will show you which integration these flavors belong to and which
service connectors they are adaptable with. If you would like to get additional
information regarding a specific flavor, you can utilize the command:

``bash
zenml container-registry flavor describe FLAVOR_NAME
``

To list all container registries available and registered for use, use the
list command:

``bash
zenml container-registry list
``

If you want the name of the container registry in the active stack, you can
also use the get command:

``bash
zenml container-registry get
``

For details about a particular container registry, use the describe command.
By default, (without a specific registry name passed in) it will describe the
active or currently used container registry:

``bash
zenml container-registry describe [CONTAINER_REGISTRY_NAME]
``

If you wish to update/rename a container registry, you can use the following
commands respectively:

``bash
zenml container-registry update CONTAINER_REGISTRY_NAME --property_to_update=new_value
zenml container-registry rename CONTAINER_REGISTRY_OLD_NAME CONTAINER_REGISTRY_NEW_NAME
``

To delete a container registry (and all of its contents), use the delete
command:

``bash
zenml container-registry delete REGISTRY_NAME
``

If you would like to connect/disconnect your container registry to/from a
service connector, you can use the following commands:

``bash
zenml container-registry connect CONTAINER_REGISTRY_NAME -c CONNECTOR_NAME
zenml container-registry disconnect
``

The ZenML CLI provides a few more utility functions for you to manage your
container registries. In order to get a full list of available functions,
use the command:

``bash
zenml container-registry --help
``

### Data Validators

In ZenML, [data validators]([https://docs.zenml.io/stack-components/data-validators](https://docs.zenml.io/stack-components/data-validators))
help you profile and validate your data.

By default, a default ZenML local stack will not register a data validator. If
you wish to register a new data validator, do so with the register command:

``bash
zenml data-validator register DATA_VALIDATOR_NAME --flavor DATA_VALIDATOR_FLAVOR [--DATA_VALIDATOR_OPTIONS]
``

You can also add any label to your stack component using the –label or -l flag:

``bash
zenml data-validator register DATA_VALIDATOR_NAME --flavor DATA_VALIDATOR_FLAVOR -l key1=value1 -l key2=value2
``

As you can see from the command above, when you register a new data validator,
you have to choose a flavor. To see the full list of available data validator
flavors, you can use the command:

``bash
zenml data-validator flavor list
``

This list will show you which integration these flavors belong to and which
service connectors they are adaptable with. If you would like to get additional
information regarding a specific flavor, you can utilize the command:

``bash
zenml data-validator flavor describe FLAVOR_NAME
``

To list all data validators available and registered for use, use the list
command:

``bash
zenml data-validator list
``

If you want the name of the data validator in the active stack, use the get
command:

``bash
zenml data-validator get
``

For details about a particular data validator, use the describe command.
By default, (without a specific data validator name passed in) it will describe
the active or currently-used data validator:

``bash
zenml data-validator describe [DATA_VALIDATOR_NAME]
``

If you wish to update/rename a data validator, you can use the following
commands respectively:

``bash
zenml data-validator update DATA_VALIDATOR_NAME --property_to_update=new_value
zenml data-validator rename DATA_VALIDATOR_OLD_NAME DATA_VALIDATOR_NEW_NAME
``

To delete a data validator (and all of its contents), use the delete command:

``bash
zenml data-validator delete DATA_VALIDATOR_NAME
``

If you would like to connect/disconnect your data validator to/from a service
connector, you can use the following commands:

``bash
zenml data-validator connect DATA_VALIDATOR_NAME -c CONNECTOR_NAME
zenml data-validator disconnect
``

The ZenML CLI provides a few more utility functions for you to manage your
data validators. In order to get a full list of available functions, use the
command:

``bash
zenml data-validator --help
``

### Experiment Trackers

[Experiment trackers]([https://docs.zenml.io/stack-components/experiment-trackers](https://docs.zenml.io/stack-components/experiment-trackers))
: let you track your ML experiments by logging the parameters

and allow you to compare between different runs. To get a better
understanding regarding experiment trackers, use the command:

``bash
zenml experiment-tracker explain
``

By default, a default ZenML local stack will not register an experiment tracker.
If you want to use an experiment tracker in one of your stacks, you need to
first register it:

``bash
zenml experiment-tracker register EXPERIMENT_TRACKER_NAME     --flavor=EXPERIMENT_TRACKER_FLAVOR [--EXPERIMENT_TRACKER_OPTIONS]
``

You can also add any label to your stack component using the –label or -l flag:

``bash
zenml experiment-tracker register EXPERIMENT_TRACKER_NAME       --flavor=EXPERIMENT_TRACKER_FLAVOR -l key1=value1 -l key2=value2
``

As you can see from the command above, when you register a new experiment
tracker, you have to choose a flavor. To see the full list of available
experiment tracker flavors, you can use the command:

``bash
zenml experiment-tracker flavor list
``

This list will show you which integration these flavors belong to and which
service connectors they are adaptable with. If you would like to get additional
information regarding a specific flavor, you can utilize the command:

``bash
zenml experiment-tracker flavor describe FLAVOR_NAME
``

To list all experiment trackers available and registered for use, use the
list command:

``bash
zenml experiment-tracker list
``

If you want the name of the experiment tracker in the active stack, use the
get command:

``bash
zenml experiment-tracker get
``

For details about a particular experiment tracker, use the describe command.
By default, (without a specific experiment tracker name passed in) it will
describe the active or currently-used experiment tracker:

``bash
zenml experiment-tracker describe [EXPERIMENT_TRACKER_NAME]
``

If you wish to update/rename an experiment tracker, you can use the following
commands respectively:

``bash
zenml experiment-tracker update EXPERIMENT_TRACKER_NAME --property_to_update=new_value
zenml experiment-tracker rename EXPERIMENT_TRACKER_OLD_NAME EXPERIMENT_TRACKER_NEW_NAME
``

To delete an experiment tracker, use the delete command:

``bash
zenml experiment-tracker delete EXPERIMENT_TRACKER_NAME
``

If you would like to connect/disconnect your experiment tracker to/from a
service connector, you can use the following commands:

``bash
zenml experiment-tracker connect EXPERIMENT_TRACKER_NAME -c CONNECTOR_NAME
zenml experiment-tracker disconnect
``

The ZenML CLI provides a few more utility functions for you to manage your
experiment trackers. In order to get a full list of available functions,
use the command:

``bash
zenml experiment-tracker --help
``

### Model Deployers

[Model deployers]([https://docs.zenml.io/stack-components/model-deployers](https://docs.zenml.io/stack-components/model-deployers))
are stack components responsible for online model serving. They are responsible
for deploying models to a remote server. Model deployers also act as a registry
for models that are served with ZenML. To get a better understanding regarding
model deployers, use the command:

``bash
zenml model-deployer explain
``

By default, a default ZenML local stack will not register a model deployer. If
you wish to register a new model deployer, do so with the register command:

``bash
zenml model-deployer register MODEL_DEPLOYER_NAME --flavor MODEL_DEPLOYER_FLAVOR [--MODEL_DEPLOYER_OPTIONS]
``

You can also add any label to your stack component using the –label or -l flag:

``bash
zenml model-deployer register MODEL_DEPLOYER_NAME --flavor MODEL_DEPLOYER_FLAVOR -l key1=value1 -l key2=value2
``

As you can see from the command above, when you register a new model deployer,
you have to choose a flavor. To see the full list of available model deployer
flavors, you can use the command:

``bash
zenml model-deployer flavor list
``

This list will show you which integration these flavors belong to and which
service connectors they are adaptable with. If you would like to get additional
information regarding a specific flavor, you can utilize the command:

``bash
zenml model-deployer flavor describe FLAVOR_NAME
``

To list all model deployers available and registered for use, use the
list command:

``bash
zenml model-deployer list
``

If you want the name of the model deployer in the active stack, use the get
command:

``bash
zenml model-deployer get
``

For details about a particular model deployer, use the describe command.
By default, (without a specific operator name passed in) it will describe the
active or currently used model deployer:

``bash
zenml model-deployer describe [MODEL_DEPLOYER_NAME]
``

If you wish to update/rename a model deployer, you can use the following
commands respectively:

``bash
zenml model-deployer update MODEL_DEPLOYER_NAME --property_to_update=new_value
zenml model-deployer rename MODEL_DEPLOYER_OLD_NAME MODEL_DEPLOYER_NEW_NAME
``

To delete a model deployer (and all of its contents), use the delete
command:

``bash
zenml model-deployer delete MODEL_DEPLOYER_NAME
``

If you would like to connect/disconnect your model deployer to/from a
service connector, you can use the following commands:

``bash
zenml model-deployer connect MODEL_DEPLOYER_NAME -c CONNECTOR_NAME
zenml model-deployer disconnect
``

Moreover, ZenML features a set of CLI commands specific to the model deployer
interface. If you want to simply see what models have been deployed within
your stack, run the following command:

``bash
zenml model-deployer models list
``

This should give you a list of served models containing their uuid, the name
of the pipeline that produced them including the run id and the step name as
well as the status. This information should help you identify the different
models.

If you want further information about a specific model, simply copy the
UUID and the following command.

``bash
zenml model-deployer models describe <UUID>
``

If you are only interested in the prediction url of the specific model you can
also run:

``bash
zenml model-deployer models get-url <UUID>
``

Finally, you will also be able to start/stop the services using the following
: two commands:

``bash
zenml model-deployer models start <UUID>
zenml model-deployer models stop <UUID>
``

If you want to completely remove a served model you can also irreversibly delete
: it using:

``bash
zenml model-deployer models delete <UUID>
``

The ZenML CLI provides a few more utility functions for you to manage your
model deployers. In order to get a full list of available functions,
use the command:

``bash
zenml model-deployer --help
``

### Step Operators

[Step operators]([https://docs.zenml.io/stack-components/step-operators](https://docs.zenml.io/stack-components/step-operators))
allow you to run individual steps in a custom environment different from the
default one used by your active orchestrator. One example use-case is to run a
training step of your pipeline in an environment with GPUs available. To get
a better understanding regarding step operators, use the command:

``bash
zenml step-operator explain
``

By default, a default ZenML local stack will not register a step operator. If
you wish to register a new step operator, do so with the register command:

``bash
zenml step-operator register STEP_OPERATOR_NAME --flavor STEP_OPERATOR_FLAVOR [--STEP_OPERATOR_OPTIONS]
``

You can also add any label to your stack component using the –label or -l flag:

``bash
zenml step-operator register STEP_OPERATOR_NAME --flavor STEP_OPERATOR_FLAVOR -l key1=value1 -l key2=value2
``

As you can see from the command above, when you register a new step operator,
you have to choose a flavor. To see the full list of available step operator
flavors, you can use the command:

``bash
zenml step-operator flavor list
``

This list will show you which integration these flavors belong to and which
service connectors they are adaptable with. If you would like to get additional
information regarding a specific flavor, you can utilize the command:

``bash
zenml step-operator flavor describe FLAVOR_NAME
``

To list all step operators available and registered for use, use the
list command:

``bash
zenml step-operator list
``

If you want the name of the step operator in the active stack, use the get
command:

``bash
zenml step-operator get
``

For details about a particular step operator, use the describe command.
By default, (without a specific operator name passed in) it will describe the
active or currently used step operator:

``bash
zenml step-operator describe [STEP_OPERATOR_NAME]
``

If you wish to update/rename a step operator, you can use the following commands
respectively:

``bash
zenml step-operator update STEP_OPERATOR_NAME --property_to_update=new_value
zenml step-operator rename STEP_OPERATOR_OLD_NAME STEP_OPERATOR_NEW_NAME
``

To delete a step operator (and all of its contents), use the delete
command:

``bash
zenml step-operator delete STEP_OPERATOR_NAME
``

If you would like to connect/disconnect your step operator to/from a
service connector, you can use the following commands:

``bash
zenml step-operator connect STEP_OPERATOR_NAME -c CONNECTOR_NAME
zenml step-operator disconnect
``

The ZenML CLI provides a few more utility functions for you to manage your
step operators. In order to get a full list of available functions,
use the command:

``bash
zenml step-operator --help
``

### Alerters

In ZenML, [alerters]([https://docs.zenml.io/stack-components/alerters](https://docs.zenml.io/stack-components/alerters))
allow you to send alerts from within your pipeline.

By default, a default ZenML local stack will not register an alerter. If
you wish to register a new alerter, do so with the register command:

``bash
zenml alerter register ALERTER_NAME --flavor ALERTER_FLAVOR [--ALERTER_OPTIONS]
``

You can also add any label to your stack component using the –label or -l flag:

``bash
zenml alerter register ALERTER_NAME --flavor ALERTER_FLAVOR -l key1=value1 -l key2=value2
``

As you can see from the command above, when you register a new alerter,
you have to choose a flavor. To see the full list of available alerter
flavors, you can use the command:

``bash
zenml alerter flavor list
``

This list will show you which integration these flavors belong to and which
service connectors they are adaptable with. If you would like to get additional
information regarding a specific flavor, you can utilize the command:

``bash
zenml alerter flavor describe FLAVOR_NAME
``

To list all alerters available and registered for use, use the list command:

``bash
zenml alerter list
``

If you want the name of the alerter in the active stack, use the get
command:

``bash
zenml alerter get
``

For details about a particular alerter, use the describe command.
By default, (without a specific alerter name passed in) it will describe
the active or currently used alerter:

``bash
zenml alerter describe [ALERTER_NAME]
``

If you wish to update/rename an alerter, you can use the following commands
respectively:

``bash
zenml alerter update ALERTER_NAME --property_to_update=new_value
zenml alerter rename ALERTER_OLD_NAME ALERTER_NEW_NAME
``

To delete an alerter (and all of its contents), use the delete command:

``bash
zenml alerter delete ALERTER_NAME
``

If you would like to connect/disconnect your alerter to/from a service
connector, you can use the following commands:

``bash
zenml alerter connect ALERTER_NAME -c CONNECTOR_NAME
zenml alerter disconnect
``

The ZenML CLI provides a few more utility functions for you to manage your
alerters. In order to get a full list of available functions, use the command:

``bash
zenml alerter --help
``

### Feature Stores

[Feature stores]([https://docs.zenml.io/stack-components/feature-stores](https://docs.zenml.io/stack-components/feature-stores))
allow data teams to serve data via an offline store and an online low-latency
store where data is kept in sync between the two. To get a better understanding
regarding feature stores, use the command:

``bash
zenml feature-store explain
``

By default, a default ZenML local stack will not register a feature store. If
you wish to register a new feature store, do so with the register command:

``bash
zenml feature-store register FEATURE_STORE_NAME --flavor FEATURE_STORE_FLAVOR [--FEATURE_STORE_OPTIONS]
``

You can also add any label to your stack component using the –label or -l flag:

``bash
zenml feature-store register FEATURE_STORE_NAME --flavor FEATURE_STORE_FLAVOR -l key1=value1 -l key2=value2
``

As you can see from the command above, when you register a new feature store,
you have to choose a flavor. To see the full list of available feature store
flavors, you can use the command:

``bash
zenml feature-store flavor list
``

This list will show you which integration these flavors belong to and which
service connectors they are adaptable with. If you would like to get additional
information regarding a specific flavor, you can utilize the command:

Note: Currently, ZenML only supports connecting to a Redis-backed Feast feature
store as a stack component integration.

``bash
zenml feature-store flavor describe FLAVOR_NAME
``

To list all feature stores available and registered for use, use the
list command:

``bash
zenml feature-store list
``

If you want the name of the feature store in the active stack, use the get
command:

``bash
zenml feature-store get
``

For details about a particular feature store, use the describe command.
By default, (without a specific feature store name passed in) it will describe
the active or currently-used feature store:

``bash
zenml feature-store describe [FEATURE_STORE_NAME]
``

If you wish to update/rename a feature store, you can use the following commands
respectively:

``bash
zenml feature-store update FEATURE_STORE_NAME --property_to_update=new_value
zenml feature-store rename FEATURE_STORE_OLD_NAME FEATURE_STORE_NEW_NAME
``

To delete a feature store (and all of its contents), use the delete
command:

``bash
zenml feature-store delete FEATURE_STORE_NAME
``

If you would like to connect/disconnect your feature store to/from a
service connector, you can use the following commands:

``bash
zenml feature-store connect FEATURE_STORE_NAME -c CONNECTOR_NAME
zenml feature-store disconnect
``

The ZenML CLI provides a few more utility functions for you to manage your
feature stores. In order to get a full list of available functions,
use the command:

``bash
zenml feature-store --help
``

### Annotators

[Annotators]([https://docs.zenml.io/stack-components/annotators](https://docs.zenml.io/stack-components/annotators))
enable the use of data annotation as part of your ZenML stack and pipelines.

By default, a default ZenML local stack will not register an annotator. If
you wish to register a new annotator, do so with the register command:

``bash
zenml annotator register ANNOTATOR_NAME --flavor ANNOTATOR_FLAVOR [--ANNOTATOR_OPTIONS]
``

You can also add any label to your stack component using the –label or -l flag:

``bash
zenml annotator register ANNOTATOR_NAME --flavor ANNOTATOR_FLAVOR -l key1=value1 -l key2=value2
``

As you can see from the command above, when you register a new annotator,
you have to choose a flavor. To see the full list of available annotator
flavors, you can use the command:

``bash
zenml annotator flavor list
``

This list will show you which integration these flavors belong to and which
service connectors they are adaptable with. If you would like to get additional
information regarding a specific flavor, you can utilize the command:

``bash
zenml annotator flavor describe FLAVOR_NAME
``

To list all annotator available and registered for use, use the list command:

``bash
zenml annotator list
``

If you want the name of the annotator in the active stack, use the get
command:

``bash
zenml annotator get
``

For details about a particular annotator, use the describe command.
By default, (without a specific annotator name passed in) it will describe
the active or currently used annotator:

``bash
zenml annotator describe [ANNOTATOR_NAME]
``

If you wish to update/rename an annotator, you can use the following commands
respectively:

``bash
zenml annotator update ANNOTATOR_NAME --property_to_update=new_value
zenml annotator rename ANNOTATOR_OLD_NAME ANNOTATOR_NEW_NAME
``

To delete an annotator (and all of its contents), use the delete command:

``bash
zenml annotator delete ANNOTATOR_NAME
``

If you would like to connect/disconnect your annotator to/from a service
connector, you can use the following commands:

``bash
zenml annotator connect ANNOTATOR_NAME -c CONNECTOR_NAME
zenml annotator disconnect
``

Finally, you can use the dataset command to interact with your annotation
datasets:

``bash
zenml annotator dataset --help
``

The ZenML CLI provides a few more utility functions for you to manage your
annotator. In order to get a full list of available functions, use the command:

``bash
zenml annotator --help
``

### Image Builders

In ZenML, [image builders]([https://docs.zenml.io/stack-components/image-builders](https://docs.zenml.io/stack-components/image-builders))
allow you to build container images such
that your machine-learning pipelines and steps can be executed in remote
environments.

By default, a default ZenML local stack will not register an image builder. If
you wish to register a new image builder, do so with the register command:

``bash
zenml image-builder register IMAGE_BUILDER_NAME --flavor IMAGE_BUILDER_FLAVOR [--IMAGE_BUILDER_OPTIONS]
``

You can also add any label to your stack component using the –label or -l flag:

``bash
zenml image-builder register IMAGE_BUILDER_NAME --flavor IMAGE_BUILDER_FLAVOR -l key1=value1 -l key2=value2
``

As you can see from the command above, when you register a new image builder,
you have to choose a flavor. To see the full list of available image builder
flavors, you can use the command:

``bash
zenml image-builder flavor list
``

This list will show you which integration these flavors belong to and which
service connectors they are adaptable with. If you would like to get additional
information regarding a specific flavor, you can utilize the command:

``bash
zenml image-builder flavor describe FLAVOR_NAME
``

To list all image builders available and registered for use, use the list
command:

``bash
zenml image-builder list
``

If you want the name of the image builder in the active stack, use the get
command:

``bash
zenml image-builder get
``

For details about a particular image builder, use the describe command.
By default, (without a specific image builder name passed in) it will describe
the active or currently used image builder:

``bash
zenml image-builder describe [IMAGE_BUILDER_NAME]
``

If you wish to update/rename an image builder, you can use the following
commands respectively:

``bash
zenml image-builder update IMAGE_BUILDER_NAME --property_to_update=new_value
zenml image-builder rename IMAGE_BUILDER_OLD_NAME IMAGE_BUILDER_NEW_NAME
``

To delete a image builder (and all of its contents), use the delete command:

``bash
zenml image-builder delete IMAGE_BUILDER_NAME
``

If you would like to connect/disconnect your image builder to/from a service
connector, you can use the following commands:

``bash
zenml image-builder connect IMAGE_BUILDER_NAME -c CONNECTOR_NAME
zenml image-builder disconnect
``

The ZenML CLI provides a few more utility functions for you to manage your
image builders. In order to get a full list of available functions, use the
command:

``bash
zenml image-builder --help
``

### Model Registries

[Model registries]([https://docs.zenml.io/stack-components/model-registries](https://docs.zenml.io/stack-components/model-registries))
are centralized repositories that facilitate the collaboration and management
of machine learning models. To get a better understanding regarding model
registries as a concept, use the command:

``bash
zenml model-registry explain
``

By default, a default ZenML local stack will not register a model registry. If
you wish to register a new model registry, do so with the register command:

``bash
zenml model-registry register MODEL_REGISTRY_NAME --flavor MODEL_REGISTRY_FLAVOR [--MODEL_REGISTRY_OPTIONS]
``

You can also add any label to your stack component using the –label or -l flag:

``bash
zenml model-registry register MODEL_REGISTRY_NAME --flavor MODEL_REGISTRY_FLAVOR -l key1=value1 -l key2=value2
``

As you can see from the command above, when you register a new model registry,
you have to choose a flavor. To see the full list of available model registry
flavors, you can use the command:

``bash
zenml model-registry flavor list
``

This list will show you which integration these flavors belong to and which
service connectors they are adaptable with. If you would like to get additional
information regarding a specific flavor, you can utilize the command:

``bash
zenml model-registry flavor describe FLAVOR_NAME
``

To list all model registries available and registered for use, use the
list command:

``bash
zenml model-registry list
``

If you want the name of the model registry in the active stack, use the get
command:

``bash
zenml model-registry get
``

For details about a particular model registry, use the describe command.
By default, (without a specific operator name passed in) it will describe the
active or currently used model registry:

``bash
zenml model-registry describe [MODEL_REGISTRY_NAME]
``

If you wish to update/rename a model registry, you can use the following commands
respectively:

``bash
zenml model-registry update MODEL_REGISTRY_NAME --property_to_update=new_value
zenml model-registry rename MODEL_REGISTRY_OLD_NAME MODEL_REGISTRY_NEW_NAME
``

To delete a model registry (and all of its contents), use the delete
command:

``bash
zenml model-registry delete MODEL_REGISTRY_NAME
``

If you would like to connect/disconnect your model registry to/from a
service connector, you can use the following commands:

``bash
zenml model-registry connect MODEL_REGISTRY_NAME -c CONNECTOR_NAME
zenml model-registry disconnect
``

The ZenML CLI provides a few more utility functions for you to manage your
model registries. In order to get a full list of available functions,
use the command:

``bash
zenml model-registry --help
``

### Managing your Stacks

[The stack]([https://docs.zenml.io/user-guide/production-guide/understand-stacks](https://docs.zenml.io/user-guide/production-guide/understand-stacks))
is a grouping of your artifact store, your orchestrator, and other
optional MLOps tools like experiment trackers or model deployers.
With the ZenML tool, switching from a local stack to a distributed cloud
environment can be accomplished with just a few CLI commands.

To register a new stack, you must already have registered the individual
components of the stack using the commands listed above.

Use the `zenml stack register` command to register your stack. It
takes four arguments as in the following example:

``bash
zenml stack register STACK_NAME        -a ARTIFACT_STORE_NAME        -o ORCHESTRATOR_NAME
``

Each corresponding argument should be the name, id or even the first few letters
: of the id that uniquely identify the artifact store or orchestrator.

To create a new stack using the new service connector with a set of minimal components, 
use the following command:

``bash
zenml stack register STACK_NAME        -p CLOUD_PROVIDER
``

To create a new stack using the existing service connector with a set of minimal components, 
use the following command:

``bash
zenml stack register STACK_NAME        -sc SERVICE_CONNECTOR_NAME
``

To create a new stack using the existing service connector with existing components (
important, that the components are already registered in the service connector), use the 
following command:

``bash
zenml stack register STACK_NAME        -sc SERVICE_CONNECTOR_NAME        -a ARTIFACT_STORE_NAME        -o ORCHESTRATOR_NAME        ...
``

If you want to immediately set this newly created stack as your active stack,
simply pass along the –set flag.

``bash
zenml stack register STACK_NAME ... --set
``

To list the stacks that you have registered within your current ZenML
workspace, type:

``bash
zenml stack list
``
To delete a stack that you have previously registered, type:

``bash
zenml stack delete STACK_NAME
``
By default, ZenML uses a local stack whereby all pipelines run on your
local computer. If you wish to set a different stack as the current
active stack to be used when running your pipeline, type:

``bash
zenml stack set STACK_NAME
``
This changes a configuration property within your local environment.

To see which stack is currently set as the default active stack, type:

``bash
zenml stack get
``

If you want to copy a stack, run the following command:
``shell
zenml stack copy SOURCE_STACK_NAME TARGET_STACK_NAME
``

If you wish to transfer one of your stacks to another machine, you can do so
by exporting the stack configuration and then importing it again.

To export a stack to YAML, run the following command:

``bash
zenml stack export STACK_NAME FILENAME.yaml
``

This will create a FILENAME.yaml containing the config of your stack and all
of its components, which you can then import again like this:

``bash
zenml stack import STACK_NAME -f FILENAME.yaml
``

If you wish to update a stack that you have already registered, first make sure
you have registered whatever components you want to use, then use the following
command:

``bash
# assuming that you have already registered a new orchestrator
# with NEW_ORCHESTRATOR_NAME
zenml stack update STACK_NAME -o NEW_ORCHESTRATOR_NAME
``

You can update one or many stack components at the same time out of the ones
that ZenML supports. To see the full list of options for updating a stack, use
the following command:

``bash
zenml stack update --help
``

To remove a stack component from a stack, use the following command:

``shell
# assuming you want to remove the image builder and the feature-store
# from your stack
zenml stack remove-component -i -f
``

If you wish to rename your stack, use the following command:

``shell
zenml stack rename STACK_NAME NEW_STACK_NAME
``

If you want to copy a stack component, run the following command:
``bash
zenml STACK_COMPONENT copy SOURCE_COMPONENT_NAME TARGET_COMPONENT_NAME
``

If you wish to update a specific stack component, use the following command,
switching out “STACK_COMPONENT” for the component you wish to update (i.e.
‘orchestrator’ or ‘artifact-store’ etc.):

``shell
zenml STACK_COMPONENT update --some_property=NEW_VALUE
``

Note that you are not permitted to update the stack name or UUID in this way. To
change the name of your stack component, use the following command:

``shell
zenml STACK_COMPONENT rename STACK_COMPONENT_NAME NEW_STACK_COMPONENT_NAME
``

If you wish to remove an attribute (or multiple attributes) from a stack
component, use the following command:

``shell
zenml STACK_COMPONENT remove-attribute STACK_COMPONENT_NAME ATTRIBUTE_NAME [OTHER_ATTRIBUTE_NAME]
``

Note that you can only remove optional attributes.

If you want to register secrets for all secret references in a stack, use the
following command:

``shell
zenml stack register-secrets [<STACK_NAME>]
``

If you want to connect a service connector to a stack’s components, you can use
the connect command:

``shell
zenml stack connect STACK_NAME -c CONNECTOR_NAME
``

Note that this only connects the service connector to the current components
of the stack and not to the stack itself, which means that you need to rerun
the command after adding new components to the stack.

The ZenML CLI provides a few more utility functions for you to manage your
stacks. In order to get a full list of available functions, use the command:

``bash
zenml stack --help
``

### Managing your Models

ZenML provides several CLI commands to help you administer your models and
their versions as part of [the Model Control Plane]([https://docs.zenml.io/user-guide/starter-guide/track-ml-models](https://docs.zenml.io/user-guide/starter-guide/track-ml-models)).

To register a new model, you can use the following CLI command:

``bash
zenml model register --name <NAME> [--MODEL_OPTIONS]
``

To list all registered models, use:

``bash
zenml model list [MODEL_FILTER_OPTIONS]
``

To update a model, use:

``bash
zenml model update <MODEL_NAME_OR_ID> [--MODEL_OPTIONS]
``

If you would like to add or remove tags from the model, use:

```
``
```

```
`
```

bash
zenml model update <MODEL_NAME_OR_ID> –tag <TAG> –tag <TAG> ..

> –remove-tag <TAG> –remove-tag <TAG> ..

```
``
```

```
`
```

To delete a model, use:

``bash
zenml model delete <MODEL_NAME_OR_ID>
``

The CLI interface for models also helps to navigate through artifacts linked to a specific model versions.

``bash
zenml model data_artifacts <MODEL_NAME_OR_ID> [-v <VERSION>]
zenml model deployment_artifacts <MODEL_NAME_OR_ID> [-v <VERSION>]
zenml model model_artifacts <MODEL_NAME_OR_ID> [-v <VERSION>]
``

You can also navigate the pipeline runs linked to a specific model versions:

``bash
zenml model runs <MODEL_NAME_OR_ID> [-v <VERSION>]
``

To list the model versions of a specific model, use:

``bash
zenml model version list [--model-name <MODEL_NAME> --name <MODEL_VERSION_NAME> OTHER_OPTIONS]
``

To delete a model version, use:

``bash
zenml model version delete <MODEL_NAME_OR_ID> <VERSION>
``

To update a model version, use:

``bash
zenml model version update <MODEL_NAME_OR_ID> <VERSION> [--MODEL_VERSION_OPTIONS]
``

These are some of the more common uses of model version updates:

- stage (i.e. promotion)

``bash
zenml model version update <MODEL_NAME_OR_ID> <VERSION> --stage <STAGE>
``

- tags

```
``
```

```
`
```

bash
zenml model version update <MODEL_NAME_OR_ID> <VERSION> –tag <TAG> –tag <TAG> ..

> –remove-tag <TAG> –remove-tag <TAG> ..

```
``
```

```
`
```

### Managing your Pipelines & Artifacts

ZenML provides several CLI commands to help you [administer your pipelines and
pipeline runs]([https://docs.zenml.io/user-guide/starter-guide/manage-artifacts](https://docs.zenml.io/user-guide/starter-guide/manage-artifacts)).

To explicitly register a pipeline you need to point to a pipeline instance
in your Python code. Let’s say you have a Python file called run.py and
it contains the following code:

```
``
```

```
`
```

python
from zenml import pipeline

@pipeline
def my_pipeline(…):

> # Connect your pipeline steps here
> pass

```
``
```

```
`
```

You can register your pipeline like this:
``bash
zenml pipeline register run.my_pipeline
``

To list all registered pipelines, use:

``bash
zenml pipeline list
``

To delete a pipeline, run:

``bash
zenml pipeline delete <PIPELINE_NAME>
``

This will delete the pipeline and change all corresponding
pipeline runs to become unlisted (not linked to any pipeline).

To list all pipeline runs that you have executed, use:

``bash
zenml pipeline runs list
``

To delete a pipeline run, use:

``bash
zenml pipeline runs delete <PIPELINE_RUN_NAME_OR_ID>
``

If you run any of your pipelines with pipeline.run(schedule=…), ZenML keeps
track of the schedule and you can list all schedules via:

``bash
zenml pipeline schedule list
``

To delete a schedule, use:

``bash
zenml pipeline schedule delete <SCHEDULE_NAME_OR_ID>
``

Note, however, that this will only delete the reference saved in ZenML and does
NOT stop/delete the schedule in the respective orchestrator. This still needs to
be done manually. For example, using the Airflow orchestrator you would have
to open the web UI to manually click to stop the schedule from executing.

Each pipeline run automatically saves its artifacts in the artifact store. To
list all artifacts that have been saved, use:

``bash
zenml artifact list
``

Each artifact has one or several versions. To list artifact versions, use:

``bash
zenml artifact versions list
``

If you would like to rename an artifact or adjust the tags of an artifact or
artifact version, use the corresponding update command:

``bash
zenml artifact update <NAME> -n <NEW_NAME>
zenml artifact update <NAME> -t <TAG1> -t <TAG2> -r <TAG_TO_REMOVE>
zenml artifact version update <NAME> -v <VERSION> -t <TAG1> -t <TAG2> -r <TAG_TO_REMOVE>
``

The metadata of artifacts or artifact versions stored by ZenML can only be
deleted once they are no longer used by any pipeline runs. I.e., an artifact
version can only be deleted if the run that produced it and all runs that used
it as an input have been deleted. Similarly, an artifact can only be deleted if
all its versions can be deleted.

To delete all artifacts and artifact versions that are no longer linked to any
pipeline runs, use:

``bash
zenml artifact prune
``

You might find that some artifacts throw errors when you try to prune them,
likely because they were stored locally and no longer exist. If you wish to
continue pruning and to ignore these errors, please add the –ignore-errors
flag. Warning messages will still be output to the terminal during this
process.

Each pipeline run that requires Docker images also stores a build which
contains the image names used for this run. To list all builds, use:

``bash
zenml pipeline builds list
``

To delete a specific build, use:

``bash
zenml pipeline builds delete <BUILD_ID>
``

### Managing the local ZenML Dashboard

The ZenML dashboard is a web-based UI that allows you to visualize and navigate
the stack configurations, pipelines and pipeline runs tracked by ZenML among
other things. You can start the ZenML dashboard locally by running the following
command:

``bash
zenml up
``

This will start the dashboard on your local machine where you can access it at
the URL printed to the console.

If you have closed the dashboard in your browser and want to open it again,
you can run:

``bash
zenml show
``

If you want to stop the dashboard, simply run:

``bash
zenml down
``

The zenml up command has a few additional options that you can use to
customize how the ZenML dashboard is running.

By default, the dashboard is started as a background process. On some operating
systems, this capability is not available. In this case, you can use the
–blocking flag to start the dashboard in the foreground:

``bash
zenml up --blocking
``

This will block the terminal until you stop the dashboard with CTRL-C.

Another option you can use, if you have Docker installed on your machine, is to
run the dashboard in a Docker container. This is useful if you don’t want to
install all the Zenml server dependencies on your machine. To do so, simply run:

``bash
zenml up --docker
``

The TCP port and the host address that the dashboard uses to listen for
connections can also be customized. Using an IP address that is not the default
localhost or 127.0.0.1 is especially useful if you’re running some type of
local ZenML orchestrator, such as the k3d Kubeflow orchestrator or Docker
orchestrator, that cannot directly connect to the local ZenML server.

For example, to start the dashboard on port 9000 and have it listen
on all locally available interfaces on your machine, run:

``bash
zenml up --port 9000 --ip-address 0.0.0.0
``

Note that the above 0.0.0.0 IP address also exposes your ZenML dashboard
externally through your public interface. Alternatively, you can choose an
explicit IP address that is configured on one of your local interfaces, such as
the Docker bridge interface, which usually has the IP address 172.17.0.1:

``bash
zenml up --port 9000 --ip-address 172.17.0.1
``

### Connecting to a ZenML Server

The ZenML client can be [configured to connect to a remote database or ZenML
server]([https://docs.zenml.io/how-to/connecting-to-zenml](https://docs.zenml.io/how-to/connecting-to-zenml))
with the zenml connect command. If no arguments are supplied, ZenML
will attempt to connect to the last ZenML server deployed from the local host
using the ‘zenml deploy’ command:

``bash
zenml connect
``

To connect to a ZenML server, you can either pass the configuration as command
line arguments or as a YAML file:

``bash
zenml connect --url=https://zenml.example.com:8080 --no-verify-ssl
``

or

``bash
zenml connect --config=/path/to/zenml_server_config.yaml
``

The YAML file should have the following structure when connecting to a ZenML
server:

```
``
```

```
`
```

yaml
url: <The URL of the ZenML server>
verify_ssl: |

> <Either a boolean, in which case it controls whether the
> server’s TLS certificate is verified, or a string, in which case it
> must be a path to a CA certificate bundle to use or the CA bundle
> value itself>

```
``
```

```
`
```

Both options can be combined, in which case the command line arguments will
override the values in the YAML file. For example:

``bash
zenml connect --no-verify-ssl --config=/path/to/zenml_server_config.yaml
``

You can open the ZenML dashboard of your currently connected ZenML server using
the following command:

``bash
zenml show
``

If you would like to take a look at the logs for the ZenML server:

``bash
zenml logs
``

Note that if you have set your AUTO_OPEN_DASHBOARD environment variable to
false then this will not open the dashboard until you set it back to true.
To disconnect from the current ZenML server and revert to using the local
default database, use the following command:

``bash
zenml disconnect
``

You can inspect the current ZenML configuration at any given time using the
following command:

``bash
zenml status
``

Example output:

```
``
```

```
`
```

: zenml status

Running without an active repository root.
Connected to a ZenML server: ‘[https://ac8ef63af203226194a7725ee71d85a-7635928635.us-east-1.elb.amazonaws.com](https://ac8ef63af203226194a7725ee71d85a-7635928635.us-east-1.elb.amazonaws.com)’
The current user is: ‘default’
The active workspace is: ‘default’ (global)
The active stack is: ‘default’ (global)
The status of the local dashboard:

> ZenML server ‘local’

┏━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ URL            │ [http://172.17.0.1:9000](http://172.17.0.1:9000)      ┃
┠────────────────┼─────────────────────────────┨
┃ STATUS         │ ✅                          ┃
┠────────────────┼─────────────────────────────┨
┃ STATUS_MESSAGE │ Docker container is running ┃
┠────────────────┼─────────────────────────────┨
┃ CONNECTED      │                             ┃
┗━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

```
``
```

```
`
```

The `zenml connect` command can also be used to configure your client with
more advanced options, such as connecting directly to a local or remote SQL
database. In this case, the –raw-config flag must be passed to instruct the
CLI to not validate or fill in the missing configuration fields. For example,
to connect to a remote MySQL database, run:

``bash
zenml connect --raw-config --config=/path/to/mysql_config.yaml
``

with a YAML configuration file that looks like this:

```
``
```

```
`
```

yaml
type: sql
url: mysql://<username>:<password>@mysql.database.com/<database_name>
ssl_ca: |

> —–BEGIN CERTIFICATE—–
> …
> —–END CERTIFICATE—–

ssl_cert: null
ssl_key: null
ssl_verify_server_cert: false

```
``
```

```
`
```

Keep in mind, while connecting to a ZenML server, you will be provided with the
option to Trust this device. If you opt out of it a 24-hour token will be
issued for the authentication service. If you opt-in, you will be issued a 30-day token instead.

If you would like to see a list of all trusted devices, you can use:

``bash
zenml authorized-device list
``

or if you would like to get the details regarding a specific device,
you can use:

``bash
zenml authorized-device describe DEVICE_ID_OR_PREFIX
``

Alternatively, you can lock and unlock an authorized device by using the
following commands:

``bash
zenml authorized-device lock DEVICE_ID_OR_PREFIX
zenml authorized-device unlock DEVICE_ID_OR_PREFIX
``

Finally, you can remove an authorized device by using the delete command:

``bash
zenml authorized-device delete DEVICE_ID_OR_PREFIX
``

### Secrets management

ZenML offers a way to [securely store secrets associated with your other
stack components and infrastructure]([https://docs.zenml.io/getting-started/deploying-zenml/manage-the-deployed-services/secret-management](https://docs.zenml.io/getting-started/deploying-zenml/manage-the-deployed-services/secret-management)).
A ZenML Secret is a collection or grouping of key-value pairs stored by the
ZenML secrets store. ZenML Secrets are identified by a unique name which
allows you to fetch or reference them in your pipelines and stacks.

Depending on how you set up and deployed ZenML, the secrets store keeps secrets
in the local database or uses the ZenML server your client is connected to:

* if you are using the default ZenML client settings, or if you connect your

ZenML client to a local ZenML server started with zenml up, the secrets store
is using the same local SQLite database as the rest of ZenML
\* if you connect your ZenML client to a remote ZenML server, the
secrets are no longer managed on your local machine, but through the remote
server instead. Secrets are stored in whatever secrets store back-end the
remote server is configured to use. This can be a SQL database, one of the
managed cloud secrets management services, or even a custom back-end.

To create a secret, use the create command and pass the key-value pairs
as command-line arguments:

```
``
```

```
`
```

bash
zenml secret create SECRET_NAME –key1=value1 –key2=value2 –key3=value3 …

# Another option is to use the ‘–values’ option and provide key-value pairs in either JSON or YAML format.
zenml secret create SECRET_NAME –values=’{“key1”:”value2”,”key2”:”value2”,”key3”:”value3”}’

```
``
```

```
`
```

Note that when using the previous command the keys and values will be preserved in your bash_history file, so
you may prefer to use the interactive create command instead:

``shell
zenml secret create SECRET_NAME -i
``

As an alternative to the interactive mode, also useful for values that
are long or contain newline or special characters, you can also use the special
@ syntax to indicate to ZenML that the value needs to be read from a file:

```
``
```

```
`
```

bash
zenml secret create SECRET_NAME    –aws_access_key_id=1234567890    –aws_secret_access_key=abcdefghij    [–aws_session_token=@/path/to/token.txt](mailto:--aws_session_token=@/path/to/token.txt)

# Alternatively for providing key-value pairs, you can utilize the ‘–values’ option by specifying a file path containing
# key-value pairs in either JSON or YAML format.
zenml secret create SECRET_NAME [–values=@/path/to/token.txt](mailto:--values=@/path/to/token.txt)

```
``
```

```
`
```

To list all the secrets available, use the list command:

``bash
zenml secret list
``

To get the key-value pairs for a particular secret, use the get command:

``bash
zenml secret get SECRET_NAME
``

To update a secret, use the update command:

```
``
```

```
`
```

bash
zenml secret update SECRET_NAME –key1=value1 –key2=value2 –key3=value3 …

# Another option is to use the ‘–values’ option and provide key-value pairs in either JSON or YAML format.
zenml secret update SECRET_NAME –values=’{“key1”:”value2”,”key2”:”value2”,”key3”:”value3”}’

```
``
```

```
`
```

Note that when using the previous command the keys and values will be preserved in your bash_history file, so
you may prefer to use the interactive update command instead:

``shell
zenml secret update SECRET_NAME -i
``

Finally, to delete a secret, use the delete command:

``bash
zenml secret delete SECRET_NAME
``

Secrets can be scoped to a workspace or a user. By default, secrets
are scoped to the current workspace. To scope a secret to a user, use the
–scope user argument in the register command.

### Auth management

Building and maintaining an MLOps workflow can involve numerous third-party
libraries and external services. In most cases, this ultimately presents a
challenge in configuring uninterrupted, secure access to infrastructure
resources. In ZenML, Service Connectors streamline this process by abstracting
away the complexity of authentication and help you connect your stack to your
resources. You can find the full docs on the ZenML service connectors
[here]([https://docs.zenml.io/how-to/auth-management](https://docs.zenml.io/how-to/auth-management)).

The ZenML CLI features a variety of commands to help you manage your service
connectors. First of all, to explore all the types of service connectors
available in ZenML, you can use the following commands:

```
``
```

```
`
```

bash
# To get the complete list
zenml service-connector list-types

# To get the details regarding a single type
zenml service-connector describe-type

```
``
```

```
`
```

For each type of service connector, you will also see a list of supported
resource types. These types provide a way for organizing different resources
into logical classes based on the standard and/or protocol used to access them.
In addition to the resource types, each type will feature a different set of
authentication methods.

Once you decided which service connector to use, you can create it with the
register command as follows:

``bash
zenml service-connector register SERVICE_CONNECTOR_NAME     --type TYPE [--description DESCRIPTION] [--resource-type RESOURCE_TYPE]     [--auth-method AUTH_METHOD] ...
``

For more details on how to create a service connector, please refer to our
[docs]([https://docs.zenml.io/how-to/auth-management](https://docs.zenml.io/how-to/auth-management)).

To check if your service connector is registered properly, you can verify it.
By doing this, you can both check if it is configured correctly and also, you
can fetch the list of resources it has access to:

``bash
zenml service-connector verify SERVICE_CONNECTOR_NAME_ID_OR_PREFIX
``

Some service connectors come equipped with the capability of configuring
the clients and SDKs on your local machine with the credentials inferred from
your service connector. To use this functionality, simply use the login
command:

``bash
zenml service-connector login SERVICE_CONNECTOR_NAME_ID_OR_PREFIX
``

To list all the service connectors that you have registered, you can use:

``bash
zenml service-connector list
``

Moreover, if you would like to list all the resources accessible by your
service connectors, you can use the following command:

```
``
```

```
`
```

bash
zenml service-connector list-resources [–resource-type RESOURCE_TYPE] /

> [–connector-type CONNECTOR_TYPE] …

```
``
```

```
`
```

This command can possibly take a long time depending on the number of service
connectors you have registered. Consider using the right filters when you are
listing resources.

If you want to see the details about a specific service connector that you have
registered, you can use the describe command:

``bash
zenml service-connector describe SERVICE_CONNECTOR_NAME_ID_OR_PREFIX
``

You can update a registered service connector by using the update command.
Keep in mind that all service connector updates are validated before being
applied. If you want to disable this behavior please use the –no-verify
flag.

``bash
zenml service-connector update SERVICE_CONNECTOR_NAME_ID_OR_PREFIX ...
``

Finally, if you wish to remove a service connector, you can use the delete
command:

``bash
zenml service-connector delete SERVICE_CONNECTOR_NAME_ID_OR_PREFIX
``

### Managing users

When using the ZenML service, you can manage permissions by managing users
using the CLI. If you want to create a new user or delete an existing one,
run either

``bash
zenml user create USER_NAME
zenml user delete USER_NAME
``

To see a list of all users, run:

``bash
zenml user list
``

For detail about the particular user, use the describe command. By default,
(without a specific user name passed in) it will describe the active user:

``bash
zenml user describe [USER_NAME]
``

If you want to update any properties of a specific user, you can use the
update command. Use the –help flag to get a full list of available
properties to update:

``bash
zenml user update --help
``

If you want to change the password of the current user account:

``bash
zenml user change-password --help
``

### Service Accounts

ZenML supports the use of service accounts to authenticate clients to the
ZenML server using API keys. This is useful for automating tasks such as
running pipelines or deploying models.

To create a new service account, run:

``bash
zenml service-account create SERVICE_ACCOUNT_NAME
``

This command creates a service account and an API key for it. The API key is
displayed as part of the command output and cannot be retrieved later. You can
then use the issued API key to connect your ZenML client to the server with the
CLI:

``bash
zenml connect --url https://... --api-key <API_KEY>
``

or by setting the ZENML_STORE_URL and ZENML_STORE_API_KEY environment
variables when you set up your ZenML client for the first time:

``bash
export ZENML_STORE_URL=https://...
export ZENML_STORE_API_KEY=<API_KEY>
``

To see all the service accounts you’ve created and their API keys, use the
following commands:

``bash
zenml service-account list
zenml service-account api-key <SERVICE_ACCOUNT_NAME> list
``

Additionally, the following command allows you to more precisely inspect one of
these service accounts and an API key:

``bash
zenml service-account describe <SERVICE_ACCOUNT_NAME>
zenml service-account api-key <SERVICE_ACCOUNT_NAME> describe <API_KEY_NAME>
``

API keys don’t have an expiration date. For increased security, we recommend
that you regularly rotate the API keys to prevent unauthorized access to your
ZenML server. You can do this with the ZenML CLI:

``bash
zenml service-account api-key <SERVICE_ACCOUNT_NAME> rotate <API_KEY_NAME>
``

Running this command will create a new API key and invalidate the old one. The
new API key is displayed as part of the command output and cannot be retrieved
later. You can then use the new API key to connect your ZenML client to the
server just as described above.

When rotating an API key, you can also configure a retention period for the old
API key. This is useful if you need to keep the old API key for a while to
ensure that all your workloads have been updated to use the new API key. You can
do this with the –retain flag. For example, to rotate an API key and keep the
old one for 60 minutes, you can run the following command:

``bash
zenml service-account api-key <SERVICE_ACCOUNT_NAME> rotate <API_KEY_NAME>       --retain 60
``

For increased security, you can deactivate a service account or an API key using
one of the following commands:

``
zenml service-account update <SERVICE_ACCOUNT_NAME> --active false
zenml service-account api-key <SERVICE_ACCOUNT_NAME> update <API_KEY_NAME>       --active false
``

Deactivating a service account or an API key will prevent it from being used to
authenticate and has immediate effect on all workloads that use it.

To permanently delete an API key for a service account, use the following
command:

``bash
zenml service-account api-key <SERVICE_ACCOUNT_NAME> delete <API_KEY_NAME>
``

### Managing Code Repositories

[Code repositories]([https://docs.zenml.io/user-guide/production-guide/connect-code-repository](https://docs.zenml.io/user-guide/production-guide/connect-code-repository))
enable ZenML to keep track of the code version that you use for your pipeline
runs. Additionally, running a pipeline which is tracked in a registered code
repository can decrease the time it takes Docker to build images for
containerized stack components.

To register a code repository, use the following CLI
command:

``shell
zenml code-repository register <NAME> --type=<CODE_REPOSITORY_TYPE]    [--CODE_REPOSITORY_OPTIONS]
``

ZenML currently supports code repositories of type github and gitlab, but
you can also use your custom code repository implementation by passing the
type custom and a source of your repository class.

``shell
zenml code-repository register <NAME> --type=custom    --source=<CODE_REPOSITORY_SOURCE> [--CODE_REPOSITORY_OPTIONS]
``

The CODE_REPOSITORY_OPTIONS depend on the configuration necessary for the
type of code repository that you’re using.

If you want to list your registered code repositories, run:

``shell
zenml code-repository list
``

You can delete one of your registered code repositories like this:

``shell
zenml code-repository delete <REPOSITORY_NAME_OR_ID>
``

### Building an image without Runs

To build or run a pipeline from the CLI, you need to know the source path of
your pipeline. Let’s imagine you have defined your pipeline in a python file
called run.py like this:

```
``
```

```
`
```

python
from zenml import pipeline

@pipeline
def my_pipeline(…):

> # Connect your pipeline steps here
> pass

```
``
```

```
`
```

The source path of your pipeline will be run.my_pipeline. In a generalized
way, this will be <MODULE_PATH>.<PIPELINE_FUNCTION_NAME>. If the python file
defining the pipeline is not in your current directory, the module path consists
of the full path to the file, separated by dots, e.g.
some_directory.some_file.my_pipeline.

To [build Docker images for your pipeline]([https://docs.zenml.io/how-to/customize-docker-builds](https://docs.zenml.io/how-to/customize-docker-builds))
without actually running the pipeline, use:

``bash
zenml pipeline build <PIPELINE_SOURCE_PATH>
``

To specify settings for the Docker builds, use the –config/-c option of the
command. For more information about the structure of this configuration file,
check out the zenml.pipelines.base_pipeline.BasePipeline.build(…) method.

``bash
zenml pipeline build <PIPELINE_SOURCE_PATH> --config=<PATH_TO_CONFIG_YAML>
``

If you want to build the pipeline for a stack other than your current active
stack, use the –stack option.

``bash
zenml pipeline build <PIPELINE_SOURCE_PATH> --stack=<STACK_ID_OR_NAME>
``

To run a pipeline that was previously registered, use:

``bash
zenml pipeline run <PIPELINE_SOURCE_PATH>
``

To specify settings for the pipeline, use the –config/-c option of the
command. For more information about the structure of this configuration file,
check out the zenml.pipelines.base_pipeline.BasePipeline.run(…) method.

``bash
zenml pipeline run <PIPELINE_SOURCE_PATH> --config=<PATH_TO_CONFIG_YAML>
``

If you want to run the pipeline on a stack different than your current active
stack, use the –stack option.

``bash
zenml pipeline run <PIPELINE_SOURCE_PATH> --stack=<STACK_ID_OR_NAME>
``

### Tagging your resources with ZenML

When you are using ZenML, you can [use tags to organize and categorize your
assets]([https://docs.zenml.io/how-to/handle-data-artifacts/tagging](https://docs.zenml.io/how-to/handle-data-artifacts/tagging)).
This way, you can streamline your workflows and enhance the discoverability of
your resources more easily.

Currently, you can use tags with artifacts, models and their versions:

```
``
```

```
`
```

bash
# Tag the artifact
zenml artifact update ARTIFACT_NAME -t TAG_NAME

# Tag the artifact version
zenml artifact version update ARTIFACT_NAME ARTIFACT_VERSION -t TAG_NAME

# Tag an existing model
zenml model update MODEL_NAME –tag TAG_NAME

# Tag a specific model version
zenml model version update MODEL_NAME VERSION_NAME –tag TAG_NAME

```
``
```

```
`
```

Besides these interactions, you can also create a new tag by using the
register command:

``bash
zenml tag register -n TAG_NAME [-c COLOR]
``

If you would like to list all the tags that you have, you can use the command:

``bash
zenml tag list
``

To update the properties of a specific tag, you can use the update subcommand:

``bash
zenml tag update TAG_NAME_OR_ID [-n NEW_NAME] [-c NEW_COLOR]
``

Finally, in order to delete a tag, you can execute:

``bash
zenml tag delete TAG_NAME_OR_ID
``

### Managing the Global Configuration

The ZenML global configuration CLI commands cover options such as enabling or
disabling the collection of anonymous usage statistics, changing the logging
verbosity.

In order to help us better understand how the community uses ZenML, the library
reports anonymized usage statistics. You can always opt out by using the CLI
command:

``bash
zenml analytics opt-out
``

If you want to opt back in, use the following command:

``bash
zenml analytics opt-in
``

The verbosity of the ZenML client output can be configured using the
`zenml logging` command. For example, to set the verbosity to DEBUG, run:

``bash
zenml logging set-verbosity DEBUG
``

### Deploying ZenML to the cloud

The ZenML CLI provides a simple way to deploy ZenML to the cloud. Simply run

``bash
zenml deploy
``

You will be prompted to provide a name for your deployment and details like what
cloud provider you want to deploy to — and that’s it! It creates the
database and any VPCs, permissions, and more that are needed.

In order to be able to run the deploy command, you should have your cloud
provider’s CLI configured locally with permissions to create resources like
MySQL databases and networks.

### Deploying Stack Components

Stack components can be deployed directly via the CLI. You can use the deploy
subcommand for this. For example, you could deploy a GCP artifact store using
the following command:

``shell
zenml artifact-store deploy -f gcp -p gcp -r us-east1 -x project_id=zenml-core basic_gcp_artifact_store
``

For full documentation on this functionality, please refer to [the dedicated
documentation on stack component deploy]([https://docs.zenml.io/how-to/stack-deployment/deploy-a-stack-component](https://docs.zenml.io/how-to/stack-deployment/deploy-a-stack-component)).
