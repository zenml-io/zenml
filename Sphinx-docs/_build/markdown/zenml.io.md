# zenml.io package

## Submodules

## zenml.io.fileio module

Functionality for reading, writing and managing files.

### zenml.io.fileio.copy(src: bytes | str, dst: bytes | str, overwrite: bool = False) → None

Copy a file from the source to the destination.

Args:
: src: The path of the file to copy.
  dst: The path to copy the source file to.
  overwrite: Whether to overwrite the destination file if it exists.

Raises:
: FileExistsError: If a file already exists at the destination and
  : overwrite is not set to True.

### zenml.io.fileio.exists(path: bytes | str) → bool

Check whether a given path exists.

Args:
: path: The path to check.

Returns:
: True if the given path exists, False otherwise.

### zenml.io.fileio.glob(pattern: bytes | str) → List[bytes | str]

Find all files matching the given pattern.

Args:
: pattern: The pattern to match.

Returns:
: A list of paths matching the pattern.

### zenml.io.fileio.isdir(path: bytes | str) → bool

Check whether the given path is a directory.

Args:
: path: The path to check.

Returns:
: True if the given path is a directory, False otherwise.

### zenml.io.fileio.listdir(path: str, only_file_names: bool = True) → List[str]

Lists all files in a directory.

Args:
: path: The path to the directory.
  only_file_names: If True, only return the file names, not the full path.

Returns:
: A list of files in the directory.

### zenml.io.fileio.makedirs(path: bytes | str) → None

Make a directory at the given path, recursively creating parents.

Args:
: path: The path to the directory.

### zenml.io.fileio.mkdir(path: bytes | str) → None

Make a directory at the given path; parent directory must exist.

Args:
: path: The path to the directory.

### zenml.io.fileio.open(path: bytes | str, mode: str = 'r') → Any

Opens a file.

Args:
: path: The path to the file.
  mode: The mode to open the file in.

Returns:
: The opened file.

### zenml.io.fileio.remove(path: bytes | str) → None

Remove the file at the given path. Dangerous operation.

Args:
: path: The path to the file to remove.

Raises:
: FileNotFoundError: If the file does not exist.

### zenml.io.fileio.rename(src: bytes | str, dst: bytes | str, overwrite: bool = False) → None

Rename a file.

Args:
: src: The path of the file to rename.
  dst: The path to rename the source file to.
  overwrite: If a file already exists at the destination, this
  <br/>
  > method will overwrite it if overwrite=\`True\` and
  > raise a FileExistsError otherwise.

Raises:
: NotImplementedError: If the source and destination file systems are not
  : the same.

### zenml.io.fileio.rmtree(dir_path: str) → None

Deletes a directory recursively. Dangerous operation.

Args:
: dir_path: The path to the directory to delete.

Raises:
: TypeError: If the path is not pointing to a directory.

### zenml.io.fileio.size(path: bytes | str) → int | None

Get the size of a file or directory in bytes.

Args:
: path: The path to the file.

Returns:
: The size of the file or directory in bytes or None if the responsible
  file system does not implement the size method.

### zenml.io.fileio.stat(path: bytes | str) → Any

Get the stat descriptor for a given file path.

Args:
: path: The path to the file.

Returns:
: The stat descriptor.

### zenml.io.fileio.walk(top: bytes | str, topdown: bool = True, onerror: Callable[[...], None] | None = None) → Iterable[Tuple[bytes | str, List[bytes | str], List[bytes | str]]]

Return an iterator that walks the contents of the given directory.

Args:
: top: The path of directory to walk.
  topdown: Whether to walk directories topdown or bottom-up.
  onerror: Callable that gets called if an error occurs.

Returns:
: An Iterable of Tuples, each of which contain the path of the current
  directory path, a list of directories inside the current directory
  and a list of files inside the current directory.

## zenml.io.filesystem module

Defines the filesystem abstraction of ZenML.

### *class* zenml.io.filesystem.BaseFilesystem

Bases: `ABC`

Abstract Filesystem base class.

Design inspired by the Filesystem abstraction in TFX:
[https://github.com/tensorflow/tfx/blob/master/tfx/dsl/io/filesystem.py](https://github.com/tensorflow/tfx/blob/master/tfx/dsl/io/filesystem.py)

#### SUPPORTED_SCHEMES *: ClassVar[Set[str]]*

#### *abstract static* copyfile(src: bytes | str, dst: bytes | str, overwrite: bool = False) → None

Copy a file from the source to the destination.

Args:
: src: The path of the file to copy.
  dst: The path to copy the source file to.
  overwrite: Whether to overwrite the destination file if it exists.

Raises:
: FileExistsError: If a file already exists at the destination and
  : overwrite is not set to True.

#### *abstract static* exists(path: bytes | str) → bool

Check whether a given path exists.

Args:
: path: The path to check.

Returns:
: True if the given path exists, False otherwise.

#### *abstract static* glob(pattern: bytes | str) → List[bytes | str]

Find all files matching the given pattern.

Args:
: pattern: The pattern to match.

Returns:
: A list of paths matching the pattern.

#### *abstract static* isdir(path: bytes | str) → bool

Check whether the given path is a directory.

Args:
: path: The path to check.

Returns:
: True if the given path is a directory, False otherwise.

#### *abstract static* listdir(path: bytes | str) → List[bytes | str]

Lists all files in a directory.

Args:
: path: The path to the directory.

Returns:
: A list of files in the directory.

#### *abstract static* makedirs(path: bytes | str) → None

Make a directory at the given path, recursively creating parents.

Args:
: path: Path to the directory.

#### *abstract static* mkdir(path: bytes | str) → None

Make a directory at the given path; parent directory must exist.

Args:
: path: Path to the directory.

#### *abstract static* open(name: bytes | str, mode: str = 'r') → Any

Opens a file.

Args:
: name: The path to the file.
  mode: The mode to open the file in.

Returns:
: The opened file.

#### *abstract static* remove(path: bytes | str) → None

Remove the file at the given path. Dangerous operation.

Args:
: path: The path to the file to remove.

Raises:
: FileNotFoundError: If the file does not exist.

#### *abstract static* rename(src: bytes | str, dst: bytes | str, overwrite: bool = False) → None

Rename a file.

Args:
: src: The path of the file to rename.
  dst: The path to rename the source file to.
  overwrite: If a file already exists at the destination, this
  <br/>
  > method will overwrite it if overwrite=\`True\` and
  > raise a FileExistsError otherwise.

Raises:
: FileExistsError: If a file already exists at the destination
  : and overwrite is not set to True.

#### *abstract static* rmtree(path: bytes | str) → None

Deletes a directory recursively. Dangerous operation.

Args:
: path: The path to the directory to delete.

#### *static* size(path: bytes | str) → int

Get the size of a file in bytes.

To be implemented by subclasses but not abstract for backwards
compatibility.

Args:
: path: The path to the file.

Returns:
: The size of the file in bytes.

#### *abstract static* stat(path: bytes | str) → Any

Get the stat descriptor for a given file path.

Args:
: path: The path to the file.

Returns:
: The stat descriptor.

#### *abstract static* walk(top: bytes | str, topdown: bool = True, onerror: Callable[[...], None] | None = None) → Iterable[Tuple[bytes | str, List[bytes | str], List[bytes | str]]]

Return an iterator that walks the contents of the given directory.

Args:
: top: The path of directory to walk.
  topdown: Whether to walk directories topdown or bottom-up.
  onerror: Callable that gets called if an error occurs.

Returns:
: An Iterable of Tuples, each of which contain the path of the current
  directory path, a list of directories inside the current directory
  and a list of files inside the current directory.

## zenml.io.filesystem_registry module

Filesystem registry managing filesystem plugins.

### *class* zenml.io.filesystem_registry.FileIORegistry

Bases: `object`

Registry of pluggable filesystem implementations.

#### get_filesystem_for_path(path: PathType) → Type[[BaseFilesystem](#zenml.io.filesystem.BaseFilesystem)]

Get filesystem plugin for given path.

Args:
: path: The path to get the filesystem for.

Returns:
: The filesystem plugin for the given path.

Raises:
: ValueError: If no filesystem plugin is registered for the given
  : path.

#### get_filesystem_for_scheme(scheme: PathType) → Type[[BaseFilesystem](#zenml.io.filesystem.BaseFilesystem)]

Get filesystem plugin for given scheme string.

Args:
: scheme: The scheme to get the filesystem for.

Returns:
: The filesystem plugin for the given scheme.

Raises:
: ValueError: If no filesystem plugin is registered for the given
  : scheme.

#### register(filesystem_cls: Type[[BaseFilesystem](#zenml.io.filesystem.BaseFilesystem)]) → None

Register a filesystem implementation.

Args:
: filesystem_cls: Subclass of zenml.io.filesystem.Filesystem.

## zenml.io.local_filesystem module

Local filesystem using Python’s built-in modules (os, shutil, glob).

### *class* zenml.io.local_filesystem.LocalFilesystem

Bases: [`BaseFilesystem`](#zenml.io.filesystem.BaseFilesystem)

Filesystem that uses local file operations.

Implementation inspired by TFX:
[https://github.com/tensorflow/tfx/blob/master/tfx/dsl/io/plugins/local.py](https://github.com/tensorflow/tfx/blob/master/tfx/dsl/io/plugins/local.py)

#### SUPPORTED_SCHEMES *: ClassVar[Set[str]]* *= {''}*

#### *static* copyfile(src: bytes | str, dst: bytes | str, overwrite: bool = False) → None

Copy a file from the source to the destination.

Args:
: src: The source path.
  dst: The destination path.
  overwrite: Whether to overwrite the destination file if it exists.

Raises:
: FileExistsError: If the destination file exists and overwrite is
  : False.

#### *static* exists(path: bytes | str) → bool

Returns True if the given path exists.

Args:
: path: The path to check.

Returns:
: bool: Whether the path exists.

#### *static* glob(pattern: bytes | str) → List[bytes | str]

Return the paths that match a glob pattern.

Args:
: pattern: The glob pattern.

Returns:
: List[PathType]: The paths that match the glob pattern.

#### *static* isdir(path: bytes | str) → bool

Returns whether the given path points to a directory.

Args:
: path: The path to check.

Returns:
: bool: Whether the path points to a directory.

#### *static* listdir(path: bytes | str) → List[bytes | str]

Returns a list of files under a given directory in the filesystem.

Args:
: path: The path to the directory.

Returns:
: List[PathType]: The list of files under the given directory.

#### *static* makedirs(path: bytes | str) → None

Make a directory at the given path, recursively creating parents.

Args:
: path: The path to the directory.

#### *static* mkdir(path: bytes | str) → None

Make a directory at the given path; parent directory must exist.

Args:
: path: The path to the directory.

#### *static* open(name: bytes | str, mode: str = 'r') → Any

Open a file at the given path.

Args:
: name: The path to the file.
  mode: The mode to open the file.

Returns:
: Any: The file object.

#### *static* remove(path: bytes | str) → None

Remove the file at the given path. Dangerous operation.

Args:
: path: The path to the file.

#### *static* rename(src: bytes | str, dst: bytes | str, overwrite: bool = False) → None

Rename source file to destination file.

Args:
: src: The path of the file to rename.
  dst: The path to rename the source file to.
  overwrite: If a file already exists at the destination, this
  <br/>
  > method will overwrite it if overwrite=\`True\`

Raises:
: FileExistsError: If the destination file exists and overwrite is
  : False.

#### *static* rmtree(path: bytes | str) → None

Deletes dir recursively. Dangerous operation.

Args:
: path: The path to the directory.

#### *static* size(path: bytes | str) → int

Get the size of a file in bytes.

Args:
: path: The path to the file.

Returns:
: The size of the file in bytes.

#### *static* stat(path: bytes | str) → Any

Return the stat descriptor for a given file path.

Args:
: path: The path to the file.

Returns:
: Any: The stat descriptor for the file.

#### *static* walk(top: bytes | str, topdown: bool = True, onerror: Callable[[...], None] | None = None) → Iterable[Tuple[bytes | str, List[bytes | str], List[bytes | str]]]

Return an iterator that walks the contents of the given directory.

Args:
: top: Path of directory to walk.
  topdown: Whether to walk directories topdown or bottom-up.
  onerror: Callable that gets called if an error occurs.

Yields:
: An Iterable of Tuples, each of which contain the path of the
  current directory path, a list of directories inside the
  current directory and a list of files inside the current
  directory.

## Module contents

The io module handles file operations for the ZenML package.

It offers a standard interface for reading, writing and manipulating files and
directories. It is heavily influenced and inspired by the io module of tfx.
