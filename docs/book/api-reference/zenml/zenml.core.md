# Core

&lt;!DOCTYPE html&gt;

zenml.core package — ZenML documentation  [ZenML](https://github.com/zenml-io/zenml/tree/25d9c27ff1e23c67d7247993006f83f8404d83c4/docs/sphinx_docs/_build/html/index.html)

*  [Site](https://github.com/zenml-io/zenml/tree/25d9c27ff1e23c67d7247993006f83f8404d83c4/docs/sphinx_docs/_build/html/index.html)
  * Contents:
    * [zenml](https://github.com/zenml-io/zenml/tree/25d9c27ff1e23c67d7247993006f83f8404d83c4/docs/sphinx_docs/_build/html/modules.html)
*  [Page](zenml.core.md)
  * * [zenml.core package](zenml.core.md)
      * [Submodules](zenml.core.md#submodules)
      * [zenml.core.base\_component module](zenml.core.md#module-zenml.core.base_component)
      * [zenml.core.component\_factory module](zenml.core.md#module-zenml.core.component_factory)
      * [zenml.core.constants module](zenml.core.md#module-zenml.core.constants)
      * [zenml.core.git\_wrapper module](zenml.core.md#module-zenml.core.git_wrapper)
      * [zenml.core.local\_service module](zenml.core.md#module-zenml.core.local_service)
      * [zenml.core.local\_service\_test module](zenml.core.md#module-zenml.core.local_service_test)
      * [zenml.core.mapping\_utils module](zenml.core.md#module-zenml.core.mapping_utils)
      * [zenml.core.repo module](zenml.core.md#module-zenml.core.repo)
      * [zenml.core.repo\_test module](zenml.core.md#module-zenml.core.repo_test)
      * [zenml.core.utils module](zenml.core.md#module-zenml.core.utils)
      * [Module contents](zenml.core.md#module-zenml.core)
* [ « zenml.config package](zenml.config.md)
* [ zenml.io package »](zenml.io.md)
*  [Source](https://github.com/zenml-io/zenml/tree/25d9c27ff1e23c67d7247993006f83f8404d83c4/docs/sphinx_docs/_build/html/_sources/zenml.core.rst.txt)

## zenml.core package[¶](zenml.core.md#zenml-core-package)

### Submodules[¶](zenml.core.md#submodules)

### zenml.core.base\_component module[¶](zenml.core.md#module-zenml.core.base_component)

 _class_ zenml.core.base\_component.BaseComponent\(_\*_, _uuid: uuid.UUID = None_\)[¶](zenml.core.md#zenml.core.base_component.BaseComponent)

Bases: `pydantic.env_settings.BaseSettings`

Class definition for the base config.

The base component class defines the basic serialization / deserialization of various components used in ZenML. The logic of the serialization / deserialization is as follows:

* If a uuid is passed in, then the object is read from a file, so the

constructor becomes a query for an object that is assumed to already been serialized. \* If a ‘uuid\` is NOT passed, then a new object is created with the default args \(and any other args that are passed\), and therefore a fresh serialization takes place. _class_ Config[¶](zenml.core.md#zenml.core.base_component.BaseComponent.Config)

Bases: `object`

Configuration of settings. env\_prefix _= 'zenml\_'_[¶](zenml.core.md#zenml.core.base_component.BaseComponent.Config.env_prefix) delete\(\)[¶](zenml.core.md#zenml.core.base_component.BaseComponent.delete)

Deletes the persisted state of this object. _abstract_ get\_serialization\_dir\(\) → str[¶](zenml.core.md#zenml.core.base_component.BaseComponent.get_serialization_dir)

Return the dir where object is serialized. get\_serialization\_file\_name\(\) → str[¶](zenml.core.md#zenml.core.base_component.BaseComponent.get_serialization_file_name)

Return the name of the file where object is serialized. This has a sane default in cases where uuid is not passed externally, and therefore reading from a serialize file is not an option for the table. However, we still this function to go through without an exception, therefore the sane default. get\_serialization\_full\_path\(\) → str[¶](zenml.core.md#zenml.core.base_component.BaseComponent.get_serialization_full_path)

Returns the full path of the serialization file. update\(\)[¶](zenml.core.md#zenml.core.base_component.BaseComponent.update)

Persist the current state of the component.

Calling this will result in a persistent, stateful change in the system. uuid_: Optional\[uuid.UUID\]_[¶](zenml.core.md#zenml.core.base_component.BaseComponent.uuid)

### zenml.core.component\_factory module[¶](zenml.core.md#module-zenml.core.component_factory)

Factory to register all components. _class_ zenml.core.component\_factory.ComponentFactory\(_name: str_\)[¶](zenml.core.md#zenml.core.component_factory.ComponentFactory)

Bases: `object`

Definition of ComponentFactory to track all BaseComponent subclasses.

All BaseComponents \(including custom ones\) are to be registered here. get\_components\(\) → Dict\[Any, Any\][¶](zenml.core.md#zenml.core.component_factory.ComponentFactory.get_components)

Return all components get\_single\_component\(_key: str_\) → Any[¶](zenml.core.md#zenml.core.component_factory.ComponentFactory.get_single_component)

Get a registered component from a key. register\(_name: str_\) → Callable[¶](zenml.core.md#zenml.core.component_factory.ComponentFactory.register)

Class method to register Executor class to the internal registry.Parameters

**name** \(_str_\) – The name of the executor.Returns

The Executor class itself. register\_component\(_key: str_, _component: Any_\)[¶](zenml.core.md#zenml.core.component_factory.ComponentFactory.register_component)

### zenml.core.constants module[¶](zenml.core.md#module-zenml.core.constants)

### zenml.core.git\_wrapper module[¶](zenml.core.md#module-zenml.core.git_wrapper)

Wrapper class to handle Git integration _class_ zenml.core.git\_wrapper.GitWrapper\(_repo\_path: str_\)[¶](zenml.core.md#zenml.core.git_wrapper.GitWrapper)

Bases: `object`

Wrapper class for Git.

This class is responsible for handling git interactions, primarily handling versioning of different steps in pipelines. add\_gitignore\(_items: List\[str\]_\)[¶](zenml.core.md#zenml.core.git_wrapper.GitWrapper.add_gitignore)

Adds items to .gitignore, if .gitignore exists. Otherwise creates and adds.Parameters

**items** \(_list\[str\]_\) – Items to add. check\_file\_committed\(_file\_path: str_\) → bool[¶](zenml.core.md#zenml.core.git_wrapper.GitWrapper.check_file_committed)

Checks file is committed. If yes, return True, else False.Parameters

**file\_path** \(_str_\) – Path to any file within the ZenML repo. check\_module\_clean\(_source: str_\)[¶](zenml.core.md#zenml.core.git_wrapper.GitWrapper.check_module_clean)

Returns True if all files within source’s module are committed.Parameters

**source** \(_str_\) – relative module path pointing to a Class. checkout\(_sha\_or\_branch: Optional\[str\] = None_, _directory: Optional\[str\] = None_\)[¶](zenml.core.md#zenml.core.git_wrapper.GitWrapper.checkout)

Wrapper for git checkoutParameters

* **sha\_or\_branch** – hex string of len 40 representing git sha OR
* **branch** \(_name of_\) –
* **directory** \(_str_\) – relative path to directory to scope checkout

 get\_current\_sha\(\) → str[¶](zenml.core.md#zenml.core.git_wrapper.GitWrapper.get_current_sha)

Finds the git sha that each file within the module is currently on. is\_valid\_source\(_source: str_\) → bool[¶](zenml.core.md#zenml.core.git_wrapper.GitWrapper.is_valid_source)

Checks whether the source\_path is valid or not.Parameters

**source** \(_str_\) – class\_source e.g. this.module.Class\[@pin\]. load\_source\_path\_class\(_source: str_\) → Type[¶](zenml.core.md#zenml.core.git_wrapper.GitWrapper.load_source_path_class)

Loads a Python class from the source.Parameters

**source** – class\_source e.g. this.module.Class\[@sha\] reset\(_directory: Optional\[str\] = None_\)[¶](zenml.core.md#zenml.core.git_wrapper.GitWrapper.reset)

Wrapper for git reset HEAD &lt;directory&gt;.Parameters

**directory** \(_str_\) – relative path to directory to scope checkout resolve\_class\(_class\_: Type_\) → str[¶](zenml.core.md#zenml.core.git_wrapper.GitWrapper.resolve_class)

Resolves :param [class\_](zenml.core.md#id1): A Python Class reference.

Returns: source\_path e.g. this.module.Class\[@pin\]. resolve\_class\_source\(_class\_source: str_\) → str[¶](zenml.core.md#zenml.core.git_wrapper.GitWrapper.resolve_class_source)

Resolves class\_source with an optional pin. Takes source \(e.g. this.module.ClassName\), and appends relevant sha to it if the files within module are all committed. If even one file is not committed, then returns source unchanged.Parameters

**class\_source** \(_str_\) – class\_source e.g. this.module.Class stash\(\)[¶](zenml.core.md#zenml.core.git_wrapper.GitWrapper.stash)

Wrapper for git stash stash\_pop\(\)[¶](zenml.core.md#zenml.core.git_wrapper.GitWrapper.stash_pop)

Wrapper for git stash pop. Only pops if there’s something to pop.

### zenml.core.local\_service module[¶](zenml.core.md#module-zenml.core.local_service)

 _class_ zenml.core.local\_service.LocalService\(_\*_, _uuid: uuid.UUID = None_, _stacks: Dict\[str,_ [_zenml.stacks.base\_stack.BaseStack_](zenml.stacks.md#zenml.stacks.base_stack.BaseStack)_\] = {}_, _metadata\_store\_map: Dict\[str,_ [_zenml.core.mapping\_utils.UUIDSourceTuple_](zenml.core.md#zenml.core.mapping_utils.UUIDSourceTuple)_\] = {}_, _artifact\_store\_map: Dict\[str,_ [_zenml.core.mapping\_utils.UUIDSourceTuple_](zenml.core.md#zenml.core.mapping_utils.UUIDSourceTuple)_\] = {}_, _orchestrator\_map: Dict\[str,_ [_zenml.core.mapping\_utils.UUIDSourceTuple_](zenml.core.md#zenml.core.mapping_utils.UUIDSourceTuple)_\] = {}_\)[¶](zenml.core.md#zenml.core.local_service.LocalService)

Bases: [`zenml.core.base_component.BaseComponent`](zenml.core.md#zenml.core.base_component.BaseComponent)

Definition of a local service that keeps track of all ZenML components. artifact\_store\_map_: Dict\[str,_ [_zenml.core.mapping\_utils.UUIDSourceTuple_](zenml.core.md#zenml.core.mapping_utils.UUIDSourceTuple)_\]_[¶](zenml.core.md#zenml.core.local_service.LocalService.artifact_store_map) _property_ artifact\_stores_: Dict\[str,_ [_zenml.artifact\_stores.base\_artifact\_store.BaseArtifactStore_](zenml.artifact_stores.md#zenml.artifact_stores.base_artifact_store.BaseArtifactStore)_\]_[¶](zenml.core.md#zenml.core.local_service.LocalService.artifact_stores)

Returns all registered artifact stores. delete\(\)[¶](zenml.core.md#zenml.core.local_service.LocalService.delete)

Deletes the entire service. Dangerous operation delete\_artifact\_store\(_key: str_\)[¶](zenml.core.md#zenml.core.local_service.LocalService.delete_artifact_store)

Delete an artifact\_store.Parameters

**key** – Unique key of artifact\_store. delete\_metadata\_store\(_key: str_\)[¶](zenml.core.md#zenml.core.local_service.LocalService.delete_metadata_store)

Delete a metadata store.Parameters

**key** – Unique key of metadata store. delete\_orchestrator\(_key: str_\)[¶](zenml.core.md#zenml.core.local_service.LocalService.delete_orchestrator)

Delete a orchestrator.Parameters

**key** – Unique key of orchestrator. delete\_stack\(_key: str_\)[¶](zenml.core.md#zenml.core.local_service.LocalService.delete_stack)

Delete a stack specified with a key.Parameters

**key** – Unique key of stack. get\_artifact\_store\(_key: str_\) → [zenml.artifact\_stores.base\_artifact\_store.BaseArtifactStore](zenml.artifact_stores.md#zenml.artifact_stores.base_artifact_store.BaseArtifactStore)[¶](zenml.core.md#zenml.core.local_service.LocalService.get_artifact_store)

Return a single artifact store based on key.Parameters

**key** – Unique key of artifact store.Returns

Stack specified by key. get\_metadata\_store\(_key: str_\) → [zenml.metadata.base\_metadata\_store.BaseMetadataStore](zenml.metadata.md#zenml.metadata.base_metadata_store.BaseMetadataStore)[¶](zenml.core.md#zenml.core.local_service.LocalService.get_metadata_store)

Return a single metadata store based on key.Parameters

**key** – Unique key of metadata store.Returns

Metadata store specified by key. get\_orchestrator\(_key: str_\) → [zenml.orchestrators.base\_orchestrator.BaseOrchestrator](zenml.orchestrators/#zenml.orchestrators.base_orchestrator.BaseOrchestrator)[¶](zenml.core.md#zenml.core.local_service.LocalService.get_orchestrator)

Return a single orchestrator based on key.Parameters

**key** – Unique key of orchestrator.Returns

Orchestrator specified by key. get\_serialization\_dir\(\) → str[¶](zenml.core.md#zenml.core.local_service.LocalService.get_serialization_dir)

The local service stores everything in the zenml config dir. get\_serialization\_file\_name\(\) → str[¶](zenml.core.md#zenml.core.local_service.LocalService.get_serialization_file_name)

Return the name of the file where object is serialized. get\_stack\(_key: str_\) → [zenml.stacks.base\_stack.BaseStack](zenml.stacks.md#zenml.stacks.base_stack.BaseStack)[¶](zenml.core.md#zenml.core.local_service.LocalService.get_stack)

Return a single stack based on key.Parameters

**key** – Unique key of stack.Returns

Stack specified by key. metadata\_store\_map_: Dict\[str,_ [_zenml.core.mapping\_utils.UUIDSourceTuple_](zenml.core.md#zenml.core.mapping_utils.UUIDSourceTuple)_\]_[¶](zenml.core.md#zenml.core.local_service.LocalService.metadata_store_map) _property_ metadata\_stores_: Dict\[str,_ [_zenml.metadata.base\_metadata\_store.BaseMetadataStore_](zenml.metadata.md#zenml.metadata.base_metadata_store.BaseMetadataStore)_\]_[¶](zenml.core.md#zenml.core.local_service.LocalService.metadata_stores)

Returns all registered metadata stores. orchestrator\_map_: Dict\[str,_ [_zenml.core.mapping\_utils.UUIDSourceTuple_](zenml.core.md#zenml.core.mapping_utils.UUIDSourceTuple)_\]_[¶](zenml.core.md#zenml.core.local_service.LocalService.orchestrator_map) _property_ orchestrators_: Dict\[str,_ [_zenml.orchestrators.base\_orchestrator.BaseOrchestrator_](zenml.orchestrators/#zenml.orchestrators.base_orchestrator.BaseOrchestrator)_\]_[¶](zenml.core.md#zenml.core.local_service.LocalService.orchestrators)

Returns all registered orchestrators. register\_artifact\_store\(_key: str_, _artifact\_store:_ [_zenml.artifact\_stores.base\_artifact\_store.BaseArtifactStore_](zenml.artifact_stores.md#zenml.artifact_stores.base_artifact_store.BaseArtifactStore)\)[¶](zenml.core.md#zenml.core.local_service.LocalService.register_artifact_store)

Register an artifact store.Parameters

* **artifact\_store** – Artifact store to be registered.
* **key** – Unique key for the artifact store.

 register\_metadata\_store\(_key: str_, _metadata\_store:_ [_zenml.metadata.base\_metadata\_store.BaseMetadataStore_](zenml.metadata.md#zenml.metadata.base_metadata_store.BaseMetadataStore)\)[¶](zenml.core.md#zenml.core.local_service.LocalService.register_metadata_store)

Register a metadata store.Parameters

* **metadata\_store** – Metadata store to be registered.
* **key** – Unique key for the metadata store.

 register\_orchestrator\(_key: str_, _orchestrator:_ [_zenml.orchestrators.base\_orchestrator.BaseOrchestrator_](zenml.orchestrators/#zenml.orchestrators.base_orchestrator.BaseOrchestrator)\)[¶](zenml.core.md#zenml.core.local_service.LocalService.register_orchestrator)

Register an orchestrator.Parameters

* **orchestrator** – Metadata store to be registered.
* **key** – Unique key for the orchestrator.

 register\_stack\(_key: str_, _stack:_ [_zenml.stacks.base\_stack.BaseStack_](zenml.stacks.md#zenml.stacks.base_stack.BaseStack)\)[¶](zenml.core.md#zenml.core.local_service.LocalService.register_stack)

Register a stack.Parameters

* **key** – Unique key for the stack.
* **stack** – Stack to be registered.

 stacks_: Dict\[str,_ [_zenml.stacks.base\_stack.BaseStack_](zenml.stacks.md#zenml.stacks.base_stack.BaseStack)_\]_[¶](zenml.core.md#zenml.core.local_service.LocalService.stacks)

### zenml.core.local\_service\_test module[¶](zenml.core.md#module-zenml.core.local_service_test)

 zenml.core.local\_service\_test.test\_service\_crud\(\)[¶](zenml.core.md#zenml.core.local_service_test.test_service_crud)

Test basic service crud.

### zenml.core.mapping\_utils module[¶](zenml.core.md#module-zenml.core.mapping_utils)

 _class_ zenml.core.mapping\_utils.UUIDSourceTuple\(_\*_, _uuid: uuid.UUID_, _source: str_\)[¶](zenml.core.md#zenml.core.mapping_utils.UUIDSourceTuple)

Bases: `pydantic.main.BaseModel` source_: str_[¶](zenml.core.md#zenml.core.mapping_utils.UUIDSourceTuple.source) uuid_: uuid.UUID_[¶](zenml.core.md#zenml.core.mapping_utils.UUIDSourceTuple.uuid) zenml.core.mapping\_utils.get\_component\_from\_key\(_key: str_, _mapping: Dict\[str,_ [_zenml.core.mapping\_utils.UUIDSourceTuple_](zenml.core.md#zenml.core.mapping_utils.UUIDSourceTuple)_\]_\) → [zenml.core.base\_component.BaseComponent](zenml.core.md#zenml.core.base_component.BaseComponent)[¶](zenml.core.md#zenml.core.mapping_utils.get_component_from_key)

Given a key and a mapping, return an initialized component.Parameters

* **key** – Unique key.
* **mapping** – Dict of type Text -&gt; UUIDSourceTuple.

Returns

An object which is a subclass of type BaseComponent. zenml.core.mapping\_utils.get\_components\_from\_store\(_store\_name: str_, _mapping: Dict\[str,_ [_zenml.core.mapping\_utils.UUIDSourceTuple_](zenml.core.md#zenml.core.mapping_utils.UUIDSourceTuple)_\]_\) → Dict\[str, [zenml.core.base\_component.BaseComponent](zenml.core.md#zenml.core.base_component.BaseComponent)\][¶](zenml.core.md#zenml.core.mapping_utils.get_components_from_store)

Returns a list of components from a store.Parameters

* **store\_name** – Name of the store.
* **mapping** – Dict of type Text -&gt; UUIDSourceTuple.

Returns

A dict of objects which are a subclass of type BaseComponent. zenml.core.mapping\_utils.get\_key\_from\_uuid\(_uuid: uuid.UUID_, _mapping: Dict\[str,_ [_zenml.core.mapping\_utils.UUIDSourceTuple_](zenml.core.md#zenml.core.mapping_utils.UUIDSourceTuple)_\]_\) → str[¶](zenml.core.md#zenml.core.mapping_utils.get_key_from_uuid)

Return they key that points to a certain uuid in a mapping.Parameters

**uuid** – uuid to query.Returns

Returns the key from the mapping.

### zenml.core.repo module[¶](zenml.core.md#module-zenml.core.repo)

Base ZenML repository _class_ zenml.core.repo.Repository\(_path: Optional\[str\] = None_\)[¶](zenml.core.md#zenml.core.repo.Repository)

Bases: `object`

ZenML repository definition.

Every ZenML project exists inside a ZenML repository. clean\(\)[¶](zenml.core.md#zenml.core.repo.Repository.clean)

Deletes associated metadata store, pipelines dir and artifacts get\_active\_stack\(\) → [zenml.stacks.base\_stack.BaseStack](zenml.stacks.md#zenml.stacks.base_stack.BaseStack)[¶](zenml.core.md#zenml.core.repo.Repository.get_active_stack)

Get the active stack from global config.Returns

Currently active stack. get\_active\_stack\_key\(\) → str[¶](zenml.core.md#zenml.core.repo.Repository.get_active_stack_key)

Get the active stack key from global config.Returns

Currently active stacks key. get\_git\_wrapper\(\) → [zenml.core.git\_wrapper.GitWrapper](zenml.core.md#zenml.core.git_wrapper.GitWrapper)[¶](zenml.core.md#zenml.core.repo.Repository.get_git_wrapper) get\_pipeline\_by\_name\(_pipeline\_name: Optional\[str\] = None_\)[¶](zenml.core.md#zenml.core.repo.Repository.get_pipeline_by_name)

Loads a pipeline just by its name.Parameters

**pipeline\_name** \(_str_\) – Name of pipeline. get\_pipeline\_names\(\) → Optional\[List\[str\]\][¶](zenml.core.md#zenml.core.repo.Repository.get_pipeline_names)

Gets list of pipeline \(unique\) names get\_pipelines\(_\*\*kwargs_\)[¶](zenml.core.md#zenml.core.repo.Repository.get_pipelines) get\_pipelines\_by\_type\(_type\_filter: List\[str\]_\) → List[¶](zenml.core.md#zenml.core.repo.Repository.get_pipelines_by_type)

Gets list of pipelines filtered by type.Parameters

**type\_filter** \(_list_\) – list of types to filter by. get\_service\(\) → [zenml.core.local\_service.LocalService](zenml.core.md#zenml.core.local_service.LocalService)[¶](zenml.core.md#zenml.core.repo.Repository.get_service)

Returns the active service. For now, always local. get\_step\_by\_version\(_\*\*kwargs_\)[¶](zenml.core.md#zenml.core.repo.Repository.get_step_by_version) get\_step\_versions\(_\*\*kwargs_\)[¶](zenml.core.md#zenml.core.repo.Repository.get_step_versions) get\_step\_versions\_by\_type\(_step\_type: Union\[Type, str\]_\)[¶](zenml.core.md#zenml.core.repo.Repository.get_step_versions_by_type)

List all registered steps in repository by step\_type.Parameters

* **step\_type** – either a string specifying full source of the step or a
* **type.** \(_python class_\) –

 _static_ init\_repo\(_\*args_, _\*\*kwargs_\)[¶](zenml.core.md#zenml.core.repo.Repository.init_repo) set\_active\_stack\(_stack\_key: str_\)[¶](zenml.core.md#zenml.core.repo.Repository.set_active_stack)

Set the active stack for the repo. This change is local for the machine.Parameters

**stack\_key** – Key of the stack to set active.

### zenml.core.repo\_test module[¶](zenml.core.md#module-zenml.core.repo_test)

### zenml.core.utils module[¶](zenml.core.md#module-zenml.core.utils)

 zenml.core.utils.define\_json\_config\_settings\_source\(_config\_dir: str_, _config\_name: str_\) → Callable[¶](zenml.core.md#zenml.core.utils.define_json_config_settings_source)

Define a function to essentially deserialize a model from a serialized json config.Parameters

* **config\_dir** – A path to a dir where we want the config file to exist.
* **config\_name** – Full name of config file.

Returns

A json\_config\_settings\_source callable reading from the passed path. zenml.core.utils.generate\_customise\_sources\(_file\_dir: str_, _file\_name: str_\)[¶](zenml.core.md#zenml.core.utils.generate_customise_sources)

Generate a customise\_sources function as defined here: [https://pydantic-docs.helpmanual.io/usage/settings/](https://pydantic-docs.helpmanual.io/usage/settings/). This function generates a function that configures the priorities of the sources through which the model is loaded. The important thing to note here is that the define\_json\_config\_settings\_source is dynamically generates with the provided file\_dir and file\_name. This allows us to dynamically generate a file name for the serialization and deserialization of the model.Parameters

* **file\_dir** – Dir where file is stored.
* **file\_name** – Name of the file to persist.

Returns

A customise\_sources class method to be defined the a Pydantic BaseSettings inner Config class.

### Module contents[¶](zenml.core.md#module-zenml.core)

 [Back to top](zenml.core.md)

 © Copyright 2021, ZenML GmbH.  
 Created using [Sphinx](http://sphinx-doc.org/) 4.2.0.  


