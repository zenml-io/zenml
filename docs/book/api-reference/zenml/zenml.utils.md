# Utils

&lt;!DOCTYPE html&gt;

zenml.utils package — ZenML documentation  [ZenML](https://github.com/zenml-io/zenml/tree/25d9c27ff1e23c67d7247993006f83f8404d83c4/docs/sphinx_docs/_build/html/index.html)

*  [Site](https://github.com/zenml-io/zenml/tree/25d9c27ff1e23c67d7247993006f83f8404d83c4/docs/sphinx_docs/_build/html/index.html)
  * Contents:
    * [zenml](https://github.com/zenml-io/zenml/tree/25d9c27ff1e23c67d7247993006f83f8404d83c4/docs/sphinx_docs/_build/html/modules.html)
*  [Page](zenml.utils.md)
  * * [zenml.utils package](zenml.utils.md)
      * [Submodules](zenml.utils.md#submodules)
      * [zenml.utils.analytics\_utils module](zenml.utils.md#module-zenml.utils.analytics_utils)
      * [zenml.utils.exceptions module](zenml.utils.md#module-zenml.utils.exceptions)
      * [zenml.utils.path\_utils module](zenml.utils.md#module-zenml.utils.path_utils)
      * [zenml.utils.source\_utils module](zenml.utils.md#module-zenml.utils.source_utils)
      * [zenml.utils.yaml\_utils module](zenml.utils.md#module-zenml.utils.yaml_utils)
      * [Module contents](zenml.utils.md#module-zenml.utils)
* [ « zenml.steps package](zenml.steps.md)
*  [Source](https://github.com/zenml-io/zenml/tree/25d9c27ff1e23c67d7247993006f83f8404d83c4/docs/sphinx_docs/_build/html/_sources/zenml.utils.rst.txt)

## zenml.utils package[¶](zenml.utils.md#zenml-utils-package)

### Submodules[¶](zenml.utils.md#submodules)

### zenml.utils.analytics\_utils module[¶](zenml.utils.md#module-zenml.utils.analytics_utils)

Analytics code for ZenML zenml.utils.analytics\_utils.get\_segment\_key\(\) → str[¶](zenml.utils.md#zenml.utils.analytics_utils.get_segment_key)

Get key for authorizing to Segment backend.Returns

Segment key as a string.Raises

**requests.exceptions.RequestException if request times out.** – zenml.utils.analytics\_utils.get\_system\_info\(\) → Dict[¶](zenml.utils.md#zenml.utils.analytics_utils.get_system_info)

Returns system info as a dict.Returns

A dict of system information. zenml.utils.analytics\_utils.parametrized\(_dec_\)[¶](zenml.utils.md#zenml.utils.analytics_utils.parametrized)

This is a meta-decorator, that is, a decorator for decorators. As a decorator is a function, it actually works as a regular decorator with arguments: zenml.utils.analytics\_utils.track\(_\*args: Any_, _\*\*kwargs: Any_\)[¶](zenml.utils.md#zenml.utils.analytics_utils.track)

Internal layer zenml.utils.analytics\_utils.track\_event\(_event: str_, _metadata: Optional\[Dict\] = None_\)[¶](zenml.utils.md#zenml.utils.analytics_utils.track_event)

Track segment event if user opted-in.Parameters

* **event** – Name of event to track in segment.
* **metadata** – Dict of metadata to track.

### zenml.utils.exceptions module[¶](zenml.utils.md#module-zenml.utils.exceptions)

 _exception_ zenml.utils.exceptions.DatasourceInterfaceError[¶](zenml.utils.md#zenml.utils.exceptions.DatasourceInterfaceError)

Bases: `Exception` _exception_ zenml.utils.exceptions.PipelineInterfaceError[¶](zenml.utils.md#zenml.utils.exceptions.PipelineInterfaceError)

Bases: `Exception` _exception_ zenml.utils.exceptions.StepInterfaceError[¶](zenml.utils.md#zenml.utils.exceptions.StepInterfaceError)

Bases: `Exception`

### zenml.utils.path\_utils module[¶](zenml.utils.md#module-zenml.utils.path_utils)

File utilities zenml.utils.path\_utils.append\_file\(_file\_path: str_, _file\_contents: str_\)[¶](zenml.utils.md#zenml.utils.path_utils.append_file)

Appends file\_contents to file.Parameters

* **file\_path** – Local path in filesystem.
* **file\_contents** – Contents of file.

 zenml.utils.path\_utils.copy\(_source: str_, _destination: str_, _overwrite: bool = False_\)[¶](zenml.utils.md#zenml.utils.path_utils.copy)

Copies dir from source to destination.Parameters

* **source** \(_str_\) – Path to copy from.
* **destination** \(_str_\) – Path to copy to.
* **overwrite** – boolean, if false, then throws an error before overwrite.

 zenml.utils.path\_utils.copy\_dir\(_source\_dir: str_, _destination\_dir: str_, _overwrite: bool = False_\)[¶](zenml.utils.md#zenml.utils.path_utils.copy_dir)

Copies dir from source to destination.Parameters

* **source\_dir** – Path to copy from.
* **destination\_dir** – Path to copy to.
* **overwrite** – Boolean, if false, then throws an error before overwrite.

 zenml.utils.path\_utils.create\_dir\_if\_not\_exists\(_dir\_path: str_\)[¶](zenml.utils.md#zenml.utils.path_utils.create_dir_if_not_exists)

Creates directory if it does not exist.Parameters

**dir\_path** \(_str_\) – Local path in filesystem. zenml.utils.path\_utils.create\_dir\_recursive\_if\_not\_exists\(_dir\_path: str_\)[¶](zenml.utils.md#zenml.utils.path_utils.create_dir_recursive_if_not_exists)

Creates directory recursively if it does not exist.Parameters

**dir\_path** – Local path in filesystem. zenml.utils.path\_utils.create\_file\_if\_not\_exists\(_file\_path: str_, _file\_contents: str = '{}'_\)[¶](zenml.utils.md#zenml.utils.path_utils.create_file_if_not_exists)

Creates directory if it does not exist.Parameters

* **file\_path** – Local path in filesystem.
* **file\_contents** – Contents of file.

 zenml.utils.path\_utils.create\_tarfile\(_source\_dir: str_, _output\_filename: str = 'zipped.tar.gz'_, _exclude\_function: Optional\[Callable\] = None_\)[¶](zenml.utils.md#zenml.utils.path_utils.create_tarfile)

Create a compressed representation of source\_dir.Parameters

* **source\_dir** – Path to source dir.
* **output\_filename** – Name of outputted gz.
* **exclude\_function** – Function that determines whether to exclude file.

 zenml.utils.path\_utils.extract\_tarfile\(_source\_tar: str_, _output\_dir: str_\)[¶](zenml.utils.md#zenml.utils.path_utils.extract_tarfile)

Untars a compressed tar file to output\_dir.Parameters

* **source\_tar** – Path to a tar compressed file.
* **output\_dir** – Directory where to uncompress.

 zenml.utils.path\_utils.file\_exists\(_path: str_\) → bool[¶](zenml.utils.md#zenml.utils.path_utils.file_exists)

Returns true if file exists at path.Parameters

**path** – Local path in filesystem.Returns

True if file exists, else False. zenml.utils.path\_utils.find\_files\(_dir\_path_, _pattern_\) → List\[str\][¶](zenml.utils.md#zenml.utils.path_utils.find_files)

Find files in a directory that match pattern.Parameters

* **dir\_path** – Path to directory.
* **pattern** – pattern like [\*](zenml.utils.md#id1).png.

Yields

All matching filenames if found, else None. zenml.utils.path\_utils.get\_grandparent\(_dir\_path: str_\) → str[¶](zenml.utils.md#zenml.utils.path_utils.get_grandparent)

Get grandparent of dir.Parameters

**dir\_path** – Path to directory.Returns

The input paths parents parent. zenml.utils.path\_utils.get\_parent\(_dir\_path: str_\) → str[¶](zenml.utils.md#zenml.utils.path_utils.get_parent)

Get parent of dir.Parameters

**dir\_path** \(_str_\) – Path to directory.Returns

Parent \(stem\) of the dir as a string. zenml.utils.path\_utils.get\_zenml\_config\_dir\(_path: str = '/home/runner/work/zenml/zenml/docs/sphinx\_docs'_\) → str[¶](zenml.utils.md#zenml.utils.path_utils.get_zenml_config_dir)

Recursive function to find the zenml config starting from path.Parameters

**path** \(_Default value = os.getcwd\(\)_\) – Path to check.Returns

The full path with the resolved zenml directory.Raises

**InitializationException if directory not found until root of OS.** – zenml.utils.path\_utils.get\_zenml\_dir\(_path: str = '/home/runner/work/zenml/zenml/docs/sphinx\_docs'_\) → str[¶](zenml.utils.md#zenml.utils.path_utils.get_zenml_dir)

Recursive function to find the zenml config starting from path.Parameters

**path** \(_Default value = os.getcwd\(\)_\) – Path to check.Returns

The full path with the resolved zenml directory.Raises

**InitializationException if directory not found until root of OS.** – zenml.utils.path\_utils.is\_dir\(_dir\_path: str_\) → bool[¶](zenml.utils.md#zenml.utils.path_utils.is_dir)

Returns true if dir\_path points to a dir.Parameters

**dir\_path** – Local path in filesystem.Returns

True if is dir, else False. zenml.utils.path\_utils.is\_gcs\_path\(_path: str_\) → bool[¶](zenml.utils.md#zenml.utils.path_utils.is_gcs_path)

Returns True if path is on Google Cloud Storage.Parameters

**path** – Any path as a string.Returns

True if gcs path, else False. zenml.utils.path\_utils.is\_remote\(_path: str_\) → bool[¶](zenml.utils.md#zenml.utils.path_utils.is_remote)

Returns True if path exists remotely.Parameters

**path** – Any path as a string.Returns

True if remote path, else False. zenml.utils.path\_utils.is\_root\(_path: str_\) → bool[¶](zenml.utils.md#zenml.utils.path_utils.is_root)

Returns true if path has no parent in local filesystem.Parameters

**path** – Local path in filesystem.Returns

True if root, else False. zenml.utils.path\_utils.is\_zenml\_dir\(_path: str_\) → bool[¶](zenml.utils.md#zenml.utils.path_utils.is_zenml_dir)

Check if dir is a zenml dir or not.Parameters

**path** – Path to the root.Returns

True if path contains a zenml dir, False if not. zenml.utils.path\_utils.list\_dir\(_dir\_path: str_, _only\_file\_names: bool = False_\) → List\[str\][¶](zenml.utils.md#zenml.utils.path_utils.list_dir)

Returns a list of files under dir.Parameters

* **dir\_path** – Path in filesystem.
* **only\_file\_names** – Returns only file names if True.

Returns

List of full qualified paths. zenml.utils.path\_utils.load\_csv\_header\(_csv\_path: str_\) → List\[str\][¶](zenml.utils.md#zenml.utils.path_utils.load_csv_header)

Gets header column of csv and returns list.Parameters

**csv\_path** – Path to csv file. zenml.utils.path\_utils.move\(_source: str_, _destination: str_, _overwrite: bool = False_\)[¶](zenml.utils.md#zenml.utils.path_utils.move)

Moves dir from source to destination. Can be used to rename.Parameters

* **source** – Local path to copy from.
* **destination** – Local path to copy to.
* **overwrite** – boolean, if false, then throws an error before overwrite.

 zenml.utils.path\_utils.read\_file\_contents\(_file\_path: str_\)[¶](zenml.utils.md#zenml.utils.path_utils.read_file_contents)

Reads contents of file.Parameters

**file\_path** – Path to file. zenml.utils.path\_utils.resolve\_relative\_path\(_path: str_\)[¶](zenml.utils.md#zenml.utils.path_utils.resolve_relative_path)

Takes relative path and resolves it absolutely.Parameters

**path** – Local path in filesystem.Returns

Resolved path. zenml.utils.path\_utils.rm\_dir\(_dir\_path: str_\)[¶](zenml.utils.md#zenml.utils.path_utils.rm_dir)

Deletes dir recursively. Dangerous operation.Parameters

**dir\_path** – Dir to delete. zenml.utils.path\_utils.rm\_file\(_file\_path: str_\)[¶](zenml.utils.md#zenml.utils.path_utils.rm_file)

Deletes file. Dangerous operation.Parameters

**file\_path** – Path of file to delete. zenml.utils.path\_utils.walk\(_dir\_path_\) → Iterable\[Tuple\[Union\[bytes, str\], List\[Union\[bytes, str\]\], List\[Union\[bytes, str\]\]\]\][¶](zenml.utils.md#zenml.utils.path_utils.walk)

Walks down the dir\_path.Parameters

**dir\_path** – Path of dir to walk down.Returns

Iterable of tuples to walk down. zenml.utils.path\_utils.write\_file\_contents\(_file\_path: str_, _content: str_\)[¶](zenml.utils.md#zenml.utils.path_utils.write_file_contents)

Writes contents of file.Parameters

* **file\_path** – Path to file.
* **content** – Contents of file.

### zenml.utils.source\_utils module[¶](zenml.utils.md#module-zenml.utils.source_utils)

These utils are predicated on the following definitions:

* class\_source: This is a python-import type path to a class, e.g.

some.mod.class \* module\_source: This is a python-import type path to a module, e.g. some.mod \* file\_path, relative\_path, absolute\_path: These are file system paths. \* source: This is a class\_source or module\_source. If it is a class\_source, it can also be optionally pinned. \* pin: Whatever comes after the @ symbol from a source, usually the git sha or the version of zenml as a string. zenml.utils.source\_utils.create\_zenml\_pin\(\)[¶](zenml.utils.md#zenml.utils.source_utils.create_zenml_pin)

Creates a ZenML pin for source pinning from release version. zenml.utils.source\_utils.get\_absolute\_path\_from\_module\_source\(_module: str_\)[¶](zenml.utils.md#zenml.utils.source_utils.get_absolute_path_from_module_source)

Get a directory path from module source.

E.g. zenml.core.step will return full/path/to/zenml/core/step.Parameters

**module** \(_str_\) – A module e.g. zenml.core.step. zenml.utils.source\_utils.get\_class\_source\_from\_source\(_source: str_\) → Optional\[str\][¶](zenml.utils.md#zenml.utils.source_utils.get_class_source_from_source)

Gets class source from source, i.e. [module.path@version](mailto:module.path%40version), returns version.Parameters

**source** – source pointing to potentially pinned sha. zenml.utils.source\_utils.get\_module\_source\_from\_class\(_class\_: Union\[Type, str\]_\) → Optional\[str\][¶](zenml.utils.md#zenml.utils.source_utils.get_module_source_from_class)

Takes class input and returns module\_source. If class is already string then returns the same.Parameters

**class** – object of type class. zenml.utils.source\_utils.get\_module\_source\_from\_file\_path\(_file\_path_\)[¶](zenml.utils.md#zenml.utils.source_utils.get_module_source_from_file_path)

Gets module\_source from a file\_path. E.g. /home/myrepo/step/trainer.py returns myrepo.step.trainer if myrepo is the root of the repo.Parameters

**file\_path** – Absolute file path to a file within the module. zenml.utils.source\_utils.get\_module\_source\_from\_source\(_source: str_\) → str[¶](zenml.utils.md#zenml.utils.source_utils.get_module_source_from_source)

Gets module source from source. E.g. some.module.file.class@version, returns some.module.Parameters

**source** – source pointing to potentially pinned sha. zenml.utils.source\_utils.get\_path\_from\_source\(_source_\)[¶](zenml.utils.md#zenml.utils.source_utils.get_path_from_source)

Get file path from sourceParameters

**source** \(_str_\) – class\_source e.g. this.module.Class. zenml.utils.source\_utils.get\_pin\_from\_source\(_source: str_\) → Optional\[str\][¶](zenml.utils.md#zenml.utils.source_utils.get_pin_from_source)

Gets pin from source, i.e. [module.path@pin](mailto:module.path%40pin), returns pin.Parameters

**source** \(_str_\) – class\_source e.g. this.module.Class\[@pin\]. zenml.utils.source\_utils.get\_relative\_path\_from\_module\_source\(_module\_source: str_\)[¶](zenml.utils.md#zenml.utils.source_utils.get_relative_path_from_module_source)

Get a directory path from module, relative to root of repository.

E.g. zenml.core.step will return zenml/core/step.Parameters

**module\_source** \(_str_\) – A module e.g. zenml.core.step zenml.utils.source\_utils.is\_standard\_pin\(_pin: str_\) → bool[¶](zenml.utils.md#zenml.utils.source_utils.is_standard_pin)

Returns True if pin is valid ZenML pin, else False.Parameters

**pin** \(_str_\) – potential ZenML pin like ‘zenml\_0.1.1’ zenml.utils.source\_utils.is\_standard\_source\(_source: str_\) → bool[¶](zenml.utils.md#zenml.utils.source_utils.is_standard_source)

Returns True if source is a standard ZenML source.Parameters

**source** \(_str_\) – class\_source e.g. this.module.Class\[@pin\]. zenml.utils.source\_utils.load\_source\_path\_class\(_source: str_\) → Type[¶](zenml.utils.md#zenml.utils.source_utils.load_source_path_class)

Loads a Python class from the source.Parameters

**source** – class\_source e.g. this.module.Class\[@sha\] zenml.utils.source\_utils.resolve\_class\(_class\_: Type_\) → str[¶](zenml.utils.md#zenml.utils.source_utils.resolve_class)

Resolves a a class into a serializable source string.Parameters

**class** – A Python Class reference.

Returns: source\_path e.g. this.module.Class. zenml.utils.source\_utils.resolve\_standard\_source\(_source: str_\) → str[¶](zenml.utils.md#zenml.utils.source_utils.resolve_standard_source)

Creates a ZenML pin for source pinning from release version.Parameters

**source** \(_str_\) – class\_source e.g. this.module.Class.

### zenml.utils.yaml\_utils module[¶](zenml.utils.md#module-zenml.utils.yaml_utils)

 zenml.utils.yaml\_utils.is\_yaml\(_file\_path: str_\)[¶](zenml.utils.md#zenml.utils.yaml_utils.is_yaml)

Returns True if file\_path is YAML, else FalseParameters

**file\_path** – Path to YAML file.Returns

True if is yaml, else False. zenml.utils.yaml\_utils.read\_json\(_file\_path: str_\)[¶](zenml.utils.md#zenml.utils.yaml_utils.read_json)

Read JSON on file path and returns contents as dict.Parameters

**file\_path** – Path to JSON file. zenml.utils.yaml\_utils.read\_yaml\(_file\_path: str_\) → Dict[¶](zenml.utils.md#zenml.utils.yaml_utils.read_yaml)

Read YAML on file path and returns contents as dict.Parameters

**file\_path** \(_str_\) – Path to YAML file.Returns

Contents of the file in a dict.Raises

**FileNotFoundError if file does not exist.** – zenml.utils.yaml\_utils.write\_json\(_file\_path: str_, _contents: Dict_\)[¶](zenml.utils.md#zenml.utils.yaml_utils.write_json)

Write contents as JSON format to file\_path.Parameters

* **file\_path** – Path to JSON file.
* **contents** – Contents of JSON file as dict.

Returns

Contents of the file in a dict.Raises

**FileNotFoundError if directory does not exist.** – zenml.utils.yaml\_utils.write\_yaml\(_file\_path: str_, _contents: Dict_\)[¶](zenml.utils.md#zenml.utils.yaml_utils.write_yaml)

Write contents as YAML format to file\_path.Parameters

* **file\_path** – Path to YAML file.
* **contents** – Contents of YAML file as dict.

Raises

**FileNotFoundError if directory does not exist.** –

### Module contents[¶](zenml.utils.md#module-zenml.utils)

 [Back to top](zenml.utils.md)

 © Copyright 2021, ZenML GmbH.  
 Created using [Sphinx](http://sphinx-doc.org/) 4.2.0.  


