# zenml.utils package

## Submodules

## zenml.utils.archivable module

Archivable mixin.

### *class* zenml.utils.archivable.Archivable(\*args: Any, \*\*kwargs: Any)

Bases: `ABC`

Archivable mixin class.

#### add_directory(source: str, destination: str) → None

Adds a directory to the archive.

Args:
: source: Path to the directory.
  destination: The path inside the build context where the directory
  <br/>
  > should be added.

Raises:
: ValueError: If source does not point to a directory.

#### add_file(source: str, destination: str) → None

Adds a file to the archive.

Args:
: source: The source of the file to add. This can either be a path
  : or the file content.
  <br/>
  destination: The path inside the archive where the file
  : should be added.

#### get_extra_files() → Dict[str, str]

Gets all extra files that should be included in the archive.

Returns:
: A dict {path_in_archive: file_content} for all extra files in the
  archive.

#### *abstract* get_files() → Dict[str, str]

Gets all regular files that should be included in the archive.

Returns:
: A dict {path_in_archive: path_on_filesystem} for all regular files
  in the archive.

#### write_archive(output_file: IO[bytes], use_gzip: bool = True) → None

Writes an archive of the build context to the given file.

Args:
: output_file: The file to write the archive to.
  use_gzip: Whether to use gzip to compress the file.

## zenml.utils.cloud_utils module

Utilities for ZenML Pro.

### zenml.utils.cloud_utils.try_get_model_version_url(model_version: [ModelVersionResponse](zenml.models.v2.core.md#zenml.models.v2.core.model_version.ModelVersionResponse)) → str

Check if a model version is from a ZenML Pro server and return its’ URL.

Args:
: model_version: The model version to check.

Returns:
: URL if the model version is from a ZenML Pro server, else empty string.

## zenml.utils.code_repository_utils module

Utilities for code repositories.

### zenml.utils.code_repository_utils.find_active_code_repository(path: str | None = None) → [LocalRepositoryContext](zenml.code_repositories.md#zenml.code_repositories.local_repository_context.LocalRepositoryContext) | None

Find the active code repository for a given path.

Args:
: path: Path at which to look for the code repository. If not given, the
  : source root will be used.

Returns:
: The local repository context active at that path or None.

### zenml.utils.code_repository_utils.set_custom_local_repository(root: str, commit: str, repo: [BaseCodeRepository](zenml.code_repositories.md#zenml.code_repositories.base_code_repository.BaseCodeRepository)) → None

Manually defines a local repository for a path.

To explain what this function does we need to take a dive into source
resolving and what happens inside the Docker image entrypoint:
\* When trying to resolve an object to a source, we first determine whether
the file is a user file or not.
\* If the file is a user file, we check if that user file is inside a clean
code repository using the
code_repository_utils.find_active_code_repository(…) function. If that
is the case, the object will be resolved to a CodeRepositorySource which
includes additional information about the current commit and the ID of the
code repository.
\* The code_repository_utils.find_active_code_repository(…) uses the
code repository implementation classes to check whether the code repository
“exists” at that local path. For git repositories, this check might look as
follows: The code repository first checks if there is a git repository at
that path or in any parent directory. If there is, the remote URLs of this
git repository will be checked to see if one matches the URL defined for
the code repository.
\* When running a step inside a Docker image, ZenML potentially downloads
files from a code repository. This usually does not download the entire
repository (and in the case of git might not download a .git directory which
defines a local git repository) but only specific files. If we now try to
resolve any object while running in this container, it will not get resolved
to a CodeRepositorySource as
code_repository_utils.find_active_code_repository(…) won’t find an
active repository. As we downloaded these files, we however know that they
belong to a certain code repository at a specific commit, and that’s what we
can define using this function.

Args:
: root: The repository root.
  commit: The commit of the repository.
  repo: The code repository associated with the local repository.

## zenml.utils.code_utils module

Code utilities.

### *class* zenml.utils.code_utils.CodeArchive(root: str | None = None)

Bases: [`Archivable`](#zenml.utils.archivable.Archivable)

Code archive class.

This class is used to archive user code before uploading it to the artifact
store. If the user code is stored in a Git repository, only files not
excluded by gitignores will be included in the archive.

#### get_files() → Dict[str, str]

Gets all regular files that should be included in the archive.

Raises:
: RuntimeError: If the code archive would not include any files.

Returns:
: A dict {path_in_archive: path_on_filesystem} for all regular files
  in the archive.

#### *property* git_repo *: Repo | None*

Git repository active at the code archive root.

Returns:
: The git repository if available.

#### write_archive(output_file: IO[bytes], use_gzip: bool = True) → None

Writes an archive of the build context to the given file.

Args:
: output_file: The file to write the archive to.
  use_gzip: Whether to use gzip to compress the file.

### zenml.utils.code_utils.compute_file_hash(file: IO[bytes]) → str

Compute a hash of the content of a file.

This function will not seek the file before or after the hash computation.
This means that the content will be computed based on the current cursor
until the end of the file.

Args:
: file: The file for which to compute the hash.

Returns:
: A hash of the file content.

### zenml.utils.code_utils.download_and_extract_code(code_path: str, extract_dir: str) → None

Download and extract code.

Args:
: code_path: Path where the code is uploaded.
  extract_dir: Directory where to code should be extracted to.

Raises:
: RuntimeError: If the code is stored in an artifact store which is
  : not active.

### zenml.utils.code_utils.download_code_from_artifact_store(code_path: str) → None

Download code from the artifact store.

Args:
: code_path: Path where the code is stored.

### zenml.utils.code_utils.download_notebook_code(artifact_store: [BaseArtifactStore](zenml.artifact_stores.md#zenml.artifact_stores.base_artifact_store.BaseArtifactStore), file_name: str, download_path: str) → None

Download code extracted from a notebook cell.

Args:
: artifact_store: The artifact store from which to download the code.
  file_name: The name of the code file.
  download_path: The local path where the file should be downloaded to.

Raises:
: FileNotFoundError: If no file with the given filename exists in this
  : artifact store.

### zenml.utils.code_utils.upload_code_if_necessary(code_archive: [CodeArchive](#zenml.utils.code_utils.CodeArchive)) → str

Upload code to the artifact store if necessary.

This function computes a hash of the code to be uploaded, and if an archive
with the same hash already exists it will not re-upload but instead return
the path to the existing archive.

Args:
: code_archive: The code archive to upload.

Returns:
: The path where the archived code is uploaded.

### zenml.utils.code_utils.upload_notebook_code(artifact_store: [BaseArtifactStore](zenml.artifact_stores.md#zenml.artifact_stores.base_artifact_store.BaseArtifactStore), cell_code: str, file_name: str) → None

Upload code extracted from a notebook cell.

Args:
: artifact_store: The artifact store in which to upload the code.
  cell_code: The notebook cell code.
  file_name: The filename to use for storing the cell code.

## zenml.utils.cuda_utils module

Utilities for managing GPU memory.

### zenml.utils.cuda_utils.cleanup_gpu_memory(force: bool = False) → None

Clean up GPU memory.

Args:
: force: whether to force the cleanup of GPU memory (must be passed explicitly)

## zenml.utils.daemon module

Utility functions to start/stop daemon processes.

This is only implemented for UNIX systems and therefore doesn’t work on
Windows. Based on
[https://www.jejik.com/articles/2007/02/a_simple_unix_linux_daemon_in_python/](https://www.jejik.com/articles/2007/02/a_simple_unix_linux_daemon_in_python/)

### zenml.utils.daemon.check_if_daemon_is_running(pid_file: str) → bool

Checks whether a daemon process indicated by the PID file is running.

Args:
: pid_file: Path to file containing the PID of the daemon
  : process to check.

Returns:
: True if the daemon process is running, otherwise False.

### zenml.utils.daemon.daemonize(pid_file: str, log_file: str | None = None, working_directory: str = '/') → Callable[[F], F]

Decorator that executes the decorated function as a daemon process.

Use this decorator to easily transform any function into a daemon
process.

For example,

```
``
```

```
`
```

python
import time
from zenml.utils.daemon import daemonize

@daemonize(log_file=’/tmp/daemon.log’, pid_file=’/tmp/daemon.pid’)
def sleeping_daemon(period: int) -> None:

> print(f”I’m a daemon! I will sleep for {period} seconds.”)
> time.sleep(period)
> print(“Done sleeping, flying away.”)

sleeping_daemon(period=30)

print(“I’m the daemon’s parent!.”)
time.sleep(10) # just to prove that the daemon is running in parallel

```
``
```

```
`
```

Args:
: pid_file: a file where the PID of the daemon process will
  : be stored.
  <br/>
  log_file: file where stdout and stderr are redirected for the daemon
  : process. If not supplied, the daemon will be silenced (i.e. have
    its stdout/stderr redirected to /dev/null).
  <br/>
  working_directory: working directory for the daemon process,
  : defaults to the root directory.

Returns:
: Decorated function that, when called, will detach from the current
  process and continue executing in the background, as a daemon
  process.

### zenml.utils.daemon.get_daemon_pid_if_running(pid_file: str) → int | None

Read and return the PID value from a PID file.

It does this if the daemon process tracked by the PID file is running.

Args:
: pid_file: Path to file containing the PID of the daemon
  : process to check.

Returns:
: The PID of the daemon process if it is running, otherwise None.

### zenml.utils.daemon.run_as_daemon(daemon_function: F, \*args: Any, pid_file: str, log_file: str | None = None, working_directory: str = '/', \*\*kwargs: Any) → None

Runs a function as a daemon process.

Args:
: daemon_function: The function to run as a daemon.
  pid_file: Path to file in which to store the PID of the daemon
  <br/>
  > process.
  <br/>
  log_file: Optional file to which the daemons stdout/stderr will be
  : redirected to.
  <br/>
  working_directory: Working directory for the daemon process,
  : defaults to the root directory.
  <br/>
  args: Positional arguments to pass to the daemon function.
  kwargs: Keyword arguments to pass to the daemon function.

Raises:
: FileExistsError: If the PID file already exists.

### zenml.utils.daemon.stop_daemon(pid_file: str) → None

Stops a daemon process.

Args:
: pid_file: Path to file containing the PID of the daemon process to
  : kill.

### zenml.utils.daemon.terminate_children() → None

Terminate all processes that are children of the currently running process.

## zenml.utils.dashboard_utils module

Utility class to help with interacting with the dashboard.

### zenml.utils.dashboard_utils.get_cloud_dashboard_url() → str | None

Get the base url of the cloud dashboard if the server is a cloud tenant.

Returns:
: The base url of the cloud dashboard.

### zenml.utils.dashboard_utils.get_component_url(component: [ComponentResponse](zenml.models.v2.core.md#zenml.models.v2.core.component.ComponentResponse)) → str | None

Function to get the dashboard URL of a given component model.

Args:
: component: the response model of the given component.

Returns:
: the URL to the component if the dashboard is available, else None.

### zenml.utils.dashboard_utils.get_model_version_url(model_version_id: UUID) → str | None

Function to get the dashboard URL of a given model version.

Args:
: model_version_id: the id of the model version.

Returns:
: the URL to the model version if the dashboard is available, else None.

### zenml.utils.dashboard_utils.get_run_url(run: [PipelineRunResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_run.PipelineRunResponse)) → str | None

Function to get the dashboard URL of a given pipeline run.

Args:
: run: the response model of the given pipeline run.

Returns:
: the URL to the pipeline run if the dashboard is available, else None.

### zenml.utils.dashboard_utils.get_server_dashboard_url() → Tuple[str | None, bool]

Get the base url of the dashboard deployed by the server.

Returns:
: The server dashboard url and whether the dashboard is the legacy
  dashboard or not.

### zenml.utils.dashboard_utils.get_stack_url(stack: [StackResponse](zenml.models.v2.core.md#zenml.models.v2.core.stack.StackResponse)) → str | None

Function to get the dashboard URL of a given stack model.

Args:
: stack: the response model of the given stack.

Returns:
: the URL to the stack if the dashboard is available, else None.

### zenml.utils.dashboard_utils.is_cloud_server(server_info: [ServerModel](zenml.models.v2.misc.md#zenml.models.v2.misc.server_models.ServerModel)) → bool

Checks whether the server info refers to a ZenML Pro server.

Args:
: server_info: Info of the server.

Returns:
: Whether the server info refers to a ZenML Pro server.

### zenml.utils.dashboard_utils.show_dashboard(url: str) → None

Show the ZenML dashboard at the given URL.

In native environments, the dashboard is opened in the default browser.
In notebook environments, the dashboard is embedded in an iframe.

Args:
: url: URL of the ZenML dashboard.

## zenml.utils.deprecation_utils module

Deprecation utilities.

### zenml.utils.deprecation_utils.deprecate_pydantic_attributes(\*attributes: str | Tuple[str, str]) → Any

Utility function for deprecating and migrating pydantic attributes.

**Usage**:
To use this, you can specify it on any pydantic BaseModel subclass like
this (all the deprecated attributes need to be non-required):

```
``
```

```
`
```

python
from pydantic import BaseModel
from typing import Optional

class MyModel(BaseModel):
: deprecated: Optional[int] = None
  <br/>
  old_name: Optional[str] = None
  new_name: str
  <br/>
  \_deprecation_validator = deprecate_pydantic_attributes(
  : “deprecated”, (“old_name”, “new_name”)
  <br/>
  )

```
``
```

```
`
```

Args:
: ```
  *
  ```
  <br/>
  attributes: List of attributes to deprecate. This is either the name
  : of the attribute to deprecate, or a tuple containing the name of
    the deprecated attribute, and it’s replacement.

Returns:
: Pydantic validator class method to be used on BaseModel subclasses
  to deprecate or migrate attributes.

## zenml.utils.dict_utils module

Util functions for dictionaries.

### zenml.utils.dict_utils.dict_to_bytes(dict_: Dict[str, Any]) → bytes

Converts a dictionary to bytes.

Args:
: ```
  dict_
  ```
  <br/>
  : The dictionary to convert.

Returns:
: The dictionary as bytes.

### zenml.utils.dict_utils.recursive_update(original: Dict[str, Any], update: Dict[str, Any]) → Dict[str, Any]

Recursively updates a dictionary.

Args:
: original: The dictionary to update.
  update: The dictionary containing the updated values.

Returns:
: The updated dictionary.

### zenml.utils.dict_utils.remove_none_values(dict_: Dict[str, Any], recursive: bool = False) → Dict[str, Any]

Removes all key-value pairs with None value.

Args:
: ```
  dict_
  ```
  <br/>
  : The dict from which the key-value pairs should be removed.
  recursive: If True, will recursively remove None values in all
  <br/>
  > child dicts.

Returns:
: The updated dictionary.

## zenml.utils.docker_utils module

Utility functions relating to Docker.

### zenml.utils.docker_utils.build_image(image_name: str, dockerfile: str | List[str], build_context_root: str | None = None, dockerignore: str | None = None, extra_files: Sequence[Tuple[str, str]] = (), \*\*custom_build_options: Any) → None

Builds a docker image.

Args:
: image_name: The name to use for the built docker image.
  dockerfile: Path to a dockerfile or a list of strings representing the
  <br/>
  > Dockerfile lines/commands.
  <br/>
  build_context_root: Optional path to a directory that will be sent to
  : the Docker daemon as build context. If left empty, the Docker build
    context will be empty.
  <br/>
  dockerignore: Optional path to a dockerignore file. If no value is
  : given, the .dockerignore in the root of the build context will be
    used if it exists. Otherwise, all files inside build_context_root
    are included in the build context.
  <br/>
  extra_files: Additional files to include in the build context. The
  : files should be passed as a tuple
    (filepath_inside_build_context, file_content) and will overwrite
    existing files in the build context if they share the same path.
  <br/>
  ```
  **
  ```
  <br/>
  custom_build_options: Additional options that will be passed
  : unmodified to the Docker build call when building the image. You
    can use this to for example specify build args or a target stage.
    See [https://docker-py.readthedocs.io/en/stable/images.html#docker.models.images.ImageCollection.build](https://docker-py.readthedocs.io/en/stable/images.html#docker.models.images.ImageCollection.build)
    for a full list of available options.

### zenml.utils.docker_utils.check_docker() → bool

Checks if Docker is installed and running.

Returns:
: True if Docker is installed, False otherwise.

### zenml.utils.docker_utils.get_image_digest(image_name: str) → str | None

Gets the digest of an image.

Args:
: image_name: Name of the image to get the digest for.

Returns:
: Returns the repo digest for the given image if there exists exactly one.
  If there are zero or multiple repo digests, returns None.

### zenml.utils.docker_utils.is_local_image(image_name: str) → bool

Returns whether an image was pulled from a registry or not.

Args:
: image_name: Name of the image to check.

Returns:
: True if the image was pulled from a registry, False otherwise.

### zenml.utils.docker_utils.push_image(image_name: str, docker_client: DockerClient | None = None) → str

Pushes an image to a container registry.

Args:
: image_name: The full name (including a tag) of the image to push.
  docker_client: Optional Docker client to use for pushing the image. If
  <br/>
  > no client is given, a new client will be created using the default
  > Docker environment.

Returns:
: The Docker repository digest of the pushed image.

Raises:
: RuntimeError: If fetching the repository digest of the image failed.

### zenml.utils.docker_utils.tag_image(image_name: str, target: str) → None

Tags an image.

Args:
: image_name: The name of the image to tag.
  target: The full target name including a tag.

## zenml.utils.downloaded_repository_context module

Downloaded code repository.

## zenml.utils.enum_utils module

Util functions for enums.

### *class* zenml.utils.enum_utils.StrEnum(value, names=None, \*, module=None, qualname=None, type=None, start=1, boundary=None)

Bases: `str`, `Enum`

Base enum type for string enum values.

#### *classmethod* names() → List[str]

Get all enum names as a list of strings.

Returns:
: A list of all enum names.

#### *classmethod* values() → List[str]

Get all enum values as a list of strings.

Returns:
: A list of all enum values.

## zenml.utils.env_utils module

Utility functions for handling environment variables.

### zenml.utils.env_utils.reconstruct_environment_variables(env: Dict[str, str] | None = None) → None

Reconstruct environment variables that were split into chunks.

Reconstructs the environment variables with values that were split into
individual chunks because they were too large. The input environment
variables are modified in-place.

Args:
: env: Input environment variables dictionary. If not supplied, the OS
  : environment variables are used.

### zenml.utils.env_utils.split_environment_variables(size_limit: int, env: Dict[str, str] | None = None) → None

Split long environment variables into chunks.

Splits the input environment variables with values that exceed the supplied
maximum length into individual components. The input environment variables
are modified in-place.

Args:
: size_limit: Maximum length of an environment variable value.
  env: Input environment variables dictionary. If not supplied, the
  <br/>
  > OS environment variables are used.

Raises:
: RuntimeError: If an environment variable value is too large and requires
  : more than 10 chunks.

## zenml.utils.filesync_model module

Filesync utils for ZenML.

### *class* zenml.utils.filesync_model.FileSyncModel

Bases: `BaseModel`

Pydantic model synchronized with a configuration file.

Use this class as a base Pydantic model that is automatically synchronized
with a configuration file on disk.

This class overrides the \_\_setattr_\_ and \_\_getattr_\_ magic methods to
ensure that the FileSyncModel instance acts as an in-memory cache of the
information stored in the associated configuration file.

#### *classmethod* config_validator(data: Any, handler: ValidatorFunctionWrapHandler, info: ValidationInfo) → [FileSyncModel](#zenml.utils.filesync_model.FileSyncModel)

Wrap model validator to infer the config_file during initialization.

Args:
: data: The raw data that is provided before the validation.
  handler: The actual validation function pydantic would use for the
  <br/>
  > built-in validation function.
  <br/>
  info: The context information during the execution of this
  : validation function.

Returns:
: the actual instance after the validation

Raises:
: ValidationError: if you try to validate through a JSON string. You
  : need to provide a config_file path when you create a
    FileSyncModel.
  <br/>
  AssertionError: if the raw input does not include a config_file
  : path for the configuration file.

#### load_config() → None

Loads the model from the configuration file on disk.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

This function is meant to behave like a BaseModel method to initialise private attributes.

It takes context as an argument since that’s what pydantic-core passes when calling it.

Args:
: self: The BaseModel instance.
  context: The context.

#### write_config() → None

Writes the model to the configuration file.

## zenml.utils.function_utils module

Utility functions for python functions.

### zenml.utils.function_utils.create_cli_wrapped_script(func: F, flavor: str = 'accelerate') → Iterator[Tuple[Path, Path]]

Create a script with the CLI-wrapped function.

Args:
: func: The function to use.
  flavor: The flavor to use.

Yields:
: The paths of the script and the output.

Raises:
: ValueError: If the function is not defined in a module.

## zenml.utils.git_utils module

Utility function to clone a Git repository.

### zenml.utils.git_utils.clone_git_repository(url: str, to_path: str, branch: str | None = None, commit: str | None = None) → Repo

Clone a Git repository.

Args:
: url: URL of the repository to clone.
  to_path: Path to clone the repository to.
  branch: Branch to clone. Defaults to “main”.
  commit: Commit to checkout. If specified, the branch argument is
  <br/>
  > ignored.

Returns:
: The cloned repository.

Raises:
: RuntimeError: If the repository could not be cloned.

## zenml.utils.integration_utils module

Util functions for integration.

### zenml.utils.integration_utils.parse_requirement(requirement: str) → Tuple[str | None, str | None]

Parse a requirement string into name and extras.

Args:
: requirement: A requirement string.

Returns:
: A tuple of name and extras.

## zenml.utils.io_utils module

Various utility functions for the io module.

### zenml.utils.io_utils.copy_dir(source_dir: str, destination_dir: str, overwrite: bool = False) → None

Copies dir from source to destination.

Args:
: source_dir: Path to copy from.
  destination_dir: Path to copy to.
  overwrite: Boolean. If false, function throws an error before overwrite.

### zenml.utils.io_utils.create_dir_if_not_exists(dir_path: str) → None

Creates directory if it does not exist.

Args:
: dir_path: Local path in filesystem.

### zenml.utils.io_utils.create_dir_recursive_if_not_exists(dir_path: str) → None

Creates directory recursively if it does not exist.

Args:
: dir_path: Local path in filesystem.

### zenml.utils.io_utils.create_file_if_not_exists(file_path: str, file_contents: str = '{}') → None

Creates file if it does not exist.

Args:
: file_path: Local path in filesystem.
  file_contents: Contents of file.

### zenml.utils.io_utils.find_files(dir_path: PathType, pattern: str) → Iterable[str]

Find files in a directory that match pattern.

Args:
: dir_path: The path to directory.
  pattern: pattern like 
  <br/>
  ```
  *
  ```
  <br/>
  .png.

Yields:
: All matching filenames in the directory.

### zenml.utils.io_utils.get_global_config_directory() → str

Gets the global config directory for ZenML.

Returns:
: The global config directory for ZenML.

### zenml.utils.io_utils.get_grandparent(dir_path: str) → str

Get grandparent of dir.

Args:
: dir_path: The path to directory.

Returns:
: The input paths parents parent.

Raises:
: ValueError: If dir_path does not exist.

### zenml.utils.io_utils.get_parent(dir_path: str) → str

Get parent of dir.

Args:
: dir_path: The path to directory.

Returns:
: Parent (stem) of the dir as a string.

Raises:
: ValueError: If dir_path does not exist.

### zenml.utils.io_utils.is_remote(path: str) → bool

Returns True if path exists remotely.

Args:
: path: Any path as a string.

Returns:
: True if remote path, else False.

### zenml.utils.io_utils.is_root(path: str) → bool

Returns true if path has no parent in local filesystem.

Args:
: path: Local path in filesystem.

Returns:
: True if root, else False.

### zenml.utils.io_utils.move(source: str, destination: str, overwrite: bool = False) → None

Moves dir or file from source to destination. Can be used to rename.

Args:
: source: Local path to copy from.
  destination: Local path to copy to.
  overwrite: boolean, if false, then throws an error before overwrite.

### zenml.utils.io_utils.read_file_contents_as_string(file_path: str) → str

Reads contents of file.

Args:
: file_path: Path to file.

Returns:
: Contents of file.

Raises:
: FileNotFoundError: If file does not exist.

### zenml.utils.io_utils.resolve_relative_path(path: str) → str

Takes relative path and resolves it absolutely.

Args:
: path: Local path in filesystem.

Returns:
: Resolved path.

### zenml.utils.io_utils.write_file_contents_as_string(file_path: str, content: str) → None

Writes contents of file.

Args:
: file_path: Path to file.
  content: Contents of file.

Raises:
: ValueError: If content is not of type str.

## zenml.utils.json_utils module

Carried over version of some functions from the pydantic v1 json module.

Check out the latest version here:
[https://github.com/pydantic/pydantic/blob/v1.10.15/pydantic/json.py](https://github.com/pydantic/pydantic/blob/v1.10.15/pydantic/json.py)

### zenml.utils.json_utils.decimal_encoder(dec_value: Decimal) → int | float

Encodes a Decimal as int of there’s no exponent, otherwise float.

This is useful when we use ConstrainedDecimal to represent Numeric(x,0)
where an integer (but not int typed) is used. Encoding this as a float
results in failed round-tripping between encode and parse.
Our ID type is a prime example of this.

```pycon
>>> decimal_encoder(Decimal("1.0"))
1.0
```

```pycon
>>> decimal_encoder(Decimal("1"))
1
```

Args:
: dec_value: The input Decimal value

Returns:
: the encoded result

### zenml.utils.json_utils.isoformat(obj: date | time) → str

Function to convert a datetime into iso format.

Args:
: obj: input datetime

Returns:
: the corresponding time in iso format.

### zenml.utils.json_utils.pydantic_encoder(obj: Any) → Any

## zenml.utils.materializer_utils module

Util functions for materializers.

### zenml.utils.materializer_utils.select_materializer(data_type: Type[Any], materializer_classes: Sequence[Type[[BaseMaterializer](zenml.materializers.md#zenml.materializers.base_materializer.BaseMaterializer)]]) → Type[[BaseMaterializer](zenml.materializers.md#zenml.materializers.base_materializer.BaseMaterializer)]

Select a materializer for a given data type.

Args:
: data_type: The data type for which to select the materializer.
  materializer_classes: Available materializer classes.

Raises:
: RuntimeError: If no materializer can handle the given data type.

Returns:
: The first materializer that can handle the given data type.

## zenml.utils.mlstacks_utils module

Functionality to handle interaction with the mlstacks package.

### zenml.utils.mlstacks_utils.convert_click_params_to_mlstacks_primitives(params: Dict[str, Any], zenml_component_deploy: bool = False) → Tuple[[Stack](zenml.stack.md#zenml.stack.stack.Stack), List[Component]]

Converts raw Click CLI params to mlstacks primitives.

Args:
: params: Raw Click CLI params.
  zenml_component_deploy: A boolean indicating whether the stack
  <br/>
  > contains a single component and is being deployed through zenml
  > component deploy

Returns:
: A tuple of Stack and List[Component] objects.

### zenml.utils.mlstacks_utils.convert_mlstacks_primitives_to_dicts(stack: [Stack](zenml.stack.md#zenml.stack.stack.Stack), components: List[Component]) → Tuple[Dict[str, Any], List[Dict[str, Any]]]

Converts mlstacks Stack and Components to dicts.

Args:
: stack: A mlstacks Stack object.
  components: A list of mlstacks Component objects.

Returns:
: A tuple of Stack and List[Component] dicts.

### zenml.utils.mlstacks_utils.deploy_mlstacks_stack(spec_file_path: str, stack_name: str, stack_provider: str, debug_mode: bool = False, no_import_stack_flag: bool = False, user_created_spec: bool = False) → None

Deploys an MLStacks stack given a spec file path.

Args:
: spec_file_path: The path to the spec file.
  stack_name: The name of the stack.
  stack_provider: The cloud provider for which the stack is deployed.
  debug_mode: A boolean indicating whether to run in debug mode.
  no_import_stack_flag: A boolean indicating whether to import the stack
  <br/>
  > into ZenML.
  <br/>
  user_created_spec: A boolean indicating whether the user created the
  : spec file.

### zenml.utils.mlstacks_utils.get_stack_spec_file_path(stack_name: str) → str

Gets the path to the stack spec file for the given stack name.

Args:
: stack_name: The name of the stack spec to get the path for.

Returns:
: The path to the stack spec file for the given stack name.

Raises:
: KeyError: If the stack does not exist.

### zenml.utils.mlstacks_utils.import_new_mlstacks_component(stack_name: str, component_name: str, provider: str, stack_spec_dir: str) → None

Import a new component deployed for a particular cloud provider.

Args:
: stack_name: The name of the stack to import.
  component_name: The name of the component to import.
  provider: The cloud provider for which the stack is deployed.
  stack_spec_dir: The path to the directory containing the stack spec.

### zenml.utils.mlstacks_utils.import_new_mlstacks_stack(stack_name: str, provider: str, stack_spec_dir: str, user_stack_spec_file: str | None = None) → None

Import a new stack deployed for a particular cloud provider.

Args:
: stack_name: The name of the stack to import.
  provider: The cloud provider for which the stack is deployed.
  stack_spec_dir: The path to the directory containing the stack spec.
  user_stack_spec_file: The path to the user-created stack spec file.

### zenml.utils.mlstacks_utils.stack_exists(stack_name: str) → bool

Checks whether a stack with that name exists or not.

Args:
: stack_name: The name of the stack to check for.

Returns:
: A boolean indicating whether the stack exists or not.

### zenml.utils.mlstacks_utils.stack_spec_exists(stack_name: str) → bool

Checks whether a stack spec with that name exists or not.

Args:
: stack_name: The name of the stack spec to check for.

Returns:
: A boolean indicating whether the stack spec exists or not.

### zenml.utils.mlstacks_utils.verify_spec_and_tf_files_exist(spec_file_path: str, tf_file_path: str) → None

Checks whether both the spec and tf files exist.

Args:
: spec_file_path: The path to the spec file.
  tf_file_path: The path to the tf file.

## zenml.utils.networking_utils module

Utility functions for networking.

### zenml.utils.networking_utils.find_available_port() → int

Finds a local random unoccupied TCP port.

Returns:
: A random unoccupied TCP port.

### zenml.utils.networking_utils.get_or_create_ngrok_tunnel(ngrok_token: str, port: int) → str

Get or create an ngrok tunnel at the given port.

Args:
: ngrok_token: The ngrok auth token.
  port: The port to tunnel.

Returns:
: The public URL of the ngrok tunnel.

Raises:
: ImportError: If the pyngrok package is not installed.

### zenml.utils.networking_utils.port_available(port: int, address: str = '127.0.0.1') → bool

Checks if a local port is available.

Args:
: port: TCP port number
  address: IP address on the local machine

Returns:
: True if the port is available, otherwise False

### zenml.utils.networking_utils.port_is_open(hostname: str, port: int) → bool

Check if a TCP port is open on a remote host.

Args:
: hostname: hostname of the remote machine
  port: TCP port number

Returns:
: True if the port is open, False otherwise

### zenml.utils.networking_utils.replace_internal_hostname_with_localhost(hostname: str) → str

Replaces an internal Docker or K3D hostname with localhost.

Localhost URLs that are directly accessible on the host machine are not
accessible from within a Docker or K3D container running on that same
machine, but there are special hostnames featured by both Docker
(host.docker.internal) and K3D (host.k3d.internal) that can be used to
access host services from within the containers.

Use this method to replace one of these special hostnames with localhost
if used outside a container or in a container where special hostnames are
not available.

Args:
: hostname: The hostname to replace.

Returns:
: The original or replaced hostname.

### zenml.utils.networking_utils.replace_localhost_with_internal_hostname(url: str) → str

Replaces the localhost with an internal Docker or K3D hostname in a given URL.

Localhost URLs that are directly accessible on the host machine are not
accessible from within a Docker or K3D container running on that same
machine, but there are special hostnames featured by both Docker
(host.docker.internal) and K3D (host.k3d.internal) that can be used to
access host services from within the containers.

Use this method to attempt to replace localhost in a URL with one of these
special hostnames, if they are available inside a container.

Args:
: url: The URL to update.

Returns:
: The updated URL.

### zenml.utils.networking_utils.scan_for_available_port(start: int = 8000, stop: int = 65535) → int | None

Scan the local network for an available port in the given range.

Args:
: start: the beginning of the port range value to scan
  stop: the (inclusive) end of the port range value to scan

Returns:
: The first available port in the given range, or None if no available
  port is found.

## zenml.utils.notebook_utils module

Notebook utilities.

### zenml.utils.notebook_utils.compute_cell_replacement_module_name(cell_code: str) → str

Compute the replacement module name for a given cell code.

Args:
: cell_code: The code of the notebook cell.

Returns:
: The replacement module name.

### zenml.utils.notebook_utils.enable_notebook_code_extraction(\_obj: AnyObject | None = None) → AnyObject | Callable[[AnyObject], AnyObject]

Decorator to enable code extraction from notebooks.

Args:
: \_obj: The class or function for which to enable code extraction.

Returns:
: The decorated class or function.

### zenml.utils.notebook_utils.get_active_notebook_cell_code() → str | None

Get the code of the currently active notebook cell.

Returns:
: The code of the currently active notebook cell.

### zenml.utils.notebook_utils.is_defined_in_notebook_cell(obj: Any) → bool

Check whether an object is defined in a notebook cell.

Args:
: obj: The object to check.

Returns:
: Whether the object is defined in a notebook cell.

### zenml.utils.notebook_utils.load_notebook_cell_code(obj: Any) → str | None

Load the notebook cell code for an object.

Args:
: obj: The object for which to load the cell code.

Returns:
: The notebook cell code if it was saved.

### zenml.utils.notebook_utils.try_to_save_notebook_cell_code(obj: Any) → None

Try to save the notebook cell code for an object.

Args:
: obj: The object for which to save the notebook cell code.

### zenml.utils.notebook_utils.warn_about_notebook_cell_magic_commands(cell_code: str) → None

Warn about magic commands in the cell code.

Args:
: cell_code: The cell code.

## zenml.utils.package_utils module

Utility functions for the package.

### zenml.utils.package_utils.clean_requirements(requirements: List[str]) → List[str]

Clean requirements list from redundant requirements.

Args:
: requirements: List of requirements.

Returns:
: Cleaned list of requirements

Raises:
: TypeError: If input is not a list
  ValueError: If any element in the list is not a string

### zenml.utils.package_utils.is_latest_zenml_version() → bool

Checks if the currently running ZenML package is on the latest version.

Returns:
: True in case the current running zenml code is the latest available version on PYPI, otherwise False.

Raises:
: RuntimeError: In case something goe wrong

## zenml.utils.pagination_utils module

Pagination utilities.

### zenml.utils.pagination_utils.depaginate(list_method: Callable[[...], [Page](zenml.models.v2.base.md#id327)[AnyResponse]], \*\*kwargs: Any) → List[AnyResponse]

Depaginate the results from a client or store method that returns pages.

Args:
: list_method: The list method to depaginate.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Arguments for the list method.

Returns:
: A list of the corresponding Response Models.

## zenml.utils.pipeline_docker_image_builder module

Implementation of Docker image builds to run ZenML pipelines.

### *class* zenml.utils.pipeline_docker_image_builder.PipelineDockerImageBuilder

Bases: `object`

Builds Docker images to run a ZenML pipeline.

#### build_docker_image(docker_settings: [DockerSettings](zenml.config.md#zenml.config.docker_settings.DockerSettings), tag: str, stack: [Stack](zenml.stack.md#zenml.stack.stack.Stack), include_files: bool, download_files: bool, entrypoint: str | None = None, extra_files: Dict[str, str] | None = None, code_repository: [BaseCodeRepository](zenml.code_repositories.md#zenml.code_repositories.base_code_repository.BaseCodeRepository) | None = None) → Tuple[str, str | None, str | None]

Builds (and optionally pushes) a Docker image to run a pipeline.

Use the image name returned by this method whenever you need to uniquely
reference the pushed image in order to pull or run it.

Args:
: docker_settings: The settings for the image build.
  tag: The tag to use for the image.
  stack: The stack on which the pipeline will be deployed.
  include_files: Whether to include files in the build context.
  download_files: Whether to download files in the build context.
  entrypoint: Entrypoint to use for the final image. If left empty,
  <br/>
  > no entrypoint will be included in the image.
  <br/>
  extra_files: Extra files to add to the build context. Keys are the
  : path inside the build context, values are either the file
    content or a file path.
  <br/>
  code_repository: The code repository from which files will be
  : downloaded.

Returns:
: A tuple (image_digest, dockerfile, requirements):
  - The Docker image repo digest or local name, depending on whether
  the image was pushed or is just stored locally.
  - Dockerfile will contain the contents of the Dockerfile used to
  build the image.
  - Requirements is a string with a single pip requirement per line.

Raises:
: RuntimeError: If the stack does not contain an image builder.
  ValueError: If no Dockerfile and/or custom parent image is
  <br/>
  > specified and the Docker configuration doesn’t require an
  > image build.
  <br/>
  ValueError: If the specified Dockerfile does not exist.

#### *static* gather_requirements_files(docker_settings: [DockerSettings](zenml.config.md#zenml.config.docker_settings.DockerSettings), stack: [Stack](zenml.stack.md#zenml.stack.stack.Stack), code_repository: [BaseCodeRepository](zenml.code_repositories.md#zenml.code_repositories.base_code_repository.BaseCodeRepository) | None = None, log: bool = True) → List[Tuple[str, str, List[str]]]

Gathers and/or generates pip requirements files.

This method is called in PipelineDockerImageBuilder.build_docker_image
but it is also called by other parts of the codebase, e.g. the
AzureMLStepOperator, which needs to upload the requirements files to
AzureML where the step image is then built.

Args:
: docker_settings: Docker settings that specifies which
  : requirements to install.
  <br/>
  stack: The stack on which the pipeline will run.
  code_repository: The code repository from which files will be
  <br/>
  > downloaded.
  <br/>
  log: If True, will log the requirements.

Raises:
: RuntimeError: If the command to export the local python packages
  : failed.
  <br/>
  FileNotFoundError: If the specified requirements file does not
  : exist.

Returns:
: List of tuples (filename, file_content, pip_options) of all
  requirements files.
  The files will be in the following order:
  - Packages installed in the local Python environment
  - Requirements defined by stack integrations
  - Requirements defined by user integrations
  - User-defined requirements

## zenml.utils.proxy_utils module

Proxy design pattern utils.

### zenml.utils.proxy_utils.make_proxy_class(interface: Type[ABC], attribute: str) → Callable[[C], C]

Proxy class decorator.

Use this decorator to transform the decorated class into a proxy that
forwards all calls defined in the interface interface to the attribute
class attribute that implements the same interface.

This class is useful in cases where you need to have a base class that acts
as a proxy or facade for one or more other classes. Both the decorated class
and the class attribute must inherit from the same ABC interface for this to
work. Only regular methods are supported, not class methods or attributes.

Example: Let’s say you have an interface called BodyBuilder, a base class
called FatBob and another class called BigJim. BigJim implements the
BodyBuilder interface, but FatBob does not. And let’s say you want
FatBob to look as if it implements the BodyBuilder interface, but in
fact it just forwards all calls to BigJim. You could do this:

```
``
```

```
`
```

python
from abc import ABC, abstractmethod

class BodyBuilder(ABC):

> @abstractmethod
> def build_body(self):

> > pass

class BigJim(BodyBuilder):

> def build_body(self):
> : print(“Looks fit!”)

class FatBob(BodyBuilder)

> def \_\_init_\_(self):
> : self.big_jim = BigJim()

> def build_body(self):
> : self.big_jim.build_body()

fat_bob = FatBob()
fat_bob.build_body()

```
``
```

```
`
```

But this leads to a lot of boilerplate code with bigger interfaces and
makes everything harder to maintain. This is where the proxy class
decorator comes in handy. Here’s how to use it:

```
``
```

```
`
```

python
from zenml.utils.proxy_utils import make_proxy_class
from typing import Optional

@make_proxy_class(BodyBuilder, “big_jim”)
class FatBob(BodyBuilder)

> big_jim: Optional[BodyBuilder] = None

> def \_\_init_\_(self):
> : self.big_jim = BigJim()

fat_bob = FatBob()
fat_bob.build_body()

```
``
```

```
`
```

This is the same as implementing FatBob to call BigJim explicitly, but it
has the advantage that you don’t need to write a lot of boilerplate code
of modify the FatBob class every time you change something in the
BodyBuilder interface.

This proxy decorator also allows to extend classes dynamically at runtime:
if the attribute class attribute is set to None, the proxy class
will assume that the interface is not implemented by the class and will
raise a NotImplementedError:

```
``
```

```
`
```

python
@make_proxy_class(BodyBuilder, “big_jim”)
class FatBob(BodyBuilder)

> big_jim: Optional[BodyBuilder] = None

> def \_\_init_\_(self):
> : self.big_jim = None

fat_bob = FatBob()

# Raises NotImplementedError, class not extended yet:
fat_bob.build_body()

fat_bob.big_jim = BigJim()
# Now it works:
fat_bob.build_body()

```
``
```

```
`
```

Args:
: interface: The interface to implement.
  attribute: The attribute of the base class to forward calls to.

Returns:
: The proxy class.

## zenml.utils.pydantic_utils module

Utilities for pydantic models.

### *class* zenml.utils.pydantic_utils.TemplateGenerator(instance_or_class: BaseModel | Type[BaseModel])

Bases: `object`

Class to generate templates for pydantic models or classes.

#### run() → Dict[str, Any]

Generates the template.

Returns:
: The template dictionary.

### *class* zenml.utils.pydantic_utils.YAMLSerializationMixin

Bases: `BaseModel`

Class to serialize/deserialize pydantic models to/from YAML.

#### *classmethod* from_yaml(path: str) → M

Creates an instance from a YAML file.

Args:
: path: Path to a YAML file.

Returns:
: The model instance.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### yaml(sort_keys: bool = False, \*\*kwargs: Any) → str

YAML string representation..

Args:
: sort_keys: Whether to sort the keys in the YAML representation.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Kwargs to pass to the pydantic model_dump(…) method.

Returns:
: YAML string representation.

### zenml.utils.pydantic_utils.before_validator_handler(method: Callable[[...], Any]) → Callable[[Any, Any, Any], Any]

Decorator to handle the raw input data for pydantic model validators.

Args:
: method: the class method with the actual validation logic.

Returns:
: the validator method

### zenml.utils.pydantic_utils.has_validators(pydantic_class: Type[BaseModel], field_name: str | None = None) → bool

Function to check if a Pydantic model or a pydantic field has validators.

Args:
: pydantic_class: The class defining the pydantic model.
  field_name: Optional, field info. If specified, this function will focus
  <br/>
  > on a singular field within the class. If not specified, it will
  > check model validators.

Returns:
: Whether the specified field or class has a validator or not.

### zenml.utils.pydantic_utils.model_validator_data_handler(raw_data: Any, base_class: Type[BaseModel], validation_info: ValidationInfo) → Dict[str, Any]

Utility function to parse raw input data of varying types to a dict.

With the change to pydantic v2, validators which operate with “before”
(or previously known as the “pre” parameter) are getting “Any” types of raw
input instead of a “Dict[str, Any]” as before. Depending on the use-case,
this can create conflicts after the migration and this function will be
used as a helper function to handle different types of raw input data.

A code snippet to showcase how the behavior changes. The “before” validator
prints the type of the input:

> class Base(BaseModel):
> : a: int = 3

> class MyClass(Base):
> : @model_validator(mode=”before”)
>   @classmethod
>   def before_validator(cls, data: Any) -> Any:
>   <br/>
>   > print(type(data))
>   > return {}

> one = MyClass() # prints “<class ‘dict’>”
> MyClass.model_validate(one)  # prints NOTHING, it is already validated
> MyClass.model_validate(“asdf”)  # prints “<class ‘str’>”, fails without the modified return.
> MyClass.model_validate(RandomClass())  # prints “<class ‘RandomClass’>”, fails without the modified return.
> MyClass.model_validate(Base())  # prints “<class ‘Base’>”, fails without the modified return.
> MyClass.model_validate_json(json.dumps(“aria”))  # prints “<class ‘str’>”, fails without the modified return.
> MyClass.model_validate_json(json.dumps([1]))  # prints “<class ‘list’>”, fails without the modified return.
> MyClass.model_validate_json(one.model_dump_json())  # prints “<class ‘dict’>”

Args:
: raw_data: The raw data passed to the validator, can be “Any” type.
  base_class: The class that the validator belongs to
  validation_info: Extra information about the validation process.

Raises:
: TypeError: if the type of the data is not processable.
  ValueError: in case of an unknown validation mode.

Returns:
: A dictionary which will be passed to the eventual validator of pydantic.

### zenml.utils.pydantic_utils.update_model(original: M, update: BaseModel | Dict[str, Any], recursive: bool = True, exclude_none: bool = False) → M

Updates a pydantic model.

Args:
: original: The model to update.
  update: The update values.
  recursive: If True, dictionary values will be updated recursively.
  exclude_none: If True, None values in the update will be removed.

Returns:
: The updated model.

### zenml.utils.pydantic_utils.validate_function_args(\_\_func: Callable[[...], Any], \_\_config: ConfigDict | None, \*args: Any, \*\*kwargs: Any) → Dict[str, Any]

Validates arguments passed to a function.

This function validates that all arguments to call the function exist and
that the types match.

It raises a pydantic.ValidationError if the validation fails.

Args:
: \_\_func: The function for which the arguments are passed.
  \_\_config: The pydantic config for the underlying model that is created
  <br/>
  > to validate the types of the arguments.
  <br/>
  ```
  *
  ```
  <br/>
  args: Function arguments.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Function keyword arguments.

Returns:
: The validated arguments.

## zenml.utils.secret_utils module

Utility functions for secrets and secret references.

### zenml.utils.secret_utils.ClearTextField(\*args: Any, \*\*kwargs: Any) → Any

Marks a pydantic field to prevent secret references.

Args:
: ```
  *
  ```
  <br/>
  args: Positional arguments which will be forwarded
  : to pydantic.Field(…).
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments which will be forwarded to
  : pydantic.Field(…).

Returns:
: Pydantic field info.

### zenml.utils.secret_utils.SecretField(\*args: Any, \*\*kwargs: Any) → Any

Marks a pydantic field as something containing sensitive information.

Args:
: ```
  *
  ```
  <br/>
  args: Positional arguments which will be forwarded
  : to pydantic.Field(…).
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Keyword arguments which will be forwarded to
  : pydantic.Field(…).

Returns:
: Pydantic field info.

### *class* zenml.utils.secret_utils.SecretReference(name: str, key: str)

Bases: `NamedTuple`

Class representing a secret reference.

Attributes:
: name: The secret name.
  key: The secret key.

#### key *: str*

Alias for field number 1

#### name *: str*

Alias for field number 0

### zenml.utils.secret_utils.is_clear_text_field(field: FieldInfo) → bool

Returns whether a pydantic field prevents secret references or not.

Args:
: field: The field to check.

Returns:
: True if the field prevents secret references, False otherwise.

### zenml.utils.secret_utils.is_secret_field(field: FieldInfo) → bool

Returns whether a pydantic field contains sensitive information or not.

Args:
: field: The field to check.

Returns:
: True if the field contains sensitive information, False otherwise.

### zenml.utils.secret_utils.is_secret_reference(value: Any) → bool

Checks whether any value is a secret reference.

Args:
: value: The value to check.

Returns:
: True if the value is a secret reference, False otherwise.

### zenml.utils.secret_utils.parse_secret_reference(reference: str) → [SecretReference](#zenml.utils.secret_utils.SecretReference)

Parses a secret reference.

This function assumes the input string is a valid secret reference and
**does not** perform any additional checks. If you pass an invalid secret
reference here, this will most likely crash.

Args:
: reference: The string representing a **valid** secret reference.

Returns:
: The parsed secret reference.

## zenml.utils.settings_utils module

Utility functions for ZenML settings.

### zenml.utils.settings_utils.get_flavor_setting_key(flavor: [Flavor](zenml.stack.md#zenml.stack.flavor.Flavor)) → str

Gets the setting key for a flavor.

Args:
: flavor: The flavor for which to get the key.

Returns:
: The setting key for the flavor.

### zenml.utils.settings_utils.get_general_settings() → Dict[str, Type[[BaseSettings](zenml.config.md#zenml.config.base_settings.BaseSettings)]]

Returns all general settings.

Returns:
: Dictionary mapping general settings keys to their type.

### zenml.utils.settings_utils.get_stack_component_for_settings_key(key: str, stack: [Stack](zenml.stack.md#zenml.stack.stack.Stack)) → [StackComponent](zenml.stack.md#zenml.stack.stack_component.StackComponent)

Gets the stack component of a stack for a given settings key.

Args:
: key: The settings key for which to get the component.
  stack: The stack from which to get the component.

Raises:
: ValueError: If the key is invalid or the stack does not contain a
  : component of the correct flavor.

Returns:
: The stack component.

### zenml.utils.settings_utils.get_stack_component_setting_key(stack_component: [StackComponent](zenml.stack.md#zenml.stack.stack_component.StackComponent)) → str

Gets the setting key for a stack component.

Args:
: stack_component: The stack component for which to get the key.

Returns:
: The setting key for the stack component.

### zenml.utils.settings_utils.is_general_setting_key(key: str) → bool

Checks whether the key refers to a general setting.

Args:
: key: The key to check.

Returns:
: If the key refers to a general setting.

### zenml.utils.settings_utils.is_stack_component_setting_key(key: str) → bool

Checks whether a settings key refers to a stack component.

Args:
: key: The key to check.

Returns:
: If the key refers to a stack component.

### zenml.utils.settings_utils.is_valid_setting_key(key: str) → bool

Checks whether a settings key is valid.

Args:
: key: The key to check.

Returns:
: If the key is valid.

### zenml.utils.settings_utils.validate_setting_keys(setting_keys: Sequence[str]) → None

Validates settings keys.

Args:
: setting_keys: The keys to validate.

Raises:
: ValueError: If any key is invalid.

## zenml.utils.singleton module

Utility class to turn classes into singleton classes.

### *class* zenml.utils.singleton.SingletonMetaClass(\*args: Any, \*\*kwargs: Any)

Bases: `type`

Singleton metaclass.

Use this metaclass to make any class into a singleton class:

```
``
```

```
`
```

python
class OneRing(metaclass=SingletonMetaClass):

> def \_\_init_\_(self, owner):
> : self._owner = owner

> @property
> def owner(self):

> > return self._owner

the_one_ring = OneRing(‘Sauron’)
the_lost_ring = OneRing(‘Frodo’)
print(the_lost_ring.owner)  # Sauron
OneRing._clear() # ring destroyed

```
``
```

```
`
```

## zenml.utils.source_code_utils module

Utilities for getting the source code of objects.

### zenml.utils.source_code_utils.get_hashed_source_code(value: Any) → str

Returns a hash of the objects source code.

Args:
: value: object to get source from.

Returns:
: Hash of source code.

Raises:
: TypeError: If unable to compute the hash.

### zenml.utils.source_code_utils.get_source_code(value: Any) → str

Returns the source code of an object.

If executing within a IPython kernel environment, then this monkey-patches
inspect module temporarily with a workaround to get source from the cell.

Args:
: value: object to get source from.

Returns:
: Source code of object.

## zenml.utils.source_utils module

Utilities for loading/resolving objects.

### zenml.utils.source_utils.get_resolved_notebook_sources() → Dict[str, str]

Get all notebook sources that were resolved in this process.

Returns:
: Dictionary mapping the import path of notebook sources to the code
  of their notebook cell.

### zenml.utils.source_utils.get_source_root() → str

Get the source root.

The source root will be determined in the following order:
- The manually specified custom source root if it was set.
- The ZenML repository directory if one exists in the current working

> directory or any parent directories.
- The parent directory of the main module file.

Returns:
: The source root.

Raises:
: RuntimeError: If the main module file can’t be found.

### zenml.utils.source_utils.get_source_type(module: ModuleType) → [SourceType](zenml.config.md#zenml.config.source.SourceType)

Get the type of a source.

Args:
: module: The module for which to get the source type.

Returns:
: The source type.

### zenml.utils.source_utils.is_distribution_package_file(file_path: str, module_name: str) → bool

Checks if a file/module belongs to a distribution package.

Args:
: file_path: The file path to check.
  module_name: The module name.

Returns:
: True if the file/module belongs to a distribution package, False
  otherwise.

### zenml.utils.source_utils.is_internal_module(module_name: str) → bool

Checks if a module is internal (=part of the zenml package).

Args:
: module_name: Name of the module to check.

Returns:
: True if the module is internal, False otherwise.

### zenml.utils.source_utils.is_standard_lib_file(file_path: str) → bool

Checks if a file belongs to the Python standard library.

Args:
: file_path: The file path to check.

Returns:
: True if the file belongs to the Python standard library, False
  otherwise.

### zenml.utils.source_utils.is_user_file(file_path: str) → bool

Checks if a file is a user file.

Args:
: file_path: The file path to check.

Returns:
: True if the file is a user file, False otherwise.

### zenml.utils.source_utils.load(source: [Source](zenml.config.md#zenml.config.source.Source) | str) → Any

Load a source or import path.

Args:
: source: The source to load.

Returns:
: The loaded object.

### zenml.utils.source_utils.load_and_validate_class(source: str | [Source](zenml.config.md#zenml.config.source.Source), expected_class: Type[Any]) → Type[Any]

Loads a source class and validates its class.

Args:
: source: The source.
  expected_class: The class that the source should resolve to.

Raises:
: TypeError: If the source does not resolve to the expected class.

Returns:
: The resolved source class.

### zenml.utils.source_utils.prepend_python_path(path: str) → Iterator[None]

Context manager to temporarily prepend a path to the python path.

Args:
: path: Path that will be prepended to sys.path for the duration of
  : the context manager.

Yields:
: None

### zenml.utils.source_utils.resolve(obj: Type[Any] | Callable[[...], Any] | ModuleType | LambdaType | BuiltinMethodType | None, skip_validation: bool = False) → [Source](zenml.config.md#zenml.config.source.Source)

Resolve an object.

Args:
: obj: The object to resolve.
  skip_validation: If True, the validation that the object exist in the
  <br/>
  > module is skipped.

Raises:
: RuntimeError: If the object can’t be resolved.

Returns:
: The source of the resolved object.

### zenml.utils.source_utils.set_custom_source_root(source_root: str | None) → None

Sets a custom source root.

If set this has the highest priority and will always be used as the source
root.

Args:
: source_root: The source root to use.

### zenml.utils.source_utils.validate_source_class(source: [Source](zenml.config.md#zenml.config.source.Source) | str, expected_class: Type[Any]) → bool

Validates that a source resolves to a certain class.

Args:
: source: The source to validate.
  expected_class: The class that the source should resolve to.

Returns:
: True if the source resolves to the expected class, False otherwise.

## zenml.utils.string_utils module

Utils for strings.

### zenml.utils.string_utils.b64_decode(input_: str) → str

Returns a decoded string of the base 64 encoded input string.

Args:
: ```
  input_
  ```
  <br/>
  : Base64 encoded string.

Returns:
: Decoded string.

### zenml.utils.string_utils.b64_encode(input_: str) → str

Returns a base 64 encoded string of the input string.

Args:
: ```
  input_
  ```
  <br/>
  : The input to encode.

Returns:
: Base64 encoded string.

### zenml.utils.string_utils.format_name_template(name_template: str, \*\*kwargs: str) → str

Formats a name template with the given arguments.

By default, ZenML support Date and Time placeholders.
E.g. my_run_{date}_{time} will be formatted as my_run_1970_01_01_00_00_00.
Extra placeholders need to be explicitly passed in as kwargs.

Args:
: name_template: The name template to format.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: The arguments to replace in the template.

Returns:
: The formatted name template.

### zenml.utils.string_utils.get_human_readable_filesize(bytes_: int) → str

Convert a file size in bytes into a human-readable string.

Args:
: ```
  bytes_
  ```
  <br/>
  : The number of bytes to convert.

Returns:
: A human-readable string.

### zenml.utils.string_utils.get_human_readable_time(seconds: float) → str

Convert seconds into a human-readable string.

Args:
: seconds: The number of seconds to convert.

Returns:
: A human-readable string.

### zenml.utils.string_utils.random_str(length: int) → str

Generate a random human readable string of given length.

Args:
: length: Length of string

Returns:
: Random human-readable string.

### zenml.utils.string_utils.validate_name(model: BaseModel) → None

Validator to ensure that the given name has only allowed characters.

Args:
: model: The model to validate.

Raises:
: ValueError: If the name has invalid characters.

## zenml.utils.terraform_utils module

Terraform utilities.

### zenml.utils.terraform_utils.verify_terraform_installation() → None

Verifies the Terraform installation.

Raises:
: RuntimeError: If Terraform is not installed or ZenML was installed
  : without the terraform extra.

## zenml.utils.typed_model module

Utility classes for adding type information to Pydantic models.

### *class* zenml.utils.typed_model.BaseTypedModel(\*, type: Literal['zenml.utils.typed_model.BaseTypedModel'] = 'zenml.utils.typed_model.BaseTypedModel')

Bases: `BaseModel`

Typed Pydantic model base class.

Use this class as a base class instead of BaseModel to automatically
add a type literal attribute to the model that stores the name of the
class.

This can be useful when serializing models to JSON and then de-serializing
them as part of a submodel union field, e.g.:

```
``
```

```
`
```

python

class BluePill(BaseTypedModel):
: …

class RedPill(BaseTypedModel):
: …

class TheMatrix(BaseTypedModel):
: choice: Union[BluePill, RedPill] = Field(…, discriminator=’type’)

matrix = TheMatrix(choice=RedPill())
d = matrix.dict()
new_matrix = TheMatrix.model_validate(d)
assert isinstance(new_matrix.choice, RedPill)

```
``
```

```
`
```

It can also facilitate de-serializing objects when their type isn’t known:

``python
matrix = TheMatrix(choice=RedPill())
d = matrix.dict()
new_matrix = BaseTypedModel.from_dict(d)
assert isinstance(new_matrix.choice, RedPill)
``

#### *classmethod* from_dict(model_dict: Dict[str, Any]) → [BaseTypedModel](#zenml.utils.typed_model.BaseTypedModel)

Instantiate a Pydantic model from a serialized JSON-able dict representation.

Args:
: model_dict: the model attributes serialized as JSON-able dict.

Returns:
: A BaseTypedModel created from the serialized representation.

Raises:
: RuntimeError: if the model_dict contains an invalid type.

#### *classmethod* from_json(json_str: str) → [BaseTypedModel](#zenml.utils.typed_model.BaseTypedModel)

Instantiate a Pydantic model from a serialized JSON representation.

Args:
: json_str: the model attributes serialized as JSON.

Returns:
: A BaseTypedModel created from the serialized representation.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'type': FieldInfo(annotation=Literal['zenml.utils.typed_model.BaseTypedModel'], required=False, default='zenml.utils.typed_model.BaseTypedModel')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### type *: Literal['zenml.utils.typed_model.BaseTypedModel']*

### *class* zenml.utils.typed_model.BaseTypedModelMeta(name: str, bases: Tuple[Type[Any], ...], dct: Dict[str, Any])

Bases: `ModelMetaclass`

Metaclass responsible for adding type information to Pydantic models.

## zenml.utils.typing_utils module

Carried over version of some functions from the pydantic v1 typing module.

Check out the latest version here:
[https://github.com/pydantic/pydantic/blob/v1.10.14/pydantic/typing.py](https://github.com/pydantic/pydantic/blob/v1.10.14/pydantic/typing.py)

### zenml.utils.typing_utils.all_literal_values(type_: Type[Any]) → Tuple[Any, ...]

Fetches the literal values defined in a type in a recursive manner.

This method is used to retrieve all Literal values as Literal can be
used recursively (see [https://www.python.org/dev/peps/pep-0586](https://www.python.org/dev/peps/pep-0586))
e.g. Literal[Literal[Literal[1, 2, 3], “foo”], 5, None]

Args:
: ```
  type_
  ```
  <br/>
  : type to check.

Returns:
: tuple of all the literal values defined in the type.

### zenml.utils.typing_utils.get_args(tp: Type[Any]) → Tuple[Any, ...]

Get type arguments with all substitutions performed.

For unions, basic simplifications used by Union constructor are performed.
Examples:

```default
get_args(Dict[str, int]) == (str, int)
get_args(int) == ()
get_args(Union[int, Union[T, int], str][int]) == (int, str)
get_args(Union[int, Tuple[T, int]][str]) == (int, Tuple[str, int])
get_args(Callable[[], T][int]) == ([], int)
```

Args:
: tp: the type to check.

Returns:
: Tuple of all the args.

### zenml.utils.typing_utils.get_origin(tp: Type[Any]) → Type[Any] | None

Fetches the origin of a given type.

We can’t directly use typing.get_origin since we need a fallback to
support custom generic classes like ConstrainedList
It should be useless once [https://github.com/cython/cython/issues/3537](https://github.com/cython/cython/issues/3537) is
solved and [https://github.com/pydantic/pydantic/pull/1753](https://github.com/pydantic/pydantic/pull/1753) is merged.

Args:
: tp: type to check

Returns:
: the origin type of the provided type.

### zenml.utils.typing_utils.is_literal_type(type_: Type[Any]) → bool

Checks if the provided type is a literal type.

Args:
: ```
  type_
  ```
  <br/>
  : type to check.

Returns:
: boolean indicating whether the type is union type.

### zenml.utils.typing_utils.is_none_type(type_: Any) → bool

Checks if the provided type is a none type.

Args:
: ```
  type_
  ```
  <br/>
  : type to check.

Returns:
: boolean indicating whether the type is a none type.

### zenml.utils.typing_utils.is_optional(tp: Type[Any]) → bool

Checks whether a given annotation is typing.Optional.

Args:
: tp: the type to check.

Returns:
: boolean indicating if the type is typing.Optional.

### zenml.utils.typing_utils.is_union(type_: Type[Any] | None) → bool

Checks if the provided type is a union type.

Args:
: ```
  type_
  ```
  <br/>
  : type to check.

Returns:
: boolean indicating whether the type is union type.

### zenml.utils.typing_utils.literal_values(type_: Type[Any]) → Tuple[Any, ...]

Fetches the literal values defined in a type.

Args:
: ```
  type_
  ```
  <br/>
  : type to check.

Returns:
: tuple of the literal values.

## zenml.utils.uuid_utils module

Utility functions for handling UUIDs.

### zenml.utils.uuid_utils.generate_uuid_from_string(value: str) → UUID

Deterministically generates a UUID from a string seed.

Args:
: value: The string from which to generate the UUID.

Returns:
: The generated UUID.

### zenml.utils.uuid_utils.is_valid_uuid(value: Any, version: int = 4) → bool

Checks if a string is a valid UUID.

Args:
: value: String to check.
  version: Version of UUID to check for.

Returns:
: True if string is a valid UUID, False otherwise.

### zenml.utils.uuid_utils.parse_name_or_uuid(name_or_id: str | None) → UUID | str | None

Convert a “name or id” string value to a string or UUID.

Args:
: name_or_id: Name or id to convert.

Returns:
: A UUID if name_or_id is a UUID, string otherwise.

## zenml.utils.visualization_utils module

Utility functions for dashboard visualizations.

### zenml.utils.visualization_utils.format_csv_visualization_as_html(csv_visualization: str, max_rows: int = 10, max_cols: int = 10) → str

Formats a CSV visualization as an HTML table.

Args:
: csv_visualization: CSV visualization as a string.
  max_rows: Maximum number of rows to display. Remaining rows will be
  <br/>
  > replaced by an ellipsis in the middle of the table.
  <br/>
  max_cols: Maximum number of columns to display. Remaining columns will
  : be replaced by an ellipsis at the end of each row.

Returns:
: HTML table as a string.

### zenml.utils.visualization_utils.visualize_artifact(artifact: [ArtifactVersionResponse](zenml.models.md#zenml.models.ArtifactVersionResponse), title: str | None = None) → None

Visualize an artifact in notebook environments.

Args:
: artifact: The artifact to visualize.
  title: Optional title to show before the visualizations.

Raises:
: RuntimeError: If not in a notebook environment.

## zenml.utils.yaml_utils module

Utility functions to help with YAML files and data.

### *class* zenml.utils.yaml_utils.UUIDEncoder(\*, skipkeys=False, ensure_ascii=True, check_circular=True, allow_nan=True, sort_keys=False, indent=None, separators=None, default=None)

Bases: `JSONEncoder`

JSON encoder for UUID objects.

#### default(obj: Any) → Any

Default UUID encoder for JSON.

Args:
: obj: Object to encode.

Returns:
: Encoded object.

### zenml.utils.yaml_utils.append_yaml(file_path: str, contents: Dict[Any, Any]) → None

Append contents to a YAML file at file_path.

Args:
: file_path: Path to YAML file.
  contents: Contents of YAML file as dict.

Raises:
: FileNotFoundError: if directory does not exist.

### zenml.utils.yaml_utils.comment_out_yaml(yaml_string: str) → str

Comments out a yaml string.

Args:
: yaml_string: The yaml string to comment out.

Returns:
: The commented out yaml string.

### zenml.utils.yaml_utils.is_json_serializable(obj: Any) → bool

Checks whether an object is JSON serializable.

Args:
: obj: The object to check.

Returns:
: Whether the object is JSON serializable using pydantics encoder class.

### zenml.utils.yaml_utils.is_yaml(file_path: str) → bool

Returns True if file_path is YAML, else False.

Args:
: file_path: Path to YAML file.

Returns:
: True if is yaml, else False.

### zenml.utils.yaml_utils.read_json(file_path: str) → Any

Read JSON on file path and returns contents as dict.

Args:
: file_path: Path to JSON file.

Returns:
: Contents of the file in a dict.

Raises:
: FileNotFoundError: if file does not exist.

### zenml.utils.yaml_utils.read_yaml(file_path: str) → Any

Read YAML on file path and returns contents as dict.

Args:
: file_path: Path to YAML file.

Returns:
: Contents of the file in a dict.

Raises:
: FileNotFoundError: if file does not exist.

### zenml.utils.yaml_utils.write_json(file_path: str, contents: Any, encoder: Type[JSONEncoder] | None = None) → None

Write contents as JSON format to file_path.

Args:
: file_path: Path to JSON file.
  contents: Contents of JSON file.
  encoder: Custom JSON encoder to use when saving json.

Raises:
: FileNotFoundError: if directory does not exist.

### zenml.utils.yaml_utils.write_yaml(file_path: str, contents: Dict[Any, Any] | List[Any], sort_keys: bool = True) → None

Write contents as YAML format to file_path.

Args:
: file_path: Path to YAML file.
  contents: Contents of YAML file as dict or list.
  sort_keys: If True, keys are sorted alphabetically. If False,
  <br/>
  > the order in which the keys were inserted into the dict will
  > be preserved.

Raises:
: FileNotFoundError: if directory does not exist.

## Module contents

Initialization of the utils module.

The utils module contains utility functions handling analytics, reading and
writing YAML data as well as other general purpose functions.
