# Stacks

&lt;!DOCTYPE html&gt;

zenml.stacks package — ZenML documentation  [ZenML](https://github.com/zenml-io/zenml/tree/154f041af2db9874b351cccd305478a173a7e939/docs/sphinx_docs/_build/html/index.html)

*  [Site](https://github.com/zenml-io/zenml/tree/154f041af2db9874b351cccd305478a173a7e939/docs/sphinx_docs/_build/html/index.html)
  * Contents:
    * [zenml](https://github.com/zenml-io/zenml/tree/154f041af2db9874b351cccd305478a173a7e939/docs/sphinx_docs/_build/html/modules.html)
*  [Page](zenml.stacks.md)
  * * [zenml.stacks package](zenml.stacks.md)
      * [Submodules](zenml.stacks.md#submodules)
      * [zenml.stacks.base\_stack module](zenml.stacks.md#module-zenml.stacks.base_stack)
      * [zenml.stacks.constants module](zenml.stacks.md#module-zenml.stacks.constants)
      * [Module contents](zenml.stacks.md#module-zenml.stacks)
* [ « zenml.pipelin...](zenml.pipelines.md)
* [ zenml.steps package »](zenml.steps.md)
*  [Source](https://github.com/zenml-io/zenml/tree/154f041af2db9874b351cccd305478a173a7e939/docs/sphinx_docs/_build/html/_sources/zenml.stacks.rst.txt)

## zenml.stacks package[¶](zenml.stacks.md#zenml-stacks-package)

### Submodules[¶](zenml.stacks.md#submodules)

### zenml.stacks.base\_stack module[¶](zenml.stacks.md#module-zenml.stacks.base_stack)

 _class_ zenml.stacks.base\_stack.BaseStack\(_\_env\_file: Optional\[Union\[pathlib.Path, str\]\] = '&lt;object object&gt;'_, _\_env\_file\_encoding: Optional\[str\] = None_, _\_secrets\_dir: Optional\[Union\[pathlib.Path, str\]\] = None_, _\*_, _stack\_type:_ [_zenml.enums.StackTypes_](./#zenml.enums.StackTypes) _= StackTypes.base_, _metadata\_store\_name: str_, _artifact\_store\_name: str_, _orchestrator\_name: str_\)[¶](zenml.stacks.md#zenml.stacks.base_stack.BaseStack)

Bases: `pydantic.env_settings.BaseSettings`

Base stack for ZenML.

A ZenML stack brings together an Metadata Store, an Artifact Store, and an Orchestrator, the trifecta of the environment required to run a ZenML pipeline. A ZenML stack also happens to be a pydantic BaseSettings class, which means that there are multiple ways to use it.

* You can set it via env variables.
* You can set it through the config yaml file.
* You can set it in code by initializing an object of this class, and

passing it to pipelines as a configuration.

In the case where a value is specified for the same Settings field in multiple ways, the selected value is determined as follows \(in descending order of priority\):

* Arguments passed to the Settings class initializer.
* Environment variables, e.g. zenml\_var as described above.
* Variables loaded from a config yaml file.
* The default field values.

 _class_ Config[¶](zenml.stacks.md#zenml.stacks.base_stack.BaseStack.Config)

Bases: `object`

Configuration of settings. env\_prefix _= 'zenml\_stack\_'_[¶](zenml.stacks.md#zenml.stacks.base_stack.BaseStack.Config.env_prefix) _property_ artifact\_store_:_ [_zenml.artifact\_stores.base\_artifact\_store.BaseArtifactStore_](zenml.artifact_stores.md#zenml.artifact_stores.base_artifact_store.BaseArtifactStore)[¶](zenml.stacks.md#zenml.stacks.base_stack.BaseStack.artifact_store) artifact\_store\_name_: str_[¶](zenml.stacks.md#zenml.stacks.base_stack.BaseStack.artifact_store_name) _property_ metadata\_store_:_ [_zenml.metadata.base\_metadata\_store.BaseMetadataStore_](zenml.metadata.md#zenml.metadata.base_metadata_store.BaseMetadataStore)[¶](zenml.stacks.md#zenml.stacks.base_stack.BaseStack.metadata_store) metadata\_store\_name_: str_[¶](zenml.stacks.md#zenml.stacks.base_stack.BaseStack.metadata_store_name) _property_ orchestrator_:_ [_zenml.orchestrators.base\_orchestrator.BaseOrchestrator_](zenml.orchestrators/#zenml.orchestrators.base_orchestrator.BaseOrchestrator)[¶](zenml.stacks.md#zenml.stacks.base_stack.BaseStack.orchestrator) orchestrator\_name_: str_[¶](zenml.stacks.md#zenml.stacks.base_stack.BaseStack.orchestrator_name) stack\_type_:_ [_zenml.enums.StackTypes_](./#zenml.enums.StackTypes)[¶](zenml.stacks.md#zenml.stacks.base_stack.BaseStack.stack_type)

### zenml.stacks.constants module[¶](zenml.stacks.md#module-zenml.stacks.constants)

### Module contents[¶](zenml.stacks.md#module-zenml.stacks)

 [Back to top](zenml.stacks.md)

 © Copyright 2021, ZenML GmbH.  
 Created using [Sphinx](http://sphinx-doc.org/) 4.2.0.  


