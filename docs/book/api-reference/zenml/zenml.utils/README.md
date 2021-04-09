# Utils

&lt;!DOCTYPE html&gt;

zenml.utils package — ZenML documentation  [ZenML](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/index.html)

*  [Site](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/index.html)
  * Contents:
    * [zenml](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/modules.html)
*  [Page](./)
  * * [zenml.utils package](./)
      * [Subpackages](./#subpackages)
      * [Submodules](./#submodules)
      * [zenml.utils.analytics\_utils module](./#module-zenml.utils.analytics_utils)
      * [zenml.utils.naming\_utils module](./#module-zenml.utils.naming_utils)
      * [zenml.utils.path\_utils module](./#module-zenml.utils.path_utils)
      * [zenml.utils.preprocessing\_utils module](./#module-zenml.utils.preprocessing_utils)
      * [zenml.utils.print\_utils module](./#module-zenml.utils.print_utils)
      * [zenml.utils.requirement\_utils module](./#module-zenml.utils.requirement_utils)
      * [zenml.utils.source\_utils module](./#module-zenml.utils.source_utils)
      * [zenml.utils.string\_utils module](./#module-zenml.utils.string_utils)
      * [zenml.utils.yaml\_utils module](./#module-zenml.utils.yaml_utils)
      * [Module contents](./#module-zenml.utils)
* [ « zenml.steps.t...](../zenml.steps/zenml.steps.trainer/zenml.steps.trainer.tensorflow_trainers.md)
* [ zenml.utils.p... »](zenml.utils.post_training.md)
*  [Source](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/_sources/zenml.utils.rst.txt)

## zenml.utils package[¶](./#zenml-utils-package)

### Subpackages[¶](./#subpackages)

* [zenml.utils.post\_training package](zenml.utils.post_training.md)
  * [Submodules](zenml.utils.post_training.md#submodules)
  * [zenml.utils.post\_training.compare module](zenml.utils.post_training.md#module-zenml.utils.post_training.compare)
  * [zenml.utils.post\_training.post\_training\_utils module](zenml.utils.post_training.md#module-zenml.utils.post_training.post_training_utils)
  * [Module contents](zenml.utils.post_training.md#module-zenml.utils.post_training)

### Submodules[¶](./#submodules)

### zenml.utils.analytics\_utils module[¶](./#module-zenml.utils.analytics_utils)

Analytics code for ZenML `zenml.utils.analytics_utils.get_segment_key`\(\) → str[¶](./#zenml.utils.analytics_utils.get_segment_key) `zenml.utils.analytics_utils.get_system_info`\(\)[¶](./#zenml.utils.analytics_utils.get_system_info) `zenml.utils.analytics_utils.parametrized`\(_dec_\)[¶](./#zenml.utils.analytics_utils.parametrized)

This is a meta-decorator, that is, a decorator for decorators. As a decorator is a function, it actually works as a regular decorator with arguments: `zenml.utils.analytics_utils.track`\(_\*args_, _\*\*kwargs_\)[¶](./#zenml.utils.analytics_utils.track) `zenml.utils.analytics_utils.track_event`\(_event_, _metadata=None_\)[¶](./#zenml.utils.analytics_utils.track_event)

Track segment event if user opted-in.Parameters

* **event** – name of event to track in segment.
* **metadata** – dict of metadata

### zenml.utils.naming\_utils module[¶](./#module-zenml.utils.naming_utils)

This collection of utility functions is aiming to help the users follow a certain pre-defined naming paradigm.

However, due to the highly dynamic nature of ML tasks, users might need to implement their own naming scheme depending on their tasks. `zenml.utils.naming_utils.check_if_output_name`\(_name: str_\)[¶](./#zenml.utils.naming_utils.check_if_output_name) `zenml.utils.naming_utils.check_if_transformed_feature`\(_name: str_\)[¶](./#zenml.utils.naming_utils.check_if_transformed_feature) `zenml.utils.naming_utils.check_if_transformed_label`\(_name: str_\)[¶](./#zenml.utils.naming_utils.check_if_transformed_label) `zenml.utils.naming_utils.output_name`\(_name: str_\)[¶](./#zenml.utils.naming_utils.output_name) `zenml.utils.naming_utils.transformed_feature_name`\(_name: str_\)[¶](./#zenml.utils.naming_utils.transformed_feature_name) `zenml.utils.naming_utils.transformed_label_name`\(_name: str_\)[¶](./#zenml.utils.naming_utils.transformed_label_name)

### zenml.utils.path\_utils module[¶](./#module-zenml.utils.path_utils)

File utilities `zenml.utils.path_utils.append_file`\(_file\_path: str_, _file\_contents: str_\)[¶](./#zenml.utils.path_utils.append_file)

Appends file\_contents to file.Parameters

* **file\_path** \(_str_\) – Local path in filesystem.
* **file\_contents** \(_str_\) – Contents of file.

 `zenml.utils.path_utils.copy`\(_source: str_, _destination: str_, _overwrite: bool = False_\)[¶](./#zenml.utils.path_utils.copy)

Copies dir from source to destination.Parameters

* **source** \(_str_\) – Path to copy from.
* **destination** \(_str_\) – Path to copy to.
* **overwrite** – boolean, if false, then throws an error before overwrite.

 `zenml.utils.path_utils.copy_dir`\(_source\_dir: str_, _destination\_dir: str_, _overwrite: bool = False_\)[¶](./#zenml.utils.path_utils.copy_dir)

Copies dir from source to destination.Parameters

* **source\_dir** \(_str_\) – Path to copy from.
* **destination\_dir** \(_str_\) – Path to copy to.
* **overwrite** – boolean, if false, then throws an error before overwrite.

 `zenml.utils.path_utils.create_dir_if_not_exists`\(_dir\_path: str_\)[¶](./#zenml.utils.path_utils.create_dir_if_not_exists)

Creates directory if it does not exist.Parameters

**dir\_path** \(_str_\) – Local path in filesystem. `zenml.utils.path_utils.create_dir_recursive_if_not_exists`\(_dir\_path: str_\)[¶](./#zenml.utils.path_utils.create_dir_recursive_if_not_exists)

Creates directory recursively if it does not exist.Parameters

**dir\_path** \(_str_\) – Local path in filesystem. `zenml.utils.path_utils.create_file_if_not_exists`\(_file\_path: str_, _file\_contents: str_\)[¶](./#zenml.utils.path_utils.create_file_if_not_exists)

Creates directory if it does not exist.Parameters

* **file\_path** \(_str_\) – Local path in filesystem.
* **file\_contents** \(_str_\) – Contents of file.

 `zenml.utils.path_utils.create_tarfile`\(_source\_dir: str_, _output\_filename: str = 'zipped.tar.gz'_, _exclude\_function: Callable = None_\)[¶](./#zenml.utils.path_utils.create_tarfile)

Create a compressed representation of source\_dir.Parameters

* **source\_dir** – path to source dir
* **output\_filename** – name of outputted gz
* **exclude\_function** – function that determines whether to exclude file

 `zenml.utils.path_utils.extract_tarfile`\(_source\_tar: str_, _output\_dir: str_\)[¶](./#zenml.utils.path_utils.extract_tarfile)

Untars a compressed tar file to output\_dir.Parameters

* **source\_tar** – path to a tar compressed file
* **output\_dir** – directory where to uncompress

 `zenml.utils.path_utils.file_exists`\(_path: str_\)[¶](./#zenml.utils.path_utils.file_exists)

Returns true if file exists at path.Parameters

**path** \(_str_\) – Local path in filesystem. `zenml.utils.path_utils.get_grandparent`\(_dir\_path: str_\)[¶](./#zenml.utils.path_utils.get_grandparent)

Get grandparent of dir.Parameters

**dir\_path** \(_str_\) – Path to directory. `zenml.utils.path_utils.get_parent`\(_dir\_path: str_\)[¶](./#zenml.utils.path_utils.get_parent)

Get parent of dir.Parameters

**dir\_path** \(_str_\) – Path to directory. `zenml.utils.path_utils.is_dir`\(_dir\_path: str_\)[¶](./#zenml.utils.path_utils.is_dir)

Returns true if dir\_path points to a dir.Parameters

**dir\_path** \(_str_\) – Local path in filesystem. `zenml.utils.path_utils.is_gcs_path`\(_path: str_\)[¶](./#zenml.utils.path_utils.is_gcs_path)

Returns True if path is on Google Cloud Storage.Parameters

**path** \(_str_\) – Any path. `zenml.utils.path_utils.is_remote`\(_path: str_\)[¶](./#zenml.utils.path_utils.is_remote)

Returns True if path exists remotely.Parameters

**path** \(_str_\) – Any path. `zenml.utils.path_utils.is_root`\(_path: str_\)[¶](./#zenml.utils.path_utils.is_root)

Returns true if path has no parent in local filesystem.Parameters

**path** \(_str_\) – Local path in filesystem. `zenml.utils.path_utils.list_dir`\(_dir\_path: str_, _only\_file\_names: bool = False_\)[¶](./#zenml.utils.path_utils.list_dir)

Returns a list of files under dir.Parameters

* **dir\_path** \(_str_\) – Path in filesystem.
* **only\_file\_names** \(_bool_\) – Returns only file names if True.

 `zenml.utils.path_utils.load_csv_header`\(_csv\_path: str_\)[¶](./#zenml.utils.path_utils.load_csv_header)

Gets header column of csv and returns list.Parameters

**csv\_path** \(_str_\) – Path to csv file. `zenml.utils.path_utils.move`\(_source: str_, _destination: str_, _overwrite: bool = False_\)[¶](./#zenml.utils.path_utils.move)

Moves dir from source to destination. Can be used to rename.Parameters

* **source** \(_str_\) – Local path to copy from.
* **destination** \(_str_\) – Local path to copy to.
* **overwrite** – boolean, if false, then throws an error before overwrite.

 `zenml.utils.path_utils.read_file_contents`\(_file\_path: str_\)[¶](./#zenml.utils.path_utils.read_file_contents)

Reads contents of file.Parameters

**file\_path** \(_str_\) – Path to file. `zenml.utils.path_utils.resolve_relative_path`\(_path: str_\)[¶](./#zenml.utils.path_utils.resolve_relative_path)

Takes relative path and resolves it absolutely.Parameters

**path** \(_str_\) – Local path in filesystem. `zenml.utils.path_utils.rm_dir`\(_dir\_path: str_\)[¶](./#zenml.utils.path_utils.rm_dir)

Deletes dir recursively. Dangerous operation.Parameters

**dir\_path** \(_str_\) – Dir to delete. `zenml.utils.path_utils.rm_file`\(_file\_path: str_\)[¶](./#zenml.utils.path_utils.rm_file)

Deletes file. Dangerous operation.Parameters

**file\_path** \(_str_\) – Path of file to delete. `zenml.utils.path_utils.write_file_contents`\(_file\_path: str_, _content: str_\)[¶](./#zenml.utils.path_utils.write_file_contents)

Writes contents of file.Parameters

* **file\_path** \(_str_\) – Path to file.
* **content** \(_str_\) – Contents of file.

### zenml.utils.preprocessing\_utils module[¶](./#module-zenml.utils.preprocessing_utils)

 _class_ `zenml.utils.preprocessing_utils.MethodDescriptions`[¶](./#zenml.utils.preprocessing_utils.MethodDescriptions)

Bases: `object` `MODES` _= {}_[¶](./#zenml.utils.preprocessing_utils.MethodDescriptions.MODES) _classmethod_ `check_name_and_params`\(_method\_name_, _method\_params_\)[¶](./#zenml.utils.preprocessing_utils.MethodDescriptions.check_name_and_params)Parameters

* **method\_name** –
* **method\_params** –

 _classmethod_ `get_method`\(_method\_name_\)[¶](./#zenml.utils.preprocessing_utils.MethodDescriptions.get_method)Parameters

**method\_name** – `zenml.utils.preprocessing_utils.parse_methods`\(_input\_dict_, _process_, _methods_\)[¶](./#zenml.utils.preprocessing_utils.parse_methods)Parameters

* **input\_dict** –
* **process** –
* **methods** –

### zenml.utils.print\_utils module[¶](./#module-zenml.utils.print_utils)

 _class_ `zenml.utils.print_utils.PrintStyles`\(_value_\)[¶](./#zenml.utils.print_utils.PrintStyles)

Bases: `enum.Enum`

An enumeration. `NATIVE` _= 0_[¶](./#zenml.utils.print_utils.PrintStyles.NATIVE) `PPRINT` _= 2_[¶](./#zenml.utils.print_utils.PrintStyles.PPRINT) `YAML` _= 1_[¶](./#zenml.utils.print_utils.PrintStyles.YAML) `zenml.utils.print_utils.format_date`\(_dt_, _format='%Y-%m-%d %H:%M:%S'_\)[¶](./#zenml.utils.print_utils.format_date)

Formatting a datetime object nicely.Parameters

* **dt** – datetime object
* **format** – format

 `zenml.utils.print_utils.format_timedelta`\(_td_\)[¶](./#zenml.utils.print_utils.format_timedelta)

Format timedelta object nicely.Parameters

**td** – timedelta object `zenml.utils.print_utils.to_pretty_string`\(_d_, _style=&lt;PrintStyles.YAML: 1&gt;_\)[¶](./#zenml.utils.print_utils.to_pretty_string)Parameters

* **d** –
* **style** –

### zenml.utils.requirement\_utils module[¶](./#module-zenml.utils.requirement_utils)

 `zenml.utils.requirement_utils.check_integration`\(_integration_\)[¶](./#zenml.utils.requirement_utils.check_integration) `zenml.utils.requirement_utils.list_integrations`\(\)[¶](./#zenml.utils.requirement_utils.list_integrations)

Prints integrations in an easy to read format.

### zenml.utils.source\_utils module[¶](./#module-zenml.utils.source_utils)

These utils are predicated on the following definitions:

* class\_source: This is a python-import type path to a class, e.g.

some.mod.class \* module\_source: This is a python-import type path to a module, e.g. some.mod \* file\_path, relative\_path, absolute\_path: These are file system paths. \* source: This is a class\_source or module\_source. If it is a class\_source, it can also be optionally pinned. \* pin: Whatever comes after the @ symbol from a source, usually the git sha or the version of zenml as a string. `zenml.utils.source_utils.create_zenml_pin`\(\)[¶](./#zenml.utils.source_utils.create_zenml_pin)

Creates a ZenML pin for source pinning from release version. `zenml.utils.source_utils.get_absolute_path_from_module_source`\(_module: str_\)[¶](./#zenml.utils.source_utils.get_absolute_path_from_module_source)

Get a directory path from module source.

E.g. zenml.core.step will return full/path/to/zenml/core/step.Parameters

**module** \(_str_\) – A module e.g. zenml.core.step. `zenml.utils.source_utils.get_class_source_from_source`\(_source: str_\) → Optional\[str\][¶](./#zenml.utils.source_utils.get_class_source_from_source)

Gets class source from source, i.e. [module.path@version](mailto:module.path%40version), returns version.Parameters

**source** – source pointing to potentially pinned sha. `zenml.utils.source_utils.get_module_source_from_class`\(_class\_: Union\[Type, str\]_\) → Optional\[str\][¶](./#zenml.utils.source_utils.get_module_source_from_class)

Takes class input and returns module\_source. If class is already string then returns the same.Parameters

**class** – object of type class. `zenml.utils.source_utils.get_module_source_from_file_path`\(_file\_path_\)[¶](./#zenml.utils.source_utils.get_module_source_from_file_path)

Gets module\_source from a file\_path. E.g. /home/myrepo/step/trainer.py returns myrepo.step.trainer if myrepo is the root of the repo.Parameters

**file\_path** – Absolute file path to a file within the module. `zenml.utils.source_utils.get_module_source_from_source`\(_source: str_\) → str[¶](./#zenml.utils.source_utils.get_module_source_from_source)

Gets module source from source. E.g. some.module.file.class@version, returns some.module.Parameters

**source** – source pointing to potentially pinned sha. `zenml.utils.source_utils.get_path_from_source`\(_source_\)[¶](./#zenml.utils.source_utils.get_path_from_source)

Get file path from sourceParameters

**source** \(_str_\) – class\_source e.g. this.module.Class. `zenml.utils.source_utils.get_pin_from_source`\(_source: str_\) → Optional\[str\][¶](./#zenml.utils.source_utils.get_pin_from_source)

Gets pin from source, i.e. [module.path@pin](mailto:module.path%40pin), returns pin.Parameters

**source** \(_str_\) – class\_source e.g. this.module.Class\[@pin\]. `zenml.utils.source_utils.get_relative_path_from_module_source`\(_module\_source: str_\)[¶](./#zenml.utils.source_utils.get_relative_path_from_module_source)

Get a directory path from module, relative to root of repository.

E.g. zenml.core.step will return zenml/core/step.Parameters

**module\_source** \(_str_\) – A module e.g. zenml.core.step `zenml.utils.source_utils.is_standard_pin`\(_pin: str_\) → bool[¶](./#zenml.utils.source_utils.is_standard_pin)

Returns True if pin is valid ZenML pin, else False.Parameters

**pin** \(_str_\) – potential ZenML pin like ‘zenml\_0.1.1’ `zenml.utils.source_utils.is_standard_source`\(_source: str_\) → bool[¶](./#zenml.utils.source_utils.is_standard_source)

Returns True if source is a standard ZenML source.Parameters

**source** \(_str_\) – class\_source e.g. this.module.Class\[@pin\]. `zenml.utils.source_utils.is_valid_source`\(_source: str_\) → bool[¶](./#zenml.utils.source_utils.is_valid_source)

Checks whether the source\_path is valid or not.Parameters

**source** \(_str_\) – class\_source e.g. this.module.Class\[@pin\]. `zenml.utils.source_utils.load_source_path_class`\(_source: str_\) → Type[¶](./#zenml.utils.source_utils.load_source_path_class)

Loads a Python class from the source.Parameters

**source** \(_str_\) – class\_source e.g. this.module.Class\[@sha\] `zenml.utils.source_utils.resolve_class`\(_class\_: Type_\) → str[¶](./#zenml.utils.source_utils.resolve_class)

Resolves :param [class\_](./#id1): A Python Class reference.

Returns: source\_path e.g. this.module.Class\[@pin\]. `zenml.utils.source_utils.resolve_class_source`\(_class\_source: str_\) → str[¶](./#zenml.utils.source_utils.resolve_class_source)

Resolves class\_source with an optional pin.Parameters

**class\_source** \(_str_\) – class\_source e.g. this.module.Class `zenml.utils.source_utils.resolve_standard_source`\(_source: str_\) → str[¶](./#zenml.utils.source_utils.resolve_standard_source)

Creates a ZenML pin for source pinning from release version.Parameters

**source** \(_str_\) – class\_source e.g. this.module.Class.

### zenml.utils.string\_utils module[¶](./#module-zenml.utils.string_utils)

 `zenml.utils.string_utils.get_id`\(_text: str_\)[¶](./#zenml.utils.string_utils.get_id) `zenml.utils.string_utils.to_dns1123`\(_name: str_, _length=253_\)[¶](./#zenml.utils.string_utils.to_dns1123)

### zenml.utils.yaml\_utils module[¶](./#module-zenml.utils.yaml_utils)

 `zenml.utils.yaml_utils.is_yaml`\(_file\_path: str_\)[¶](./#zenml.utils.yaml_utils.is_yaml)

Returns True if file\_path is YAML, else FalseParameters

**file\_path** \(_str_\) – Path to YAML file. `zenml.utils.yaml_utils.read_json`\(_file\_path: str_\)[¶](./#zenml.utils.yaml_utils.read_json)

Read JSON on file path and returns contents as dict.Parameters

**file\_path** \(_str_\) – Path to JSON file. `zenml.utils.yaml_utils.read_yaml`\(_file\_path: str_\)[¶](./#zenml.utils.yaml_utils.read_yaml)

Read YAML on file path and returns contents as dict.Parameters

**file\_path** \(_str_\) – Path to YAML file. `zenml.utils.yaml_utils.write_json`\(_file\_path: str_, _contents: Dict_\)[¶](./#zenml.utils.yaml_utils.write_json)

Write contents as JSON format to file\_path.Parameters

* **file\_path** \(_str_\) – Path to JSON file.
* **contents** \(_dict_\) – Contents of JSON file as dict.

 `zenml.utils.yaml_utils.write_yaml`\(_file\_path: str_, _contents: Dict_\)[¶](./#zenml.utils.yaml_utils.write_yaml)

Write contents as YAML format to file\_path.Parameters

* **file\_path** \(_str_\) – Path to YAML file.
* **contents** \(_dict_\) – Contents of YAML file as dict.

### Module contents[¶](./#module-zenml.utils)

 [Back to top](./)

 © Copyright 2021, maiot GmbH.  
 Created using [Sphinx](http://sphinx-doc.org/) 3.3.1.  


