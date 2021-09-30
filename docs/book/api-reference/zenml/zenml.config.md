# Config

&lt;!DOCTYPE html&gt;

zenml.config package — ZenML documentation  [ZenML](https://github.com/zenml-io/zenml/tree/f912d2d512477e6ed84e839259d42cb73eeedf2b/docs/sphinx_docs/_build/html/index.html)

*  [Site](https://github.com/zenml-io/zenml/tree/f912d2d512477e6ed84e839259d42cb73eeedf2b/docs/sphinx_docs/_build/html/index.html)
  * Contents:
    * [zenml](https://github.com/zenml-io/zenml/tree/f912d2d512477e6ed84e839259d42cb73eeedf2b/docs/sphinx_docs/_build/html/modules.html)
*  [Page](zenml.config.md)
  * * [zenml.config package](zenml.config.md)
      * [Submodules](zenml.config.md#submodules)
      * [zenml.config.constants module](zenml.config.md#module-zenml.config.constants)
      * [zenml.config.global\_config module](zenml.config.md#module-zenml.config.global_config)
      * [Module contents](zenml.config.md#module-zenml.config)
* [ « zenml.cli package](zenml.cli.md)
* [ zenml.core package »](zenml.core.md)
*  [Source](https://github.com/zenml-io/zenml/tree/f912d2d512477e6ed84e839259d42cb73eeedf2b/docs/sphinx_docs/_build/html/_sources/zenml.config.rst.txt)

## zenml.config package[¶](zenml.config.md#zenml-config-package)

### Submodules[¶](zenml.config.md#submodules)

### zenml.config.constants module[¶](zenml.config.md#module-zenml.config.constants)

### zenml.config.global\_config module[¶](zenml.config.md#module-zenml.config.global_config)

Global config for the ZenML installation. _class_ zenml.config.global\_config.GlobalConfig\(_\*_, _uuid: uuid.UUID = None_, _user\_id: uuid.UUID = None_, _analytics\_opt\_in: bool = True_, _repo\_active\_stacks: Dict\[str, str\] = {}_\)[¶](zenml.config.md#zenml.config.global_config.GlobalConfig)

Bases: [`zenml.core.base_component.BaseComponent`](zenml.core.md#zenml.core.base_component.BaseComponent)

Class definition for the global config.

Defines global data such as unique user ID and whether they opted in for analytics. analytics\_opt\_in_: bool_[¶](zenml.config.md#zenml.config.global_config.GlobalConfig.analytics_opt_in) get\_serialization\_dir\(\) → str[¶](zenml.config.md#zenml.config.global_config.GlobalConfig.get_serialization_dir)

Gets the global config dir for installed package. get\_serialization\_file\_name\(\) → str[¶](zenml.config.md#zenml.config.global_config.GlobalConfig.get_serialization_file_name)

Gets the global config dir for installed package. repo\_active\_stacks_: Optional\[Dict\[str, str\]\]_[¶](zenml.config.md#zenml.config.global_config.GlobalConfig.repo_active_stacks) set\_stack\_for\_repo\(_repo\_path: str_, _stack\_key: str_\)[¶](zenml.config.md#zenml.config.global_config.GlobalConfig.set_stack_for_repo) user\_id_: uuid.UUID_[¶](zenml.config.md#zenml.config.global_config.GlobalConfig.user_id)

### Module contents[¶](zenml.config.md#module-zenml.config)

 [Back to top](zenml.config.md)

 © Copyright 2021, ZenML GmbH.  
 Created using [Sphinx](http://sphinx-doc.org/) 4.2.0.  


