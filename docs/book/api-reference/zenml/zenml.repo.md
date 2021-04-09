# Repo

&lt;!DOCTYPE html&gt;

zenml.repo package — ZenML documentation  [ZenML](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/index.html)

*  [Site](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/index.html)
  * Contents:
    * [zenml](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/modules.html)
*  [Page](zenml.repo.md)
  * * [zenml.repo package](zenml.repo.md)
      * [Submodules](zenml.repo.md#submodules)
      * [zenml.repo.artifact\_store module](zenml.repo.md#module-zenml.repo.artifact_store)
      * [zenml.repo.constants module](zenml.repo.md#module-zenml.repo.constants)
      * [zenml.repo.git\_wrapper module](zenml.repo.md#module-zenml.repo.git_wrapper)
      * [zenml.repo.global\_config module](zenml.repo.md#module-zenml.repo.global_config)
      * [zenml.repo.repo module](zenml.repo.md#module-zenml.repo.repo)
      * [zenml.repo.repo\_test module](zenml.repo.md#module-zenml.repo.repo_test)
      * [zenml.repo.zenml\_config module](zenml.repo.md#module-zenml.repo.zenml_config)
      * [zenml.repo.zenml\_config\_test module](zenml.repo.md#module-zenml.repo.zenml_config_test)
      * [Module contents](zenml.repo.md#module-zenml.repo)
* [ « zenml.pipelin...](zenml.pipelines.md)
* [ zenml.standar... »](zenml.standards.md)
*  [Source](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/_sources/zenml.repo.rst.txt)

## zenml.repo package[¶](zenml.repo.md#zenml-repo-package)

### Submodules[¶](zenml.repo.md#submodules)

### zenml.repo.artifact\_store module[¶](zenml.repo.md#module-zenml.repo.artifact_store)

Definition of an Artifact Store _class_ `zenml.repo.artifact_store.ArtifactStore`\(_path: str_\)[¶](zenml.repo.md#zenml.repo.artifact_store.ArtifactStore)

Bases: `object`

Base class for all ZenML datasources.

Every ZenML datasource should override this class. _static_ `get_component_name_from_uri`\(_artifact\_uri: str_\)[¶](zenml.repo.md#zenml.repo.artifact_store.ArtifactStore.get_component_name_from_uri)

Gets component name from artifact URI.Parameters

**artifact\_uri** \(_str_\) – URI to artifact. `resolve_uri_locally`\(_artifact\_uri: str_, _path: str = None_\)[¶](zenml.repo.md#zenml.repo.artifact_store.ArtifactStore.resolve_uri_locally)

Takes a URI that points within the artifact store, downloads the URI locally, then returns local URI.Parameters

* **artifact\_uri** – uri to artifact.
* **path** – optional path to download to. If None, is inferred.

### zenml.repo.constants module[¶](zenml.repo.md#module-zenml.repo.constants)

### zenml.repo.git\_wrapper module[¶](zenml.repo.md#module-zenml.repo.git_wrapper)

Wrapper class to handle Git integration _class_ `zenml.repo.git_wrapper.GitWrapper`\(_repo\_path: str_\)[¶](zenml.repo.md#zenml.repo.git_wrapper.GitWrapper)

Bases: `object`

Wrapper class for Git.

This class is responsible for handling git interactions, primarily handling versioning of different steps in pipelines. `add_gitignore`\(_items: List\[str\]_\)[¶](zenml.repo.md#zenml.repo.git_wrapper.GitWrapper.add_gitignore)

Adds items to .gitignore, if .gitignore exists. Otherwise creates and adds.Parameters

**items** \(_list\[str\]_\) – Items to add. `check_file_committed`\(_file\_path: str_\) → bool[¶](zenml.repo.md#zenml.repo.git_wrapper.GitWrapper.check_file_committed)

Checks file is committed. If yes, return True, else False.Parameters

**file\_path** \(_str_\) – Path to any file within the ZenML repo. `check_module_clean`\(_source: str_\)[¶](zenml.repo.md#zenml.repo.git_wrapper.GitWrapper.check_module_clean)

Returns True if all files within source’s module are committed.Parameters

**source** \(_str_\) – relative module path pointing to a Class. `checkout`\(_sha\_or\_branch: str = None_, _directory: str = None_\)[¶](zenml.repo.md#zenml.repo.git_wrapper.GitWrapper.checkout)

Wrapper for git checkoutParameters

* **sha\_or\_branch** – hex string of len 40 representing git sha OR
* **of branch** \(_name_\) –
* **directory** \(_str_\) – relative path to directory to scope checkout

 `get_current_sha`\(\) → str[¶](zenml.repo.md#zenml.repo.git_wrapper.GitWrapper.get_current_sha)

Finds the git sha that each file within the module is currently on. `reset`\(_directory: str = None_\)[¶](zenml.repo.md#zenml.repo.git_wrapper.GitWrapper.reset)

Wrapper for git reset HEAD &lt;directory&gt;.Parameters

**directory** \(_str_\) – relative path to directory to scope checkout `resolve_class_source`\(_source: str_\) → str[¶](zenml.repo.md#zenml.repo.git_wrapper.GitWrapper.resolve_class_source)

Takes source \(e.g. this.module.ClassName\), and appends relevant sha to it if the files within module are all committed. If even one file is not committed, then returns source unchanged.Parameters

**source** \(_str_\) – relative module path pointing to a Class. `stash`\(\)[¶](zenml.repo.md#zenml.repo.git_wrapper.GitWrapper.stash)

Wrapper for git stash `stash_pop`\(\)[¶](zenml.repo.md#zenml.repo.git_wrapper.GitWrapper.stash_pop)

Wrapper for git stash pop. Only pops if there’s something to pop.

### zenml.repo.global\_config module[¶](zenml.repo.md#module-zenml.repo.global_config)

Global config for the ZenML installation. _class_ `zenml.repo.global_config.GlobalConfig`\(_\*args_, _\*\*kwargs_\)[¶](zenml.repo.md#zenml.repo.global_config.GlobalConfig)

Bases: `dict`

Class definition for the global config. `create_user_id`\(\)[¶](zenml.repo.md#zenml.repo.global_config.GlobalConfig.create_user_id)

Creates user\_id if it does not exist. `get_analytics_opt_in`\(\) → bool[¶](zenml.repo.md#zenml.repo.global_config.GlobalConfig.get_analytics_opt_in)

Gets user\_id from config. If not present, creates a new one. _static_ `get_config_dir`\(\)[¶](zenml.repo.md#zenml.repo.global_config.GlobalConfig.get_config_dir)

Gets config dir. _static_ `get_instance`\(\)[¶](zenml.repo.md#zenml.repo.global_config.GlobalConfig.get_instance)

Static method to fetch the current instance. `get_user_id`\(\)[¶](zenml.repo.md#zenml.repo.global_config.GlobalConfig.get_user_id)

Gets user\_id from config. If not present, creates a new one. `load`\(\)[¶](zenml.repo.md#zenml.repo.global_config.GlobalConfig.load)

Load from YAML file. `save`\(\)[¶](zenml.repo.md#zenml.repo.global_config.GlobalConfig.save)

Save current config to YAML file `set_analytics_opt_in`\(_toggle: bool_\)[¶](zenml.repo.md#zenml.repo.global_config.GlobalConfig.set_analytics_opt_in)

Set opt-in flag for analytics

### zenml.repo.repo module[¶](zenml.repo.md#module-zenml.repo.repo)

Base ZenML repository _class_ `zenml.repo.repo.Repository`\(_path: str = None_\)[¶](zenml.repo.md#zenml.repo.repo.Repository)

Bases: `object`

ZenML repository definition. This is a Singleton class.

Every ZenML project exists inside a ZenML repository. `clean`\(\)[¶](zenml.repo.md#zenml.repo.repo.Repository.clean)

Deletes associated metadata store, pipelines dir and artifacts `compare_training_runs`\(_port: int = 0_\)[¶](zenml.repo.md#zenml.repo.repo.Repository.compare_training_runs)

Launch the compare app for all training pipelines in repo `get_datasource_by_name`\(_name: str_\)[¶](zenml.repo.md#zenml.repo.repo.Repository.get_datasource_by_name)

Get all datasources in this repo.

Returns: list of datasources used in this repo `get_datasource_id_by_name`\(_name: str_\) → List[¶](zenml.repo.md#zenml.repo.repo.Repository.get_datasource_id_by_name)

Get ID of a datasource by just its name.

Returns: ID of datasource. `get_datasource_names`\(\) → List[¶](zenml.repo.md#zenml.repo.repo.Repository.get_datasource_names)

Get all datasources in this repo.

Returns: List of datasource names used in this repo. `get_datasources`\(_\*\*kwargs_\)[¶](zenml.repo.md#zenml.repo.repo.Repository.get_datasources) `get_default_artifact_store`\(\) → Optional\[[zenml.repo.artifact\_store.ArtifactStore](zenml.repo.md#zenml.repo.artifact_store.ArtifactStore)\][¶](zenml.repo.md#zenml.repo.repo.Repository.get_default_artifact_store) `get_default_metadata_store`\(\)[¶](zenml.repo.md#zenml.repo.repo.Repository.get_default_metadata_store) `get_default_pipelines_dir`\(\) → str[¶](zenml.repo.md#zenml.repo.repo.Repository.get_default_pipelines_dir) `get_git_wrapper`\(\) → [zenml.repo.git\_wrapper.GitWrapper](zenml.repo.md#zenml.repo.git_wrapper.GitWrapper)[¶](zenml.repo.md#zenml.repo.repo.Repository.get_git_wrapper) _static_ `get_instance`\(_path: str = None_\)[¶](zenml.repo.md#zenml.repo.repo.Repository.get_instance)

Static method to fetch the current instance. `get_pipeline_by_name`\(_pipeline\_name: str = None_\)[¶](zenml.repo.md#zenml.repo.repo.Repository.get_pipeline_by_name)

Loads a pipeline just by its name.Parameters

**pipeline\_name** \(_str_\) – Name of pipeline. `get_pipeline_file_paths`\(_only\_file\_names: bool = False_\) → Optional\[List\[str\]\][¶](zenml.repo.md#zenml.repo.repo.Repository.get_pipeline_file_paths)

Gets list of pipeline file path `get_pipeline_names`\(\) → Optional\[List\[str\]\][¶](zenml.repo.md#zenml.repo.repo.Repository.get_pipeline_names)

Gets list of pipeline \(unique\) names `get_pipelines`\(_\*\*kwargs_\)[¶](zenml.repo.md#zenml.repo.repo.Repository.get_pipelines) `get_pipelines_by_datasource`\(_datasource_\)[¶](zenml.repo.md#zenml.repo.repo.Repository.get_pipelines_by_datasource)

Gets list of pipelines associated with datasource.Parameters

**datasource** \([_BaseDatasource_](zenml.datasources.md#zenml.datasources.base_datasource.BaseDatasource)\) – object of type BaseDatasource. `get_pipelines_by_type`\(_type\_filter: List\[str\]_\) → List[¶](zenml.repo.md#zenml.repo.repo.Repository.get_pipelines_by_type)

Gets list of pipelines filtered by type.Parameters

**type\_filter** \(_list_\) – list of types to filter by. `get_step_by_version`\(_\*\*kwargs_\)[¶](zenml.repo.md#zenml.repo.repo.Repository.get_step_by_version) `get_step_versions`\(_\*\*kwargs_\)[¶](zenml.repo.md#zenml.repo.repo.Repository.get_step_versions) `get_step_versions_by_type`\(_step\_type: Union\[Type, str\]_\)[¶](zenml.repo.md#zenml.repo.repo.Repository.get_step_versions_by_type)

List all registered steps in repository by step\_type.Parameters

* **step\_type** – either a string specifying full source of the step or a
* **class type.** \(_python_\) –

 _static_ `get_zenml_dir`\(_path: str_\)[¶](zenml.repo.md#zenml.repo.repo.Repository.get_zenml_dir)

Recursive function to find the zenml config starting from path.Parameters

**path** \(_str_\) – starting path _static_ `init_repo`\(_\*args_, _\*\*kwargs_\)[¶](zenml.repo.md#zenml.repo.repo.Repository.init_repo) `load_pipeline_config`\(_file\_name: str_\) → Dict\[str, Any\][¶](zenml.repo.md#zenml.repo.repo.Repository.load_pipeline_config)

Loads a ZenML config from YAML.Parameters

**file\_name** \(_str_\) – file name of pipeline `register_pipeline`\(_\*\*kwargs_\)[¶](zenml.repo.md#zenml.repo.repo.Repository.register_pipeline)

### zenml.repo.repo\_test module[¶](zenml.repo.md#module-zenml.repo.repo_test)

 `zenml.repo.repo_test.test_get_datasource_by_name`\(_repo_\)[¶](zenml.repo.md#zenml.repo.repo_test.test_get_datasource_by_name) `zenml.repo.repo_test.test_get_datasource_names`\(_repo_\)[¶](zenml.repo.md#zenml.repo.repo_test.test_get_datasource_names) `zenml.repo.repo_test.test_get_datasources`\(_repo_\)[¶](zenml.repo.md#zenml.repo.repo_test.test_get_datasources) `zenml.repo.repo_test.test_get_pipeline_by_name`\(_repo_, _equal\_pipelines_\)[¶](zenml.repo.md#zenml.repo.repo_test.test_get_pipeline_by_name) `zenml.repo.repo_test.test_get_pipeline_file_paths`\(_repo_, _monkeypatch_\)[¶](zenml.repo.md#zenml.repo.repo_test.test_get_pipeline_file_paths) `zenml.repo.repo_test.test_get_pipeline_names`\(_repo_\)[¶](zenml.repo.md#zenml.repo.repo_test.test_get_pipeline_names) `zenml.repo.repo_test.test_get_pipelines`\(_repo_\)[¶](zenml.repo.md#zenml.repo.repo_test.test_get_pipelines) `zenml.repo.repo_test.test_get_pipelines_by_datasource`\(_repo_\)[¶](zenml.repo.md#zenml.repo.repo_test.test_get_pipelines_by_datasource) `zenml.repo.repo_test.test_get_pipelines_by_type`\(_repo_\)[¶](zenml.repo.md#zenml.repo.repo_test.test_get_pipelines_by_type) `zenml.repo.repo_test.test_get_step_by_version`\(_repo_\)[¶](zenml.repo.md#zenml.repo.repo_test.test_get_step_by_version) `zenml.repo.repo_test.test_get_step_versions`\(_repo_\)[¶](zenml.repo.md#zenml.repo.repo_test.test_get_step_versions) `zenml.repo.repo_test.test_get_step_versions_by_type`\(_repo_\)[¶](zenml.repo.md#zenml.repo.repo_test.test_get_step_versions_by_type) `zenml.repo.repo_test.test_repo_double_init`\(\)[¶](zenml.repo.md#zenml.repo.repo_test.test_repo_double_init)

### zenml.repo.zenml\_config module[¶](zenml.repo.md#module-zenml.repo.zenml_config)

Functions to handle ZenML config _class_ `zenml.repo.zenml_config.ZenMLConfig`\(_repo\_path: str_\)[¶](zenml.repo.md#zenml.repo.zenml_config.ZenMLConfig)

Bases: `object`

ZenML config class to handle config operations.

This is an internal class and should not be used by the user. `from_config`\(_config\_dict: Dict_\)[¶](zenml.repo.md#zenml.repo.zenml_config.ZenMLConfig.from_config)

Sets metadata and artifact\_store variablesParameters

**config\_dict** \(_dict_\) – .zenml config object in dict format. `get_artifact_store`\(\) → [zenml.repo.artifact\_store.ArtifactStore](zenml.repo.md#zenml.repo.artifact_store.ArtifactStore)[¶](zenml.repo.md#zenml.repo.zenml_config.ZenMLConfig.get_artifact_store)

Get artifact store from config `get_metadata_store`\(\) → [zenml.metadata.metadata\_wrapper.ZenMLMetadataStore](zenml.metadata.md#zenml.metadata.metadata_wrapper.ZenMLMetadataStore)[¶](zenml.repo.md#zenml.repo.zenml_config.ZenMLConfig.get_metadata_store)

Get metadata store from config. `get_pipelines_dir`\(\) → str[¶](zenml.repo.md#zenml.repo.zenml_config.ZenMLConfig.get_pipelines_dir)

Get absolute path of pipelines dir from config _static_ `is_zenml_dir`\(_path: str_\)[¶](zenml.repo.md#zenml.repo.zenml_config.ZenMLConfig.is_zenml_dir)

Check if dir is a zenml dir or not.Parameters

**path** \(_str_\) – path to the root. `save`\(\)[¶](zenml.repo.md#zenml.repo.zenml_config.ZenMLConfig.save) `set_artifact_store`\(_artifact\_store\_path: str_\)[¶](zenml.repo.md#zenml.repo.zenml_config.ZenMLConfig.set_artifact_store)

Updates artifact store to point to path.Parameters

**artifact\_store\_path** – new path to artifact store `set_metadata_store`\(_metadata\_store:_ [_zenml.metadata.metadata\_wrapper.ZenMLMetadataStore_](zenml.metadata.md#zenml.metadata.metadata_wrapper.ZenMLMetadataStore)\)[¶](zenml.repo.md#zenml.repo.zenml_config.ZenMLConfig.set_metadata_store)

Updates artifact store to point to path.Parameters

**metadata\_store** – metadata store `set_pipelines_dir`\(_pipelines\_dir: str_\)[¶](zenml.repo.md#zenml.repo.zenml_config.ZenMLConfig.set_pipelines_dir)

Updates artifact store to point to path.Parameters

**pipelines\_dir** – new path to pipelines dir _static_ `to_config`\(_path: str_, _artifact\_store\_path: str = None_, _metadata\_store: Optional\[Type\[_[_zenml.metadata.metadata\_wrapper.ZenMLMetadataStore_](zenml.metadata.md#zenml.metadata.metadata_wrapper.ZenMLMetadataStore)_\]\] = None_, _pipelines\_dir: str = None_\)[¶](zenml.repo.md#zenml.repo.zenml_config.ZenMLConfig.to_config)

Creates a default .zenml config at path/zenml/.zenml\_config.Parameters

* **path** \(_str_\) – path to a directory.
* **metadata\_store** – metadata store definition.
* **artifact\_store\_path** \(_str_\) – path where to store artifacts.
* **pipelines\_dir** \(_str_\) – path where to store pipeline configs.

### zenml.repo.zenml\_config\_test module[¶](zenml.repo.md#module-zenml.repo.zenml_config_test)

 `zenml.repo.zenml_config_test.test_is_zenml_dir`\(\)[¶](zenml.repo.md#zenml.repo.zenml_config_test.test_is_zenml_dir) `zenml.repo.zenml_config_test.test_zenml_config_getters`\(\)[¶](zenml.repo.md#zenml.repo.zenml_config_test.test_zenml_config_getters) `zenml.repo.zenml_config_test.test_zenml_config_init`\(\)[¶](zenml.repo.md#zenml.repo.zenml_config_test.test_zenml_config_init) `zenml.repo.zenml_config_test.test_zenml_config_setters`\(_equal\_md\_stores_\)[¶](zenml.repo.md#zenml.repo.zenml_config_test.test_zenml_config_setters)

### Module contents[¶](zenml.repo.md#module-zenml.repo)

 [Back to top](zenml.repo.md)

 © Copyright 2021, maiot GmbH.  
 Created using [Sphinx](http://sphinx-doc.org/) 3.3.1.  


