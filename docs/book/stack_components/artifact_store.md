---
description: Setting up the storage for your artifacts
---

In ZenML, the inputs and outputs which go through any step is treated as an
artifact and as its name suggests, an `ArtifactStore` is a place where these
artifacts get stored.

{% hint style="warning" %}
Before reading this chapter, make sure that you are familiar with the 
concept of [stacks, stack components and their flavors](./introduction.md).  
{% endhint %}

## Base Abstraction

The artifact store establishes one of the main components in every ZenML stack.
Now, let us take a deeper dive into the fundamentals behind its abstraction,
namely the `BaseArtifactStore`:

1. As it is the base class for a specific type of StackComponent,
    it inherits from the StackComponent class. This sets the `TYPE`
    variable to a StackComponentType. The `FLAVOR` class variable needs to be 
    set in the specific subclass.
2. As ZenML only supports filesystem-based artifact stores, it features an 
    instance configuration parameter called `path`, which will indicate the 
    root path of the artifact store. When creating an instance of any flavor of 
    an `ArtifactStore`, the users will have to define this parameter.
3. Moreover, there is an empty class variable called `SUPPORTED_SCHEMES` that 
    needs to be defined by every flavor implementation. It indicates the 
    supported filepath schemes for the corresponding implementation.
    For instance, for the Azure artifact store, this set will be defined as
    `{"abfs://", "az://"}`.
4. Lastly, the base class features a set of `abstractmethod`s: `open`,
   `copyfile`,`exists`,`glob`,`isdir`,`listdir`,`makedirs`,`mkdir`,`remove`,
   `rename`,`rmtree`,`stat`,`walk`. In the implementation of every 
   `ArtifactStore` flavor, it is required to define these methods with respect 
    to the flavor at hand.

Putting all these considerations together, we end up with the following 
implementation:

```python
from zenml.enums import StackComponentType
from zenml.stack import StackComponent

PathType = Union[bytes, str]

class BaseArtifactStore(StackComponent):
    """Base class for all ZenML artifact stores."""

    # --- Instance configuration ---
    path: str  # The root path of the artifact store.

    # --- Class variables ---
    TYPE: ClassVar[StackComponentType] = StackComponentType.ARTIFACT_STORE
    SUPPORTED_SCHEMES: ClassVar[Set[str]]

    # --- User interface ---
    @abstractmethod
    def open(self, name: PathType, mode: str = "r") -> Any:
        """Open a file at the given path."""

    @abstractmethod
    def copyfile(
        self, src: PathType, dst: PathType, overwrite: bool = False
    ) -> None:
        """Copy a file from the source to the destination."""

    @abstractmethod
    def exists(self, path: PathType) -> bool:
        """Returns `True` if the given path exists."""

    @abstractmethod
    def glob(self, pattern: PathType) -> List[PathType]:
        """Return the paths that match a glob pattern."""

    @abstractmethod
    def isdir(self, path: PathType) -> bool:
        """Returns whether the given path points to a directory."""

    @abstractmethod
    def listdir(self, path: PathType) -> List[PathType]:
        """Returns a list of files under a given directory in the filesystem."""

    @abstractmethod
    def makedirs(self, path: PathType) -> None:
        """Make a directory at the given path, recursively creating parents."""

    @abstractmethod
    def mkdir(self, path: PathType) -> None:
        """Make a directory at the given path; parent directory must exist."""

    @abstractmethod
    def remove(self, path: PathType) -> None:
        """Remove the file at the given path. Dangerous operation."""

    @abstractmethod
    def rename(
        self, src: PathType, dst: PathType, overwrite: bool = False
    ) -> None:
        """Rename source file to destination file."""

    @abstractmethod
    def rmtree(self, path: PathType) -> None:
        """Deletes dir recursively. Dangerous operation."""

    @abstractmethod
    def stat(self, path: PathType) -> Any:
        """Return the stat descriptor for a given file path."""

    @abstractmethod
    def walk(
        self,
        top: PathType,
        topdown: bool = True,
        onerror: Optional[Callable[..., None]] = None,
    ) -> Iterable[Tuple[PathType, List[PathType], List[PathType]]]:
        """Return an iterator that walks the contents of the given directory."""
```

{% hint style="warning" %}
This is a slimmed-down version of the base implementation which aims to 
highlight the abstraction layer. In order to see the full implementation 
and get the complete docstrings, please check the source code on GitHub.
{% endhint %}

description: <!--- TODO: Short description about fileio --->

## List of available artifact stores

Out of the box, ZenML comes with a `LocalArtifactStore` implementation, which 
is a simple implementation for a local setup.

Moreover, additional artifact stores can be found in specific `integration`
modules, such as the `GCPArtifactStore` in the `gcp` integration and the
`AzureArtifactStore` in the `azure` integration.

|                     | Flavor | Integration |
|---------------------|--------|-------------|
| LocalArtifactStore  | local  | `built-in`  |
| S3ArtifactStore     | s3     | s3          |
| GCPArtifactStore    | gcp    | gcp         |
| AzureArtifactStore  | azure  | azure       |

If you would like to see the available flavors for artifact stores, you can 
use the command:

```shell
zenml artifact-store flavor list
```

## Build your own custom artifact store

If you want to create your own custom flavor for an artifact store, you can 
follow the following steps:

1. Create a class which inherits from the `BaseArtifactStore`.
2. Define the `FLAVOR` class variable.
3. Implement the `abstactmethod`s based on your desired filesystem.

Once you are done with the implementation, you can register it through the CLI 
as:

```shell
zenml artifact-store flavor register <THE-SOURCE-PATH-OF-YOUR-ARTIFACT-STORE>
```
