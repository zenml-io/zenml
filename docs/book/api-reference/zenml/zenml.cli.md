# Cli

&lt;!DOCTYPE html&gt;

zenml.cli package — ZenML documentation  [ZenML](https://github.com/zenml-io/zenml/tree/25d9c27ff1e23c67d7247993006f83f8404d83c4/docs/sphinx_docs/_build/html/index.html)

*  [Site](https://github.com/zenml-io/zenml/tree/25d9c27ff1e23c67d7247993006f83f8404d83c4/docs/sphinx_docs/_build/html/index.html)
  * Contents:
    * [zenml](https://github.com/zenml-io/zenml/tree/25d9c27ff1e23c67d7247993006f83f8404d83c4/docs/sphinx_docs/_build/html/modules.html)
*  [Page](zenml.cli.md)
  * * [zenml.cli package](zenml.cli.md)
      * [Submodules](zenml.cli.md#submodules)
      * [zenml.cli.base module](zenml.cli.md#module-zenml.cli.base)
      * [zenml.cli.cli module](zenml.cli.md#module-zenml.cli.cli)
      * [zenml.cli.config module](zenml.cli.md#module-zenml.cli.config)
      * [zenml.cli.example module](zenml.cli.md#module-zenml.cli.example)
      * [zenml.cli.pipeline module](zenml.cli.md#module-zenml.cli.pipeline)
      * [zenml.cli.stack module](zenml.cli.md#module-zenml.cli.stack)
      * [zenml.cli.step module](zenml.cli.md#module-zenml.cli.step)
      * [zenml.cli.utils module](zenml.cli.md#module-zenml.cli.utils)
      * [zenml.cli.version module](zenml.cli.md#module-zenml.cli.version)
      * [Module contents](zenml.cli.md#module-zenml.cli)
* [ « zenml.artifac...](https://github.com/zenml-io/zenml/tree/25d9c27ff1e23c67d7247993006f83f8404d83c4/docs/sphinx_docs/_build/html/zenml.artifacts.data_artifacts.html)
* [ zenml.config package »](zenml.config.md)
*  [Source](https://github.com/zenml-io/zenml/tree/25d9c27ff1e23c67d7247993006f83f8404d83c4/docs/sphinx_docs/_build/html/_sources/zenml.cli.rst.txt)

## zenml.cli package[¶](zenml.cli.md#zenml-cli-package)

### Submodules[¶](zenml.cli.md#submodules)

### zenml.cli.base module[¶](zenml.cli.md#module-zenml.cli.base)

### zenml.cli.cli module[¶](zenml.cli.md#module-zenml.cli.cli)

### zenml.cli.config module[¶](zenml.cli.md#module-zenml.cli.config)

CLI for manipulating ZenML local and global config file.

### zenml.cli.example module[¶](zenml.cli.md#module-zenml.cli.example)

 zenml.cli.example.get\_all\_examples\(\) → List\[str\][¶](zenml.cli.md#zenml.cli.example.get_all_examples)

Get all the examples zenml.cli.example.get\_example\_readme\(_example\_path_\) → str[¶](zenml.cli.md#zenml.cli.example.get_example_readme)

Get the example README file contents. zenml.cli.example.get\_examples\_dir\(\) → str[¶](zenml.cli.md#zenml.cli.example.get_examples_dir)

Return the examples dir.

### zenml.cli.pipeline module[¶](zenml.cli.md#module-zenml.cli.pipeline)

### zenml.cli.stack module[¶](zenml.cli.md#module-zenml.cli.stack)

CLI for manipulating ZenML local and global config file.

### zenml.cli.step module[¶](zenml.cli.md#module-zenml.cli.step)

### zenml.cli.utils module[¶](zenml.cli.md#module-zenml.cli.utils)

 zenml.cli.utils.confirmation\(_text: str_, _\*args_, _\*\*kwargs_\) → bool[¶](zenml.cli.md#zenml.cli.utils.confirmation)

Echo a confirmation string on the CLI.Parameters

* **text** – Input text string.
* **\*args** – Args to be passed to click.confirm\(\).
* **\*\*kwargs** – Kwargs to be passed to click.confirm\(\).

Returns

Boolean based on user response. zenml.cli.utils.declare\(_text: str_\)[¶](zenml.cli.md#zenml.cli.utils.declare)

Echo a declaration on the CLI.Parameters

**text** – Input text string. zenml.cli.utils.echo\_component\_list\(_component\_list: Dict\[str,_ [_zenml.core.base\_component.BaseComponent_](zenml.core.md#zenml.core.base_component.BaseComponent)_\]_\)[¶](zenml.cli.md#zenml.cli.utils.echo_component_list)

Echoes a list of components in a pretty style. zenml.cli.utils.error\(_text: str_\)[¶](zenml.cli.md#zenml.cli.utils.error)

Echo an error string on the CLI.Parameters

**text** – Input text string.Raises

**click.ClickException when called.** – zenml.cli.utils.format\_date\(_dt: datetime.datetime_, _format: str = '%Y-%m-%d %H:%M:%S'_\) → str[¶](zenml.cli.md#zenml.cli.utils.format_date)

Format a date into a string.Parameters

* **dt** – Datetime object to be formatted.
* **format** – The format in string you want the datetime formatted to.

Returns

Formatted string according to specification. zenml.cli.utils.format\_timedelta\(_td: datetime.timedelta_\) → str[¶](zenml.cli.md#zenml.cli.utils.format_timedelta)

Format a timedelta into a string.Parameters

**td** – datetime.timedelta object to be formatted.Returns

Formatted string according to specification. zenml.cli.utils.notice\(_text: str_\)[¶](zenml.cli.md#zenml.cli.utils.notice)

Echo a notice string on the CLI.Parameters

**text** – Input text string. zenml.cli.utils.parse\_unknown\_options\(_args: List\[str\]_\) → Dict\[str, Any\][¶](zenml.cli.md#zenml.cli.utils.parse_unknown_options)

Parse unknown options from the cli.Parameters

**args** – A list of strings from the CLI.Returns

Dict of parsed args. zenml.cli.utils.pretty\_print\(_obj: Any_\)[¶](zenml.cli.md#zenml.cli.utils.pretty_print)

Pretty print an object on the CLI.Parameters

**obj** – Any object with a \_\_str\_\_ method defined. zenml.cli.utils.question\(_text: str_, _\*args_, _\*\*kwargs_\) → Any[¶](zenml.cli.md#zenml.cli.utils.question)

Echo a question string on the CLI.Parameters

* **text** – Input text string.
* **\*args** – Args to be passed to click.prompt\(\).
* **\*\*kwargs** – Kwargs to be passed to click.prompt\(\).

Returns

The answer to the question of any type, usually string. zenml.cli.utils.title\(_text: str_\)[¶](zenml.cli.md#zenml.cli.utils.title)

Echo a title formatted string on the CLI.Parameters

**text** – Input text string. zenml.cli.utils.warning\(_text: str_\)[¶](zenml.cli.md#zenml.cli.utils.warning)

Echo a warning string on the CLI.Parameters

**text** – Input text string.

### zenml.cli.version module[¶](zenml.cli.md#module-zenml.cli.version)

### Module contents[¶](zenml.cli.md#module-zenml.cli)

 [Back to top](zenml.cli.md)

 © Copyright 2021, ZenML GmbH.  
 Created using [Sphinx](http://sphinx-doc.org/) 4.2.0.  


